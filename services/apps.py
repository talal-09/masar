from django.apps import AppConfig
from core.i18n import tr


class ServicesConfig(AppConfig):
    name = 'services'
    verbose_name = tr("Services")
