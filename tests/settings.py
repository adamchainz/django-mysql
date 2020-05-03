import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DEBUG = False
TEMPLATE_DEBUG = DEBUG

SECRET_KEY = "THISuISdNOT9A$SECRET9x&ji!vceayg+wwt472!bgs$0!i3k4"

DATABASES = {
    "default": {
        "ENGINE": "tests.db_backend",
        "NAME": "django_mysql",
        "USER": os.environ.get("DB_USER", ""),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", ""),
        "PORT": os.environ.get("DB_PORT", ""),
        "OPTIONS": {"charset": "utf8mb4"},
        "TEST": {"COLLATION": "utf8mb4_general_ci", "CHARSET": "utf8mb4"},
    },
    "other": {
        "ENGINE": "tests.db_backend",
        "NAME": "django_mysql2",
        "USER": os.environ.get("DB_USER", ""),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", ""),
        "PORT": os.environ.get("DB_PORT", ""),
        "OPTIONS": {"charset": "utf8mb4"},
        "TEST": {"COLLATION": "utf8mb4_general_ci", "CHARSET": "utf8mb4"},
    },
    "other2": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
    },
}

DATABASE_ROUTERS = ["tests.testapp.routers.NothingOnSQLiteRouter"]

ALLOWED_HOSTS = []

INSTALLED_APPS = ["django.contrib.contenttypes", "django_mysql", "tests.testapp"]

ROOT_URLCONF = "tests.urls"
TIME_ZONE = "UTC"
USE_I18N = True

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "OPTIONS": {
            "context_processors": ["django.contrib.auth.context_processors.auth"]
        },
    }
]


DJANGO_MYSQL_REWRITE_QUERIES = True
