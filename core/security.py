import math
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.utils.translation import get_language

from .models import AuditLog, LoginAttempt


LOGIN_FAILURE_LIMIT = 5
LOGIN_WINDOW = timedelta(minutes=15)
LOGIN_LOCKOUT = timedelta(minutes=15)


def _login_key(request, username):
    remote_address = request.META.get("REMOTE_ADDR", "unknown") if request else "unknown"
    normalized_username = (username or "").strip().casefold()[:150]
    value = f"{normalized_username}|{remote_address}"
    return salted_hmac("masar.login-throttle", value, settings.SECRET_KEY).hexdigest()


def _lockout_message(blocked_until):
    seconds = max((blocked_until - timezone.now()).total_seconds(), 1)
    minutes = max(math.ceil(seconds / 60), 1)
    if (get_language() or "ar").startswith("en"):
        return f"Too many failed sign-in attempts. Try again in {minutes} minutes."
    return f"محاولات دخول كثيرة غير ناجحة. حاول مجددًا بعد {minutes} دقيقة."


def enforce_login_throttle(request, username):
    attempt = LoginAttempt.objects.filter(key_hash=_login_key(request, username)).first()
    if attempt and attempt.blocked_until and attempt.blocked_until > timezone.now():
        raise ValidationError(_lockout_message(attempt.blocked_until), code="login_throttled")


def record_login_failure(request, username):
    key_hash = _login_key(request, username)
    now = timezone.now()
    LoginAttempt.objects.filter(updated_at__lt=now - timedelta(days=7)).delete()
    with transaction.atomic():
        attempt, _ = LoginAttempt.objects.select_for_update().get_or_create(
            key_hash=key_hash,
            defaults={"window_started_at": now},
        )
        if now - attempt.window_started_at >= LOGIN_WINDOW:
            attempt.failures = 0
            attempt.window_started_at = now
            attempt.blocked_until = None
        attempt.failures += 1
        if attempt.failures >= LOGIN_FAILURE_LIMIT:
            attempt.blocked_until = now + LOGIN_LOCKOUT
            AuditLog.objects.create(
                action=AuditLog.SECURITY,
                object_type="authentication",
                object_id=key_hash[:12],
                object_repr="Repeated failed sign-in attempts",
                details={"event": "temporary_login_lockout"},
            )
        attempt.save()


def clear_login_failures(request, username):
    LoginAttempt.objects.filter(key_hash=_login_key(request, username)).delete()


class LoginThrottleMixin:
    def clean(self):
        username = self.data.get("username", "")
        enforce_login_throttle(self.request, username)
        try:
            cleaned_data = super().clean()
        except ValidationError:
            record_login_failure(self.request, username)
            raise
        clear_login_failures(self.request, username)
        return cleaned_data
