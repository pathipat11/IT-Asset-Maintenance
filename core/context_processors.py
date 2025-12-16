from .models import Notification

def nav_permissions(request):
    user = request.user
    can_admin_area = False
    unread = 0

    if user.is_authenticated:
        from .permissions import is_it, is_manager
        can_admin_area = user.is_superuser or is_it(user) or is_manager(user)
        unread = Notification.objects.filter(recipient=user, is_read=False).count()

    return {"can_admin_area": can_admin_area, "unread_notifications": unread}
