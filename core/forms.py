from django import forms
from django.utils import timezone
from .models import Asset, Ticket, TicketAttachment, TicketComment, Part, PartStockMovement
from .permissions import is_it, is_manager


class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = [
            "asset_code", "serial_number", "category", "brand", "model_name",
            "status", "department", "owner", "location",
            "purchase_date", "warranty_end", "note",
        ]
        widgets = {
            "purchase_date": forms.DateInput(attrs={"type": "date"}),
            "warranty_end": forms.DateInput(attrs={"type": "date"}),
            "note": forms.Textarea(attrs={"rows": 3}),
        }


class TicketForm(forms.ModelForm):
    """
    Role policy:
    - EMPLOYEE: create/update เฉพาะ subject/description/priority/asset (requested_by ถูก set อัตโนมัติ)
    - MANAGER/IT/ADMIN: เห็นทุกฟิลด์และแก้ได้
    """
    class Meta:
        model = Ticket
        fields = [
            "asset", "subject", "description",
            "priority", "status",
            "assigned_to",
            "vendor", "cost",
            "sla_hours", "due_at",
            "started_at", "resolved_at", "closed_at",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "due_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "started_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "resolved_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "closed_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        # ให้เลือกเฉพาะ asset ที่มีจริง และ sort
        self.fields["asset"].queryset = Asset.objects.all().order_by("asset_code")

        # ถ้าไม่ใช่ IT/Manager → ซ่อนฟิลด์ admin-like
        if user and not (is_it(user) or is_manager(user)):
            allow = {"asset", "subject", "description", "priority"}
            for f in list(self.fields.keys()):
                if f not in allow:
                    self.fields.pop(f)

        # เพิ่ม class bootstrap ให้ฟอร์มดูดี
        for name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.EmailInput, forms.NumberInput,
                                        forms.Select, forms.Textarea, forms.DateInput, forms.DateTimeInput)):
                existing = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = (existing + " form-control").strip()
            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"


class TicketAttachmentForm(forms.ModelForm):
    class Meta:
        model = TicketAttachment
        fields = ["file"]


class TicketCommentForm(forms.ModelForm):
    class Meta:
        model = TicketComment
        fields = ["message"]
        widgets = {"message": forms.Textarea(attrs={"rows": 2, "placeholder": "Add a comment..."})}

class PartForm(forms.ModelForm):
    class Meta:
        model = Part
        fields = ["sku", "name", "vendor", "unit", "unit_cost", "low_stock_threshold"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.NumberInput, forms.Select)):
                field.widget.attrs["class"] = "form-control"
            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"


class StockMovementForm(forms.ModelForm):
    class Meta:
        model = PartStockMovement
        fields = ["movement_type", "qty", "ref_ticket", "note"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        self.fields["movement_type"].widget.attrs["class"] = "form-select"
        self.fields["qty"].widget.attrs["class"] = "form-control"
        self.fields["ref_ticket"].widget.attrs["class"] = "form-select"
        self.fields["note"].widget.attrs["class"] = "form-control"

        # จำกัด movement_type ให้ใช้แค่ IN/OUT ใน UI ก่อน (ปรับง่ายสุด)
        self.fields["movement_type"].choices = [("IN", "Stock In"), ("OUT", "Stock Out")]

        self.fields["ref_ticket"].queryset = Ticket.objects.all().order_by("-created_at")[:200]
        self.fields["ref_ticket"].required = False

class TicketUsePartForm(forms.Form):
    part = forms.ModelChoiceField(queryset=Part.objects.all().order_by("sku"))
    qty = forms.IntegerField(min_value=1)
    note = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["part"].widget.attrs["class"] = "form-select"
        self.fields["qty"].widget.attrs["class"] = "form-control"
        self.fields["note"].widget.attrs["class"] = "form-control"
        self.fields["note"].widget.attrs["placeholder"] = "Optional note (e.g. replaced RAM)"
