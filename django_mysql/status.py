# -*- coding:utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)

import time

from django.db import connections
from django.db.utils import DEFAULT_DB_ALIAS
from django.utils.functional import SimpleLazyObject

from django_mysql.exceptions import TimeoutError


class BaseStatus(object):
    """
    Base class for the status classes
    """
    query = ""

    def __init__(self, using=None):
        if using is None:
            self.db = DEFAULT_DB_ALIAS
        else:
            self.db = using

    def get_cursor(self):
        return connections[self.db].cursor()

    def get(self, name):
        if '%' in name:
            raise ValueError("get() is for fetching single variables, "
                             "no % wildcards")
        with self.get_cursor() as cursor:
            num_rows = cursor.execute(self.query + " LIKE %s", (name,))
            if num_rows == 0:
                raise KeyError("No such status variable '%s'" % (name,))
            return self._cast(cursor.fetchone()[1])

    def get_many(self, names):
        if not names:
            return {}

        if any(("%" in name) for name in names):
            raise ValueError("get_many() is for fetching named "
                             "variables, no % wildcards")

        with self.get_cursor() as cursor:
            query = [self.query, "WHERE Variable_name IN ("]
            query.extend(", ".join("%s" for n in names))
            query.append(")")
            cursor.execute(" ".join(query), names)

            return {
                name: self._cast(value)
                for name, value in cursor.fetchall()
            }

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

    def wait_until_load_low(self, thresholds=None, timeout=60.0, sleep=0.1):
        if thresholds is None:
            thresholds = {'Threads_running': 10}

        start = time.time()
        names = thresholds.keys()

        while True:
            current = self.get_many(names)

            higher = []
            for name in names:
                if current[name] > thresholds[name]:
                    higher.append(name)

            if not higher:
                return

            if timeout and time.time() > start + timeout:
                raise TimeoutError(
                    "Span too long waiting for load to drop: " +
                    ",".join(
                        "{} > {}".format(name, thresholds[name])
                        for name in higher
                    ),
                )
            time.sleep(sleep)


class SessionStatus(BaseStatus):
    query = "SHOW SESSION STATUS"


global_status = SimpleLazyObject(GlobalStatus)
session_status = SimpleLazyObject(SessionStatus)
