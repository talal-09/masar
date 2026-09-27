from django.core.exceptions import ValidationError


MAX_IMAGE_SIZE = 5 * 1024 * 1024
ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


def validate_uploaded_image(upload):
    if upload.size > MAX_IMAGE_SIZE:
        raise ValidationError("حجم الصورة يجب ألا يتجاوز 5 ميجابايت.")
    content_type = getattr(upload, "content_type", None)
    if content_type and content_type.lower() not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise ValidationError("نوع الصورة غير مدعوم. استخدم JPEG أو PNG أو WebP.")
