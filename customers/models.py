from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from core.i18n import tr


class Customer(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="customer_profile",
        null=True,
        blank=True,
        verbose_name="حساب المستخدم",
    )
    full_name = models.CharField(tr("Full name"), max_length=150)
    phone = models.CharField(tr("Mobile"), max_length=20, unique=True)
    email = models.EmailField(tr("Email"), blank=True)
    address = models.TextField(tr("Address"), blank=True)

    class Meta:
        verbose_name = tr("Customer")
        verbose_name_plural = tr("Customers")

    def __str__(self):
        return self.full_name

    def clean(self):
        if self.user_id and hasattr(self.user, "employee"):
            raise ValidationError(
                {"user": "لا يمكن ربط حساب موظف بسجل عميل."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        if self.user_id:
            user = self.user
            changed = user.is_staff or user.is_superuser
            user.is_staff = False
            user.is_superuser = False
            if changed:
                user.save(update_fields=["is_staff", "is_superuser"])
            user.groups.clear()
            user.user_permissions.clear()


class Vehicle(models.Model):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="vehicles",
        verbose_name=tr("Customer"),
    )

    plate_number = models.CharField(tr("Plate number"), max_length=20)
    chassis_number = models.CharField(tr("Chassis number"), max_length=100, unique=True)

    brand = models.CharField(tr("Brand"), max_length=100)
    model = models.CharField(tr("Model"), max_length=100)
    year = models.PositiveIntegerField(tr("Year"))
    color = models.CharField(tr("Color"), max_length=50)
    mileage = models.PositiveIntegerField(tr("Mileage"))
    is_active = models.BooleanField("نشطة", default=True)

    class Meta:
        verbose_name = tr("Vehicle")
        verbose_name_plural = tr("Vehicles")

    def __str__(self):
        return f"{self.brand} {self.model} ({self.plate_number})"
