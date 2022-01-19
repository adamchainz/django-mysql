from __future__ import annotations

from contextlib import contextmanager

import django
import pytest
from django.db import DEFAULT_DB_ALIAS, connection, connections
from django.test.utils import CaptureQueriesContext

from django_mysql.utils import connection_is_mariadb


@contextmanager
def skip_if_mysql_8_plus():
    if not connection_is_mariadb(connection) and connection.mysql_version >= (8,):
        pytest.skip("Requires MySQL<8 or MariaDB")
    yield


skip_if_django_3_1_plus = pytest.mark.skipif(
    django.VERSION >= (3, 1), reason="Requires Django < 3.1"
)
skip_if_django_before_3_1 = pytest.mark.skipif(
    django.VERSION < (3, 1), reason="Requires Django 3.1+"
)


def column_type(table_name, column_name):
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
               WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND
                     COLUMN_NAME = %s""",
            (table_name, column_name),
        )
        return cursor.fetchone()[0]


class CaptureLastQuery:
    def __init__(self, conn=None):
        if conn is None:  # pragma: no branch
            conn = connection
        self.conn = conn

    def __enter__(self):
        self.capturer = CaptureQueriesContext(self.conn)
        self.capturer.__enter__()
        return self

    def __exit__(self, a, b, c):
        self.capturer.__exit__(a, b, c)

    @property
    def query(self):
        return self.capturer.captured_queries[-1]["sql"]


class print_all_queries:
    def __init__(self, conn=None):
        if conn is None:  # pragma: no branch
            conn = connection
        self.conn = conn

    def __enter__(self):
        self.capturer = CaptureQueriesContext(self.conn)
        self.capturer.__enter__()
        return self

    def __exit__(self, a, b, c):
        self.capturer.__exit__(a, b, c)
        for q in self.capturer.captured_queries:
            print(q["sql"])


def used_indexes(query, using=DEFAULT_DB_ALIAS):
    """
    Given SQL 'query', run EXPLAIN and return the names of the indexes used
    """
    connection = connections[using]
    with connection.cursor() as cursor:
        cursor.execute("EXPLAIN " + query)

        return {row["key"] for row in fetchall_dicts(cursor) if row["key"] is not None}


def fetchall_dicts(cursor):
    columns = [x[0] for x in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
