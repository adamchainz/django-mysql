# -*- coding:utf-8 -*-
from __future__ import unicode_literals

import django
from django.db import connection


def pytest_report_header(config):
    dot_version = '.'.join(str(x) for x in django.VERSION)
    header = "Django version: " + dot_version

    if hasattr(connection, '_nodb_connection'):
        with connection._nodb_connection.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
        header += "\nMySQL version: {}".format(version)

    return header
