from typing import Any, List

import django
from django.core import checks

from django_mysql.utils import mysql_connections


def register_checks() -> None:
    checks.register(checks.Tags.database)(check_variables)


def check_variables(**kwargs: Any) -> List[checks.CheckMessage]:
    if django.VERSION >= (3, 1):
        # when moving to Django 3.1+ only support, make this a real argument
        databases = kwargs["databases"]
    else:
        databases = {alias for alias, connection in mysql_connections()}

    errors: List[checks.CheckMessage] = []

    if databases is None:
        return errors
    databases = set(databases)

    for alias, connection in mysql_connections():
        if alias not in databases:
            continue

        with connection.temporary_connection() as cursor:
            cursor.execute(
                """SELECT @@innodb_strict_mode,
                          @@character_set_connection"""
            )
            variables = cursor.fetchone()
            innodb_strict_mode, character_set_connection = variables

        if not innodb_strict_mode:
            errors.append(innodb_strict_mode_warning(alias))

        if character_set_connection != "utf8mb4":
            errors.append(utf8mb4_warning(alias))

    return errors


def innodb_strict_mode_warning(alias: str) -> checks.Warning:
    return checks.Warning(
        f"InnoDB Strict Mode is not set for database connection '{alias}'",
        hint=(
            "InnoDB Strict Mode escalates several warnings around "
            + "InnoDB-specific statements into errors. It's recommended you "
            + "activate this, but it's not very likely to affect you if you "
            + "don't. See: "
            + "https://django-mysql.readthedocs.io/en/latest/checks.html#django-mysql-w002-innodb-strict-mode"  # noqa: B950
        ),
        id="django_mysql.W002",
    )


def utf8mb4_warning(alias: str) -> checks.Warning:
    return checks.Warning(
        f"The character set is not utf8mb4 for database connection '{alias}'",
        hint=(
            "The default 'utf8' character set does not include support for "
            + "all Unicode characters. It's strongly recommended you move to "
            + "use 'utf8mb4'. See: "
            + "https://django-mysql.readthedocs.io/en/latest/checks.html#django-mysql-w003-utf8mb4"  # noqa: B950
        ),
        id="django_mysql.W003",
    )
