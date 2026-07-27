from django.contrib import admin

from .models import Customer, Vehicle


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "full_name",
        "phone",
        "email",
    )

    search_fields = (
        "full_name",
        "phone",
        "email",
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        employee = getattr(request.user, "employee", None)
        if employee and employee.role != employee.GENERAL_MANAGER:
            return queryset.filter(workorder__branch=employee.branch).distinct()
        return queryset


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "plate_number",
        "brand",
        "model",
        "year",
        "customer",
        "is_active",
    )

    search_fields = (
        "plate_number",
        "brand",
        "model",
        "customer__full_name",
    )

    list_filter = (
        "brand",
        "year",
        "is_active",
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        employee = getattr(request.user, "employee", None)
        if employee and employee.role != employee.GENERAL_MANAGER:
            return queryset.filter(workorder__branch=employee.branch).distinct()
        return queryset
