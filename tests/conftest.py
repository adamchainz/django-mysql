# -*- coding:utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import django
from django.db import connection
from pytest_django.plugin import _blocking_manager


def pytest_report_header(config):
    dot_version = '.'.join(str(x) for x in django.VERSION)
    header = "Django version: " + dot_version

    with _blocking_manager.unblock():
        with connection._nodb_connection.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
        header += "\nMySQL version: {}".format(version)

    return header
