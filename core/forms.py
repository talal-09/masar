from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User


INPUT_CLASSES = (
    "mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3.5 "
    "text-slate-950 outline-none transition placeholder:text-slate-400 "
    "focus:border-teal-500 focus:bg-white focus:ring-4 focus:ring-teal-500/10"
)


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(label="الاسم", max_length=150)
    email = forms.EmailField(label="البريد الإلكتروني")
    phone = forms.CharField(label="رقم الجوال", max_length=20)

    class Meta:
        model = User
        fields = (
            "first_name",
            "email",
            "phone",
            "username",
            "password1",
            "password2",
        )
        labels = {"username": "اسم المستخدم"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            "first_name": "اكتب اسمك",
            "email": "name@example.com",
            "phone": "05xxxxxxxx",
            "username": "اختر اسم مستخدم",
            "password1": "كلمة مرور قوية",
            "password2": "أعد كتابة كلمة المرور",
        }
        for name, field in self.fields.items():
            field.widget.attrs.update(
                {
                    "class": INPUT_CLASSES,
                    "placeholder": placeholders[name],
                    "autocomplete": (
                        "new-password" if name.startswith("password") else name
                    ),
                }
            )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("يوجد حساب مسجل بهذا البريد الإلكتروني.")
        return email

    def clean_phone(self):
        from customers.models import Customer

        phone = self.cleaned_data["phone"].strip()
        if Customer.objects.filter(phone=phone).exists():
            raise forms.ValidationError("يوجد حساب مسجل برقم الجوال هذا.")
        return phone


class StyledAuthenticationForm(AuthenticationForm):
    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request=request, *args, **kwargs)
        self.fields["username"].label = "اسم المستخدم"
        self.fields["password"].label = "كلمة المرور"
        self.fields["username"].widget.attrs.update(
            {
                "class": INPUT_CLASSES,
                "placeholder": "اكتب اسم المستخدم",
                "autocomplete": "username",
            }
        )
        self.fields["password"].widget.attrs.update(
            {
                "class": INPUT_CLASSES,
                "placeholder": "اكتب كلمة المرور",
                "autocomplete": "current-password",
            }
        )

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if user.is_staff:
            raise forms.ValidationError(
                "حسابات فريق المركز تسجّل الدخول من بوابة الموظفين فقط.",
                code="staff_account_in_customer_portal",
            )
        if not user.is_staff and not hasattr(user, "customer_profile"):
            raise forms.ValidationError(
                "هذا الحساب غير مرتبط بملف عميل. تواصل مع إدارة المركز.",
                code="missing_customer_profile",
            )
