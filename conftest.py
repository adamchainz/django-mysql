# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from django.db import connection


def pytest_report_header(config):
    with connection.cursor() as cursor:
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
    return "MySQL version: {}".format(version)
