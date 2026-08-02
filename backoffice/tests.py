from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import Branch, Employee
from customers.models import Customer
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
