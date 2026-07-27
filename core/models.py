from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from .i18n import tr


class Branch(models.Model):
    name = models.CharField(tr("Branch name"), max_length=100)
    address = models.TextField(tr("Address"))
    phone = models.CharField(tr("Phone number"), max_length=20)
    is_active = models.BooleanField(tr("Active"), default=True)
    business_hours = models.CharField(
        "ساعات العمل",
        max_length=200,
        blank=True,
        default="الأحد - الخميس، 8:00 ص - 6:00 م",
    )

    class Meta:
        verbose_name = tr("Branch")
        verbose_name_plural = tr("Branches")

    def __str__(self):
        return self.name


class Employee(models.Model):
    GENERAL_MANAGER = "general_manager"
    BRANCH_MANAGER = "branch_manager"
    RECEPTIONIST = "receptionist"
    TECHNICIAN = "technician"
    ACCOUNTANT = "accountant"
    INVENTORY_MANAGER = "inventory_manager"
    ROLE_CHOICES = [
        (GENERAL_MANAGER, "مدير عام"),
        (BRANCH_MANAGER, "مدير فرع"),
        (RECEPTIONIST, "موظف استقبال"),
        (TECHNICIAN, "فني"),
        (ACCOUNTANT, "محاسب"),
        (INVENTORY_MANAGER, "مسؤول مخزون"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name=tr("User"))
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name="employees",
        verbose_name=tr("Branch"),
    )

    job_title = models.CharField(tr("Job title"), max_length=100)
    phone = models.CharField(tr("Mobile"), max_length=20)
    role = models.CharField(
        "الدور",
        max_length=30,
        choices=ROLE_CHOICES,
        default=RECEPTIONIST,
    )

    class Meta:
        verbose_name = tr("Employee")
        verbose_name_plural = tr("Employees")

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    def clean(self):
        if self.user_id and hasattr(self.user, "customer_profile"):
            raise ValidationError(
                {"user": "لا يمكن ربط حساب عميل بسجل موظف."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.user_id and not self.user.is_staff:
            self.user.is_staff = True
            self.user.save(update_fields=["is_staff"])
        super().save(*args, **kwargs)
        from .roles import sync_employee_role

        sync_employee_role(self)


class ContactMessage(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="contact_messages",
        verbose_name="المستخدم",
    )
    subject = models.CharField("الموضوع", max_length=150)
    message = models.TextField("الرسالة")
    created_at = models.DateTimeField("تاريخ الإرسال", auto_now_add=True)
    is_resolved = models.BooleanField("تمت المعالجة", default=False)

    class Meta:
        verbose_name = "رسالة عميل"
        verbose_name_plural = "رسائل العملاء"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.subject}"


class WorkshopReview(models.Model):
    customer = models.OneToOneField(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="workshop_review",
        verbose_name="العميل",
    )
    rating = models.PositiveSmallIntegerField(
        "التقييم",
        choices=[(value, f"{value} نجوم") for value in range(1, 6)],
    )
    comment = models.TextField("التعليق", max_length=600)
    is_approved = models.BooleanField("معتمد للنشر", default=False)
    created_at = models.DateTimeField("تاريخ التقييم", auto_now_add=True)

    class Meta:
        verbose_name = "تقييم الورشة"
        verbose_name_plural = "تقييمات الورشة"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.customer} - {self.rating}/5"
