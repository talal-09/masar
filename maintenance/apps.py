from django.apps import AppConfig
from core.i18n import tr


class MaintenanceConfig(AppConfig):
    name = 'maintenance'
    verbose_name = tr("Maintenance")

    def ready(self):
        from . import signals  # noqa: F401
