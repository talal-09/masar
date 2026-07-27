from django.contrib import admin

from .models import Invoice, InvoiceItem, Payment


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0
    readonly_fields = ("item_type", "description", "quantity", "unit_price", "line_total")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 1


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "work_order",
        "subtotal",
        "tax",
        "discount",
        "total",
        "status",
        "created_at",
    )

    list_filter = ("status", "created_at")

    search_fields = (
        "work_order__id",
        "work_order__customer__full_name",
        "work_order__vehicle__plate_number",
    )
    readonly_fields = ("subtotal", "tax", "total", "status", "created_at")
    inlines = (InvoiceItemInline, PaymentInline)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.subtotal = 0
            obj.tax = 0
            obj.total = 0
        super().save_model(request, obj, form, change)
        obj.recalculate()

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        employee = getattr(request.user, "employee", None)
        if employee and employee.role not in {
            employee.GENERAL_MANAGER,
            employee.ACCOUNTANT,
        }:
            return queryset.filter(work_order__branch=employee.branch)
        return queryset


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("invoice", "amount", "method", "reference", "paid_at")
    list_filter = ("method", "paid_at")
    search_fields = (
        "invoice__id",
        "invoice__work_order__customer__full_name",
        "reference",
    )
    readonly_fields = ("paid_at",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        employee = getattr(request.user, "employee", None)
        if employee and employee.role not in {
            employee.GENERAL_MANAGER,
            employee.ACCOUNTANT,
        }:
            return queryset.filter(invoice__work_order__branch=employee.branch)
        return queryset
