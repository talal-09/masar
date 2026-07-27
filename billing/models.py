from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Sum

from maintenance.models import WorkOrder
from core.i18n import tr


class Invoice(models.Model):
    STATUS = [
        ("pending", tr("Unpaid")),
        ("paid", tr("Paid")),
        ("partial", tr("Partially paid")),
    ]

    work_order = models.OneToOneField(
        WorkOrder,
        on_delete=models.PROTECT,
        related_name="invoice",
        verbose_name=tr("Work order"),
    )

    subtotal = models.DecimalField(tr("Subtotal"), max_digits=10, decimal_places=2)
    tax = models.DecimalField(tr("Tax"), max_digits=10, decimal_places=2)
    discount = models.DecimalField(
        "الخصم",
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    total = models.DecimalField(tr("Total"), max_digits=10, decimal_places=2)

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="pending",
        verbose_name=tr("Status"),
    )

    created_at = models.DateTimeField(tr("Created at"), auto_now_add=True)

    class Meta:
        verbose_name = tr("Invoice")
        verbose_name_plural = tr("Invoices")

    def __str__(self):
        return f"INV-{self.id}"

    @property
    def paid_amount(self):
        return self.payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    @property
    def remaining_amount(self):
        return max(self.total - self.paid_amount, Decimal("0.00"))

    def recalculate(self, tax_rate=Decimal("0.15")):
        service_total = sum(
            (item.service.price for item in self.work_order.services.select_related("service")),
            Decimal("0.00"),
        )
        part_total = sum(
            (item.unit_price * item.quantity for item in self.work_order.installed_parts.all()),
            Decimal("0.00"),
        )
        self.subtotal = service_total + part_total
        taxable = max(self.subtotal - self.discount, Decimal("0.00"))
        self.tax = (taxable * tax_rate).quantize(Decimal("0.01"))
        self.total = taxable + self.tax
        self.save(update_fields=["subtotal", "tax", "total"])
        self.sync_items()

    def sync_items(self):
        with transaction.atomic():
            self.items.all().delete()
            InvoiceItem.objects.bulk_create(
                [
                    InvoiceItem(
                        invoice=self,
                        item_type=InvoiceItem.SERVICE,
                        description=item.service.name,
                        quantity=1,
                        unit_price=item.service.price,
                    )
                    for item in self.work_order.services.select_related("service")
                ]
                + [
                    InvoiceItem(
                        invoice=self,
                        item_type=InvoiceItem.PART,
                        description=item.part.name,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                    )
                    for item in self.work_order.installed_parts.select_related("part")
                ]
            )

    def update_payment_status(self):
        paid = self.paid_amount
        new_status = "paid" if paid >= self.total else ("partial" if paid > 0 else "pending")
        if self.status != new_status:
            self.status = new_status
            self.save(update_fields=["status"])


class InvoiceItem(models.Model):
    SERVICE = "service"
    PART = "part"
    TYPES = [(SERVICE, "خدمة"), (PART, "قطعة غيار")]

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="الفاتورة",
    )
    item_type = models.CharField("النوع", max_length=10, choices=TYPES)
    description = models.CharField("البيان", max_length=200)
    quantity = models.PositiveIntegerField("الكمية", default=1)
    unit_price = models.DecimalField("سعر الوحدة", max_digits=10, decimal_places=2)

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    class Meta:
        verbose_name = "بند فاتورة"
        verbose_name_plural = "بنود الفاتورة"


class Payment(models.Model):
    METHODS = [
        ("cash", "نقدي"),
        ("card", "بطاقة"),
        ("transfer", "تحويل بنكي"),
    ]

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name="الفاتورة",
    )
    amount = models.DecimalField("المبلغ", max_digits=10, decimal_places=2)
    method = models.CharField("طريقة الدفع", max_length=20, choices=METHODS)
    reference = models.CharField("المرجع", max_length=100, blank=True)
    paid_at = models.DateTimeField("تاريخ الدفع", auto_now_add=True)

    def clean(self):
        if self.amount <= 0:
            raise ValidationError({"amount": "يجب أن يكون مبلغ الدفع أكبر من صفر."})
        if self.invoice_id:
            previous = Decimal("0.00")
            if self.pk:
                previous = type(self).objects.get(pk=self.pk).amount
            if self.amount - previous > self.invoice.remaining_amount:
                raise ValidationError({"amount": "مبلغ الدفع أكبر من المبلغ المتبقي."})

    def save(self, *args, **kwargs):
        self.full_clean()
        result = super().save(*args, **kwargs)
        self.invoice.update_payment_status()
        return result

    def delete(self, *args, **kwargs):
        invoice = self.invoice
        result = super().delete(*args, **kwargs)
        invoice.update_payment_status()
        return result

    class Meta:
        verbose_name = "دفعة"
        verbose_name_plural = "المدفوعات"
        ordering = ("-paid_at",)
