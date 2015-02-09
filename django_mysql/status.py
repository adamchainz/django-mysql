# -*- coding:utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import contextlib

from django.db import connections
from django.db.utils import DEFAULT_DB_ALIAS


class BaseStatus(object):
    """
    Base class for the status classes
    """
    query = ""

    def __init__(self, connection_name=None):
        if connection_name is None:
            connection_name = DEFAULT_DB_ALIAS
        self.connection_name = connection_name

    def get_cursor(self):
        return connections[self.connection_name].cursor()

    def get(self, name):
        if '%' in name:
            raise ValueError("get() is for fetching single variables, "
                             "no % wildcards")
        cursor = self.get_cursor()
        with contextlib.closing(cursor):
            num_rows = cursor.execute(self.query + " LIKE %s", (name,))
            if num_rows == 0:
                raise KeyError("No such status variable '%s'" % (name,))
            return self._cast(cursor.fetchone()[1])

    def as_dict(self, prefix=None):
        cursor = self.get_cursor()
        with contextlib.closing(cursor):
            if prefix is None:
                cursor.execute(self.query)
            else:
                cursor.execute(self.query + " LIKE %s", (prefix + '%',))
            rows = cursor.fetchall()
            return {name: self._cast(value) for name, value in rows}

    def _cast(self, value):
        # Many status variables are integers or floats but SHOW GLOBAL STATUS
        # returns them as strings
        try:
            value = int(value)
        except ValueError:
            try:
                value = float(value)
            except ValueError:
                pass

        if value == 'ON':
            return True
        elif value == 'OFF':
            return False

        return value


class GlobalStatus(BaseStatus):
    query = "SHOW GLOBAL STATUS"


class SessionStatus(BaseStatus):
    query = "SHOW SESSION STATUS"
