from django.apps import AppConfig
from django.db.models.signals import post_migrate
from .i18n import tr


class CoreConfig(AppConfig):
    name = 'core'
    verbose_name = tr("Branches")

    def ready(self):
        post_migrate.connect(
            sync_existing_employee_roles,
            dispatch_uid="core.sync_existing_employee_roles",
        )


def sync_existing_employee_roles(**kwargs):
    from .models import Employee
    from .roles import sync_employee_role

    for employee in Employee.objects.select_related("user"):
        sync_employee_role(employee)
