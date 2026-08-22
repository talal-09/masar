from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.db import transaction
from django.db.models import Q
from django.utils.translation import get_language

from core.models import Employee
from customers.models import Customer, Vehicle
from maintenance.models import WorkOrder

from .access import is_platform_manager, scope_queryset


class ManagementAuthenticationForm(AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "اسم المستخدم أو كلمة المرور غير صحيحة.",
        "inactive": "هذا الحساب غير نشط.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if (get_language() or "ar").startswith("en"):
            self.error_messages.update({
                "invalid_login": "The username or password is incorrect.",
                "inactive": "This account is inactive.",
            })

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not is_platform_manager(user):
            raise forms.ValidationError(
                "This account is not authorized to use platform management."
                if (get_language() or "ar").startswith("en")
                else "هذا الحساب غير مصرح له باستخدام لوحة إدارة المنصة.",
                code="not_management_user",
            )


class ManagementModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop("request_user", None)
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = "bo-control"
            if isinstance(field.widget, forms.CheckboxInput):
                css_class = "bo-checkbox"
            field.widget.attrs["class"] = css_class
            if isinstance(field.widget, forms.DateTimeInput):
                field.widget.input_type = "datetime-local"
            if (
                self.request_user
                and isinstance(field, forms.ModelChoiceField)
            ):
                field.queryset = scope_queryset(
                    field.queryset,
                    self.request_user,
                )


class EmployeeManagementForm(forms.ModelForm):
    username = forms.CharField(label="اسم المستخدم", max_length=150)
    first_name = forms.CharField(label="الاسم الأول", max_length=150)
    last_name = forms.CharField(label="اسم العائلة", max_length=150, required=False)
    email = forms.EmailField(label="البريد الإلكتروني", required=False)
    password = forms.CharField(
        label="كلمة المرور",
        widget=forms.PasswordInput,
        required=False,
        help_text="اتركها فارغة عند التعديل للإبقاء على كلمة المرور الحالية.",
    )

    class Meta:
        model = Employee
        fields = ("branch", "job_title", "phone", "role")

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop("request_user", None)
        super().__init__(*args, **kwargs)
        if (get_language() or "ar").startswith("en"):
            labels = {
                "username": "Username", "first_name": "First name",
                "last_name": "Last name", "email": "Email", "password": "Password",
            }
            for name, label in labels.items():
                self.fields[name].label = label
            self.fields["password"].help_text = (
                "Leave blank while editing to keep the current password."
            )
        if self.instance.pk:
            self.fields["username"].initial = self.instance.user.username
            self.fields["first_name"].initial = self.instance.user.first_name
            self.fields["last_name"].initial = self.instance.user.last_name
            self.fields["email"].initial = self.instance.user.email
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "bo-checkbox"
                if isinstance(field.widget, forms.CheckboxInput)
                else "bo-control"
            )
        if self.request_user:
            self.fields["branch"].queryset = scope_queryset(
                self.fields["branch"].queryset,
                self.request_user,
            )
            current_employee = getattr(self.request_user, "employee", None)
            if (
                current_employee
                and current_employee.role != Employee.GENERAL_MANAGER
                and not self.request_user.is_superuser
            ):
                allowed_roles = {
                    Employee.RECEPTIONIST,
                    Employee.TECHNICIAN,
                    Employee.ACCOUNTANT,
                    Employee.INVENTORY_MANAGER,
                }
                self.fields["role"].choices = [
                    choice
                    for choice in self.fields["role"].choices
                    if not choice[0] or choice[0] in allowed_roles
                ]

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        queryset = Employee._meta.get_field("user").remote_field.model.objects.filter(
            username__iexact=username
        )
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.user_id)
        if queryset.exists():
            raise forms.ValidationError("اسم المستخدم مستخدم بالفعل.")
        return username

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if not self.instance.pk and not password:
            raise forms.ValidationError("كلمة المرور مطلوبة للموظف الجديد.")
        return password

    @transaction.atomic
    def save(self, commit=True):
        employee = super().save(commit=False)
        if employee.pk:
            user = employee.user
        else:
            user_model = Employee._meta.get_field("user").remote_field.model
            user = user_model(is_staff=True)
        user.username = self.cleaned_data["username"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        user.is_staff = True
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        user.save()
        employee.user = user
        if commit:
            employee.save()
        return employee


class WorkOrderManagementForm(ManagementModelForm):
    class Meta:
        model = WorkOrder
        fields = (
            "branch", "customer", "vehicle", "created_by", "description",
            "mileage", "status", "scheduled_at", "center_notes",
            "assigned_technician", "started_at", "completed_at",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["customer"].queryset = Customer.objects.order_by("full_name")

        customer_id = self._selected_id("customer")
        branch_id = self._selected_id("branch")

        vehicles = Vehicle.objects.none()
        if customer_id:
            vehicles = Vehicle.objects.filter(
                customer_id=customer_id,
                is_active=True,
            ).order_by("brand", "model", "year")
            submitted_vehicle_id = (
                self.data.get(self.add_prefix("vehicle")) if self.is_bound else None
            )
            retained_vehicle_id = (
                submitted_vehicle_id
                if str(submitted_vehicle_id).isdigit()
                else self.instance.vehicle_id if self.instance.pk else None
            )
            if retained_vehicle_id:
                vehicles = Vehicle.objects.filter(
                    Q(pk=retained_vehicle_id)
                    | Q(
                        customer_id=customer_id,
                        is_active=True,
                    )
                ).order_by("brand", "model", "year")
        self.fields["vehicle"].queryset = vehicles
        self.fields["vehicle"].empty_label = (
            "اختر السيارة" if customer_id else "اختر العميل أولاً"
        )
        self.fields["vehicle"].widget.attrs.update({
            "data-dependent": "vehicle",
            "disabled": not bool(customer_id),
        })

        technicians = Employee.objects.none()
        receptionists = Employee.objects.none()
        if branch_id:
            employees = Employee.objects.filter(
                branch_id=branch_id,
                user__is_active=True,
            ).select_related("user").order_by("user__first_name", "user__username")
            technicians = employees.filter(role=Employee.TECHNICIAN)
            receptionists = employees.filter(role=Employee.RECEPTIONIST)
            if self.is_bound:
                submitted_technician_id = self.data.get(
                    self.add_prefix("assigned_technician")
                )
                submitted_receptionist_id = self.data.get(
                    self.add_prefix("created_by")
                )
                if str(submitted_technician_id).isdigit():
                    technicians = Employee.objects.filter(
                        Q(pk=submitted_technician_id)
                        | Q(
                            branch_id=branch_id,
                            role=Employee.TECHNICIAN,
                            user__is_active=True,
                        )
                    ).select_related("user")
                if str(submitted_receptionist_id).isdigit():
                    receptionists = Employee.objects.filter(
                        Q(pk=submitted_receptionist_id)
                        | Q(
                            branch_id=branch_id,
                            role=Employee.RECEPTIONIST,
                            user__is_active=True,
                        )
                    ).select_related("user")
        self.fields["assigned_technician"].queryset = technicians
        self.fields["created_by"].queryset = receptionists
        self.fields["assigned_technician"].widget.attrs.update({
            "data-dependent": "technician",
            "disabled": not bool(branch_id),
        })
        self.fields["created_by"].widget.attrs.update({
            "data-dependent": "receptionist",
            "disabled": not bool(branch_id),
        })

    def _selected_id(self, field_name):
        if self.is_bound:
            value = self.data.get(self.add_prefix(field_name))
            return value if str(value).isdigit() else None
        return getattr(self.instance, f"{field_name}_id", None)

    def clean(self):
        cleaned_data = super().clean()
        customer = cleaned_data.get("customer")
        vehicle = cleaned_data.get("vehicle")
        branch = cleaned_data.get("branch")
        technician = cleaned_data.get("assigned_technician")
        receptionist = cleaned_data.get("created_by")
        if customer and vehicle and vehicle.customer_id != customer.pk:
            self.add_error(
                "vehicle",
                "السيارة المحددة لا تتبع العميل المختار.",
            )
        if branch and technician and (
            technician.branch_id != branch.pk
            or technician.role != Employee.TECHNICIAN
            or not technician.user.is_active
        ):
            self.add_error(
                "assigned_technician",
                "اختر فنيًا فعالًا من نفس الفرع.",
            )
        if branch and receptionist and (
            receptionist.branch_id != branch.pk
            or receptionist.role != Employee.RECEPTIONIST
            or not receptionist.user.is_active
        ):
            self.add_error(
                "created_by",
                "اختر موظف استقبال فعالًا من نفس الفرع.",
            )
        return cleaned_data


def form_for_resource(resource):
    if resource.model is Employee:
        return EmployeeManagementForm
    if resource.model is WorkOrder:
        return WorkOrderManagementForm
    meta = type(
        "Meta",
        (),
        {
            "model": resource.model,
            "fields": resource.form_fields or "__all__",
            "exclude": resource.exclude_fields or None,
        },
    )
    return type(
        f"{resource.model.__name__}ManagementForm",
        (ManagementModelForm,),
        {"Meta": meta},
    )
