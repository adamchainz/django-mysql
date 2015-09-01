import pytest
from django.db import connection, connections
from django.test import TestCase

from django_mysql.test.utils import (
    assert_mysql_queries, override_mysql_variables
)


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


class AssertMySQLQueriesTests(TestCase):

    def test_nothing(self):
        with connection.cursor() as cursor, assert_mysql_queries():
            cursor.execute("SELECT 1")

    def test_detects_full_joins(self):
        with pytest.raises(AssertionError) as excinfo:
            with connection.cursor() as cursor, assert_mysql_queries():
                cursor.execute(self.full_join_query)
        assert '1 full join was executed - expected 0' in str(excinfo.value)

    def test_allows_full_joins_when_None(self):
        checker = assert_mysql_queries(full_joins=None)
        with connection.cursor() as cursor, checker:
            cursor.execute(self.full_join_query)

    def test_detects_selects(self):
        checker = assert_mysql_queries(selects=0)
        with pytest.raises(AssertionError) as excinfo:
            with connection.cursor() as cursor, checker:
                cursor.execute("SELECT 1")
        assert '1 SELECT was executed - expected 0.' in str(excinfo.value)

    def test_detects_inserts(self):
        checker = assert_mysql_queries(inserts=0)
        with pytest.raises(AssertionError) as excinfo:
            with connection.cursor() as cursor, checker:
                cursor.execute("CREATE TEMPORARY TABLE test (c1 int)")
                cursor.execute("INSERT INTO test (c1) VALUES (1)")
                cursor.execute("DROP TEMPORARY TABLE test")
        assert '1 INSERT was executed - expected 0.' in str(excinfo.value)

    def test_detects_updates(self):
        checker = assert_mysql_queries(updates=0)
        with pytest.raises(AssertionError) as excinfo:
            with connection.cursor() as cursor, checker:
                cursor.execute("CREATE TEMPORARY TABLE test (c1 int)")
                cursor.execute("UPDATE test SET c1 = 2")
                cursor.execute("DROP TEMPORARY TABLE test")
        assert '1 UPDATE was executed - expected 0.' in str(excinfo.value)

    def test_detects_deletes(self):
        checker = assert_mysql_queries(deletes=0)
        with pytest.raises(AssertionError) as excinfo:
            with connection.cursor() as cursor, checker:
                cursor.execute("CREATE TEMPORARY TABLE test (c1 int)")
                cursor.execute("DELETE FROM test")
                cursor.execute("DROP TEMPORARY TABLE test")
        assert '1 DELETE was executed - expected 0.' in str(excinfo.value)

    # This always is a 'full join' since I_S tables have no indexes
    full_join_query = """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.TABLES I1
        INNER JOIN INFORMATION_SCHEMA.TABLES I2
        ON I1.TABLE_NAME = I2.TABLE_NAME"""
