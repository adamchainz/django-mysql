# -*- coding:utf-8 -*-
from datetime import datetime

from django.db.models import DateTimeField

from django_mysql.compat import field_class

__all__ = ('TimestampField',)


class TimestampField(field_class(DateTimeField)):
    # def __init__(self, null=False, blank=False, **kwargs):
        # super(UnixTimestampField, self).__init__(**kwargs)
        # # default for TIMESTAMP is NOT NULL unlike most fields, so we have to
        # # cheat a little:
        # self.blank, self.isnull = blank, null
        # self.null = True # To prevent the framework from shoving in "not null".

    def db_type(self, connection):
        typ = ['TIMESTAMP']
        # See above!
        if self.isnull:
            typ += ['NULL']
        # This should go into has_default and get_default
        # if self.auto_created:
        #     typ += ['default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP']
        return ' '.join(typ)

    def to_python(self, value):
        if isinstance(value, int):
            return datetime.fromtimestamp(value)
        else:
            return super(TimestampField, self).to_python(self, value)

    def get_db_prep_value(self, value, connection, prepared=False):
        if value is None:
            return value
        else:
            return datetime.strftime('%Y-%m-%d %H:%M:%S', value.timetuple())
