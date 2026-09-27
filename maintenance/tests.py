from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from core.models import Branch, Employee
from customers.models import Customer, Vehicle

from .models import WorkOrder


class WorkOrderWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.branch = Branch.objects.create(
            name="فرع الدورة", address="الرياض", phone="0111234567"
        )
        cls.customer = Customer.objects.create(
            full_name="عميل الدورة", phone="0599999991"
        )
        cls.vehicle = Vehicle.objects.create(
            customer=cls.customer,
            plate_number="د و ر 1",
            chassis_number="WORKFLOW-CHASSIS-1",
            brand="Toyota",
            model="Camry",
            year=2025,
            color="White",
            mileage=1000,
        )
        technician_user = User.objects.create_user(
            username="workflow-tech", password="SecurePass!2026", is_staff=True
        )
        cls.technician = Employee.objects.create(
            user=technician_user,
            branch=cls.branch,
            job_title="فني",
            phone="0599999992",
            role=Employee.TECHNICIAN,
        )

    def make_order(self, status=WorkOrder.NEW, technician=None):
        order = WorkOrder.objects.create(
            branch=self.branch,
            customer=self.customer,
            vehicle=self.vehicle,
            description="اختبار دورة العمل",
            mileage=1000,
            assigned_technician=technician,
        )
        if status != WorkOrder.NEW:
            WorkOrder.objects.filter(pk=order.pk).update(status=status)
            order.refresh_from_db()
        return order

    def assert_transition_rejected(self, order, target):
        order.status = target
        with self.assertRaises(ValidationError):
            order.save(update_fields=["status"])
        order.refresh_from_db()

    def test_new_to_inspection_succeeds(self):
        order = self.make_order()
        order.status = WorkOrder.INSPECTION
        order.save(update_fields=["status"])
        self.assertEqual(order.status, WorkOrder.INSPECTION)

    def test_new_to_delivered_fails_with_clear_message(self):
        order = self.make_order()
        order.status = WorkOrder.DELIVERED
        with self.assertRaisesMessage(
            ValidationError,
            "لا يمكن نقل أمر الصيانة من حالة «جديد» مباشرة إلى «تم التسليم»",
        ):
            order.save(update_fields=["status"])

    def test_awaiting_approval_to_approved_succeeds(self):
        order = self.make_order(WorkOrder.AWAITING_APPROVAL)
        order.status = WorkOrder.APPROVED
        order.save(update_fields=["status"])
        self.assertEqual(order.status, WorkOrder.APPROVED)

    def test_awaiting_approval_to_testing_fails(self):
        order = self.make_order(WorkOrder.AWAITING_APPROVAL)
        self.assert_transition_rejected(order, WorkOrder.TESTING)

    def test_working_to_testing_succeeds(self):
        order = self.make_order(WorkOrder.WORKING, self.technician)
        order.status = WorkOrder.TESTING
        order.save(update_fields=["status"])
        self.assertEqual(order.status, WorkOrder.TESTING)

    def test_testing_can_return_to_working(self):
        order = self.make_order(WorkOrder.TESTING, self.technician)
        order.status = WorkOrder.WORKING
        order.save(update_fields=["status"])
        self.assertEqual(order.status, WorkOrder.WORKING)

    def test_ready_to_delivered_succeeds_and_keeps_completion_time(self):
        order = self.make_order(WorkOrder.TESTING, self.technician)
        order.status = WorkOrder.READY_FOR_DELIVERY
        order.save(update_fields=["status"])
        order.refresh_from_db()
        self.assertIsNotNone(order.completed_at)

        order.status = WorkOrder.DELIVERED
        order.save(update_fields=["status"])
        self.assertEqual(order.status, WorkOrder.DELIVERED)

    def test_delivered_order_is_terminal(self):
        order = self.make_order(WorkOrder.DELIVERED, self.technician)
        self.assert_transition_rejected(order, WorkOrder.WORKING)

    def test_cancelled_order_is_terminal(self):
        order = self.make_order(WorkOrder.CANCELLED)
        self.assert_transition_rejected(order, WorkOrder.INSPECTION)

    def test_working_requires_assigned_technician(self):
        order = self.make_order(WorkOrder.APPROVED)
        order.status = WorkOrder.WORKING
        with self.assertRaisesMessage(
            ValidationError,
            "يجب تحديد فني مسؤول قبل بدء الصيانة",
        ):
            order.save(update_fields=["status"])

    def test_branch_appointment_capacity_is_enforced(self):
        self.branch.appointment_capacity = 2
        self.branch.save(update_fields=["appointment_capacity"])
        scheduled_at = timezone.now() + timedelta(days=1)
        vehicles = [self.vehicle]
        for index in (2, 3):
            vehicles.append(Vehicle.objects.create(
                customer=self.customer,
                plate_number=f"د و ر {index}",
                chassis_number=f"WORKFLOW-CHASSIS-{index}",
                brand="Toyota",
                model="Camry",
                year=2025,
                color="White",
                mileage=1000,
            ))

        for vehicle in vehicles[:2]:
            WorkOrder.objects.create(
                branch=self.branch,
                customer=self.customer,
                vehicle=vehicle,
                scheduled_at=scheduled_at,
                description="موعد ضمن السعة",
                mileage=1000,
            )

        with self.assertRaisesMessage(ValidationError, "اكتملت سعة هذا الموعد"):
            WorkOrder.objects.create(
                branch=self.branch,
                customer=self.customer,
                vehicle=vehicles[2],
                scheduled_at=scheduled_at,
                description="موعد يتجاوز السعة",
                mileage=1000,
            )

# Create your tests here.
