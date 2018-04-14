# -*- coding:utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)

import warnings

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


# MySQL 5.7 warns about some sql mode changes
warnings.filterwarnings('ignore', r'.*Changing sql mode.*')
warnings.filterwarnings(
    'ignore',
    r'.*sql modes should be used with strict mode.*',
)
# MySQL 5.7 turned 'explain' into 'explain extended' so it always warns the
# optimized query
warnings.filterwarnings('ignore', r'.*/\* select#\d+ \*/')
# MySQL 5.7 deprecated some query hints
warnings.filterwarnings('ignore', r".*'SQL_CACHE' is deprecated.*")
warnings.filterwarnings('ignore', r".*'SQL_NO_CACHE' is deprecated.*")
