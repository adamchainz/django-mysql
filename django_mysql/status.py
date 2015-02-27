# -*- coding:utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import time

from django.db import connections
from django.db.utils import DEFAULT_DB_ALIAS

from .exceptions import TimeoutError


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
        with self.get_cursor() as cursor:
            num_rows = cursor.execute(self.query + " LIKE %s", (name,))
            if num_rows == 0:
                raise KeyError("No such status variable '%s'" % (name,))
            return self._cast(cursor.fetchone()[1])

    def as_dict(self, prefix=None):
        with self.get_cursor() as cursor:
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

    def wait_until_load_low(self, var_name='Threads_running', var_max=5,
                            timeout=60.0, sleep=0.1):
        start = time.time()

        while True:
            if self.get(var_name) <= var_max:
                return

            if timeout and time.time() > start + timeout:
                raise TimeoutError(
                    "Span too long waiting for {} to drop below {}"
                    .format(var_name, var_max)
                )
            time.sleep(sleep)


class SessionStatus(BaseStatus):
    query = "SHOW SESSION STATUS"
