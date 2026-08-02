from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Avg
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect, render

from billing.models import Invoice
from customers.models import Customer
from maintenance.models import Notification, WorkOrder
from services.models import Service

from .forms import SignUpForm
from .forms_contact import ContactMessageForm, WorkshopReviewForm
from .models import Branch, WorkshopReview
from customers.access import customer_required
from backoffice.access import management_required


def home(request):
    customer = (
        getattr(request.user, "customer_profile", None)
        if request.user.is_authenticated
        else None
    )
    review_instance = (
        getattr(customer, "workshop_review", None) if customer else None
    )
    review_form = WorkshopReviewForm(
        request.POST or None,
        instance=review_instance,
    )
    if request.method == "POST":
        if customer is None:
            messages.info(request, "سجّل الدخول بحساب عميل لإضافة تقييمك.")
            return redirect_to_login(request.get_full_path())
        if review_form.is_valid():
            review = review_form.save(commit=False)
            review.customer = customer
            review.is_approved = False
            review.save()
            messages.success(
                request,
                "شكرًا لتقييمك. سيظهر بعد مراجعته من إدارة الورشة.",
            )
            return redirect("home")

    reviews = WorkshopReview.objects.filter(is_approved=True).select_related(
        "customer"
    )
    rating_summary = reviews.aggregate(average=Avg("rating"))
    context = {
        "branches": Branch.objects.filter(is_active=True).order_by("name"),
        "services": Service.objects.filter(active=True)
        .select_related("category")
        .order_by("category__name", "name")[:12],
        "reviews": reviews[:6],
        "reviews_count": reviews.count(),
        "average_rating": rating_summary["average"],
        "review_form": review_form,
        "customer_review": review_instance,
    }
    return render(request, "site/index.html", context)


@management_required
def center_system(request):
    return render(request, "site/center_system.html", {"center_system": True})


def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = form.save(commit=False)
            user.is_staff = False
            user.is_superuser = False
            user.email = form.cleaned_data["email"]
            user.save()
            user.groups.clear()
            user.user_permissions.clear()
            Customer.objects.create(
                user=user,
                full_name=form.cleaned_data["first_name"],
                phone=form.cleaned_data["phone"],
                email=form.cleaned_data["email"],
            )
        login(request, user)
        return redirect("dashboard")

    return render(request, "registration/signup.html", {"form": form})


@login_required
def dashboard(request):
    if request.user.is_staff:
        return redirect("backoffice:dashboard")

    customer = getattr(request.user, "customer_profile", None)
    if customer is None:
        logout(request)
        messages.error(
            request,
            "هذا الحساب غير مرتبط بملف عميل. تواصل مع إدارة المركز.",
        )
        return redirect("login")

    orders = WorkOrder.objects.filter(customer=customer).select_related(
        "vehicle", "branch"
    )
    notifications = Notification.objects.filter(user=request.user)
    recent_activity = []
    for order in orders.order_by("-created_at")[:4]:
        recent_activity.append({
            "title": f"طلب الصيانة WO-{order.pk}",
            "description": f"{order.vehicle} — {order.get_status_display()}",
            "date": order.created_at,
            "url": "maintenance:order-detail",
            "pk": order.pk,
        })
    for notification in notifications.order_by("-created_at")[:4]:
        recent_activity.append({
            "title": notification.title,
            "description": notification.message,
            "date": notification.created_at,
            "url": "maintenance:notifications",
            "pk": None,
        })
    recent_activity.sort(key=lambda item: item["date"], reverse=True)
    context = {
        "customer": customer,
        "vehicles_count": customer.vehicles.filter(is_active=True).count(),
        "work_orders_count": orders.count(),
        "in_progress_count": orders.filter(
            status__in=("new", "inspection", "approved", "working")
        ).count(),
        "completed_count": orders.filter(
            status__in=("completed", "delivered")
        ).count(),
        "unread_count": notifications.filter(is_read=False).count(),
        "invoices_count": Invoice.objects.filter(
            work_order__customer=customer
        ).count(),
        "recent_orders": orders.order_by("-created_at")[:5],
        "latest_order": orders.order_by("-created_at").first(),
        "recent_activity": recent_activity[:6],
    }
    return render(request, "dashboard.html", context)


@customer_required
def contact(request):
    form = ContactMessageForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        message = form.save(commit=False)
        message.user = request.user
        message.save()
        messages.success(request, "تم إرسال رسالتك إلى المركز.")
        return redirect("contact")
    previous_messages = request.user.contact_messages.all()[:10]
    return render(
        request,
        "contact.html",
        {"form": form, "previous_messages": previous_messages},
    )


@customer_required
def branch_list(request):
    branches = Branch.objects.filter(is_active=True)
    return render(request, "branches.html", {"branches": branches})


def custom_400(request, exception=None):
    return render(request, "400.html", status=400)


def custom_403(request, exception=None):
    return render(request, "403.html", status=403)


def custom_404(request, exception=None):
    return render(request, "404.html", status=404)


def custom_500(request):
    return render(request, "500.html", status=500)
