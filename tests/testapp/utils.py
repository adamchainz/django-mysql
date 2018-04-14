# -*- encoding:utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)

import sys
from contextlib import contextmanager
from unittest import skipUnless

from django.db import DEFAULT_DB_ALIAS, connection, connections
from django.test.utils import CaptureQueriesContext
from django.utils import six

requiresPython2 = skipUnless(six.PY2, "Python 2 only")


# Copied from Django 1.8
@contextmanager
def captured_output(stream_name):
    """Return a context manager used by captured_stdout/stdin/stderr
    that temporarily replaces the sys stream *stream_name* with a StringIO.

    Note: This function and the following ``captured_std*`` are copied
          from CPython's ``test.support`` module."""
    orig_stdout = getattr(sys, stream_name)
    setattr(sys, stream_name, six.StringIO())
    try:
        yield getattr(sys, stream_name)
    finally:
        setattr(sys, stream_name, orig_stdout)


# Copied from Django 1.8
def captured_stdout():
    """Capture the output of sys.stdout:

       with captured_stdout() as stdout:
           print("hello")
       self.assertEqual(stdout.getvalue(), "hello\n")
    """
    return captured_output("stdout")


def column_type(table_name, column_name):
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
               WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND
                     COLUMN_NAME = %s""",
            (table_name, column_name),
        )
        return cursor.fetchone()[0]


class CaptureLastQuery(object):
    def __init__(self, conn=None):
        if conn is None:
            self.conn = connection
        else:
            self.conn = conn

    def __enter__(self):
        self.capturer = CaptureQueriesContext(self.conn)
        self.capturer.__enter__()
        return self

    def __exit__(self, a, b, c):
        self.capturer.__exit__(a, b, c)

    @property
    def query(self):
        return self.capturer.captured_queries[-1]['sql']


class print_all_queries(object):
    def __init__(self, conn=None):
        if conn is None:
            self.conn = connection
        else:
            self.conn = conn

    def __enter__(self):
        self.capturer = CaptureQueriesContext(self.conn)
        self.capturer.__enter__()
        return self

    def __exit__(self, a, b, c):
        self.capturer.__exit__(a, b, c)
        for q in self.capturer.captured_queries:
            print(q['sql'])


def used_indexes(query, using=DEFAULT_DB_ALIAS):
    """
    Given SQL 'query', run EXPLAIN and return the names of the indexes used
    """
    connection = connections[using]
    with connection.cursor() as cursor:
        cursor.execute("EXPLAIN " + query)

        return {row['key'] for row in fetchall_dicts(cursor)
                if row['key'] is not None}


def fetchall_dicts(cursor):
    columns = [x[0] for x in cursor.description]
    rows = []
    for row in cursor.fetchall():
        rows.append(
            dict(zip(columns, row)),
        )
    return rows
