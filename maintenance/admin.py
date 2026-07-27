from django.contrib import admin

from .models import (
    Notification,
    Quote,
    WorkOrder,
    WorkOrderImage,
    WorkOrderPart,
    WorkOrderService,
)


class WorkOrderServiceInline(admin.TabularInline):
    model = WorkOrderService
    extra = 1
    autocomplete_fields = ("service", "technician")


class WorkOrderPartInline(admin.TabularInline):
    model = WorkOrderPart
    extra = 0
    autocomplete_fields = ("part",)


class WorkOrderImageInline(admin.TabularInline):
    model = WorkOrderImage
    extra = 0


class QuoteInline(admin.StackedInline):
    model = Quote
    extra = 0
    max_num = 1


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "branch",
        "customer",
        "vehicle",
        "assigned_technician",
        "status",
        "created_at",
    )

    list_filter = (
        "branch",
        "status",
    )

    search_fields = (
        "customer__full_name",
        "vehicle__plate_number",
    )
    autocomplete_fields = (
        "branch",
        "customer",
        "vehicle",
        "created_by",
        "assigned_technician",
    )
    readonly_fields = ("created_at", "started_at", "completed_at")
    date_hierarchy = "created_at"

    inlines = [
        WorkOrderServiceInline,
        WorkOrderPartInline,
        WorkOrderImageInline,
        QuoteInline,
    ]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        employee = getattr(request.user, "employee", None)
        if not employee or employee.role == employee.GENERAL_MANAGER:
            return queryset
        if employee.role == employee.TECHNICIAN:
            return queryset.filter(assigned_technician=employee)
        if employee.role in {
            employee.BRANCH_MANAGER,
            employee.RECEPTIONIST,
            employee.INVENTORY_MANAGER,
        }:
            return queryset.filter(branch=employee.branch)
        return queryset

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        employee = getattr(request.user, "employee", None)
        if employee and employee.role != employee.GENERAL_MANAGER:
            if db_field.name == "branch":
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(
                    pk=employee.branch_id
                )
            elif db_field.name == "assigned_technician":
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(
                    branch=employee.branch,
                    role=employee.TECHNICIAN,
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(WorkOrderService)
class WorkOrderServiceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "work_order",
        "service",
        "technician",
    )

    search_fields = (
        "work_order__id",
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        employee = getattr(request.user, "employee", None)
        if not employee or employee.role == employee.GENERAL_MANAGER:
            return queryset
        if employee.role == employee.TECHNICIAN:
            return queryset.filter(work_order__assigned_technician=employee)
        return queryset.filter(work_order__branch=employee.branch)


@admin.register(WorkOrderPart)
class WorkOrderPartAdmin(admin.ModelAdmin):
    list_display = ("work_order", "part", "quantity", "unit_price")

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        employee = getattr(request.user, "employee", None)
        if not employee or employee.role == employee.GENERAL_MANAGER:
            return queryset
        if employee.role == employee.TECHNICIAN:
            return queryset.filter(work_order__assigned_technician=employee)
        return queryset.filter(work_order__branch=employee.branch)


@admin.register(WorkOrderImage)
class WorkOrderImageAdmin(admin.ModelAdmin):
    list_display = ("work_order", "phase", "caption", "created_at")

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        employee = getattr(request.user, "employee", None)
        if not employee or employee.role == employee.GENERAL_MANAGER:
            return queryset
        if employee.role == employee.TECHNICIAN:
            return queryset.filter(work_order__assigned_technician=employee)
        return queryset.filter(work_order__branch=employee.branch)


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ("work_order", "amount", "status", "created_at")
    list_filter = ("status",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        employee = getattr(request.user, "employee", None)
        if employee and employee.role not in {
            employee.GENERAL_MANAGER,
            employee.ACCOUNTANT,
        }:
            return queryset.filter(work_order__branch=employee.branch)
        return queryset


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "work_order", "is_read", "created_at")
    list_filter = ("is_read",)
    readonly_fields = ("user", "work_order", "title", "message", "created_at")
