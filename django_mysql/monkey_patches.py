# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from django.utils.functional import cached_property


@cached_property
def is_mariadb(self):
    """
    Method to be monkey-patched onto connection, to allow easy checks for if
    the current database connection is MariaDB
    """
    with self.temporary_connection():
        server_info = self.connection.get_server_info()
        return 'MariaDB' in server_info
