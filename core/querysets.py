from django.db.models import Sum, Case, When, IntegerField, Value, F
from django.db.models.functions import Coalesce

def parts_with_balance_qs(PartModel):
    """
    คืน queryset ของ Part ที่มี field เพิ่มชื่อ `balance`
    balance = sum(IN) - sum(OUT)
    """
    return (
        PartModel.objects.select_related("vendor")
        .annotate(
            in_qty=Coalesce(
                Sum(
                    Case(
                        When(movements__movement_type="IN", then=F("movements__qty")),
                        default=Value(0),
                        output_field=IntegerField(),
                    )
                ),
                0,
            ),
            out_qty=Coalesce(
                Sum(
                    Case(
                        When(movements__movement_type="OUT", then=F("movements__qty")),
                        default=Value(0),
                        output_field=IntegerField(),
                    )
                ),
                0,
            ),
        )
        .annotate(balance=F("in_qty") - F("out_qty"))
    )
