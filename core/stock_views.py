from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect
from django.utils import timezone
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from .froms import PartForm, StockMovementForm
from .models import Part, PartStockMovement, AuditLog
from .permissions import GroupRequiredMixin, is_it, is_manager


class PartListView(LoginRequiredMixin, GroupRequiredMixin, ListView):
    required_groups = ["ADMIN", "IT", "MANAGER"]
    model = Part
    template_name = "core/part_list.html"
    context_object_name = "parts"
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset().select_related("vendor").order_by("sku")
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
    model = Part
    template_name = "core/low_stock.html"
    context_object_name = "parts"
    paginate_by = 20

    def get_queryset(self):
        # ดึงทั้งหมดแล้วคัดใน python (MVP ง่ายสุด)
        parts = Part.objects.select_related("vendor").order_by("sku")
        low = [p for p in parts if p.stock_balance() <= p.low_stock_threshold]
        return low