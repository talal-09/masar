from django.contrib.auth.models import Group, Permission


ROLE_GROUPS = {
    "general_manager": "مدير عام",
    "branch_manager": "مدير فرع",
    "receptionist": "موظف استقبال",
    "technician": "فني",
    "accountant": "محاسب",
    "inventory_manager": "مسؤول مخزون",
}

ROLE_MODELS = {
    "branch_manager": {
        "branch",
        "employee",
        "customer",
        "vehicle",
        "workorder",
        "workorderservice",
        "workorderpart",
        "workorderimage",
        "quote",
        "notification",
        "invoice",
        "invoiceitem",
        "payment",
        "service",
        "servicecategory",
        "sparepart",
        "branchstock",
        "stockmovement",
        "contactmessage",
        "workshopreview",
    },
    "receptionist": {
        "customer",
        "vehicle",
        "workorder",
        "workorderservice",
        "quote",
        "contactmessage",
    },
    "technician": {
        "workorder",
        "workorderservice",
        "workorderpart",
        "workorderimage",
    },
    "accountant": {
        "invoice",
        "invoiceitem",
        "payment",
        "workorder",
        "quote",
        "customer",
    },
    "inventory_manager": {
        "sparepart",
        "branchstock",
        "stockmovement",
        "workorderpart",
    },
}

PROJECT_APPS = {
    "core",
    "customers",
    "maintenance",
    "billing",
    "inventory",
    "services",
}


def sync_employee_role(employee):
    groups = {
        role: Group.objects.get_or_create(name=name)[0]
        for role, name in ROLE_GROUPS.items()
    }
    employee.user.groups.remove(*groups.values())
    group = groups[employee.role]

    permissions = Permission.objects.filter(
        content_type__app_label__in=PROJECT_APPS
    )
    if employee.role != "general_manager":
        permissions = permissions.filter(
            content_type__model__in=ROLE_MODELS[employee.role]
        )
        if employee.role in {"technician", "accountant"}:
            permissions = permissions.exclude(codename__startswith="delete_")

    group.permissions.set(permissions)
    employee.user.groups.add(group)
