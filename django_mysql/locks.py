# -*- coding:utf-8 -*-
import contextlib

from django.db import connections
from django.db.utils import DEFAULT_DB_ALIAS


class TimeoutError(Exception):
    pass


class Lock(object):
    def __init__(self, name, acquire_timeout=10.0, connection_name=None):
        self.acquire_timeout = acquire_timeout
        if connection_name is None:
            connection_name = DEFAULT_DB_ALIAS
        self.connection_name = connection_name

        # For multi-database servers, we prefix the name of the lock wth
        # the database, to protect against concurrent apps with the same locks
        self.name = '.'.join((
            connections[self.connection_name].settings_dict['NAME'],
            name
        ))

    def get_cursor(self):
        return connections[self.connection_name].cursor()

    def __enter__(self):
        cursor = self.get_cursor()
        with contextlib.closing(cursor):
            cursor.execute(
                "SELECT GET_LOCK(%s, %s)",
                (self.name, self.acquire_timeout)
            )
            result = cursor.fetchone()[0]
            if result == 1:
                return self
            else:
                raise TimeoutError(
                    "Waited >{} seconds to gain lock".format(
                        self.acquire_timeout)
                )

    def __exit__(self, a, b, c):
        cursor = self.get_cursor()
        with contextlib.closing(cursor):
            cursor.execute("SELECT RELEASE_LOCK(%s)", (self.name,))
            result = cursor.fetchone()[0]

            if result is not None and result == 0:
                raise ValueError("Tried to release an unheld lock.")

    def is_held(self):
        return (self.holding_connection_id() is not None)

    def holding_connection_id(self):
        cursor = self.get_cursor()
        with contextlib.closing(cursor):
            cursor.execute("SELECT IS_USED_LOCK(%s)", (self.name,))
            return cursor.fetchone()[0]
