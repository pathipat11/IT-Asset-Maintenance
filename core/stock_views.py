from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, Q
from django.shortcuts import redirect
from django.utils import timezone
from decimal import Decimal
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView

from .forms import PartForm, StockMovementForm
from .models import Part, PartStockMovement, AuditLog
from .querysets import parts_with_balance_qs
from .permissions import GroupRequiredMixin, is_it, is_manager


class PartListView(LoginRequiredMixin, GroupRequiredMixin, ListView):
    required_groups = ["ADMIN", "IT", "MANAGER"]
    model = Part
    template_name = "core/part_list.html"
    context_object_name = "parts"
    paginate_by = 10

    def get_queryset(self):
        qs = parts_with_balance_qs(Part).order_by("sku")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(sku__icontains=q) | Q(name__icontains=q))
        return qs


class PartDetailView(LoginRequiredMixin, GroupRequiredMixin, DetailView):
    required_groups = ["ADMIN", "IT", "MANAGER"]
    model = Part
    template_name = "core/part_detail.html"
    context_object_name = "part"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        part = self.object
        ctx["balance"] = part.stock_balance()
        ctx["in_total"] = part.stock_in_total()
        ctx["out_total"] = part.stock_out_total()

        ctx["can_move_stock"] = is_it(self.request.user)
        ctx["movement_form"] = StockMovementForm(user=self.request.user)
        ctx["movements"] = part.movements.select_related("created_by", "ref_ticket").all()[:50]
        return ctx

    def post(self, request, *args, **kwargs):
        part = self.get_object()

        # เฉพาะ IT/Admin เท่านั้นที่ทำ stock movement ได้
        if not is_it(request.user):
            return redirect("core:part_detail", pk=part.pk)

        form = StockMovementForm(request.POST, user=request.user)
        if form.is_valid():
            mv = form.save(commit=False)
            mv.part = part
            mv.created_by = request.user
            mv.save()

            AuditLog.objects.create(
                action="STOCK_MOVEMENT",
                object_type="Part",
                object_id=str(part.id),
                summary=f"{part.sku} {mv.movement_type} {mv.qty}",
                created_by=request.user,
            )
            messages.success(request, "Stock movement saved")
        else:
            messages.error(request, "Invalid movement data")

        return redirect("core:part_detail", pk=part.pk)


class PartCreateView(LoginRequiredMixin, GroupRequiredMixin, CreateView):
    required_groups = ["ADMIN", "IT"]
    model = Part
    form_class = PartForm
    template_name = "core/part_form.html"
    success_url = reverse_lazy("core:part_list")

    def form_valid(self, form):
        res = super().form_valid(form)
        AuditLog.objects.create(
            action="CREATE_PART",
            object_type="Part",
            object_id=str(self.object.id),
            summary=f"{self.object.sku}",
            created_by=self.request.user,
        )
        messages.success(self.request, "Part created")
        return res


class PartUpdateView(LoginRequiredMixin, GroupRequiredMixin, UpdateView):
    required_groups = ["ADMIN", "IT"]
    model = Part
    form_class = PartForm
    template_name = "core/part_form.html"

    def get_success_url(self):
        return reverse_lazy("core:part_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        res = super().form_valid(form)
        AuditLog.objects.create(
            action="UPDATE_PART",
            object_type="Part",
            object_id=str(self.object.id),
            summary=f"{self.object.sku}",
            created_by=self.request.user,
        )
        messages.success(self.request, "Part updated")
        return res


class PartDeleteView(LoginRequiredMixin, GroupRequiredMixin, DeleteView):
    required_groups = ["ADMIN", "IT"]
    model = Part
    template_name = "core/confirm_delete.html"
    success_url = reverse_lazy("core:part_list")

class LowStockListView(LoginRequiredMixin, GroupRequiredMixin, ListView):
    required_groups = ["ADMIN", "IT", "MANAGER"]
    template_name = "core/low_stock.html"
    context_object_name = "parts"
    paginate_by = 20

    def get_queryset(self):
        qs = parts_with_balance_qs(Part).order_by("sku")
        # balance <= threshold
        return qs.filter(balance__lte=F("low_stock_threshold"))

class MovementHistoryView(LoginRequiredMixin, GroupRequiredMixin, ListView):
    required_groups = ["ADMIN", "IT", "MANAGER"]
    model = PartStockMovement
    template_name = "core/movement_history.html"
    context_object_name = "movements"
    paginate_by = 25

    def get_queryset(self):
        qs = (
            PartStockMovement.objects
            .select_related("part", "ref_ticket", "created_by")
            .order_by("-created_at")
        )

        q = self.request.GET.get("q", "").strip()
        mtype = self.request.GET.get("type", "").strip()     # IN/OUT
        part = self.request.GET.get("part", "").strip()      # sku contains
        ticket = self.request.GET.get("ticket", "").strip()  # ticket_no contains
        date_from = self.request.GET.get("from", "").strip() # YYYY-MM-DD
        date_to = self.request.GET.get("to", "").strip()     # YYYY-MM-DD

        if q:
            qs = qs.filter(
                Q(part__sku__icontains=q) |
                Q(part__name__icontains=q) |
                Q(note__icontains=q) |
                Q(ref_ticket__ticket_no__icontains=q)
            )
        if mtype in ["IN", "OUT"]:
            qs = qs.filter(movement_type=mtype)
        if part:
            qs = qs.filter(Q(part__sku__icontains=part) | Q(part__name__icontains=part))
        if ticket:
            qs = qs.filter(ref_ticket__ticket_no__icontains=ticket)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        return qs

class StockReportView(LoginRequiredMixin, GroupRequiredMixin, TemplateView):
    required_groups = ["ADMIN", "IT", "MANAGER"]
    template_name = "core/stock_report.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        parts = parts_with_balance_qs(Part).order_by("sku")

        total_value = Decimal("0")
        low_count = 0
        items = []

        for p in parts:
            # p.balance มาจาก DB
            value = Decimal(p.balance) * p.unit_cost
            total_value += value
            if p.balance <= p.low_stock_threshold:
                low_count += 1
            items.append((p, value))

        items.sort(key=lambda x: x[1], reverse=True)

        ctx["total_parts"] = parts.count()
        ctx["low_count"] = low_count
        ctx["total_value"] = total_value
        ctx["top_value_parts"] = items[:10]
        return ctx