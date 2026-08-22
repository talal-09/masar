from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Notification, WorkOrder, WorkOrderPart, WorkOrderService


@receiver(pre_save, sender=WorkOrder)
def remember_previous_status(sender, instance, **kwargs):
    instance._previous_status = None
    if instance.pk:
        instance._previous_status = (
            sender.objects.filter(pk=instance.pk)
            .values_list("status", flat=True)
            .first()
        )


@receiver(post_save, sender=WorkOrder)
def notify_customer_of_status_change(sender, instance, created, **kwargs):
    updates = {}
    if instance.status == WorkOrder.WORKING and not instance.started_at:
        updates["started_at"] = timezone.now()
    if instance.status in {
        WorkOrder.READY_FOR_DELIVERY,
        WorkOrder.COMPLETED,
    } and not instance.completed_at:
        updates["completed_at"] = timezone.now()
    if instance.status == WorkOrder.DELIVERED and not instance.delivered_at:
        updates["delivered_at"] = timezone.now()
    if updates:
        WorkOrder.objects.filter(pk=instance.pk).update(**updates)

    user = getattr(instance.customer, "user", None)
    if not user:
        return

    if created:
        title = "تم استلام طلب الصيانة"
        message = f"تم إنشاء طلب الصيانة رقم WO-{instance.pk} بنجاح."
    elif instance._previous_status != instance.status:
        title = "تحديث حالة الصيانة"
        message = (
            f"تم تحديث حالة أمر الصيانة WO-{instance.pk} إلى "
            f"{instance.get_status_display()}."
        )
    else:
        return

    Notification.objects.create(
        user=user,
        work_order=instance,
        title=title,
        message=message,
    )


@receiver([post_save, post_delete], sender=WorkOrderService)
@receiver([post_save, post_delete], sender=WorkOrderPart)
def recalculate_existing_invoice(sender, instance, **kwargs):
    from billing.models import Invoice

    invoice = Invoice.objects.filter(work_order=instance.work_order).first()
    if invoice:
        invoice.recalculate(sync_from_work_order=True)
