from django.contrib import admin

from .models import Branch, ContactMessage, Employee, WorkshopReview


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "phone",
        "is_active",
    )

    search_fields = (
        "name",
        "phone",
    )

    list_filter = (
        "is_active",
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        employee = getattr(request.user, "employee", None)
        if employee and employee.role != employee.GENERAL_MANAGER:
            return queryset.filter(pk=employee.branch_id)
        return queryset


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "branch",
        "job_title",
        "role",
        "phone",
    )

    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "phone",
    )

    list_filter = (
        "branch",
        "job_title",
        "role",
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        employee = getattr(request.user, "employee", None)
        if employee and employee.role != employee.GENERAL_MANAGER:
            return queryset.filter(branch=employee.branch)
        return queryset


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "subject", "created_at", "is_resolved")
    list_filter = ("is_resolved", "created_at")
    search_fields = ("user__username", "subject", "message")
    readonly_fields = ("user", "subject", "message", "created_at")


@admin.register(WorkshopReview)
class WorkshopReviewAdmin(admin.ModelAdmin):
    list_display = ("customer", "rating", "is_approved", "created_at")
    list_filter = ("rating", "is_approved", "created_at")
    search_fields = ("customer__full_name", "comment")
    readonly_fields = ("customer", "rating", "comment", "created_at")
    actions = ("approve_reviews",)

    @admin.action(description="اعتماد التقييمات المحددة للنشر")
    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
