from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Ticket, Notification
from .notify import notify_users

@receiver(post_save, sender=Ticket)
def ticket_update_notify(sender, instance: Ticket, created, **kwargs):
    # created เคสแจ้ง IT เราทำใน view แล้วก็ได้ (หรือทำที่นี่ก็ได้)
    if created:
        return

    # แจ้งคนแจ้ง (requested_by) เมื่อ ticket ถูกอัปเดต
    if instance.requested_by_id:
        notify_users(
            [instance.requested_by],
            Notification.Type.TICKET_UPDATE,
            title=f"Ticket updated: {instance.ticket_no}",
            message=f"Status: {instance.status}",
            url=f"/tickets/{instance.pk}/",
        )

    # ถ้าปิดแล้ว แจ้งเพิ่มแบบชัด ๆ
    if instance.status == "CLOSED" and instance.requested_by_id:
        notify_users(
            [instance.requested_by],
            Notification.Type.TICKET_CLOSED,
            title=f"Ticket closed: {instance.ticket_no}",
            message=instance.subject,
            url=f"/tickets/{instance.pk}/",
        )
