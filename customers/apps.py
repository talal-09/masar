from django.apps import AppConfig
from core.i18n import tr


class CustomersConfig(AppConfig):
    name = 'customers'
    verbose_name = tr("Customers")
