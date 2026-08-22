from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import get_language

from billing.models import Invoice, Payment
from core.models import Branch
from customers.models import Customer, Vehicle
from core.models import Employee
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


@management_required
def work_order_options(request):
    require_model_permission(request.user, WorkOrder, "view")
    option_type = request.GET.get("type", "")
    parent_id = request.GET.get("parent", "")
    if not parent_id.isdigit():
        return JsonResponse({"options": []})

    if option_type == "vehicles":
        queryset = Vehicle.objects.filter(
            customer_id=parent_id,
            is_active=True,
        ).order_by("brand", "model", "year")
    elif option_type in {"technicians", "receptionists"}:
        role = (
            Employee.TECHNICIAN
            if option_type == "technicians"
            else Employee.RECEPTIONIST
        )
        queryset = scope_queryset(
            Employee.objects.filter(
                branch_id=parent_id,
                role=role,
                user__is_active=True,
            ).select_related("user"),
            request.user,
        ).order_by("user__first_name", "user__username")
    else:
        return JsonResponse({"options": []}, status=400)

    return JsonResponse({
        "options": [
            {"value": item.pk, "label": str(item)}
            for item in queryset
        ]
    })


@management_required
def invoice_preview(request):
    require_model_permission(request.user, Invoice, "view")
    work_order_id = request.GET.get("work_order", "")
    invoice_id = request.GET.get("invoice", "")
    try:
        discount = max(
            Decimal(request.GET.get("discount", "0")),
            Decimal("0.00"),
        )
    except (ArithmeticError, ValueError):
        discount = Decimal("0.00")

    if invoice_id.isdigit():
        invoice = get_object_or_404(
            scope_queryset(Invoice.objects.all(), request.user),
            pk=invoice_id,
        )
        service_total = invoice.services_total
        part_total = invoice.parts_total
    elif work_order_id.isdigit():
        work_order = get_object_or_404(
            scope_queryset(WorkOrder.objects.all(), request.user),
            pk=work_order_id,
        )
        service_total = sum(
            (
                item.service.price
                for item in work_order.services.select_related("service")
            ),
            Decimal("0.00"),
        )
        part_total = sum(
            (
                item.unit_price * item.quantity
                for item in work_order.installed_parts.all()
            ),
            Decimal("0.00"),
        )
    else:
        return JsonResponse({"error": "اختر أمر الصيانة أولًا."}, status=400)

    subtotal = service_total + part_total
    taxable = max(subtotal - discount, Decimal("0.00"))
    tax = (taxable * Invoice.TAX_RATE).quantize(Decimal("0.01"))
    return JsonResponse({
        "services": f"{service_total:.2f}",
        "parts": f"{part_total:.2f}",
        "subtotal": f"{subtotal:.2f}",
        "tax": f"{tax:.2f}",
        "total": f"{taxable + tax:.2f}",
    })


def is_english():
    return (get_language() or "ar").startswith("en")


def is_general_manager(user):
    employee = getattr(user, "employee", None)
    return user.is_superuser or (
        employee and employee.role == Employee.GENERAL_MANAGER
    )


def workshop_metrics(queryset):
    now = timezone.now()
    today = timezone.localdate()
    return queryset.aggregate(
        in_center=Count("id", filter=Q(status__in=WorkOrder.ACTIVE_STATUSES)),
        new=Count("id", filter=Q(status=WorkOrder.NEW)),
        inspection=Count("id", filter=Q(status=WorkOrder.INSPECTION)),
        inspected=Count("id", filter=Q(status=WorkOrder.INSPECTED)),
        awaiting_approval=Count("id", filter=Q(status=WorkOrder.AWAITING_APPROVAL)),
        approved=Count("id", filter=Q(status=WorkOrder.APPROVED)),
        working=Count("id", filter=Q(status=WorkOrder.WORKING)),
        awaiting_parts=Count("id", filter=Q(status=WorkOrder.AWAITING_PARTS)),
        testing=Count("id", filter=Q(status=WorkOrder.TESTING)),
        ready_for_delivery=Count("id", filter=Q(status=WorkOrder.READY_FOR_DELIVERY)),
        overdue=Count(
            "id",
            filter=(
                Q(expected_delivery_at__lt=now)
                & ~Q(status__in=(WorkOrder.DELIVERED, WorkOrder.CANCELLED))
            ),
        ),
        delivered_today=Count(
            "id",
            filter=Q(status=WorkOrder.DELIVERED, delivered_at__date=today),
        ),
        active_orders=Count("id", filter=Q(status__in=WorkOrder.ACTIVE_STATUSES)),
    )


def work_order_list_url(params=None):
    url = reverse("backoffice:resource-list", args=["work-orders"])
    if params:
        from urllib.parse import urlencode
        return f"{url}?{urlencode(params)}"
    return url


@management_required
def dashboard(request):
    all_work_orders = scope_queryset(
        WorkOrder.objects.select_related("customer", "vehicle", "branch"),
        request.user,
    )
    general_manager = is_general_manager(request.user)
    branches = Branch.objects.filter(is_active=True).order_by("name")
    selected_branch = request.GET.get("branch", "") if general_manager else ""
    if selected_branch and selected_branch.isdigit() and branches.filter(pk=selected_branch).exists():
        work_orders = all_work_orders.filter(branch_id=selected_branch)
    else:
        selected_branch = ""
        work_orders = all_work_orders

    metrics = workshop_metrics(work_orders)
    branch_param = {"branch": selected_branch} if selected_branch else {}
    metric_definitions = (
        ("in_center", "السيارات الموجودة حاليًا", "Vehicles currently in center", {"active": "1"}),
        ("new", "جديدة / تم استقبالها", "New / received", {"status": WorkOrder.NEW}),
        ("inspection", "جاري فحصها", "Under inspection", {"status": WorkOrder.INSPECTION}),
        ("inspected", "تم فحصها", "Inspected", {"status": WorkOrder.INSPECTED}),
        ("awaiting_approval", "بانتظار موافقة العميل", "Awaiting customer approval", {"status": WorkOrder.AWAITING_APPROVAL}),
        ("approved", "معتمدة ولم يبدأ العمل", "Approved, not started", {"status": WorkOrder.APPROVED}),
        ("working", "قيد الصيانة", "Under maintenance", {"status": WorkOrder.WORKING}),
        ("awaiting_parts", "بانتظار قطع غيار", "Awaiting parts", {"status": WorkOrder.AWAITING_PARTS}),
        ("testing", "قيد الاختبار", "Under testing", {"status": WorkOrder.TESTING}),
        ("ready_for_delivery", "جاهزة للتسليم", "Ready for delivery", {"status": WorkOrder.READY_FOR_DELIVERY}),
        ("overdue", "متأخرة عن التسليم", "Overdue delivery", {"overdue": "1"}),
        ("delivered_today", "تم تسليمها اليوم", "Delivered today", {"delivered_today": "1"}),
        ("active_orders", "أوامر الصيانة النشطة", "Active work orders", {"active": "1"}),
    )
    metric_cards = [
        {
            "key": key,
            "label": ar_label if not is_english() else en_label,
            "value": metrics[key],
            "url": work_order_list_url({**params, **branch_param}),
        }
        for key, ar_label, en_label, params in metric_definitions
    ]
    attention = [card for card in metric_cards if card["key"] in {
        "overdue", "awaiting_approval", "awaiting_parts", "ready_for_delivery"
    }]

    branch_comparison = []
    if general_manager:
        comparison_data = {
            row["branch_id"]: row
            for row in all_work_orders.values("branch_id").annotate(
                active=Count("id", filter=Q(status__in=WorkOrder.ACTIVE_STATUSES)),
                overdue=Count("id", filter=Q(expected_delivery_at__lt=timezone.now()) & ~Q(status__in=(WorkOrder.DELIVERED, WorkOrder.CANCELLED))),
                inspection=Count("id", filter=Q(status=WorkOrder.INSPECTION)),
                working=Count("id", filter=Q(status=WorkOrder.WORKING)),
                ready=Count("id", filter=Q(status=WorkOrder.READY_FOR_DELIVERY)),
            )
        }
        for branch in branches:
            values = comparison_data.get(branch.pk, {})
            branch_comparison.append({
                "branch": branch,
                "active": values.get("active", 0),
                "overdue": values.get("overdue", 0),
                "inspection": values.get("inspection", 0),
                "working": values.get("working", 0),
                "ready": values.get("ready", 0),
                "url": f"{reverse('backoffice:dashboard')}?branch={branch.pk}",
            })

    context = base_context(
        request,
        page_title="Dashboard" if is_english() else "مركز القيادة",
        metrics=metrics,
        metric_cards=metric_cards,
        attention=attention,
        general_manager=general_manager,
        branches=branches,
        selected_branch=selected_branch,
        branch_comparison=branch_comparison,
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
    if resource.model is WorkOrder:
        status = request.GET.get("status", "")
        if status in dict(WorkOrder.STATUS):
            queryset = queryset.filter(status=status)
        branch = request.GET.get("branch", "")
        if branch.isdigit():
            queryset = queryset.filter(branch_id=branch)
        if request.GET.get("overdue") == "1":
            queryset = queryset.filter(expected_delivery_at__lt=timezone.now()).exclude(
                status__in=(WorkOrder.DELIVERED, WorkOrder.CANCELLED)
            )
        if request.GET.get("delivered_today") == "1":
            queryset = queryset.filter(
                status=WorkOrder.DELIVERED,
                delivered_at__date=timezone.localdate(),
            )
        if request.GET.get("active") == "1":
            queryset = queryset.filter(status__in=WorkOrder.ACTIVE_STATUSES)
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
    preserved_query = request.GET.copy()
    preserved_query.pop("page", None)
    context = base_context(
        request,
        page_title=resource.title,
        resource=resource,
        page=page,
        query=query,
        filters_active=any(
            request.GET.get(key)
            for key in ("status", "branch", "overdue", "delivered_today", "active")
        ),
        preserved_query=preserved_query.urlencode(),
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
        except ValidationError as error:
            messages.error(request, "; ".join(error.messages))
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
