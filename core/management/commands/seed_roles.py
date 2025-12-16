from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group


class Command(BaseCommand):
    help = "Create default groups for IT AMS"

    def handle(self, *args, **options):
        groups = ["ADMIN", "IT", "MANAGER", "EMPLOYEE"]
        for g in groups:
            Group.objects.get_or_create(name=g)
        self.stdout.write(self.style.SUCCESS("✅ Groups created: " + ", ".join(groups)))
