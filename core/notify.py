from django.contrib.auth.models import User, Group
from .models import Notification

def users_in_groups(group_names: list[str]):
    return User.objects.filter(groups__name__in=group_names, is_active=True).distinct()

def notify_users(users, ntype, title, message="", url=""):
    notis = []
    for u in users:
        notis.append(Notification(
            recipient=u, ntype=ntype, title=title, message=message, url=url
        ))
    Notification.objects.bulk_create(notis)

def notify_it(ntype, title, message="", url=""):
    users = users_in_groups(["ADMIN", "IT"])
    notify_users(users, ntype, title, message, url)
