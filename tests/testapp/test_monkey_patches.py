# -*- coding:utf-8 -*-
from django.db import connections
from django.test import TestCase


class IsMariaDBTests(TestCase):

    def test_connections(self):
        for alias in connections:
            connection = connections[alias]
            if not hasattr(connection, 'mysql_version'):
                continue
            with connection.cursor() as cursor:
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()[0]

            is_mariadb = ('MariaDB' in version)
            assert connection.is_mariadb == is_mariadb

            # Check it was cached by cached_property
            assert 'is_mariadb' in connection.__dict__
