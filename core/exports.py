import csv
from django.http import HttpResponse
from django.utils import timezone
from .models import Asset, Ticket, Part, PartStockMovement
from .permissions import is_it, is_manager


def export_assets_csv(request):
    if not (is_it(request.user) or is_manager(request.user)):
        return HttpResponse("Forbidden", status=403)

    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="assets_{timezone.now().date()}.csv"'
    w = csv.writer(resp)
    w.writerow(["asset_code", "category", "status", "serial_number", "owner", "department", "location", "updated_at"])

    for a in Asset.objects.select_related("category", "owner", "department", "location").all().order_by("asset_code"):
        w.writerow([
            a.asset_code,
            str(a.category),
            a.status,
            a.serial_number,
            getattr(a.owner, "username", ""),
            str(a.department) if a.department else "",
            str(a.location) if a.location else "",
            a.updated_at.isoformat(),
        ])
    return resp


def export_tickets_csv(request):
    if not (is_it(request.user) or is_manager(request.user)):
        return HttpResponse("Forbidden", status=403)

    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="tickets_{timezone.now().date()}.csv"'
    w = csv.writer(resp)
    w.writerow(["ticket_no", "asset_code", "subject", "status", "priority", "requested_by", "assigned_to", "due_at", "cost"])

    for t in Ticket.objects.select_related("asset", "requested_by", "assigned_to").all().order_by("-created_at"):
        w.writerow([
            t.ticket_no,
            t.asset.asset_code,
            t.subject,
            t.status,
            t.priority,
            getattr(t.requested_by, "username", ""),
            getattr(t.assigned_to, "username", ""),
            t.due_at.isoformat() if t.due_at else "",
            str(t.cost) if t.cost is not None else "",
        ])
    return resp

def export_parts_csv(request):
    if not (is_it(request.user) or is_manager(request.user)):
        return HttpResponse("Forbidden", status=403)

    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="parts_{timezone.now().date()}.csv"'
    w = csv.writer(resp)
    w.writerow(["sku", "name", "vendor", "unit", "unit_cost", "balance", "threshold"])

    for p in Part.objects.select_related("vendor").all().order_by("sku"):
        w.writerow([
            p.sku,
            p.name,
            str(p.vendor) if p.vendor else "",
            p.unit,
            str(p.unit_cost),
            p.stock_balance(),
            p.low_stock_threshold,
        ])
    return resp


def export_movements_csv(request):
    if not (is_it(request.user) or is_manager(request.user)):
        return HttpResponse("Forbidden", status=403)

    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="movements_{timezone.now().date()}.csv"'
    w = csv.writer(resp)
    w.writerow(["time", "part_sku", "type", "qty", "ticket_no", "by", "note"])

    qs = PartStockMovement.objects.select_related("part", "ref_ticket", "created_by").all().order_by("-created_at")[:5000]
    for m in qs:
        w.writerow([
            m.created_at.isoformat(),
            m.part.sku,
            m.movement_type,
            m.qty,
            m.ref_ticket.ticket_no if m.ref_ticket else "",
            getattr(m.created_by, "username", ""),
            m.note,
        ])
    return resp