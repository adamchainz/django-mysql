import django
from django.core.checks import Tags, Warning, register

from django_mysql.utils import mysql_connections


def register_checks():
    register(Tags.database)(check_variables)


def check_variables(app_configs, **kwargs):
    if django.VERSION >= (3, 1):
        # when moving to Django 3.1+ only support, make this a real argument
        databases = kwargs["databases"]
    else:
        databases = {alias for alias, connection in mysql_connections()}

    errors = []

    if databases is None:
        return errors
    databases = set(databases)

    for alias, connection in mysql_connections():
        if alias not in databases:
            continue

        with connection.temporary_connection() as cursor:
            cursor.execute(
                """SELECT @@sql_mode,
                          @@innodb_strict_mode,
                          @@character_set_connection"""
            )
            variables = cursor.fetchone()
            sql_mode, innodb_strict_mode, character_set_connection = variables

        modes = set(sql_mode.split(","))
        if not (modes & {"STRICT_TRANS_TABLES", "STRICT_ALL_TABLES"}):
            errors.append(strict_mode_warning(alias))

        if not innodb_strict_mode:
            errors.append(innodb_strict_mode_warning(alias))

        if character_set_connection != "utf8mb4":
            errors.append(utf8mb4_warning(alias))

    return errors


def strict_mode_warning(alias):
    return Warning(
        f"MySQL Strict Mode is not set for database connection '{alias}'",
        hint=(
            "MySQL's Strict Mode fixes many data integrity problems in MySQL, "
            + "such as data truncation upon insertion, by escalating warnings "
            + "into errors. It is strongly recommended you activate it. See: "
            + "https://django-mysql.readthedocs.io/en/latest/checks.html#django-mysql-w001-strict-mode"  # noqa: B950
        ),
        id="django_mysql.W001",
    )


def innodb_strict_mode_warning(alias):
    return Warning(
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


def utf8mb4_warning(alias):
    return Warning(
        f"The character set is not utf8mb4 for database connection '{alias}'",
        hint=(
            "The default 'utf8' character set does not include support for "
            + "all Unicode characters. It's strongly recommended you move to "
            + "use 'utf8mb4'. See: "
            + "https://django-mysql.readthedocs.io/en/latest/checks.html#django-mysql-w003-utf8mb4"  # noqa: B950
        ),
        id="django_mysql.W003",
    )
