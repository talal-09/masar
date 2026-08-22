from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import Branch, Employee
from customers.models import Customer, Vehicle
from maintenance.models import WorkOrder
from backoffice.registry import RESOURCES


class BackofficeAccessTests(TestCase):
    password = "SecurePass!2026"

    @classmethod
    def setUpTestData(cls):
        cls.branch_one = Branch.objects.create(
            name="فرع الرياض",
            address="الرياض",
            phone="0110000001",
        )
        cls.branch_two = Branch.objects.create(
            name="فرع جدة",
            address="جدة",
            phone="0120000002",
        )
        cls.manager_user = User.objects.create_user(
            username="manager",
            password=cls.password,
            is_staff=True,
        )
        cls.manager = Employee.objects.create(
            user=cls.manager_user,
            branch=cls.branch_one,
            job_title="مدير عام",
            phone="0501000001",
            role=Employee.GENERAL_MANAGER,
        )
        cls.customer_user = User.objects.create_user(
            username="customer",
            password=cls.password,
        )
        Customer.objects.create(
            user=cls.customer_user,
            full_name="عميل تجريبي",
            phone="0502000002",
            email="customer@example.com",
        )

    def test_anonymous_user_is_sent_to_management_login(self):
        response = self.client.get(reverse("backoffice:dashboard"))
        self.assertRedirects(
            response,
            f"{reverse('backoffice:login')}?next={reverse('backoffice:dashboard')}",
        )

    def test_customer_cannot_login_to_management_portal(self):
        response = self.client.post(
            reverse("backoffice:login"),
            {
                "username": self.customer_user.username,
                "password": self.password,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "غير مصرح له")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_manager_can_open_dashboard_and_all_core_resources(self):
        self.client.force_login(self.manager_user)
        self.assertEqual(
            self.client.get(reverse("backoffice:dashboard")).status_code,
            200,
        )
        for resource in RESOURCES:
            slug = resource.slug
            with self.subTest(slug=slug):
                response = self.client.get(
                    reverse("backoffice:resource-list", args=[slug])
                )
                self.assertEqual(response.status_code, 200)

    def test_authenticated_portals_are_strictly_isolated(self):
        self.client.force_login(self.manager_user)
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, reverse("backoffice:dashboard"))

        self.client.force_login(self.customer_user)
        response = self.client.get(reverse("backoffice:dashboard"))
        self.assertRedirects(response, reverse("dashboard"))

    def test_all_editable_resource_create_forms_render(self):
        superuser = User.objects.create_superuser(
            username="platform-owner",
            password=self.password,
            email="owner@example.com",
        )
        self.client.force_login(superuser)
        for resource in RESOURCES:
            if resource.readonly:
                continue
            with self.subTest(slug=resource.slug):
                response = self.client.get(
                    reverse("backoffice:resource-add", args=[resource.slug])
                )
                self.assertEqual(response.status_code, 200)

    def test_employee_can_be_created_from_management_portal(self):
        self.client.force_login(self.manager_user)
        response = self.client.post(
            reverse("backoffice:resource-add", args=["employees"]),
            {
                "username": "new-technician",
                "first_name": "فني",
                "last_name": "جديد",
                "email": "tech@example.com",
                "password": self.password,
                "branch": self.branch_one.pk,
                "job_title": "فني صيانة",
                "phone": "0503000003",
                "role": Employee.TECHNICIAN,
            },
        )
        self.assertRedirects(
            response,
            reverse("backoffice:resource-list", args=["employees"]),
        )
        employee = Employee.objects.get(user__username="new-technician")
        self.assertTrue(employee.user.is_staff)
        self.assertEqual(employee.branch, self.branch_one)

    def test_management_language_switch_persists_and_is_not_mixed(self):
        self.client.force_login(self.manager_user)
        response = self.client.post(
            reverse("set_language"),
            {"language": "en", "next": reverse("backoffice:dashboard")},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Platform management")
        self.assertContains(response, "Active orders")
        self.assertContains(response, "Inventory")
        self.assertNotContains(response, "مركز القيادة")
        self.assertNotContains(response, "أوامر نشطة")

        next_response = self.client.get(
            reverse("backoffice:resource-list", args=["vehicles"])
        )
        self.assertContains(next_response, "Search Vehicles")
        self.assertContains(next_response, "Actions")
        self.assertNotContains(next_response, "الإجراءات")

        arabic = self.client.post(
            reverse("set_language"),
            {"language": "ar", "next": reverse("backoffice:dashboard")},
            follow=True,
        )
        self.assertContains(arabic, "مركز القيادة")
        self.assertNotContains(arabic, "Platform management")


class WorkOrderDependentFieldsTests(TestCase):
    password = "SecurePass!2026"

    @classmethod
    def setUpTestData(cls):
        cls.branch_a = Branch.objects.create(
            name="فرع أ", address="الرياض", phone="0111111111"
        )
        cls.branch_b = Branch.objects.create(
            name="فرع ب", address="جدة", phone="0122222222"
        )
        cls.owner = User.objects.create_superuser(
            username="owner", password=cls.password, email="owner@example.com"
        )
        cls.customer_a = Customer.objects.create(
            full_name="محمد", phone="0500000101", email="a@example.com"
        )
        cls.customer_b = Customer.objects.create(
            full_name="خالد", phone="0500000102", email="b@example.com"
        )
        cls.vehicle_a1 = Vehicle.objects.create(
            customer=cls.customer_a, plate_number="أ أ أ 1",
            chassis_number="DEPENDENT-A1", brand="Toyota", model="Camry",
            year=2022, color="White", mileage=10000,
        )
        cls.vehicle_a2 = Vehicle.objects.create(
            customer=cls.customer_a, plate_number="أ أ أ 2",
            chassis_number="DEPENDENT-A2", brand="Honda", model="Accord",
            year=2020, color="Black", mileage=20000,
        )
        cls.vehicle_b = Vehicle.objects.create(
            customer=cls.customer_b, plate_number="ب ب ب 1",
            chassis_number="DEPENDENT-B1", brand="Hyundai", model="Sonata",
            year=2024, color="Gray", mileage=3000,
        )
        cls.tech_a = cls.make_employee(
            "tech-a", cls.branch_a, Employee.TECHNICIAN, "0510000001"
        )
        cls.tech_b = cls.make_employee(
            "tech-b", cls.branch_b, Employee.TECHNICIAN, "0510000002"
        )
        cls.accountant_a = cls.make_employee(
            "accountant-a", cls.branch_a, Employee.ACCOUNTANT, "0510000003"
        )

    @classmethod
    def make_employee(cls, username, branch, role, phone):
        user = User.objects.create_user(
            username=username, password=cls.password, is_staff=True
        )
        return Employee.objects.create(
            user=user, branch=branch, job_title=username, phone=phone, role=role
        )

    def setUp(self):
        self.client.force_login(self.owner)

    def options(self, option_type, parent):
        return self.client.get(
            reverse("backoffice:work-order-options"),
            {"type": option_type, "parent": parent},
        )

    def test_vehicle_options_only_return_selected_customers_vehicles(self):
        response = self.options("vehicles", self.customer_a.pk)
        self.assertEqual(response.status_code, 200)
        values = {item["value"] for item in response.json()["options"]}
        self.assertEqual(values, {self.vehicle_a1.pk, self.vehicle_a2.pk})
        self.assertNotIn(self.vehicle_b.pk, values)

        changed = self.options("vehicles", self.customer_b.pk)
        self.assertEqual(
            {item["value"] for item in changed.json()["options"]},
            {self.vehicle_b.pk},
        )

    def test_backend_rejects_vehicle_from_another_customer(self):
        response = self.client.post(
            reverse("backoffice:resource-add", args=["work-orders"]),
            {
                "branch": self.branch_a.pk,
                "customer": self.customer_a.pk,
                "vehicle": self.vehicle_b.pk,
                "description": "طلب غير متطابق",
                "mileage": 3000,
                "status": "new",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "السيارة المحددة لا تتبع العميل المختار")
        self.assertFalse(
            WorkOrder.objects.filter(description="طلب غير متطابق").exists()
        )

    def test_technicians_are_active_role_and_branch_scoped(self):
        response = self.options("technicians", self.branch_a.pk)
        values = {item["value"] for item in response.json()["options"]}
        self.assertEqual(values, {self.tech_a.pk})
        self.assertNotIn(self.tech_b.pk, values)
        self.assertNotIn(self.accountant_a.pk, values)

        self.tech_a.user.is_active = False
        self.tech_a.user.save(update_fields=["is_active"])
        self.assertEqual(
            self.options("technicians", self.branch_a.pk).json()["options"],
            [],
        )

    def test_existing_order_edit_keeps_valid_related_values(self):
        order = WorkOrder.objects.create(
            branch=self.branch_a,
            customer=self.customer_a,
            vehicle=self.vehicle_a1,
            description="أمر قديم",
            mileage=10000,
            assigned_technician=self.tech_a,
        )
        response = self.client.get(
            reverse("backoffice:resource-edit", args=["work-orders", order.pk])
        )
        form = response.context["form"]
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.vehicle_a1, form.fields["vehicle"].queryset)
        self.assertIn(self.vehicle_a2, form.fields["vehicle"].queryset)
        self.assertNotIn(self.vehicle_b, form.fields["vehicle"].queryset)
        self.assertIn(self.tech_a, form.fields["assigned_technician"].queryset)

    def test_normal_work_order_creation_still_succeeds(self):
        response = self.client.post(
            reverse("backoffice:resource-add", args=["work-orders"]),
            {
                "branch": self.branch_a.pk,
                "customer": self.customer_a.pk,
                "vehicle": self.vehicle_a1.pk,
                "description": "إنشاء طبيعي",
                "mileage": 10100,
                "status": "new",
                "assigned_technician": self.tech_a.pk,
            },
        )
        self.assertRedirects(
            response,
            reverse("backoffice:resource-list", args=["work-orders"]),
        )
        order = WorkOrder.objects.get(description="إنشاء طبيعي")
        self.assertEqual(order.customer, self.customer_a)
        self.assertEqual(order.vehicle, self.vehicle_a1)
        self.assertEqual(order.assigned_technician, self.tech_a)
