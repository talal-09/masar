from dataclasses import dataclass

from billing.models import Invoice, InvoiceItem, Payment
from core.models import Branch, ContactMessage, Employee, WorkshopReview
from customers.models import Customer, Vehicle
from inventory.models import BranchStock, SparePart, StockMovement
from maintenance.models import (
    Notification,
    Quote,
    WorkOrder,
    WorkOrderImage,
    WorkOrderPart,
    WorkOrderService,
)
from services.models import Service, ServiceCategory


@dataclass(frozen=True)
class Resource:
    slug: str
    model: type
    icon: str
    section: str
    list_fields: tuple
    search_fields: tuple = ()
    select_related: tuple = ()
    order_by: tuple = ("-pk",)
    form_fields: tuple | None = None
    exclude_fields: tuple | None = None
    readonly: bool = False

    @property
    def title(self):
        return str(self.model._meta.verbose_name_plural)

    @property
    def singular(self):
        return str(self.model._meta.verbose_name)


RESOURCES = (
    Resource("branches", Branch, "⌂", "التشغيل", ("name", "phone", "business_hours", "is_active"), ("name", "phone", "address"), order_by=("name",)),
    Resource("employees", Employee, "♙", "التشغيل", ("user", "job_title", "branch", "role"), ("user__username", "user__first_name", "phone"), ("user", "branch"), order_by=("branch__name", "user__first_name")),
    Resource("customers", Customer, "◎", "العملاء", ("full_name", "phone", "email", "address"), ("full_name", "phone", "email"), ("user",), order_by=("full_name",)),
    Resource("vehicles", Vehicle, "◇", "العملاء", ("plate_number", "brand", "model", "customer", "mileage", "is_active"), ("plate_number", "chassis_number", "customer__full_name"), ("customer",), order_by=("-is_active", "brand")),
    Resource("work-orders", WorkOrder, "◫", "الصيانة", ("id", "customer", "vehicle", "branch", "status", "expected_delivery_at"), ("id", "customer__full_name", "vehicle__plate_number", "description"), ("customer", "vehicle", "branch", "assigned_technician"), form_fields=("branch", "customer", "vehicle", "created_by", "description", "mileage", "status", "scheduled_at", "expected_delivery_at", "center_notes", "assigned_technician", "started_at", "completed_at")),
    Resource("order-services", WorkOrderService, "⚙", "الصيانة", ("work_order", "service", "technician"), ("work_order__id", "service__name"), ("work_order", "service", "technician")),
    Resource("order-parts", WorkOrderPart, "◆", "الصيانة", ("work_order", "part", "quantity", "unit_price"), ("work_order__id", "part__name", "part__part_number"), ("work_order", "part")),
    Resource("order-images", WorkOrderImage, "▧", "الصيانة", ("work_order", "phase", "caption", "created_at"), ("work_order__id", "caption"), ("work_order",)),
    Resource("quotes", Quote, "◈", "الصيانة", ("work_order", "amount", "status", "created_at"), ("work_order__id", "notes"), ("work_order",)),
    Resource("notifications", Notification, "●", "التواصل", ("title", "user", "work_order", "is_read", "created_at"), ("title", "message", "user__username"), ("user", "work_order")),
    Resource("categories", ServiceCategory, "▦", "الخدمات", ("name",), ("name",), order_by=("name",)),
    Resource("services", Service, "✦", "الخدمات", ("name", "category", "price", "estimated_time", "active"), ("name", "category__name"), ("category",), order_by=("category__name", "name")),
    Resource("parts", SparePart, "⬡", "المخزون", ("name", "part_number", "supplier", "selling_price", "minimum_stock", "is_active"), ("name", "part_number", "supplier"), order_by=("name",)),
    Resource("stock", BranchStock, "▤", "المخزون", ("part", "branch", "quantity"), ("part__name", "part__part_number", "branch__name"), ("part", "branch"), order_by=("branch__name", "part__name")),
    Resource("stock-movements", StockMovement, "⇄", "المخزون", ("stock", "movement_type", "quantity", "work_order", "created_at"), ("stock__part__name", "note", "work_order__id"), ("stock", "work_order"), readonly=True),
    Resource("invoices", Invoice, "▣", "المالية", ("id", "work_order", "subtotal", "discount", "total", "status", "created_at"), ("id", "work_order__id", "work_order__customer__full_name"), ("work_order",)),
    Resource("invoice-items", InvoiceItem, "≡", "المالية", ("invoice", "item_type", "description", "quantity", "unit_price"), ("invoice__id", "description"), ("invoice",)),
    Resource("payments", Payment, "◉", "المالية", ("invoice", "amount", "method", "reference", "paid_at"), ("invoice__id", "reference"), ("invoice",)),
    Resource("messages", ContactMessage, "✉", "التواصل", ("subject", "user", "created_at", "is_resolved"), ("subject", "message", "user__username"), ("user",), form_fields=("user", "subject", "message", "is_resolved")),
    Resource("reviews", WorkshopReview, "★", "التواصل", ("customer", "rating", "comment", "is_approved", "created_at"), ("customer__full_name", "comment"), ("customer",), form_fields=("customer", "rating", "comment", "is_approved")),
)

RESOURCE_MAP = {resource.slug: resource for resource in RESOURCES}


def navigation_for(user):
    sections = {}
    for resource in RESOURCES:
        if user.is_superuser or user.has_perm(
            f"{resource.model._meta.app_label}.view_{resource.model._meta.model_name}"
        ):
            sections.setdefault(resource.section, []).append(resource)
    return sections
