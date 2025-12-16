from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import TemplateView

from .models import Ticket
from .permissions import is_it, is_manager


class MyDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "core/my_dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        u = self.request.user
        now = timezone.now()
        active_status = ["NEW", "ASSIGNED", "IN_PROGRESS"]

        # Employee เห็นเฉพาะของตัวเอง / IT+Manager เห็น "งานของฉัน" (assigned_to)
        if is_it(u) or is_manager(u) or u.is_superuser:
            base = Ticket.objects.filter(assigned_to=u)
            ctx["scope_title"] = "My Queue (Assigned to me)"
        else:
            base = Ticket.objects.filter(requested_by=u)
            ctx["scope_title"] = "My Tickets"

        ctx["count_open"] = base.filter(status__in=active_status).count()
        ctx["count_overdue"] = base.filter(status__in=active_status, due_at__lt=now).count()
        ctx["count_done"] = base.filter(status="DONE").count()
        ctx["count_closed"] = base.filter(status="CLOSED").count()

        ctx["due_soon"] = base.filter(
            status__in=active_status,
            due_at__gte=now,
            due_at__lte=now + timedelta(hours=24),
        ).select_related("asset").order_by("due_at")[:10]

        ctx["recent"] = base.select_related("asset").order_by("-created_at")[:10]
        return ctx
