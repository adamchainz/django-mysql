# -*- coding:utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import pytest
from django.db import connections
from django.test import TestCase

from django_mysql.test.utils import override_mysql_variables


class OverrideVarsMethodTest(TestCase):

    @override_mysql_variables(SQL_MODE="MSSQL")
    def test_method_sets_mssql(self):
        self.check_sql_mode("MSSQL")

    def check_sql_mode(self, expected, using='default'):
        with connections[using].cursor() as cursor:
            cursor.execute("SELECT @@SQL_MODE")
            mode = cursor.fetchone()[0]

        mode = mode.split(',')
        assert expected in mode


@override_mysql_variables(SQL_MODE="ANSI")
class OverrideVarsClassTest(OverrideVarsMethodTest):

    def test_class_sets_ansi(self):
        self.check_sql_mode("ANSI")

    @override_mysql_variables(using='other', SQL_MODE='MSSQL')
    def test_other_connection(self):
        self.check_sql_mode("ANSI")
        self.check_sql_mode("MSSQL", using='other')

    def test_it_fails_on_non_test_classes(self):
        with pytest.raises(Exception):
            @override_mysql_variables(SQL_MODE="ANSI")
            class MyClass(object):
                pass
