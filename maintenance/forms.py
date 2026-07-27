from django import forms

from core.models import Branch
from customers.models import Vehicle

from .models import WorkOrder


FIELD_CLASS = (
    "mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 "
    "outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-500/10"
)


class MaintenanceRequestForm(forms.ModelForm):
    ACTIVE_STATUSES = {"new", "inspection", "approved", "working"}

    class Meta:
        model = WorkOrder
        fields = ("vehicle", "branch", "scheduled_at", "description", "mileage")
        widgets = {
            "scheduled_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "description": forms.Textarea(attrs={"rows": 4}),
        }
        labels = {
            "vehicle": "السيارة",
            "branch": "الفرع",
            "scheduled_at": "موعد الصيانة المطلوب",
            "description": "وصف المشكلة أو الخدمة المطلوبة",
            "mileage": "قراءة العداد الحالية",
        }

    def __init__(self, *args, customer, **kwargs):
        super().__init__(*args, **kwargs)
        self.customer = customer
        vehicles = Vehicle.objects.filter(
            customer=customer,
            is_active=True,
        )
        self.fields["vehicle"].queryset = vehicles
        if not self.is_bound and vehicles.count() == 1:
            self.fields["vehicle"].initial = vehicles.first()
        self.fields["branch"].queryset = Branch.objects.filter(is_active=True)
        self.fields["scheduled_at"].input_formats = ("%Y-%m-%dT%H:%M",)
        for field in self.fields.values():
            field.widget.attrs["class"] = FIELD_CLASS

    def clean_vehicle(self):
        vehicle = self.cleaned_data["vehicle"]
        active_order = (
            WorkOrder.objects.filter(
                customer=self.customer,
                vehicle=vehicle,
                status__in=self.ACTIVE_STATUSES,
            )
            .order_by("-created_at")
            .first()
        )
        if active_order:
            raise forms.ValidationError(
                f"لدى هذه السيارة طلب صيانة نشط بالفعل "
                f"(WO-{active_order.pk}). تابع الطلب الحالي قبل إنشاء طلب جديد."
            )
        return vehicle
