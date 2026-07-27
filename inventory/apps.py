from django.apps import AppConfig
from core.i18n import tr


class InventoryConfig(AppConfig):
    name = 'inventory'
    verbose_name = tr("Inventory")
