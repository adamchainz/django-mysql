# -*- coding:utf-8 -*-
from __future__ import print_function, unicode_literals

from django.db import connection
from django.test.runner import DiscoverRunner


class MySQLTestRunner(DiscoverRunner):

    def setup_databases(self, **kwargs):
        ret = super(MySQLTestRunner, self).setup_databases(**kwargs)

        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
        print("MySQL version is '{}'".format(version))

        return ret
