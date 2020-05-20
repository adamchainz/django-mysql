import functools

from django.conf import settings
from django.db.backends.mysql.base import CursorWrapper

from django_mysql.rewrite_query import REWRITE_MARKER, rewrite_query


def patch():
    settings_value = getattr(settings, "DJANGO_MYSQL_REWRITE_QUERIES", False)
    if callable(settings_value):
        settings_value = settings_value()

    patch_CursorWrapper_execute(settings_value)


def patch_CursorWrapper_execute(should_apply):

    # Be idemptotent
    if getattr(CursorWrapper, "_has_django_mysql_execute", False):
        return

    orig_execute = CursorWrapper.execute

    @functools.wraps(orig_execute)
    def execute(self, sql, args=None):
        if should_apply and REWRITE_MARKER in sql:
            sql = rewrite_query(sql)
        return orig_execute(self, sql, args)

    CursorWrapper.execute = execute
    CursorWrapper._has_django_mysql_execute = True
