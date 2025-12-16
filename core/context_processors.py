from .permissions import is_it, is_manager

def nav_permissions(request):
    user = request.user
    can_admin_area = False
    if user.is_authenticated:
        can_admin_area = user.is_superuser or is_it(user) or is_manager(user)

    return {
        "can_admin_area": can_admin_area,  # IT/Manager/Admin
        "is_authenticated": user.is_authenticated,
    }
