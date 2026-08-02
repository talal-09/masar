from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, F, Q, Sum
from django.db.models.deletion import ProtectedError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.translation import get_language

from billing.models import Invoice, Payment
from core.models import Branch, ContactMessage, WorkshopReview
from customers.models import Customer, Vehicle
from inventory.models import BranchStock, SparePart
from maintenance.models import WorkOrder

from .access import (
    is_platform_manager,
    management_required,
    require_model_permission,
    scope_queryset,
)
from .forms import ManagementAuthenticationForm, form_for_resource
from .registry import RESOURCE_MAP, navigation_for


class ManagementLoginView(LoginView):
    template_name = "backoffice/login.html"
    authentication_form = ManagementAuthenticationForm
    redirect_authenticated_user = False

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and is_platform_manager(request.user):
            return redirect("backoffice:dashboard")
        if request.user.is_authenticated:
            logout(request)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return self.get_redirect_url() or str(reverse_lazy("backoffice:dashboard"))


def get_resource(slug):
    try:
        return RESOURCE_MAP[slug]
    except KeyError as exc:
        raise Http404("القسم المطلوب غير موجود.") from exc


def base_context(request, **extra):
    employee = getattr(request.user, "employee", None)
    context = {
        "management_navigation": navigation_for(request.user),
        "management_employee": employee,
    }
    context.update(extra)
    return context


def is_english():
    return (get_language() or "ar").startswith("en")


@management_required
def dashboard(request):
    work_orders = scope_queryset(
        WorkOrder.objects.select_related("customer", "vehicle", "branch"),
        request.user,
    )
    invoices = scope_queryset(Invoice.objects.all(), request.user)
    payments = scope_queryset(Payment.objects.all(), request.user)
    stocks = scope_queryset(
        BranchStock.objects.select_related("part", "branch"),
        request.user,
    )
    active_statuses = ("new", "inspection", "approved", "working")
    status_counts = {
        item["status"]: item["total"]
        for item in work_orders.values("status").annotate(total=Count("id"))
    }
    status_pipeline = [
        {
            "key": key,
            "label": label,
            "count": status_counts.get(key, 0),
        }
        for key, label in WorkOrder.STATUS
    ]
    revenue = payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    outstanding = sum(
        (invoice.remaining_amount for invoice in invoices),
        Decimal("0.00"),
    )
    context = base_context(
        request,
        page_title="Dashboard" if is_english() else "مركز القيادة",
        stats={
            "active_orders": work_orders.filter(status__in=active_statuses).count(),
            "customers": Customer.objects.count(),
            "vehicles": Vehicle.objects.filter(is_active=True).count(),
            "revenue": revenue,
        },
        status_pipeline=status_pipeline,
        recent_orders=work_orders.order_by("-created_at")[:7],
        low_stock=stocks.filter(quantity__lte=F("part__minimum_stock")).order_by("quantity")[:6],
        outstanding=outstanding,
        pending_messages=ContactMessage.objects.filter(is_resolved=False).count(),
        pending_reviews=WorkshopReview.objects.filter(is_approved=False).count(),
        active_branches=Branch.objects.filter(is_active=True).count(),
        total_parts=SparePart.objects.filter(is_active=True).count(),
    )
    return render(request, "backoffice/dashboard.html", context)


@management_required
def resource_list(request, slug):
    resource = get_resource(slug)
    require_model_permission(request.user, resource.model, "view")
    queryset = resource.model.objects.all()
    if resource.select_related:
        queryset = queryset.select_related(*resource.select_related)
    queryset = scope_queryset(queryset, request.user).order_by(*resource.order_by)
    query = request.GET.get("q", "").strip()
    if query and resource.search_fields:
        conditions = Q()
        for field in resource.search_fields:
            lookup = f"{field}__icontains"
            if field == "id" or field.endswith("__id"):
                if query.isdigit():
                    conditions |= Q(**{field: int(query)})
            else:
                conditions |= Q(**{lookup: query})
        queryset = queryset.filter(conditions)
    paginator = Paginator(queryset, 20)
    page = paginator.get_page(request.GET.get("page"))
    context = base_context(
        request,
        page_title=resource.title,
        resource=resource,
        page=page,
        query=query,
        can_add=not resource.readonly and (
            request.user.is_superuser
            or request.user.has_perm(
                f"{resource.model._meta.app_label}.add_{resource.model._meta.model_name}"
            )
        ),
    )
    return render(request, "backoffice/resource_list.html", context)


@management_required
def resource_form(request, slug, pk=None):
    resource = get_resource(slug)
    if resource.readonly:
        raise PermissionDenied("هذا السجل للعرض فقط.")
    action = "change" if pk else "add"
    require_model_permission(request.user, resource.model, action)
    queryset = scope_queryset(resource.model.objects.all(), request.user)
    instance = get_object_or_404(queryset, pk=pk) if pk else None
    form_class = form_for_resource(resource)
    form = form_class(
        request.POST or None,
        request.FILES or None,
        instance=instance,
        request_user=request.user,
    )
    if request.method == "POST" and form.is_valid():
        saved = form.save()
        messages.success(
            request,
            (
                f"{resource.singular} was {'updated' if instance else 'added'} successfully."
                if is_english()
                else f"تم {'تحديث' if instance else 'إضافة'} {resource.singular} بنجاح."
            ),
        )
        return redirect("backoffice:resource-list", slug=slug)
    context = base_context(
        request,
        page_title=f"{'تعديل' if instance else 'إضافة'} {resource.singular}",
        resource=resource,
        form=form,
        instance=instance,
    )
    return render(request, "backoffice/resource_form.html", context)


@management_required
def resource_delete(request, slug, pk):
    resource = get_resource(slug)
    if resource.readonly:
        raise PermissionDenied("هذا السجل للعرض فقط.")
    require_model_permission(request.user, resource.model, "delete")
    queryset = scope_queryset(resource.model.objects.all(), request.user)
    instance = get_object_or_404(queryset, pk=pk)
    if request.method == "POST":
        try:
            instance.delete()
            messages.success(
                request,
                f"{resource.singular} was deleted successfully."
                if is_english()
                else f"تم حذف {resource.singular} بنجاح.",
            )
        except ProtectedError:
            messages.error(
                request,
                "Deletion failed because related data exists. Disable the record or update its relationships first."
                if is_english()
                else "تعذر الحذف لوجود بيانات مرتبطة. عطّل السجل أو عدّل ارتباطاته أولًا.",
            )
        return redirect("backoffice:resource-list", slug=slug)
    return render(
        request,
        "backoffice/confirm_delete.html",
        base_context(
            request,
            page_title=f"حذف {resource.singular}",
            resource=resource,
            instance=instance,
        ),
    )


@management_required
def logout_view(request):
    if request.method == "POST":
        logout(request)
        return redirect("backoffice:login")
    return redirect("backoffice:dashboard")
