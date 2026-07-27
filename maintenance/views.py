from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from customers.access import customer_required, get_owned_or_403
from customers.models import Vehicle

from .forms import MaintenanceRequestForm
from .models import Notification, Quote, WorkOrder


@customer_required
def order_list(request):
    orders = (
        WorkOrder.objects.filter(customer=request.customer)
        .select_related("vehicle", "branch")
        .order_by("-created_at")
    )
    return render(request, "maintenance/order_list.html", {"orders": orders})


@customer_required
def order_create(request):
    form = MaintenanceRequestForm(
        request.POST or None,
        customer=request.customer,
    )
    if request.method == "POST" and form.is_valid():
        order = form.save(commit=False)
        if order.vehicle.customer_id != request.customer.pk:
            raise PermissionDenied("لا يمكنك إنشاء طلب لسيارة لا تملكها.")
        order.customer = request.customer
        order.created_by = None
        order.status = "new"
        order.save()
        messages.success(request, "تم إرسال طلب الصيانة وحجز الموعد.")
        return redirect("maintenance:order-detail", pk=order.pk)
    return render(request, "maintenance/order_form.html", {"form": form})


@customer_required
def order_detail(request, pk):
    order = get_owned_or_403(WorkOrder, request.customer, pk=pk)
    order = (
        WorkOrder.objects.select_related("vehicle", "branch")
        .prefetch_related(
            "services__service",
            "services__technician__user",
            "installed_parts__part",
            "images",
        )
        .get(pk=order.pk)
    )
    quote = getattr(order, "quote", None)
    invoice = getattr(order, "invoice", None)
    return render(
        request,
        "maintenance/order_detail.html",
        {
            "order": order,
            "quote": quote,
            "invoice": invoice,
            "show_technician": getattr(
                settings,
                "SHOW_TECHNICIAN_TO_CUSTOMERS",
                True,
            ),
        },
    )


@customer_required
def order_status(request, pk):
    order = get_owned_or_403(WorkOrder, request.customer, pk=pk)
    return JsonResponse(
        {
            "id": order.pk,
            "status": order.status,
            "status_display": str(order.get_status_display()),
            "updated_at": timezone.now().isoformat(),
        }
    )


@customer_required
def vehicle_history(request, vehicle_pk):
    vehicle = get_owned_or_403(Vehicle, request.customer, pk=vehicle_pk)
    orders = WorkOrder.objects.filter(vehicle=vehicle).order_by("-created_at")
    return render(
        request,
        "maintenance/vehicle_history.html",
        {"vehicle": vehicle, "orders": orders},
    )


@require_POST
@customer_required
def quote_response(request, pk, decision):
    quote = get_owned_or_403(Quote, request.customer, pk=pk)
    if quote.status != Quote.PENDING:
        messages.info(request, "تم تسجيل ردك على عرض السعر مسبقًا.")
        return redirect("maintenance:order-detail", pk=quote.work_order_id)
    if decision not in {"approve", "reject"}:
        raise PermissionDenied("قرار غير صالح.")
    quote.status = Quote.APPROVED if decision == "approve" else Quote.REJECTED
    quote.responded_at = timezone.now()
    quote.save(update_fields=["status", "responded_at"])
    messages.success(request, "تم تسجيل قرارك على عرض السعر.")
    return redirect("maintenance:order-detail", pk=quote.work_order_id)


@customer_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user)
    return render(
        request,
        "maintenance/notification_list.html",
        {"notifications": notifications},
    )


@require_POST
@customer_required
def notification_read(request, pk):
    notification = Notification.objects.filter(
        pk=pk,
        user=request.user,
    ).first()
    if notification is None:
        raise PermissionDenied("لا تملك صلاحية الوصول إلى هذا الإشعار.")
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    if notification.work_order_id:
        return redirect(
            "maintenance:order-detail",
            pk=notification.work_order_id,
        )
    return redirect("maintenance:notifications")
