from django.conf import settings
from django.db import models, transaction
from django.db.models import Max, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User


# -----------------------
# Master data
# -----------------------
class Department(models.Model):
    name = models.CharField(max_length=120, unique=True)

    def __str__(self):
        return self.name


class Location(models.Model):
    name = models.CharField(max_length=120)
    detail = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        unique_together = ("name", "detail")

    def __str__(self):
        return f"{self.name} {('- ' + self.detail) if self.detail else ''}".strip()


class Vendor(models.Model):
    name = models.CharField(max_length=160, unique=True)
    phone = models.CharField(max_length=60, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    address = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class AssetCategory(models.Model):
    name = models.CharField(max_length=120, unique=True)

    def __str__(self):
        return self.name


# -----------------------
# Asset
# -----------------------
class Asset(models.Model):
    class Status(models.TextChoices):
        IN_USE = "IN_USE", "In use"
        IN_STOCK = "IN_STOCK", "In stock"
        REPAIR = "REPAIR", "Repairing"
        RETIRED = "RETIRED", "Retired"
        LOST = "LOST", "Lost"

    asset_code = models.CharField(max_length=30, unique=True)  # เช่น IT-000123
    serial_number = models.CharField(max_length=100, blank=True, default="")
    category = models.ForeignKey(AssetCategory, on_delete=models.PROTECT)
    brand = models.CharField(max_length=80, blank=True, default="")
    model_name = models.CharField(max_length=120, blank=True, default="")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_USE)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, null=True, blank=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assets_owned",
    )

    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    warranty_end = models.DateField(null=True, blank=True)
    note = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["asset_code"]

    def __str__(self):
        return f"{self.asset_code} ({self.category})"


# -----------------------
# Parts / Stock
# -----------------------
class Part(models.Model):
    name = models.CharField(max_length=160)
    sku = models.CharField(max_length=80, unique=True)  # รหัสอะไหล่
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True, blank=True)
    unit = models.CharField(max_length=30, default="pcs")
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    low_stock_threshold = models.PositiveIntegerField(default=0)

    def stock_in_total(self):
        return self.movements.filter(movement_type="IN").aggregate(
            s=Coalesce(Sum("qty"), 0)
        )["s"]

    def stock_out_total(self):
        return self.movements.filter(movement_type="OUT").aggregate(
            s=Coalesce(Sum("qty"), 0)
        )["s"]

    def stock_balance(self):
        return int(self.stock_in_total() - self.stock_out_total())

    def stock_value(self):
        return self.stock_balance() * float(self.unit_cost)


    def __str__(self):
        return f"{self.sku} - {self.name}"


class PartStockMovement(models.Model):
    class Type(models.TextChoices):
        IN = "IN", "Stock In"
        OUT = "OUT", "Stock Out"
        ADJUST = "ADJUST", "Adjust"

    part = models.ForeignKey(Part, on_delete=models.PROTECT, related_name="movements")
    movement_type = models.CharField(max_length=10, choices=Type.choices)
    qty = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    ref_ticket = models.ForeignKey("Ticket", on_delete=models.SET_NULL, null=True, blank=True)
    note = models.CharField(max_length=255, blank=True, default="")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
    
    def clean(self):
        super().clean()
        # กัน OUT เกิน balance
        if self.movement_type == self.Type.OUT:
            current_balance = self.part.stock_balance()

            # ถ้าเป็นการแก้ไข movement เดิม ต้องบวก qty เดิมคืนก่อนคำนวณ
            if self.pk:
                old = PartStockMovement.objects.get(pk=self.pk)
                if old.movement_type == self.Type.OUT:
                    current_balance += old.qty
                elif old.movement_type == self.Type.IN:
                    current_balance -= old.qty

            if self.qty > current_balance:
                raise ValidationError(
                    {"qty": f"Not enough stock. Current balance = {current_balance}"}
                )

    def save(self, *args, **kwargs):
        self.full_clean()  # เรียก clean() ทุกครั้ง
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.part.sku} {self.movement_type} {self.qty}"


# -----------------------
# Maintenance Ticket
# -----------------------
class Ticket(models.Model):
    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    class Status(models.TextChoices):
        NEW = "NEW", "New"
        ASSIGNED = "ASSIGNED", "Assigned"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        DONE = "DONE", "Done"
        CLOSED = "CLOSED", "Closed"
        CANCELED = "CANCELED", "Canceled"

    ticket_no = models.CharField(max_length=30, unique=True, editable=False)  # TCK-20251216-00001

    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="tickets")
    subject = models.CharField(max_length=160)
    description = models.TextField()

    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="tickets_requested",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets_assigned",
    )

    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True, blank=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # SLA
    sla_hours = models.PositiveIntegerField(default=48)
    due_at = models.DateTimeField(null=True, blank=True)

    started_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def _generate_ticket_no(self) -> str:
        # TCK-YYYYMMDD-00001
        today = timezone.localdate()
        prefix = f"TCK-{today.strftime('%Y%m%d')}-"

        last = (
            Ticket.objects.filter(ticket_no__startswith=prefix)
            .aggregate(mx=Max("ticket_no"))
            .get("mx")
        )
        if not last:
            seq = 1
        else:
            seq = int(last.split("-")[-1]) + 1

        return f"{prefix}{seq:05d}"

    def save(self, *args, **kwargs):
        creating = self.pk is None
        if creating:
            if not self.due_at:
                self.due_at = timezone.now() + timezone.timedelta(hours=self.sla_hours)

            # ปลอดภัยกับ concurrent create
            with transaction.atomic():
                if not self.ticket_no:
                    self.ticket_no = self._generate_ticket_no()
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def is_overdue(self) -> bool:
        if self.status in {self.Status.DONE, self.Status.CLOSED, self.Status.CANCELED}:
            return False
        return bool(self.due_at and timezone.now() > self.due_at)

    def __str__(self):
        return self.ticket_no


def ticket_attachment_path(instance, filename):
    return f"tickets/{instance.ticket.id}/{filename}"


class TicketAttachment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to=ticket_attachment_path)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class TicketComment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="comments")
    message = models.TextField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


# -----------------------
# Audit Log (เบา ๆ)
# -----------------------
class AuditLog(models.Model):
    action = models.CharField(max_length=60)  # CREATE_ASSET, UPDATE_TICKET, ...
    object_type = models.CharField(max_length=60)  # Asset/Ticket/Part
    object_id = models.CharField(max_length=60)
    summary = models.CharField(max_length=255, blank=True, default="")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} {self.object_type}:{self.object_id}"

class Notification(models.Model):
    class Type(models.TextChoices):
        TICKET_NEW = "TICKET_NEW", "New Ticket"
        TICKET_UPDATE = "TICKET_UPDATE", "Ticket Updated"
        TICKET_CLOSED = "TICKET_CLOSED", "Ticket Closed"
        LOW_STOCK = "LOW_STOCK", "Low Stock"

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    ntype = models.CharField(max_length=32, choices=Type.choices)
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True, default="")
    url = models.CharField(max_length=300, blank=True, default="")
    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]