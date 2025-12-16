from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
)

from .permissions import GroupRequiredMixin, is_it, is_manager
from .forms import AssetForm, TicketForm, TicketAttachmentForm, TicketCommentForm, TicketUsePartForm
from .models import Asset, Ticket, TicketAttachment, TicketComment, AuditLog, PartStockMovement
from .sla import get_sla_hours, calc_due_at
from .notify import notify_it, notify_users
from .models import Notification

class HomeRedirectView(View):
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if request.user.is_superuser or is_it(request.user) or is_manager(request.user):
            return redirect("core:dashboard")
        return redirect("core:ticket_list")

class DashboardView(LoginRequiredMixin, GroupRequiredMixin, TemplateView):
    template_name = "core/dashboard.html"
    required_groups = ["ADMIN", "IT", "MANAGER"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        now = timezone.now()
        active_status = ["NEW", "ASSIGNED", "IN_PROGRESS"]

        ctx["open_tickets"] = Ticket.objects.filter(status__in=active_status).count()
        ctx["overdue_tickets"] = Ticket.objects.filter(status__in=active_status, due_at__lt=now).count()
        ctx["assets_total"] = Asset.objects.count()
        ctx["cost_month"] = Ticket.objects.filter(cost__isnull=False).aggregate(s=Sum("cost"))["s"] or 0

        ctx["top_assets"] = (
            Asset.objects.annotate(ticket_count=Count("tickets"))
            .order_by("-ticket_count")[:5]
        )
        return ctx


# -----------------------
# Asset CRUD
# -----------------------
class AssetListView(LoginRequiredMixin, ListView):
    model = Asset
    template_name = "core/asset_list.html"
    context_object_name = "assets"
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset().select_related("category", "department", "owner", "location")
        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "").strip()
        if q:
            qs = qs.filter(asset_code__icontains=q) | qs.filter(serial_number__icontains=q)
        if status:
            qs = qs.filter(status=status)
        return qs


class AssetDetailView(LoginRequiredMixin, DetailView):
    model = Asset
    template_name = "core/asset_detail.html"
    context_object_name = "asset"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["assign_logs"] = self.object.assign_logs.select_related(
            "old_owner", "new_owner", "changed_by"
        )[:20]
        return ctx



class AssetCreateView(LoginRequiredMixin, GroupRequiredMixin, CreateView):
    model = Asset
    form_class = AssetForm
    template_name = "core/asset_form.html"
    success_url = reverse_lazy("core:asset_list")

    def form_valid(self, form):
        res = super().form_valid(form)
        AuditLog.objects.create(
            action="CREATE_ASSET",
            object_type="Asset",
            object_id=str(self.object.id),
            summary=f"{self.object.asset_code}",
            created_by=self.request.user,
        )
        return res


class AssetUpdateView(LoginRequiredMixin, GroupRequiredMixin, UpdateView):
    model = Asset
    form_class = AssetForm
    template_name = "core/asset_form.html"

    def get_success_url(self):
        return reverse_lazy("core:asset_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj._changed_by = self.request.user
        obj.save()
        form.save_m2m()
        self.object = obj

        AuditLog.objects.create(
            action="UPDATE_ASSET",
            object_type="Asset",
            object_id=str(self.object.id),
            summary=f"{self.object.asset_code}",
            created_by=self.request.user,
        )
        return redirect("core:asset_detail", pk=self.object.pk)



class AssetDeleteView(LoginRequiredMixin, GroupRequiredMixin, DeleteView):
    required_groups = ["ADMIN", "IT"]
    model = Asset
    template_name = "core/confirm_delete.html"
    success_url = reverse_lazy("core:asset_list")

# -----------------------
# Ticket CRUD
# -----------------------
class TicketListView(LoginRequiredMixin, ListView):
    model = Ticket
    template_name = "core/ticket_list.html"
    context_object_name = "tickets"
    paginate_by = 10

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["now"] = timezone.now()
        return ctx
    
    def get_queryset(self):
        qs = (
            Ticket.objects
            .select_related("asset", "assigned_to", "requested_by", "vendor")
            .all()
            .order_by("-created_at")
        )

        u = self.request.user

        if not (is_it(u) or is_manager(u) or u.is_superuser):
            qs = qs.filter(requested_by=u)

        q = (self.request.GET.get("q") or "").strip()
        status = (self.request.GET.get("status") or "").strip()
        mine = (self.request.GET.get("mine") or "").strip()
        overdue = (self.request.GET.get("overdue") or "").strip()

        if q:
            qs = qs.filter(
                Q(ticket_no__icontains=q)
                | Q(subject__icontains=q)
                | Q(asset__asset_code__icontains=q)
            )

        if status:
            qs = qs.filter(status=status)

        if mine == "1":
            qs = qs.filter(assigned_to=u)

        if overdue == "1":
            now = timezone.now()
            qs = qs.filter(status__in=["NEW", "ASSIGNED", "IN_PROGRESS"], due_at__lt=now)

        return qs
    


class TicketDetailView(LoginRequiredMixin, DetailView):
    model = Ticket
    template_name = "core/ticket_detail.html"
    context_object_name = "ticket"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["attach_form"] = TicketAttachmentForm()
        ctx["comment_form"] = TicketCommentForm()
        ctx["use_part_form"] = TicketUsePartForm()
        ctx["used_parts"] = PartStockMovement.objects.filter(
            ref_ticket=self.object, movement_type="OUT"
        ).select_related("part", "created_by").order_by("-created_at")[:50]
        ctx["now"] = timezone.now()
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        # upload file
        if "upload_file" in request.POST:
            form = TicketAttachmentForm(request.POST, request.FILES)
            if form.is_valid():
                att = form.save(commit=False)
                att.ticket = self.object
                att.uploaded_by = request.user
                att.save()
                AuditLog.objects.create(
                    action="UPLOAD_TICKET_FILE",
                    object_type="Ticket",
                    object_id=str(self.object.id),
                    summary=self.object.ticket_no,
                    created_by=request.user,
                )
            return redirect("core:ticket_detail", pk=self.object.pk)

        # add comment
        if "add_comment" in request.POST:
            form = TicketCommentForm(request.POST)
            if form.is_valid():
                c = form.save(commit=False)
                c.ticket = self.object
                c.created_by = request.user
                c.save()
                AuditLog.objects.create(
                    action="ADD_TICKET_COMMENT",
                    object_type="Ticket",
                    object_id=str(self.object.id),
                    summary=self.object.ticket_no,
                    created_by=request.user,
                )
            return redirect("core:ticket_detail", pk=self.object.pk)

        # use part (Stock OUT)
        if "use_part" in request.POST:
            if not is_it(request.user):
                messages.error(request, "Only IT/Admin can use parts.")
                return redirect("core:ticket_detail", pk=self.object.pk)

            form = TicketUsePartForm(request.POST)
            if form.is_valid():
                part = form.cleaned_data["part"]
                qty = form.cleaned_data["qty"]
                note = form.cleaned_data.get("note", "")

                try:
                    PartStockMovement.objects.create(
                        part=part,
                        movement_type="OUT",
                        qty=qty,
                        ref_ticket=self.object,
                        note=note,
                        created_by=request.user,
                    )
                    AuditLog.objects.create(
                        action="USE_PART_FOR_TICKET",
                        object_type="Ticket",
                        object_id=str(self.object.id),
                        summary=f"{self.object.ticket_no} OUT {part.sku} x{qty}",
                        created_by=request.user,
                    )
                    messages.success(request, f"Used {part.sku} x{qty}")
                except Exception as e:
                    # ถ้า OUT เกิน balance จะโดน ValidationError จาก model
                    messages.error(request, f"Cannot use part: {e}")

            else:
                messages.error(request, "Invalid part usage form")

            return redirect("core:ticket_detail", pk=self.object.pk)

        return redirect("core:ticket_detail", pk=self.object.pk)



class TicketCreateView(LoginRequiredMixin, CreateView):
    model = Ticket
    form_class = TicketForm
    template_name = "core/ticket_form.html"
    success_url = reverse_lazy("core:ticket_list")

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["user"] = self.request.user
        return kw

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.requested_by = self.request.user

        obj.status = Ticket.Status.NEW

        now = timezone.now()
        sla = getattr(obj, "sla_hours", None)
        if not sla:
            obj.sla_hours = get_sla_hours(obj.priority)
        if not obj.due_at:
            obj.due_at = calc_due_at(now, obj.sla_hours)

        obj.save()
        notify_it(
            Notification.Type.TICKET_NEW,
            title=f"New Ticket: {obj.ticket_no}",
            message=obj.subject,
            url=f"/tickets/{obj.pk}/",
        )
        self.object = obj

        AuditLog.objects.create(
            action="CREATE_TICKET",
            object_type="Ticket",
            object_id=str(self.object.id),
            summary=self.object.ticket_no,
            created_by=self.request.user,
        )
        messages.success(self.request, "Ticket created")
        return redirect("core:ticket_detail", pk=self.object.pk)



class TicketUpdateView(LoginRequiredMixin, GroupRequiredMixin, UpdateView):
    required_groups = ["ADMIN", "IT", "MANAGER"]
    model = Ticket
    form_class = TicketForm
    template_name = "core/ticket_form.html"

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["user"] = self.request.user
        return kw

    def get_success_url(self):
        return reverse_lazy("core:ticket_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        res = super().form_valid(form)
        AuditLog.objects.create(
            action="UPDATE_TICKET",
            object_type="Ticket",
            object_id=str(self.object.id),
            summary=self.object.ticket_no,
            created_by=self.request.user,
        )
        messages.success(self.request, "Ticket updated")
        return res


class TicketDeleteView(LoginRequiredMixin, GroupRequiredMixin, DeleteView):
    required_groups = ["ADMIN", "IT"]
    model = Ticket
    template_name = "core/confirm_delete.html"
    success_url = reverse_lazy("core:ticket_list")

class TicketActionBase(LoginRequiredMixin, GroupRequiredMixin):
    required_groups = ["ADMIN", "IT", "MANAGER"]

    def get_ticket(self, pk):
        return Ticket.objects.select_related("asset", "assigned_to", "requested_by").get(pk=pk)


class TicketAssignToMeView(TicketActionBase, TemplateView):
    template_name = "core/_noop.html"  # ไม่ต้องมีจริง (จะ redirect)

    def post(self, request, *args, **kwargs):
        t = self.get_ticket(kwargs["pk"])
        t.assigned_to = request.user
        if t.status == Ticket.Status.NEW:
            t.status = Ticket.Status.ASSIGNED
        t.save(update_fields=["assigned_to", "status", "updated_at"])

        AuditLog.objects.create(
            action="ASSIGN_TICKET_TO_ME",
            object_type="Ticket",
            object_id=str(t.id),
            summary=t.ticket_no,
            created_by=request.user,
        )
        messages.success(request, "Assigned to you")
        return redirect("core:ticket_detail", pk=t.pk)


class TicketStartView(TicketActionBase, TemplateView):
    template_name = "core/_noop.html"

    def post(self, request, *args, **kwargs):
        t = self.get_ticket(kwargs["pk"])
        if not t.assigned_to:
            t.assigned_to = request.user
        t.status = Ticket.Status.IN_PROGRESS
        if not t.started_at:
            t.started_at = timezone.now()
        t.save(update_fields=["assigned_to", "status", "started_at", "updated_at"])

        AuditLog.objects.create(
            action="START_TICKET",
            object_type="Ticket",
            object_id=str(t.id),
            summary=t.ticket_no,
            created_by=request.user,
        )
        messages.success(request, "Ticket started")
        return redirect("core:ticket_detail", pk=t.pk)


class TicketResolveView(TicketActionBase, TemplateView):
    template_name = "core/_noop.html"

    def post(self, request, *args, **kwargs):
        t = self.get_ticket(kwargs["pk"])
        t.status = Ticket.Status.DONE
        if not t.resolved_at:
            t.resolved_at = timezone.now()
        t.save(update_fields=["status", "resolved_at", "updated_at"])

        AuditLog.objects.create(
            action="RESOLVE_TICKET",
            object_type="Ticket",
            object_id=str(t.id),
            summary=t.ticket_no,
            created_by=request.user,
        )
        messages.success(request, "Ticket resolved (DONE)")
        return redirect("core:ticket_detail", pk=t.pk)


class TicketCloseView(TicketActionBase, TemplateView):
    template_name = "core/_noop.html"

    def post(self, request, *args, **kwargs):
        t = self.get_ticket(kwargs["pk"])
        t.status = Ticket.Status.CLOSED
        if not t.closed_at:
            t.closed_at = timezone.now()
        t.save(update_fields=["status", "closed_at", "updated_at"])

        AuditLog.objects.create(
            action="CLOSE_TICKET",
            object_type="Ticket",
            object_id=str(t.id),
            summary=t.ticket_no,
            created_by=request.user,
        )
        messages.success(request, "Ticket closed")
        return redirect("core:ticket_detail", pk=t.pk)
