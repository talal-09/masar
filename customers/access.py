from functools import wraps

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from .models import Customer


def get_request_customer(request):
    if request.user.is_staff:
        raise PermissionDenied("هذه الصفحة مخصصة للعملاء فقط.")
    try:
        return request.user.customer_profile
    except Customer.DoesNotExist as exc:
        raise PermissionDenied("لا يوجد ملف عميل مرتبط بهذا الحساب.") from exc


def customer_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login

            return redirect_to_login(request.get_full_path())
        request.customer = get_request_customer(request)
        return view_func(request, *args, **kwargs)

    return wrapped


def get_owned_or_403(model, customer, **lookup):
    obj = get_object_or_404(model, **lookup)
    owner_id = (
        obj.customer_id
        if hasattr(obj, "customer_id")
        else obj.work_order.customer_id
    )
    if owner_id != customer.pk:
        raise PermissionDenied("لا تملك صلاحية الوصول إلى هذه البيانات.")
    return obj
