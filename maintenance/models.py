from django.db import models, transaction
from django.db.models import F, Q
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from core.models import Branch, Employee
from customers.models import Customer, Vehicle
from services.models import Service
from core.i18n import tr


class WorkOrder(models.Model):
    NEW = "new"
    INSPECTION = "inspection"
    INSPECTED = "inspected"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    WORKING = "working"
    AWAITING_PARTS = "awaiting_parts"
    TESTING = "testing"
    READY_FOR_DELIVERY = "ready_for_delivery"
    COMPLETED = "completed"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

    STATUS = [
        (NEW, tr("New")),
        (INSPECTION, "بانتظار الفحص"),
        (INSPECTED, "تم الفحص"),
        (AWAITING_APPROVAL, "بانتظار موافقة العميل"),
        (APPROVED, tr("Approved")),
        (WORKING, tr("In progress")),
        (AWAITING_PARTS, "بانتظار قطع الغيار"),
        (TESTING, "قيد الاختبار"),
        (READY_FOR_DELIVERY, "جاهز للتسليم"),
        (COMPLETED, tr("Completed")),
        (DELIVERED, tr("Delivered")),
        (CANCELLED, "ملغي"),
    ]
    ALLOWED_TRANSITIONS = {
        NEW: {INSPECTION, CANCELLED},
        INSPECTION: {INSPECTED, CANCELLED},
        INSPECTED: {AWAITING_APPROVAL, APPROVED, CANCELLED},
        AWAITING_APPROVAL: {APPROVED, CANCELLED},
        APPROVED: {WORKING, AWAITING_PARTS, CANCELLED},
        WORKING: {AWAITING_PARTS, TESTING},
        AWAITING_PARTS: {WORKING},
        TESTING: {WORKING, READY_FOR_DELIVERY},
        READY_FOR_DELIVERY: {DELIVERED},
        COMPLETED: {DELIVERED},
        DELIVERED: set(),
        CANCELLED: set(),
    }
    ACTIVE_STATUSES = {
        NEW, INSPECTION, INSPECTED, AWAITING_APPROVAL, APPROVED,
        WORKING, AWAITING_PARTS, TESTING, READY_FOR_DELIVERY,
    }

    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, verbose_name=tr("Branch"))
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, verbose_name=tr("Customer"))
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, verbose_name=tr("Vehicle"))

    created_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=tr("Created by"),
    )

    description = models.TextField(tr("Description"))
    mileage = models.PositiveIntegerField(tr("Mileage"))

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default=NEW,
        verbose_name=tr("Status"),
    )

    created_at = models.DateTimeField(tr("Created at"), auto_now_add=True)
    scheduled_at = models.DateTimeField("موعد الصيانة", null=True, blank=True)
    expected_delivery_at = models.DateTimeField(
        "موعد التسليم المتوقع", null=True, blank=True
    )
    center_notes = models.TextField("ملاحظات المركز", blank=True)
    assigned_technician = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_work_orders",
        limit_choices_to={"role": Employee.TECHNICIAN},
        verbose_name="الفني المسؤول",
    )
    started_at = models.DateTimeField("تاريخ بدء العمل", null=True, blank=True)
    completed_at = models.DateTimeField("تاريخ انتهاء العمل", null=True, blank=True)
    delivered_at = models.DateTimeField("تاريخ التسليم", null=True, blank=True)

    class Meta:
        verbose_name = tr("Work order")
        verbose_name_plural = tr("Work orders")
        constraints = [
            models.UniqueConstraint(
                fields=("vehicle",),
                condition=Q(
                    status__in=(
                        "new", "inspection", "inspected", "awaiting_approval",
                        "approved", "working", "awaiting_parts", "testing",
                        "ready_for_delivery",
                    )
                ),
                name="one_active_work_order_per_vehicle",
            )
        ]

    def __str__(self):
        return f"WO-{self.id}"

    def clean(self):
        previous_status = None
        if self.pk:
            previous_status = (
                type(self).objects.filter(pk=self.pk)
                .values_list("status", flat=True)
                .first()
            )
        if (
            previous_status
            and previous_status != self.status
            and self.status not in self.ALLOWED_TRANSITIONS.get(
                previous_status,
                set(),
            )
        ):
            labels = dict(self.STATUS)
            raise ValidationError({
                "status": (
                    f"لا يمكن نقل أمر الصيانة من حالة «{labels.get(previous_status, previous_status)}» "
                    f"مباشرة إلى «{labels.get(self.status, self.status)}»."
                )
            })
        if (
            previous_status != self.status
            and self.status == self.WORKING
            and not self.assigned_technician_id
        ):
            raise ValidationError({
                "assigned_technician": "يجب تحديد فني مسؤول قبل بدء الصيانة."
            })
        if (
            self.vehicle_id
            and self.customer_id
            and self.vehicle.customer_id != self.customer_id
        ):
            raise ValidationError(
                {"vehicle": "السيارة المحددة لا تتبع العميل المختار."}
            )
        if (
            self.assigned_technician_id
            and self.branch_id
            and self.assigned_technician.branch_id != self.branch_id
        ):
            raise ValidationError(
                {"assigned_technician": "يجب أن يكون الفني من الفرع المحدد."}
            )
        if self.completed_at and self.started_at and self.completed_at < self.started_at:
            raise ValidationError(
                {"completed_at": "تاريخ الانتهاء يجب أن يكون بعد تاريخ البدء."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def get_allowed_status_choices(self):
        allowed = self.ALLOWED_TRANSITIONS.get(self.status, set())
        return [
            (value, label)
            for value, label in self.STATUS
            if value in allowed
        ]


class WorkOrderService(models.Model):
    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        related_name="services",
        verbose_name=tr("Work order"),
    )

    service = models.ForeignKey(Service, on_delete=models.CASCADE, verbose_name=tr("Service"))

    technician = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=tr("Technician"),
    )

    class Meta:
        verbose_name = tr("Work order service")
        verbose_name_plural = tr("Work order services")
        constraints = [
            models.UniqueConstraint(
                fields=("work_order", "service"),
                name="unique_service_per_work_order",
            )
        ]


class WorkOrderPart(models.Model):
    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        related_name="installed_parts",
        verbose_name="أمر الصيانة",
    )
    part = models.ForeignKey(
        "inventory.SparePart",
        on_delete=models.PROTECT,
        verbose_name="قطعة الغيار",
    )
    quantity = models.PositiveIntegerField("الكمية", default=1)
    unit_price = models.DecimalField(
        "سعر الوحدة",
        max_digits=10,
        decimal_places=2,
    )

    class Meta:
        verbose_name = "قطعة مركبة"
        verbose_name_plural = "القطع المركبة"
        constraints = [
            models.UniqueConstraint(
                fields=("work_order", "part"),
                name="unique_part_per_work_order",
            )
        ]

    def clean(self):
        if self.quantity < 1:
            raise ValidationError({"quantity": "يجب أن تكون الكمية واحدًا على الأقل."})
        if self.work_order_id and self.part_id:
            from inventory.models import BranchStock

            previous_quantity = 0
            if self.pk:
                previous_quantity = (
                    type(self).objects.filter(pk=self.pk)
                    .values_list("quantity", flat=True)
                    .first()
                    or 0
                )
            stock_quantity = (
                BranchStock.objects.filter(
                    branch=self.work_order.branch,
                    part=self.part,
                )
                .values_list("quantity", flat=True)
                .first()
                or 0
            )
            required = self.quantity - previous_quantity
            if required > stock_quantity:
                raise ValidationError(
                    {"quantity": f"المتوفر في مخزون الفرع {stock_quantity} فقط."}
                )

    def save(self, *args, **kwargs):
        from inventory.models import BranchStock, StockMovement

        self.full_clean()
        with transaction.atomic():
            previous = None
            if self.pk:
                previous = type(self).objects.select_for_update().get(pk=self.pk)

            if previous and (
                previous.part_id != self.part_id
                or previous.work_order.branch_id != self.work_order.branch_id
            ):
                old_stock = BranchStock.objects.select_for_update().get(
                    branch=previous.work_order.branch,
                    part=previous.part,
                )
                old_stock.quantity = F("quantity") + previous.quantity
                old_stock.save(update_fields=["quantity"])
                quantity_to_use = self.quantity
            else:
                quantity_to_use = self.quantity - (previous.quantity if previous else 0)

            stock = BranchStock.objects.select_for_update().filter(
                branch=self.work_order.branch,
                part=self.part,
            ).first()
            if stock is None or stock.quantity < quantity_to_use:
                available = stock.quantity if stock else 0
                raise ValidationError(
                    {"quantity": f"المتوفر في مخزون الفرع {available} فقط."}
                )
            if quantity_to_use:
                stock.quantity = F("quantity") - quantity_to_use
                stock.save(update_fields=["quantity"])
                StockMovement.objects.create(
                    stock=stock,
                    movement_type=(
                        StockMovement.USAGE
                        if quantity_to_use > 0
                        else StockMovement.ADJUSTMENT
                    ),
                    quantity=abs(quantity_to_use),
                    work_order=self.work_order,
                    note="تحديث قطعة مستخدمة في أمر الصيانة",
                )
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        from inventory.models import BranchStock, StockMovement

        with transaction.atomic():
            stock = BranchStock.objects.select_for_update().get(
                branch=self.work_order.branch,
                part=self.part,
            )
            stock.quantity = F("quantity") + self.quantity
            stock.save(update_fields=["quantity"])
            StockMovement.objects.create(
                stock=stock,
                movement_type=StockMovement.ADJUSTMENT,
                quantity=self.quantity,
                work_order=self.work_order,
                note="إرجاع قطعة بعد حذفها من أمر الصيانة",
            )
            return super().delete(*args, **kwargs)


class WorkOrderImage(models.Model):
    BEFORE = "before"
    AFTER = "after"
    PHASE_CHOICES = [(BEFORE, "قبل الصيانة"), (AFTER, "بعد الصيانة")]

    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="أمر الصيانة",
    )
    image = models.ImageField("الصورة", upload_to="work_orders/%Y/%m/")
    phase = models.CharField(
        "المرحلة",
        max_length=10,
        choices=PHASE_CHOICES,
    )
    caption = models.CharField("الوصف", max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "صورة صيانة"
        verbose_name_plural = "صور الصيانة"


class Quote(models.Model):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    STATUS_CHOICES = [
        (PENDING, "بانتظار الموافقة"),
        (APPROVED, "موافق عليه"),
        (REJECTED, "مرفوض"),
    ]

    work_order = models.OneToOneField(
        WorkOrder,
        on_delete=models.CASCADE,
        related_name="quote",
        verbose_name="أمر الصيانة",
    )
    amount = models.DecimalField("قيمة العرض", max_digits=10, decimal_places=2)
    notes = models.TextField("تفاصيل العرض", blank=True)
    status = models.CharField(
        "حالة العرض",
        max_length=10,
        choices=STATUS_CHOICES,
        default=PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "عرض سعر"
        verbose_name_plural = "عروض الأسعار"


class Notification(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="المستخدم",
    )
    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    title = models.CharField("العنوان", max_length=150)
    message = models.TextField("الرسالة")
    is_read = models.BooleanField("مقروء", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "إشعار"
        verbose_name_plural = "الإشعارات"
        ordering = ["-created_at"]
