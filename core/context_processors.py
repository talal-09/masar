from maintenance.models import Notification


def portal_context(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated or user.is_staff:
        return {"unread_notifications_count": 0}
    return {
        "unread_notifications_count": Notification.objects.filter(
            user=user,
            is_read=False,
        ).count()
    }
