from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from core.models import Branch
from customers.models import Customer, Vehicle
from inventory.models import BranchStock, SparePart
from maintenance.models import WorkOrder, WorkOrderPart, WorkOrderService
from services.models import Service, ServiceCategory

from .models import Invoice, InvoiceItem, Payment


class BillingLogicTests(TestCase):
    password = "SecurePass!2026"

    @classmethod
    def setUpTestData(cls):
        cls.branch = Branch.objects.create(
            name="فرع الفوترة", address="الرياض", phone="0117654321"
        )
        cls.customer = Customer.objects.create(
            full_name="عميل الفوترة", phone="0588888881"
        )
        cls.vehicle = Vehicle.objects.create(
            customer=cls.customer,
            plate_number="ف و ت 1",
            chassis_number="BILLING-CHASSIS-1",
            brand="Toyota",
            model="Camry",
            year=2025,
            color="White",
            mileage=5000,
        )
        cls.order = WorkOrder.objects.create(
            branch=cls.branch,
            customer=cls.customer,
            vehicle=cls.vehicle,
            description="أعمال فوترة",
            mileage=5000,
        )
        category = ServiceCategory.objects.create(name="خدمات الفوترة")
        cls.service_one = Service.objects.create(
            category=category,
            name="خدمة أولى",
            price=Decimal("100.00"),
            estimated_time=30,
        )
        cls.service_two = Service.objects.create(
            category=category,
            name="خدمة ثانية",
            price=Decimal("50.00"),
            estimated_time=20,
        )
        WorkOrderService.objects.create(
            work_order=cls.order, service=cls.service_one, technician=None
        )
        WorkOrderService.objects.create(
            work_order=cls.order, service=cls.service_two, technician=None
        )
        cls.part = SparePart.objects.create(
            name="قطعة فوترة",
            part_number="BILLING-PART-1",
            purchase_price=Decimal("20.00"),
            selling_price=Decimal("25.00"),
        )
        BranchStock.objects.create(
            branch=cls.branch, part=cls.part, quantity=10
        )
        WorkOrderPart.objects.create(
            work_order=cls.order,
            part=cls.part,
            quantity=2,
            unit_price=Decimal("25.00"),
        )
        cls.owner = User.objects.create_superuser(
            username="billing-owner",
            password=cls.password,
            email="owner@example.com",
        )

    def setUp(self):
        self.invoice = Invoice.objects.create(
            work_order=self.order,
            subtotal=Decimal("0.00"),
            tax=Decimal("0.00"),
            total=Decimal("0.00"),
        )
        self.invoice.recalculate(sync_from_work_order=True)

    def test_services_parts_tax_and_totals_are_calculated(self):
        self.assertEqual(self.invoice.services_total, Decimal("150.00"))
        self.assertEqual(self.invoice.parts_total, Decimal("50.00"))
        self.assertEqual(self.invoice.subtotal, Decimal("200.00"))
        self.assertEqual(self.invoice.tax, Decimal("30.00"))
        self.assertEqual(self.invoice.total, Decimal("230.00"))
        part_item = self.invoice.items.get(item_type=InvoiceItem.PART)
        self.assertEqual(part_item.line_total, Decimal("50.00"))

    def test_discount_recalculates_tax_and_total(self):
        self.invoice.discount = Decimal("20.00")
        self.invoice.recalculate()
        self.assertEqual(self.invoice.tax, Decimal("27.00"))
        self.assertEqual(self.invoice.total, Decimal("207.00"))

    def test_partial_then_complete_payments_update_status(self):
        Payment.objects.create(
            invoice=self.invoice, amount=Decimal("100.00"), method="card"
        )
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "partial")
        self.assertEqual(self.invoice.paid_amount, Decimal("100.00"))
        self.assertEqual(self.invoice.remaining_amount, Decimal("130.00"))

        Payment.objects.create(
            invoice=self.invoice, amount=Decimal("130.00"), method="cash"
        )
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "paid")
        self.assertEqual(self.invoice.remaining_amount, Decimal("0.00"))

    def test_overpayment_is_rejected_with_clear_message(self):
        with self.assertRaisesMessage(
            ValidationError,
            "قيمة الدفعة تتجاوز المبلغ المتبقي على الفاتورة",
        ):
            Payment.objects.create(
                invoice=self.invoice,
                amount=Decimal("230.01"),
                method="cash",
            )

    def test_zero_payment_is_rejected(self):
        with self.assertRaisesMessage(
            ValidationError,
            "مبلغ الدفع أكبر من صفر",
        ):
            Payment.objects.create(
                invoice=self.invoice,
                amount=Decimal("0.00"),
                method="cash",
            )

    def test_historical_service_price_does_not_change(self):
        original_total = self.invoice.total
        self.service_one.price = Decimal("999.00")
        self.service_one.save(update_fields=["price"])
        self.invoice.recalculate()
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.total, original_total)
        self.assertEqual(
            self.invoice.items.get(description="خدمة أولى").unit_price,
            Decimal("100.00"),
        )

    def test_negative_or_excessive_discount_is_rejected(self):
        self.invoice.discount = Decimal("-1.00")
        with self.assertRaisesMessage(ValidationError, "الخصم سالبًا"):
            self.invoice.recalculate()
        self.invoice.discount = Decimal("201.00")
        with self.assertRaisesMessage(ValidationError, "يتجاوز الخصم"):
            self.invoice.recalculate()

    def test_tampered_totals_are_ignored_by_management_form(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("backoffice:resource-edit", args=["invoices", self.invoice.pk]),
            {
                "work_order": self.order.pk,
                "discount": "10.00",
                "subtotal": "1.00",
                "tax": "1.00",
                "total": "1.00",
                "status": "paid",
            },
        )
        self.assertRedirects(
            response,
            reverse("backoffice:resource-list", args=["invoices"]),
        )
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.subtotal, Decimal("200.00"))
        self.assertEqual(self.invoice.tax, Decimal("28.50"))
        self.assertEqual(self.invoice.total, Decimal("218.50"))
        self.assertEqual(self.invoice.status, "pending")

    def test_invoice_create_and_edit_forms_preserve_calculated_data(self):
        self.client.force_login(self.owner)
        edit_response = self.client.get(
            reverse("backoffice:resource-edit", args=["invoices", self.invoice.pk])
        )
        self.assertEqual(edit_response.status_code, 200)
        self.assertEqual(
            set(edit_response.context["form"].fields),
            {"work_order", "discount"},
        )

        second_vehicle = Vehicle.objects.create(
            customer=self.customer,
            plate_number="ف و ت 2",
            chassis_number="BILLING-CHASSIS-2",
            brand="Honda",
            model="Accord",
            year=2024,
            color="Black",
            mileage=8000,
        )
        second_order = WorkOrder.objects.create(
            branch=self.branch,
            customer=self.customer,
            vehicle=second_vehicle,
            description="فاتورة جديدة",
            mileage=8000,
        )
        WorkOrderService.objects.create(
            work_order=second_order,
            service=self.service_one,
            technician=None,
        )
        create_response = self.client.post(
            reverse("backoffice:resource-add", args=["invoices"]),
            {
                "work_order": second_order.pk,
                "discount": "10.00",
                "subtotal": "1.00",
                "tax": "1.00",
                "total": "1.00",
                "status": "paid",
            },
        )
        self.assertRedirects(
            create_response,
            reverse("backoffice:resource-list", args=["invoices"]),
        )
        created = Invoice.objects.get(work_order=second_order)
        self.assertEqual(created.subtotal, Decimal("100.00"))
        self.assertEqual(created.tax, Decimal("13.50"))
        self.assertEqual(created.total, Decimal("103.50"))
        self.assertEqual(created.status, "pending")

    def test_invoice_preview_uses_backend_calculation(self):
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse("backoffice:invoice-preview"),
            {
                "invoice": self.invoice.pk,
                "work_order": self.order.pk,
                "discount": "20.00",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "services": "150.00",
            "parts": "50.00",
            "subtotal": "200.00",
            "tax": "27.00",
            "total": "207.00",
        })

# Create your tests here.
