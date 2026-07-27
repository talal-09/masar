from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.db import transaction

from core.models import Employee

from .access import is_platform_manager, scope_queryset


class ManagementAuthenticationForm(AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "اسم المستخدم أو كلمة المرور غير صحيحة.",
        "inactive": "هذا الحساب غير نشط.",
    }

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not is_platform_manager(user):
            raise forms.ValidationError(
                "هذا الحساب غير مصرح له باستخدام لوحة إدارة المنصة.",
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


def form_for_resource(resource):
    if resource.model is Employee:
        return EmployeeManagementForm
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
