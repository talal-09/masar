import os
from pathlib import Path

import cloudinary
import dj_database_url
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

# تحميل ملف .env في بيئة التطوير المحلية
load_dotenv(BASE_DIR / ".env")


# ==========================
# دوال مساعدة
# ==========================

def env_list(name: str, default: str = "") -> list[str]:
    return [
        item.strip()
        for item in os.getenv(name, default).split(",")
        if item.strip()
    ]


# ==========================
# الإعدادات الأساسية
# ==========================

DEBUG = os.getenv(
    "DJANGO_DEBUG",
    "False",
).strip().lower() == "true"

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "").strip()

if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "django-insecure-local-development-only"
    else:
        raise RuntimeError(
            "DJANGO_SECRET_KEY is required in production"
        )

ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    "127.0.0.1,localhost",
)

CSRF_TRUSTED_ORIGINS = env_list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    "",
)

# Render يضيف هذا المتغير تلقائيًا لخدمة الويب
RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")

if RENDER_EXTERNAL_HOSTNAME:
    if RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

    render_origin = f"https://{RENDER_EXTERNAL_HOSTNAME}"

    if render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(render_origin)


# ==========================
# التطبيقات
# ==========================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Cloudinary
    "cloudinary_storage",
    "cloudinary",

    # تطبيقات المشروع
    "core.apps.CoreConfig",
    "customers.apps.CustomersConfig",
    "maintenance.apps.MaintenanceConfig",
    "services.apps.ServicesConfig",
    "inventory.apps.InventoryConfig",
    "billing.apps.BillingConfig",
    "backoffice.apps.BackofficeConfig",
]


# ==========================
# Middleware
# ==========================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",

    "backoffice.middleware.PortalIsolationMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "myproject.urls"


# ==========================
# القوالب
# ==========================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


WSGI_APPLICATION = "myproject.wsgi.application"


# ==========================
# قاعدة البيانات
# ==========================

USE_TARGET_DATABASE = os.getenv(
    "USE_TARGET_DATABASE",
    "0",
).strip() == "1"

TARGET_DATABASE_URL = os.getenv(
    "TARGET_DATABASE_URL",
    "",
).strip()

if USE_TARGET_DATABASE:
    if not TARGET_DATABASE_URL:
        raise RuntimeError(
            "TARGET_DATABASE_URL is required when "
            "USE_TARGET_DATABASE=1"
        )

    DATABASES = {
        "default": dj_database_url.parse(
            TARGET_DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# ==========================
# حماية كلمات المرور
# ==========================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# ==========================
# اللغة والتوقيت
# ==========================

LANGUAGE_CODE = "ar"

LANGUAGES = [
    ("ar", "العربية"),
    ("en", "English"),
]

TIME_ZONE = "Asia/Riyadh"

USE_I18N = True
USE_TZ = True


# ==========================
# Cloudinary
# ==========================

CLOUDINARY_STORAGE = {
    "CLOUD_NAME": os.getenv(
        "CLOUDINARY_CLOUD_NAME",
        "",
    ).strip(),
    "API_KEY": os.getenv(
        "CLOUDINARY_API_KEY",
        "",
    ).strip(),
    "API_SECRET": os.getenv(
        "CLOUDINARY_API_SECRET",
        "",
    ).strip(),
    "SECURE": True,
}

CLOUDINARY_CONFIGURED = all(
    CLOUDINARY_STORAGE[key]
    for key in ("CLOUD_NAME", "API_KEY", "API_SECRET")
)

if CLOUDINARY_CONFIGURED:
    cloudinary.config(
        cloud_name=CLOUDINARY_STORAGE["CLOUD_NAME"],
        api_key=CLOUDINARY_STORAGE["API_KEY"],
        api_secret=CLOUDINARY_STORAGE["API_SECRET"],
        secure=True,
    )


# ==========================
# التخزين
# ==========================

STORAGES = {
    "default": {
        "BACKEND": (
            "cloudinary_storage.storage.MediaCloudinaryStorage"
            if CLOUDINARY_CONFIGURED
            else "django.core.files.storage.FileSystemStorage"
        ),
    },
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage."
            "CompressedManifestStaticFilesStorage"
        ),
    },
}


# ==========================
# الملفات الثابتة
# ==========================

STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"


# ==========================
# ملفات الوسائط
# ==========================

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# ==========================
# إعدادات عامة
# ==========================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_REDIRECT_URL = "/dashboard/"
LOGIN_URL = "/login/"
LOGOUT_REDIRECT_URL = "/"

SHOW_TECHNICIAN_TO_CUSTOMERS = True


# ==========================
# أمان الإنتاج
# ==========================

SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

SECURE_SSL_REDIRECT = not DEBUG

# قيمة أولية آمنة، ويمكن رفعها لاحقًا بعد التأكد من HTTPS
SECURE_HSTS_SECONDS = 3600 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)