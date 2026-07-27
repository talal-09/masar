from django.urls import path

from . import views

app_name = "customers"

urlpatterns = [
    path("profile/", views.profile, name="profile"),
    path("password/", views.change_password, name="password"),
    path("vehicles/", views.vehicle_list, name="vehicle-list"),
    path("vehicles/new/", views.vehicle_create, name="vehicle-create"),
    path("vehicles/<int:pk>/edit/", views.vehicle_update, name="vehicle-update"),
    path("vehicles/<int:pk>/delete/", views.vehicle_delete, name="vehicle-delete"),
]
