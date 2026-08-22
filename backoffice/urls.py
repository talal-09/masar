from django.urls import path

from . import views


app_name = "backoffice"

urlpatterns = [
    path("login/", views.ManagementLoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.dashboard, name="dashboard"),
    path(
        "work-orders/options/",
        views.work_order_options,
        name="work-order-options",
    ),
    path(
        "invoices/preview/",
        views.invoice_preview,
        name="invoice-preview",
    ),
    path("<slug:slug>/", views.resource_list, name="resource-list"),
    path("<slug:slug>/add/", views.resource_form, name="resource-add"),
    path("<slug:slug>/<int:pk>/edit/", views.resource_form, name="resource-edit"),
    path("<slug:slug>/<int:pk>/delete/", views.resource_delete, name="resource-delete"),
]
