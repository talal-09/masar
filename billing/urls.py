from django.urls import path

from . import views

app_name = "billing"

urlpatterns = [
    path("", views.invoice_list, name="invoice-list"),
    path("<int:pk>/", views.invoice_detail, name="invoice-detail"),
    path("<int:pk>/pdf/", views.invoice_pdf, name="invoice-pdf"),
]
