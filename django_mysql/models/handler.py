from random import randint

from django.db import connections


class Handler(object):
    def __init__(self, manager):
        self.manager = manager

    def __enter__(self):
        self._handler_name = '{}_{}'.format(
            self._table_name,
            randint(1, 9999999)
        )
        self.cursor = connections[self.manager.db].cursor()
        self.cursor.__enter__()
        self.cursor.execute("HANDLER `{}` OPEN AS {}"
                            .format(self._table_name, self._handler_name))
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.cursor.execute("HANDLER {} CLOSE".format(self._handler_name))
        self.cursor.__exit__(exc_type, exc_value, traceback)

    def read(self, limit):
        return self.manager.raw(
            "HANDLER {} READ `PRIMARY` FIRST LIMIT {:d}"
            .format(self._handler_name, limit)
        )

    @property
    def _table_name(self):
        return self.manager.model._meta.db_table
