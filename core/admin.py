from django.contrib import admin
from .models import (
    Department, Location, Vendor, AssetCategory, Asset,
    Part, PartStockMovement,
    Ticket, TicketAttachment, TicketComment,
    AuditLog,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    search_fields = ["name", "detail"]


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ["name", "phone", "email", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "phone", "email"]


@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ["asset_code", "category", "status", "department", "owner", "location", "updated_at"]
    list_filter = ["status", "category", "department"]
    search_fields = ["asset_code", "serial_number", "brand", "model_name", "owner__username"]
    autocomplete_fields = ["owner"]
    ordering = ["asset_code"]


@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = ["sku", "name", "vendor", "unit", "low_stock_threshold"]
    search_fields = ["sku", "name"]
    list_filter = ["vendor"]


@admin.register(PartStockMovement)
class PartStockMovementAdmin(admin.ModelAdmin):
    list_display = ["part", "movement_type", "qty", "ref_ticket", "created_by", "created_at"]
    list_filter = ["movement_type", "created_at"]
    search_fields = ["part__sku", "part__name", "ref_ticket__ticket_no", "note"]
    autocomplete_fields = ["ref_ticket", "created_by"]


class TicketAttachmentInline(admin.TabularInline):
    model = TicketAttachment
    extra = 0


class TicketCommentInline(admin.TabularInline):
    model = TicketComment
    extra = 0


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ["ticket_no", "asset", "priority", "status", "assigned_to", "due_at", "created_at"]
    list_filter = ["priority", "status", "created_at"]
    search_fields = ["ticket_no", "asset__asset_code", "subject", "assigned_to__username"]
    autocomplete_fields = ["asset", "requested_by", "assigned_to", "vendor"]
    inlines = [TicketAttachmentInline, TicketCommentInline]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["action", "object_type", "object_id", "created_by", "created_at"]
    list_filter = ["action", "object_type", "created_at"]
    search_fields = ["action", "object_type", "object_id", "summary", "created_by__username"]
