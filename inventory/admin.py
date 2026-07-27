from django.contrib import admin
from django.db import transaction
from django.db.models import F

from .models import BranchStock, SparePart, StockMovement


@admin.register(SparePart)
class SparePartAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "part_number",
        "purchase_price",
        "selling_price",
        "supplier",
        "minimum_stock",
        "is_active",
    )

    search_fields = (
        "name",
        "part_number",
        "supplier",
    )
    list_filter = ("is_active",)


@admin.register(BranchStock)
class BranchStockAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "branch",
        "part",
        "quantity",
    )

    search_fields = (
        "part__name",
    )

    list_filter = (
        "branch",
    )
    autocomplete_fields = ("branch", "part")
    readonly_fields = ("quantity",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        employee = getattr(request.user, "employee", None)
        if employee and employee.role != employee.GENERAL_MANAGER:
            return queryset.filter(branch=employee.branch)
        return queryset


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        "stock",
        "movement_type",
        "quantity",
        "work_order",
        "created_at",
    )
    list_filter = ("movement_type", "stock__branch", "created_at")
    search_fields = ("stock__part__name", "stock__part__part_number", "note")
    readonly_fields = ("movement_type", "work_order", "created_at")
    autocomplete_fields = ("stock",)

    def has_add_permission(self, request):
        return request.user.has_perm("inventory.add_stockmovement")

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        employee = getattr(request.user, "employee", None)
        if employee and employee.role != employee.GENERAL_MANAGER:
            return queryset.filter(stock__branch=employee.branch)
        return queryset

    def save_model(self, request, obj, form, change):
        if change:
            return
        obj.movement_type = StockMovement.ADDITION
        with transaction.atomic():
            stock = BranchStock.objects.select_for_update().get(pk=obj.stock_id)
            stock.quantity = F("quantity") + obj.quantity
            stock.save(update_fields=["quantity"])
            super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        employee = getattr(request.user, "employee", None)
        if db_field.name == "stock" and employee and employee.role != employee.GENERAL_MANAGER:
            kwargs["queryset"] = BranchStock.objects.filter(branch=employee.branch)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
