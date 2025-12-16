from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Asset, AssetAssignmentLog

@receiver(pre_save, sender=Asset)
def asset_owner_change_log(sender, instance: Asset, **kwargs):
    if not instance.pk:
        return
    old = Asset.objects.filter(pk=instance.pk).only("owner_id").first()
    if not old:
        return
    if old.owner_id != instance.owner_id:
        # changed_by เราจะ set ผ่าน view (ดูด้านล่าง) ถ้าไม่มีให้เป็น None
        AssetAssignmentLog.objects.create(
            asset=instance,
            old_owner_id=old.owner_id,
            new_owner_id=instance.owner_id,
            changed_by=getattr(instance, "_changed_by", None),
        )
