# -*- coding:utf-8 -*-
from __future__ import unicode_literals

import functools

from django.conf import settings
from django.db.backends.mysql.base import CursorWrapper
from django.utils.functional import cached_property

from django_mysql.rewrite_query import REWRITE_MARKER, rewrite_query


@cached_property
def is_mariadb(self):
    """
    Method to be monkey-patched onto connection, to allow easy checks for if
    the current database connection is MariaDB
    """
    with self.temporary_connection():
        server_info = self.connection.get_server_info()
        return 'MariaDB' in server_info


# Query rewriting


def patch_CursorWrapper_execute():

    # Be idemptotent
    if getattr(CursorWrapper, '_has_django_mysql_execute', False):
        return

    orig_execute = CursorWrapper.execute

    @functools.wraps(orig_execute)
    def execute(self, sql, args=None):
        if (
            getattr(settings, 'DJANGO_MYSQL_REWRITE_QUERIES', False) and
            REWRITE_MARKER in sql
        ):
            sql = rewrite_query(sql)
        return orig_execute(self, sql, args)

    CursorWrapper.execute = execute
    CursorWrapper._has_django_mysql_execute = True
