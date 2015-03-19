from random import randint
import re

from django.db import connections


class Handler(object):
    absolute_col_re = re.compile("`[^`]+`.(`[^`]+`)")

    def __init__(self, queryset):
        self._queryset = queryset
        self._model = queryset.model
        self._table_name = self._model._meta.db_table
        self._handler_name = '{}_{}'.format(self._table_name, randint(1, 2e10))

        sql, params = queryset.query.sql_with_params()
        where_pos = sql.find('WHERE ')
        if where_pos != -1:
            where_clause = sql[where_pos:]
            # replace absolute table-column refs with relative ones
            where_clause, _ = self.absolute_col_re.subn(r"\1", where_clause)
            self._where_clause = where_clause
            self._params = params
        else:
            self._where_clause = ""
            self._params = ()

    def __enter__(self):
        self.cursor = connections[self._queryset.db].cursor()
        self.cursor.__enter__()
        self.cursor.execute("HANDLER `{}` OPEN AS {}"
                            .format(self._table_name, self._handler_name))
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.cursor.execute("HANDLER `{}` CLOSE".format(self._handler_name))
        self.cursor.__exit__(exc_type, exc_value, traceback)

    def read(self, mode='first', limit=None):
        sql = ["HANDLER {} READ `PRIMARY`".format(self._handler_name)]
        params = ()

        if mode == 'first':
            sql.append("FIRST")

        if self._where_clause:
            sql.append(self._where_clause)
            params += self._params

        if limit is not None:
            sql.append("LIMIT %s")
            params += (limit,)

        return self._model.objects.raw(" ".join(sql), params)
