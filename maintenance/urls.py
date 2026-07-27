from django.urls import path

from . import views

app_name = "maintenance"

urlpatterns = [
    path("", views.order_list, name="order-list"),
    path("new/", views.order_create, name="order-create"),
    path("<int:pk>/", views.order_detail, name="order-detail"),
    path("<int:pk>/status/", views.order_status, name="order-status"),
    path(
        "vehicle/<int:vehicle_pk>/history/",
        views.vehicle_history,
        name="vehicle-history",
    ),
    path(
        "quotes/<int:pk>/<str:decision>/",
        views.quote_response,
        name="quote-response",
    ),
    path("notifications/", views.notification_list, name="notifications"),
    path(
        "notifications/<int:pk>/read/",
        views.notification_read,
        name="notification-read",
    ),
]
