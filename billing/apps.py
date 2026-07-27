from django.apps import AppConfig
from core.i18n import tr


class BillingConfig(AppConfig):
    name = 'billing'
    verbose_name = tr("Billing")
