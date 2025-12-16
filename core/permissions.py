from django.contrib.auth.mixins import UserPassesTestMixin
from django.utils import timezone

def in_group(user, group_name: str) -> bool:
    return user.is_authenticated and user.groups.filter(name=group_name).exists()


def is_admin(user) -> bool:
    return user.is_superuser or in_group(user, "ADMIN")


def is_it(user) -> bool:
    return is_admin(user) or in_group(user, "IT")


def is_manager(user) -> bool:
    return is_admin(user) or in_group(user, "MANAGER")


def is_employee(user) -> bool:
    return user.is_authenticated  # ทุกคนที่ login ถือเป็น employee ได้


class GroupRequiredMixin(UserPassesTestMixin):
    required_groups: list[str] = []

    def test_func(self):
        u = self.request.user
        if u.is_superuser:
            return True
        if not u.is_authenticated:
            return False
        return any(u.groups.filter(name=g).exists() for g in self.required_groups)

def can_edit_ticket(user, ticket) -> bool:
    if not user.is_authenticated:
        return False

    if is_it(user) or is_manager(user) or user.is_superuser:
        return True

    if ticket.requested_by_id != user.id:
        return False

    if ticket.status in [ticket.Status.DONE, ticket.Status.CLOSED, ticket.Status.CANCELED]:
        return False

    return True