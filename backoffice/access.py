from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def is_platform_manager(user):
    return user.is_active and user.is_staff and (
        user.is_superuser or hasattr(user, "employee")
    )


def management_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(
                request.get_full_path(),
                login_url="backoffice:login",
            )
        if not is_platform_manager(request.user):
            messages.error(request, "هذه البوابة مخصصة لفريق إدارة المركز فقط.")
            return redirect("backoffice:login")
        return view_func(request, *args, **kwargs)

    return wrapped


def require_model_permission(user, model, action):
    if user.is_superuser:
        return
    permission = f"{model._meta.app_label}.{action}_{model._meta.model_name}"
    if not user.has_perm(permission):
        raise PermissionDenied("لا تملك صلاحية تنفيذ هذا الإجراء.")


def scope_queryset(queryset, user):
    if user.is_superuser:
        return queryset

    employee = getattr(user, "employee", None)
    if employee is None or employee.role == employee.GENERAL_MANAGER:
        return queryset

    branch_id = employee.branch_id
    model_name = queryset.model._meta.model_name
    branch_lookups = {
        "branch": "pk",
        "employee": "branch_id",
        "workorder": "branch_id",
        "workorderservice": "work_order__branch_id",
        "workorderpart": "work_order__branch_id",
        "workorderimage": "work_order__branch_id",
        "quote": "work_order__branch_id",
        "invoice": "work_order__branch_id",
        "invoiceitem": "invoice__work_order__branch_id",
        "payment": "invoice__work_order__branch_id",
        "branchstock": "branch_id",
        "stockmovement": "stock__branch_id",
    }
    lookup = branch_lookups.get(model_name)
    if lookup:
        return queryset.filter(**{lookup: branch_id})
    return queryset
