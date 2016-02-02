# -*- coding:utf-8 -*-
from __future__ import unicode_literals

import django
from django.core.checks import Tags, Warning, register
from django.db import DEFAULT_DB_ALIAS, connections

from django_mysql.utils import collapse_spaces


def register_checks():
    if django.VERSION[:2] >= (1, 8):
        # These checks connect to the DB, which only works on Django 1.8+
        register(Tags.compatibility)(check_variables)


def check_variables(app_configs, **kwargs):
    errors = []

    for alias, connection in mysql_connections():
        with connection.cursor() as cursor:
            cursor.execute("""SELECT @@sql_mode,
                                     @@innodb_strict_mode,
                                     @@character_set_connection""")
            variables = cursor.fetchone()
            sql_mode, innodb_strict_mode, character_set_connection = variables

        modes = set(sql_mode.split(','))
        if not (modes & {'STRICT_TRANS_TABLES', 'STRICT_ALL_TABLES'}):
            errors.append(strict_mode_warning(alias))

        if not innodb_strict_mode:
            errors.append(innodb_strict_mode_warning(alias))

        if character_set_connection != 'utf8mb4':
            errors.append(utf8mb4_warning(alias))

    return errors


def strict_mode_warning(alias):
    message = "MySQL Strict Mode is not set for database connection '{}'"
    hint = collapse_spaces("""
        MySQL's Strict Mode fixes many data integrity problems in MySQL, such
        as data truncation upon insertion, by escalating warnings into errors.
        It is strongly recommended you activate it. See:
        http://django-mysql.readthedocs.org/en/latest/checks.html#django-mysql-w001-strict-mode
    """)
    return Warning(
        message.format(alias),
        hint=hint,
        id='django_mysql.W001',
    )


def innodb_strict_mode_warning(alias):
    message = "InnoDB Strict Mode is not set for database connection '{}'"
    hint = collapse_spaces("""
        InnoDB Strict Mode escalates several warnings around InnoDB-specific
        statements into errors. It's recommended you activate this, but it's
        not very likely to affect you if you don't. See:
        http://django-mysql.readthedocs.org/en/latest/checks.html#django-mysql-w002-innodb-strict-mode
    """)

    return Warning(
        message.format(alias),
        hint=hint,
        id='django_mysql.W002',
    )


def utf8mb4_warning(alias):
    message = "The character set is not utf8mb4 for database connection '{}'"
    hint = collapse_spaces("""
        The default 'utf8' character set does not include support for all
        Unicode characters. It's strongly recommended you move to use
        'utf8mb4'. See:
        http://django-mysql.readthedocs.org/en/latest/checks.html#django-mysql-w003-utf8mb4
    """)

    return Warning(
        message.format(alias),
        hint=hint,
        id='django_mysql.W003',
    )


def mysql_connections():
    conn_names = [DEFAULT_DB_ALIAS] + list(
        set(connections) - {DEFAULT_DB_ALIAS}
    )
    for alias in conn_names:
        connection = connections[alias]
        if not hasattr(connection, 'mysql_version'):
            continue  # pragma: no cover

        yield alias, connection
