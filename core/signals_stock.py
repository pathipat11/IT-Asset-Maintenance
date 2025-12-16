from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import PartStockMovement, Notification
from .notify import notify_it

@receiver(post_save, sender=PartStockMovement)
def low_stock_notify(sender, instance: PartStockMovement, created, **kwargs):
    if not created:
        return
    part = instance.part
    balance = part.stock_balance()

    if balance <= part.low_stock_threshold:
        notify_it(
            Notification.Type.LOW_STOCK,
            title=f"LOW STOCK: {part.sku}",
            message=f"Balance={balance} threshold={part.low_stock_threshold}",
            url=f"/parts/{part.pk}/",
        )
