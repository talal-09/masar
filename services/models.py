from django.db import models
from core.i18n import tr


class ServiceCategory(models.Model):
    name = models.CharField(
        tr("Category name"),
        max_length=100,
        unique=True,
    )

    class Meta:
        verbose_name = tr("Service category")
        verbose_name_plural = tr("Service categories")

    def __str__(self):
        return self.name


class Service(models.Model):
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.PROTECT,
        related_name="services",
        verbose_name=tr("Category"),
    )
    name = models.CharField(
        tr("Service name"),
        max_length=150,
    )
    price = models.DecimalField(
        tr("Price"),
        max_digits=10,
        decimal_places=2,
    )
    estimated_time = models.PositiveIntegerField(
        tr("Estimated time in minutes"),
    )
    active = models.BooleanField(
        tr("Active"),
        default=True,
    )

    class Meta:
        verbose_name = tr("Service")
        verbose_name_plural = tr("Services")
        constraints = [
            models.UniqueConstraint(
                fields=("category", "name"),
                name="unique_service_name_per_category",
            )
        ]

    def __str__(self):
        return self.name
