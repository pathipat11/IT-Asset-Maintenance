from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import ListView, View
from .models import Notification

class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = "core/notifications.html"
    context_object_name = "items"
    paginate_by = 20

    def get_queryset(self):
        return (
            Notification.objects
            .filter(recipient_id=self.request.user.id)
            .order_by("-created_at")
        )


class NotificationMarkReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        Notification.objects.filter(pk=pk, recipient=request.user).update(is_read=True)
        return redirect("core:notifications")

class NotificationMarkAllReadView(LoginRequiredMixin, View):
    def post(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return redirect("core:notifications")
