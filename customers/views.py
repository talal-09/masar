from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render

from maintenance.models import WorkOrder

from .access import customer_required, get_owned_or_403
from .forms import CAR_BRANDS, CustomerProfileForm, VehicleForm
from .models import Vehicle


@customer_required
def profile(request):
    form = CustomerProfileForm(
        request.POST or None,
        instance=request.customer,
        user=request.user,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تم تحديث بياناتك بنجاح.")
        return redirect("customers:profile")
    return render(request, "customers/profile.html", {"form": form})


@customer_required
def change_password(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    for field in form.fields.values():
        field.widget.attrs["class"] = (
            "mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 "
            "outline-none focus:border-teal-500"
        )
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "تم تغيير كلمة المرور بنجاح.")
        return redirect("customers:profile")
    return render(request, "customers/password.html", {"form": form})


@customer_required
def vehicle_list(request):
    vehicles = Vehicle.objects.filter(
        customer=request.customer,
        is_active=True,
    )
    return render(request, "customers/vehicle_list.html", {"vehicles": vehicles})


@customer_required
def vehicle_create(request):
    form = VehicleForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        vehicle = form.save(commit=False)
        vehicle.customer = request.customer
        vehicle.save()
        messages.success(request, "تمت إضافة السيارة بنجاح.")
        return redirect("customers:vehicle-list")
    return render(
        request,
        "customers/vehicle_form.html",
        {"form": form, "car_brands": CAR_BRANDS},
    )


@customer_required
def vehicle_update(request, pk):
    vehicle = get_owned_or_403(Vehicle, request.customer, pk=pk)
    form = VehicleForm(request.POST or None, instance=vehicle)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تم تحديث بيانات السيارة.")
        return redirect("customers:vehicle-list")
    return render(
        request,
        "customers/vehicle_form.html",
        {"form": form, "vehicle": vehicle, "car_brands": CAR_BRANDS},
    )


@customer_required
def vehicle_delete(request, pk):
    vehicle = get_owned_or_403(Vehicle, request.customer, pk=pk)
    active_statuses = {"new", "inspection", "approved", "working"}
    if WorkOrder.objects.filter(
        vehicle=vehicle,
        status__in=active_statuses,
    ).exists():
        raise PermissionDenied("لا يمكن حذف سيارة عليها أمر صيانة نشط.")
    if request.method == "POST":
        vehicle.is_active = False
        vehicle.save(update_fields=["is_active"])
        messages.success(request, "تم حذف السيارة.")
        return redirect("customers:vehicle-list")
    return render(request, "customers/vehicle_confirm_delete.html", {"vehicle": vehicle})
