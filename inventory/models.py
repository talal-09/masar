from django.core.validators import MinValueValidator
from django.db import models
from core.models import Branch
from core.i18n import tr


class SparePart(models.Model):
    name = models.CharField(tr("Part name"), max_length=150)
    part_number = models.CharField(tr("Part number"), max_length=100, unique=True)

    purchase_price = models.DecimalField(tr("Purchase price"), max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(tr("Selling price"), max_digits=10, decimal_places=2)
    supplier = models.CharField("المورد", max_length=150, blank=True)
    minimum_stock = models.PositiveIntegerField("الحد الأدنى للمخزون", default=0)
    is_active = models.BooleanField("متاحة", default=True)

    class Meta:
        verbose_name = tr("Spare part")
        verbose_name_plural = tr("Spare parts")

    def __str__(self):
        return self.name


class BranchStock(models.Model):
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        verbose_name=tr("Branch"),
    )

    part = models.ForeignKey(
        SparePart,
        on_delete=models.CASCADE,
        verbose_name=tr("Part"),
    )

    quantity = models.PositiveIntegerField(tr("Quantity"), default=0)

    class Meta:
        verbose_name = tr("Branch stock")
        verbose_name_plural = tr("Branch stock")
        constraints = [
            models.UniqueConstraint(
                fields=("branch", "part"),
                name="unique_part_stock_per_branch",
            )
        ]

    def __str__(self):
        return f"{self.branch} - {self.part}"


class StockMovement(models.Model):
    ADDITION = "addition"
    USAGE = "usage"
    ADJUSTMENT = "adjustment"
    TYPES = [
        (ADDITION, "إضافة"),
        (USAGE, "استخدام في صيانة"),
        (ADJUSTMENT, "تسوية"),
    ]

    stock = models.ForeignKey(
        BranchStock,
        on_delete=models.PROTECT,
        related_name="movements",
        verbose_name="المخزون",
    )
    movement_type = models.CharField("نوع الحركة", max_length=20, choices=TYPES)
    quantity = models.PositiveIntegerField(
        "الكمية",
        validators=[MinValueValidator(1)],
    )
    work_order = models.ForeignKey(
        "maintenance.WorkOrder",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="stock_movements",
        verbose_name="أمر الصيانة",
    )
    note = models.CharField("ملاحظة", max_length=200, blank=True)
    created_at = models.DateTimeField("تاريخ الحركة", auto_now_add=True)

    class Meta:
        verbose_name = "حركة مخزون"
        verbose_name_plural = "حركات المخزون"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.stock.part}"
