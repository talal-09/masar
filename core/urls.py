
from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views

from . import views
from .forms import (
    StyledAuthenticationForm,
    StyledPasswordResetForm,
    StyledSetPasswordForm,
)

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("contact/", views.contact, name="contact"),
    path("branches/", views.branch_list, name="branches"),
    path("health/", views.health, name="health"),
    path("signup/", views.signup, name="signup"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            authentication_form=StyledAuthenticationForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            email_template_name="registration/password_reset_email.txt",
            subject_template_name="registration/password_reset_subject.txt",
            form_class=StyledPasswordResetForm,
            success_url=reverse_lazy("password-reset-done"),
        ),
        name="password-reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html",
        ),
        name="password-reset-done",
    ),
    path(
        "password-reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
            form_class=StyledSetPasswordForm,
            success_url=reverse_lazy("password-reset-complete"),
        ),
        name="password-reset-confirm",
    ),
    path(
        "password-reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html",
        ),
        name="password-reset-complete",
    ),
]
