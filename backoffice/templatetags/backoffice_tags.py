from django import template
from django.utils.translation import get_language
from core.i18n import ARABIC


register = template.Library()

ENGLISH = {
    "التشغيل": "Operations", "العملاء": "Customers", "الصيانة": "Maintenance",
    "التواصل": "Communication", "الخدمات": "Services", "المخزون": "Inventory",
    "المالية": "Finance", "مركز القيادة": "Dashboard", "الفروع": "Branches",
    "الموظفون": "Employees", "السيارات": "Vehicles", "أوامر الصيانة": "Work orders",
    "خدمات أوامر الصيانة": "Work order services", "القطع المركبة": "Installed parts",
    "صور أوامر الصيانة": "Work order images", "عروض الأسعار": "Quotes",
    "الإشعارات": "Notifications", "تصنيفات الخدمات": "Service categories",
    "قطع الغيار": "Spare parts", "مخزون الفروع": "Branch stock",
    "حركات المخزون": "Stock movements", "الفواتير": "Invoices",
    "بنود الفواتير": "Invoice items", "المدفوعات": "Payments",
    "رسائل العملاء": "Customer messages", "تقييمات الورشة": "Workshop reviews",
    "نشط": "Active", "غير نشط": "Inactive", "مدير عام": "General manager",
    "مدير فرع": "Branch manager", "موظف استقبال": "Receptionist", "فني": "Technician",
    "محاسب": "Accountant", "مسؤول مخزون": "Inventory manager",
    "اسم المستخدم": "Username", "الاسم الأول": "First name", "اسم العائلة": "Last name",
    "البريد الإلكتروني": "Email", "كلمة المرور": "Password", "فرع": "Branch",
    "موظف": "Employee", "عميل": "Customer", "سيارة": "Vehicle",
    "أمر صيانة": "Work order", "فاتورة": "Invoice", "دفعة": "Payment",
    "تقييم الورشة": "Workshop review", "رسالة عميل": "Customer message",
    "العنوان": "Address", "رقم الهاتف": "Phone number", "ساعات العمل": "Business hours",
    "الدور": "Role", "المسمى الوظيفي": "Job title", "الجوال": "Mobile",
    "الاسم": "Name", "رقم اللوحة": "Plate number", "رقم الهيكل": "Chassis number",
    "الشركة": "Brand", "الموديل": "Model", "سنة الصنع": "Year", "اللون": "Color",
    "العداد": "Mileage", "الوصف": "Description", "الحالة": "Status",
    "موعد الصيانة": "Appointment", "ملاحظات المركز": "Center notes",
    "الفني المسؤول": "Assigned technician", "تاريخ بدء العمل": "Started at",
    "تاريخ انتهاء العمل": "Completed at", "الكمية": "Quantity", "سعر الوحدة": "Unit price",
    "العنوان": "Title", "الرسالة": "Message", "مقروء": "Read", "التصنيف": "Category",
    "السعر": "Price", "المدة التقديرية": "Estimated time", "رقم القطعة": "Part number",
    "المورد": "Supplier", "سعر البيع": "Selling price", "الحد الأدنى للمخزون": "Minimum stock",
    "المجموع الفرعي": "Subtotal", "الخصم": "Discount", "الإجمالي": "Total",
    "المبلغ": "Amount", "طريقة الدفع": "Payment method", "المرجع": "Reference",
    "الموضوع": "Subject", "تمت المعالجة": "Resolved", "التعليق": "Comment",
    "معتمد للنشر": "Approved for publishing", "التقييم": "Rating",
}
ENGLISH.update({arabic: english for english, arabic in ARABIC.items()})


def translate_management(value):
    text = str(value)
    if (get_language() or "ar").startswith("en"):
        for prefix, translated in (("إضافة ", "Add "), ("تعديل ", "Edit "), ("حذف ", "Delete ")):
            if text.startswith(prefix):
                return translated + ENGLISH.get(text[len(prefix):], text[len(prefix):])
        return ENGLISH.get(text, text)
    return text


@register.filter
def bo_tr(value):
    return translate_management(value)


@register.simple_tag
def field_value(obj, field_name):
    value = getattr(obj, field_name, "")
    method = getattr(obj, f"get_{field_name}_display", None)
    if callable(method):
        value = method()
    if value is True:
        return translate_management("نشط")
    if value is False:
        return translate_management("غير نشط")
    if value in (None, ""):
        return "—"
    return translate_management(value)


@register.simple_tag
def field_label(resource, field_name):
    return translate_management(
        resource.model._meta.get_field(field_name).verbose_name
    )


@register.filter
def can_change(user, resource):
    return user.is_superuser or user.has_perm(
        f"{resource.model._meta.app_label}.change_{resource.model._meta.model_name}"
    )


@register.filter
def can_delete(user, resource):
    return user.is_superuser or user.has_perm(
        f"{resource.model._meta.app_label}.delete_{resource.model._meta.model_name}"
    )
