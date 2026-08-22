from decimal import Decimal
from io import BytesIO

from django.contrib.auth.models import Group, Permission, User
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from pypdf import PdfReader

from billing.models import Invoice
from billing.models import Payment
from core.models import Branch, Employee, WorkshopReview
from customers.models import Customer, Vehicle
from inventory.models import BranchStock, SparePart, StockMovement
from maintenance.models import Quote, WorkOrder, WorkOrderPart, WorkOrderService
from services.models import Service, ServiceCategory
from customers.forms import CAR_BRANDS, VehicleForm
from core.views import custom_500


class CustomerPermissionTests(TestCase):
    password = "SecurePass!2026"

    @classmethod
    def setUpTestData(cls):
        cls.branch = Branch.objects.create(
            name="الفرع الرئيسي",
            address="الرياض",
            phone="0110000000",
        )
        cls.user_one = User.objects.create_user(
            username="customer-one",
            password=cls.password,
        )
        cls.customer_one = Customer.objects.create(
            user=cls.user_one,
            full_name="العميل الأول",
            phone="0500000001",
            email="one@example.com",
        )
        cls.vehicle_one = Vehicle.objects.create(
            customer=cls.customer_one,
            plate_number="أ ب ج 1",
            chassis_number="CHASSIS-ONE",
            brand="Toyota",
            model="Camry",
            year=2025,
            color="White",
            mileage=12000,
        )
        cls.order_one = WorkOrder.objects.create(
            branch=cls.branch,
            customer=cls.customer_one,
            vehicle=cls.vehicle_one,
            description="صيانة دورية",
            mileage=12000,
        )
        cls.invoice_one = Invoice.objects.create(
            work_order=cls.order_one,
            subtotal=Decimal("100.00"),
            tax=Decimal("15.00"),
            total=Decimal("115.00"),
        )
        cls.quote_one = Quote.objects.create(
            work_order=cls.order_one,
            amount=Decimal("115.00"),
        )

        cls.user_two = User.objects.create_user(
            username="customer-two",
            password=cls.password,
        )
        cls.customer_two = Customer.objects.create(
            user=cls.user_two,
            full_name="العميل الثاني",
            phone="0500000002",
            email="two@example.com",
        )
        cls.vehicle_two = Vehicle.objects.create(
            customer=cls.customer_two,
            plate_number="د هـ و 2",
            chassis_number="CHASSIS-TWO",
            brand="Nissan",
            model="Patrol",
            year=2024,
            color="Black",
            mileage=9000,
        )
        cls.order_two = WorkOrder.objects.create(
            branch=cls.branch,
            customer=cls.customer_two,
            vehicle=cls.vehicle_two,
            description="فحص",
            mileage=9000,
        )
        cls.invoice_two = Invoice.objects.create(
            work_order=cls.order_two,
            subtotal=Decimal("200.00"),
            tax=Decimal("30.00"),
            total=Decimal("230.00"),
        )
        cls.quote_two = Quote.objects.create(
            work_order=cls.order_two,
            amount=Decimal("230.00"),
        )

    def login_customer_one(self):
        self.client.force_login(self.user_one)

    def test_public_home_is_for_workshop_customers(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "احجز موعد صيانة")
        self.assertContains(response, "خدمات الورشة")
        self.assertContains(response, "آراء عملائنا")
        self.assertNotContains(response, "نظّم عملاءك")

    def test_customer_site_has_no_center_system_links(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "نظام المراكز")
        self.assertNotContains(response, reverse("backoffice:dashboard"))

    def test_staff_account_cannot_login_from_customer_portal(self):
        staff_user = User.objects.create_user(
            username="portal-staff",
            password=self.password,
            is_staff=True,
        )

        response = self.client.post(
            reverse("login"),
            {
                "username": staff_user.username,
                "password": self.password,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "بوابة الموظفين فقط")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_customer_can_submit_review_pending_approval(self):
        self.login_customer_one()

        response = self.client.post(
            reverse("home"),
            {"rating": 5, "comment": "خدمة ممتازة وواضحة."},
        )

        self.assertRedirects(response, reverse("home"))
        review = WorkshopReview.objects.get(customer=self.customer_one)
        self.assertEqual(review.rating, 5)
        self.assertFalse(review.is_approved)

    def test_vehicle_form_has_40_brands_and_years_1960_to_2027(self):
        form = VehicleForm()
        brand_values = [
            value for value, _label in form.fields["brand"].widget.choices if value
        ]
        year_values = [
            value for value, _label in form.fields["year"].widget.choices if value
        ]

        self.assertEqual(len(CAR_BRANDS), 40)
        self.assertEqual(len(brand_values), 40)
        self.assertEqual(max(year_values), 2027)
        self.assertEqual(min(year_values), 1960)
        self.assertEqual(len(year_values), 68)

    def test_vehicle_form_rejects_model_from_another_brand(self):
        form = VehicleForm(
            data={
                "plate_number": "ج د هـ 3",
                "chassis_number": "CHASSIS-MISMATCH",
                "brand": "Toyota",
                "model": "Patrol",
                "year": 2027,
                "color": "White",
                "mileage": 0,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("model", form.errors)

    def test_signup_creates_plain_customer_without_privileges(self):
        group = Group.objects.create(name="موظفون")
        permission = Permission.objects.first()
        group.permissions.add(permission)

        response = self.client.post(
            reverse("signup"),
            {
                "first_name": "عميل جديد",
                "email": "new@example.com",
                "phone": "0500000099",
                "username": "new-customer",
                "password1": self.password,
                "password2": self.password,
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        user = User.objects.get(username="new-customer")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.groups.exists())
        self.assertFalse(user.user_permissions.exists())
        self.assertEqual(user.customer_profile.phone, "0500000099")
        self.assertFalse(hasattr(user, "employee"))

    def test_customer_cannot_enter_django_admin(self):
        self.login_customer_one()
        response = self.client.get(reverse("admin:index"))
        self.assertRedirects(response, reverse("dashboard"))

    def test_unlinked_account_sees_login_error_instead_of_403(self):
        unlinked_user = User.objects.create_user(
            username="unlinked-user",
            password=self.password,
        )

        response = self.client.post(
            reverse("login"),
            {
                "username": unlinked_user.username,
                "password": self.password,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "هذا الحساب غير مرتبط بملف عميل")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logged_in_unlinked_account_is_returned_to_login(self):
        unlinked_user = User.objects.create_user(
            username="unlinked-session",
            password=self.password,
        )
        self.client.force_login(unlinked_user)

        response = self.client.get(reverse("dashboard"))

        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_dashboard_and_lists_only_show_own_data(self):
        self.login_customer_one()
        dashboard = self.client.get(reverse("dashboard"))
        self.assertContains(dashboard, f"WO-{self.order_one.pk}")
        self.assertNotContains(dashboard, f"WO-{self.order_two.pk}")

        vehicles = self.client.get(reverse("customers:vehicle-list"))
        self.assertContains(vehicles, "Toyota")
        self.assertNotContains(vehicles, "Nissan")

        orders = self.client.get(reverse("maintenance:order-list"))
        self.assertContains(orders, f"WO-{self.order_one.pk}")
        self.assertNotContains(orders, f"WO-{self.order_two.pk}")

        invoices = self.client.get(reverse("billing:invoice-list"))
        self.assertContains(invoices, f"INV-{self.invoice_one.pk}")
        self.assertNotContains(invoices, f"INV-{self.invoice_two.pk}")

    def test_foreign_objects_return_403(self):
        self.login_customer_one()
        protected_urls = [
            reverse("customers:vehicle-update", args=[self.vehicle_two.pk]),
            reverse("customers:vehicle-delete", args=[self.vehicle_two.pk]),
            reverse("maintenance:vehicle-history", args=[self.vehicle_two.pk]),
            reverse("maintenance:order-detail", args=[self.order_two.pk]),
            reverse("maintenance:order-status", args=[self.order_two.pk]),
            reverse("billing:invoice-detail", args=[self.invoice_two.pk]),
            reverse("billing:invoice-pdf", args=[self.invoice_two.pk]),
        ]
        for url in protected_urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

        quote_url = reverse(
            "maintenance:quote-response",
            args=[self.quote_two.pk, "approve"],
        )
        self.assertEqual(self.client.post(quote_url).status_code, 403)

    def test_cannot_create_order_for_another_customers_vehicle(self):
        self.login_customer_one()
        response = self.client.post(
            reverse("maintenance:order-create"),
            {
                "vehicle": self.vehicle_two.pk,
                "branch": self.branch.pk,
                "description": "طلب غير مصرح",
                "mileage": 9000,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            WorkOrder.objects.filter(description="طلب غير مصرح").exists()
        )

    def test_cannot_create_second_active_order_for_same_vehicle(self):
        self.login_customer_one()

        response = self.client.post(
            reverse("maintenance:order-create"),
            {
                "vehicle": self.vehicle_one.pk,
                "branch": self.branch.pk,
                "description": "طلب صيانة مكرر",
                "mileage": 12100,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"WO-{self.order_one.pk}")
        self.assertContains(response, "طلب صيانة نشط بالفعل")
        self.assertFalse(
            WorkOrder.objects.filter(description="طلب صيانة مكرر").exists()
        )

    def test_single_vehicle_is_selected_by_default(self):
        self.login_customer_one()

        response = self.client.get(reverse("maintenance:order-create"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["form"].fields["vehicle"].initial,
            self.vehicle_one,
        )

    def test_active_vehicle_cannot_be_deleted(self):
        self.login_customer_one()
        response = self.client.post(
            reverse("customers:vehicle-delete", args=[self.vehicle_one.pk])
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(
            Vehicle.objects.filter(
                pk=self.vehicle_one.pk,
                is_active=True,
            ).exists()
        )

    def test_quote_response_is_limited_to_owner(self):
        self.login_customer_one()
        response = self.client.post(
            reverse(
                "maintenance:quote-response",
                args=[self.quote_one.pk, "approve"],
            )
        )
        self.assertRedirects(
            response,
            reverse("maintenance:order-detail", args=[self.order_one.pk]),
        )
        self.quote_one.refresh_from_db()
        self.assertEqual(self.quote_one.status, Quote.APPROVED)

    def test_invoice_pdf_is_valid_and_owned(self):
        self.login_customer_one()
        response = self.client.get(
            reverse("billing:invoice-pdf", args=[self.invoice_one.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        reader = PdfReader(BytesIO(response.content))
        self.assertEqual(len(reader.pages), 1)

    def test_pages_require_authentication(self):
        for url in [
            reverse("dashboard"),
            reverse("customers:profile"),
            reverse("customers:vehicle-list"),
            reverse("maintenance:order-list"),
            reverse("billing:invoice-list"),
        ]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse("login"), response.url)

    @override_settings(DEBUG=False)
    def test_custom_404_page_has_correct_status_and_branding(self):
        response = self.client.get("/page-that-does-not-exist/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "لم نجد هذه الصفحة", status_code=404)
        self.assertContains(response, "مَسَار", status_code=404)

    @override_settings(DEBUG=False)
    def test_foreign_object_uses_custom_403_page(self):
        self.login_customer_one()
        response = self.client.get(
            reverse("maintenance:order-detail", args=[self.order_two.pk])
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "لا تملك صلاحية الوصول", status_code=403)

    def test_custom_500_handler_hides_exception_details(self):
        response = custom_500(RequestFactory().get("/"))
        self.assertEqual(response.status_code, 500)
        self.assertNotContains(response, "Traceback", status_code=500)

    def test_past_appointment_is_rejected(self):
        WorkOrder.objects.filter(pk=self.order_one.pk).update(status="completed")
        self.order_one.refresh_from_db()
        self.login_customer_one()
        response = self.client.post(
            reverse("maintenance:order-create"),
            {
                "vehicle": self.vehicle_one.pk,
                "branch": self.branch.pk,
                "scheduled_at": (timezone.now() - timedelta(days=1)).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "description": "موعد قديم",
                "mileage": 12100,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "اختر موعدًا حاليًا أو قادمًا")
        self.assertFalse(WorkOrder.objects.filter(description="موعد قديم").exists())

    def test_vehicle_delete_get_only_shows_confirmation(self):
        WorkOrder.objects.filter(pk=self.order_one.pk).update(status="completed")
        self.order_one.refresh_from_db()
        self.login_customer_one()
        response = self.client.get(
            reverse("customers:vehicle-delete", args=[self.vehicle_one.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.vehicle_one.refresh_from_db()
        self.assertTrue(self.vehicle_one.is_active)

    def test_customer_portal_pages_render_for_owner(self):
        self.login_customer_one()
        urls = [
            reverse("dashboard"),
            reverse("customers:profile"),
            reverse("customers:password"),
            reverse("customers:vehicle-list"),
            reverse("customers:vehicle-create"),
            reverse("maintenance:order-list"),
            reverse("maintenance:order-create"),
            reverse("maintenance:order-detail", args=[self.order_one.pk]),
            reverse("maintenance:order-status", args=[self.order_one.pk]),
            reverse(
                "maintenance:vehicle-history",
                args=[self.vehicle_one.pk],
            ),
            reverse("maintenance:notifications"),
            reverse("billing:invoice-list"),
            reverse("billing:invoice-detail", args=[self.invoice_one.pk]),
            reverse("branches"),
            reverse("contact"),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_completed_vehicle_is_soft_deleted_without_losing_history(self):
        WorkOrder.objects.filter(pk=self.order_one.pk).update(status="completed")
        self.order_one.refresh_from_db()
        self.login_customer_one()
        response = self.client.post(
            reverse("customers:vehicle-delete", args=[self.vehicle_one.pk])
        )
        self.assertRedirects(response, reverse("customers:vehicle-list"))
        self.vehicle_one.refresh_from_db()
        self.assertFalse(self.vehicle_one.is_active)
        self.assertTrue(
            WorkOrder.objects.filter(pk=self.order_one.pk).exists()
        )

    def test_employee_role_is_admin_created_and_grouped(self):
        user = User.objects.create_user(
            username="technician-user",
            password=self.password,
        )
        employee = Employee.objects.create(
            user=user,
            branch=self.branch,
            job_title="فني",
            phone="0555555555",
            role=Employee.TECHNICIAN,
        )
        user.refresh_from_db()
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.groups.filter(name="فني").exists())
        self.assertEqual(employee.role, Employee.TECHNICIAN)

    def test_parts_reduce_stock_and_invoice_uses_services_and_parts(self):
        category = ServiceCategory.objects.create(name="الصيانة الدورية")
        service = Service.objects.create(
            category=category,
            name="تغيير زيت",
            price=Decimal("100.00"),
            estimated_time=30,
        )
        part = SparePart.objects.create(
            name="فلتر زيت",
            part_number="FILTER-001",
            purchase_price=Decimal("15.00"),
            selling_price=Decimal("25.00"),
        )
        stock = BranchStock.objects.create(
            branch=self.branch,
            part=part,
            quantity=5,
        )
        WorkOrderService.objects.create(
            work_order=self.order_one,
            service=service,
        )
        WorkOrderPart.objects.create(
            work_order=self.order_one,
            part=part,
            quantity=2,
            unit_price=part.selling_price,
        )
        stock.refresh_from_db()
        self.assertEqual(stock.quantity, 3)
        self.assertTrue(
            StockMovement.objects.filter(
                work_order=self.order_one,
                movement_type=StockMovement.USAGE,
                quantity=2,
            ).exists()
        )

        invoice = Invoice.objects.get(pk=self.invoice_one.pk)
        invoice.recalculate()
        self.assertEqual(invoice.subtotal, Decimal("150.00"))
        self.assertEqual(invoice.tax, Decimal("22.50"))
        self.assertEqual(invoice.total, Decimal("172.50"))
        self.assertEqual(invoice.items.count(), 2)

        Payment.objects.create(
            invoice=invoice,
            amount=Decimal("72.50"),
            method="card",
        )
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, "partial")
        Payment.objects.create(
            invoice=invoice,
            amount=Decimal("100.00"),
            method="cash",
        )
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, "paid")

    def test_cannot_use_more_parts_than_branch_stock(self):
        part = SparePart.objects.create(
            name="بطارية",
            part_number="BATTERY-001",
            purchase_price=Decimal("200.00"),
            selling_price=Decimal("300.00"),
        )
        BranchStock.objects.create(branch=self.branch, part=part, quantity=1)

        with self.assertRaisesMessage(
            ValidationError,
            "المتوفر في مخزون الفرع 1 فقط",
        ):
            WorkOrderPart.objects.create(
                work_order=self.order_one,
                part=part,
                quantity=2,
                unit_price=part.selling_price,
            )
