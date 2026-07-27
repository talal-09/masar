from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("management/", include("backoffice.urls")),
    path("admin/", admin.site.urls),

    path("", include("core.urls")),

    path("customers/", include("customers.urls")),
    path("maintenance/", include("maintenance.urls")),
    path("services/", include("services.urls")),
    path("inventory/", include("inventory.urls")),
    path("billing/", include("billing.urls")),
]

if settings.DEBUG and not settings.CLOUDINARY_CONFIGURED:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
