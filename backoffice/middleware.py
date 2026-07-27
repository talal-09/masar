from django.shortcuts import redirect

from .access import is_platform_manager


class PortalIsolationMiddleware:
    """
    Keeps authenticated customer and management sessions inside their own UI.

    Anonymous visitors may still reach the public customer website and either
    login page. Authorization is always enforced again by the target views.
    """

    MANAGEMENT_PREFIXES = ("/management/", "/admin/")
    SHARED_PREFIXES = ("/static/", "/media/", "/i18n/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if (
            request.user.is_authenticated
            and not path.startswith(self.SHARED_PREFIXES)
        ):
            is_management_path = path.startswith(self.MANAGEMENT_PREFIXES)
            if is_platform_manager(request.user) and not is_management_path:
                return redirect("backoffice:dashboard")
            if (
                is_management_path
                and not request.user.is_staff
                and hasattr(request.user, "customer_profile")
            ):
                return redirect("dashboard")
        return self.get_response(request)
