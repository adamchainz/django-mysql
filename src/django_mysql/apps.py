from __future__ import annotations

from typing import Any
from typing import Callable

from django.apps import AppConfig
from django.conf import settings
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.signals import connection_created
from django.utils.translation import gettext_lazy as _

from django_mysql.checks import register_checks
from django_mysql.rewrite_query import REWRITE_MARKER
from django_mysql.rewrite_query import rewrite_query
from django_mysql.utils import mysql_connections


class MySQLConfig(AppConfig):
    name = "django_mysql"
    verbose_name = _("MySQL extensions")

    def ready(self) -> None:
        self.add_database_instrumentation()
        self.add_lookups()
        register_checks()

    def add_database_instrumentation(self) -> None:
        if not getattr(
            settings, "DJANGO_MYSQL_REWRITE_QUERIES", False
        ):  # pragma: no cover
            return
        for _alias, connection in mysql_connections():
            install_rewrite_hook(connection)
        connection_created.connect(install_rewrite_hook)

    def add_lookups(self) -> None:
        from django.db.models import CharField, TextField

        from django_mysql.models.lookups import CaseSensitiveExact, Soundex, SoundsLike

        CharField.register_lookup(CaseSensitiveExact)
        CharField.register_lookup(SoundsLike)
        CharField.register_lookup(Soundex)
        TextField.register_lookup(CaseSensitiveExact)
        TextField.register_lookup(SoundsLike)
        TextField.register_lookup(Soundex)


def install_rewrite_hook(connection: BaseDatabaseWrapper, **kwargs: Any) -> None:
    """
    Rather than use the documented API of the `execute_wrapper()` context
    manager, directly insert the hook. This is done because:
    1. Deleting the context manager closes it, so it's not possible to enter it
       here and not exit it, unless we store it forever in some variable.
    2. We want to be idempotent and only install the hook once.
    """
    if connection.vendor != "mysql":
        return
    if rewrite_hook not in connection.execute_wrappers:  # pragma: no branch
        connection.execute_wrappers.insert(0, rewrite_hook)


def rewrite_hook(
    execute: Callable[[str, str, bool, dict[str, Any]], Any],
    sql: str,
    params: str,
    many: bool,
    context: dict[str, Any],
) -> Any:
    if (
        getattr(settings, "DJANGO_MYSQL_REWRITE_QUERIES", False)
        and REWRITE_MARKER in sql
    ):
        sql = rewrite_query(sql)
    return execute(sql, params, many, context)
