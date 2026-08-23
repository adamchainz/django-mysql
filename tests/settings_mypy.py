"""
Settings for django-stubs’ Mypy plugin, which calls django.setup().

django-mysql’s AppConfig.ready() loads any MySQL connections, which imports the
MySQL backend, which imports MySQLdb. Use SQLite here so that type checking
doesn’t require mysqlclient to be installed, notably on pre-commit.ci.
"""

from __future__ import annotations

from tests.settings import *  # noqa: F403

DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
}

DATABASE_ROUTERS = []
