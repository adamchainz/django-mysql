import re
from random import randint

from django.db import connections


class Handler:
    def __init__(self, queryset):
        self.open = False

        self.db = queryset.db
        self._model = queryset.model
        self._table_name = self._model._meta.db_table

        self._handler_name = self._construct_name(self._table_name)
        self._where, self._params = self._extract_where(queryset)

    def _construct_name(self, table_name):
        # Undocumented max of 64 chars (get error on HANDLER CLOSE only!)
        return "{}_{}".format(table_name[-31:], randint(1, 2e10))

    # Context manager

    def __enter__(self):
        if self.open:
            raise ValueError("You cannot open the same handler twice!")
        self.cursor = connections[self.db].cursor()
        self.cursor.__enter__()
        self.cursor.execute(
            "HANDLER `{}` OPEN AS {}".format(self._table_name, self._handler_name)
        )
        self.open = True
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not self.open:
            raise ValueError("You cannot close an unopened handler!")
        self.cursor.execute("HANDLER `{}` CLOSE".format(self._handler_name))
        self.cursor.__exit__(exc_type, exc_value, traceback)
        self.open = False

    # Public methods

    def read(self, index="PRIMARY", mode=None, where=None, limit=None, **kwargs):
        if not self.open:
            raise RuntimeError("This handler isn't open yet")

        index_op, index_value = self._parse_index_value(kwargs)

        if index_op is not None and mode is not None:
            raise ValueError(
                "You cannot use an index operator and mode "
                "together in a handler read"
            )
        elif index_op is None and mode is None:
            # Default
            mode = "first"

        sql = ["HANDLER {} READ".format(self._handler_name)]
        params = ()

        # Caller's responsibility to ensure the index name is correct
        sql.append("`{}`".format(index))

        if index_op is not None:
            sql.append(index_op)
            if isinstance(index_value, tuple):
                sql.append("(")
                sql.append(",".join("%s" for x in index_value))
                sql.append(")")
                params += index_value
            else:
                sql.append("(%s)")
                params += (index_value,)

        if index_op is None:
            try:
                sql.append(self._read_modes[mode])
            except KeyError:
                raise ValueError(
                    "'mode' must be one of: {}".format(
                        ",".join(self._read_modes.keys())
                    )
                )

        if where is None:
            # Use default
            if self._where:
                sql.append(self._where)
                params += self._params
        else:
            # 'where' is another queryset to use the clause from
            if isinstance(where, tuple):
                # Allow parsing in a pre-extracted where clause + params -
                # as iter() does
                where, where_params = where
            else:
                where, where_params = self._extract_where(where)
            sql.append(where)
            params += where_params

        if limit is not None:
            sql.append("LIMIT %s")
            params += (limit,)

        return self._model.objects.using(self.db).raw(" ".join(sql), params)

    _read_modes = {"first": "FIRST", "last": "LAST", "next": "NEXT", "prev": "PREV"}

    def _parse_index_value(self, kwargs):
        """
        Parse the HANDLER-supported subset of django's __ expression syntax
        """
        if len(kwargs) == 0:
            return None, None
        elif len(kwargs) > 1:
            raise ValueError(
                "You can't pass more than one value expression, "
                "you passed {}".format(",".join(kwargs.keys()))
            )

        name, value = list(kwargs.items())[0]

        if not name.startswith("value"):
            raise ValueError(
                "The keyword arg {} is not valid for this " "function".format(name)
            )

        if name == "value":
            return ("=", value)

        if not name.startswith("value__"):
            raise ValueError(
                "The keyword arg {} is not valid for this " "function".format(name)
            )

        operator = name[name.find("__") + 2 :]
        try:
            return (self._operator_values[operator], value)
        except KeyError:
            raise ValueError(
                "The operator {op} is not valid for index value matching. "
                "Valid operators are {valid}".format(
                    op=operator, valid=",".join(self._operator_values.keys())
                )
            )

    _operator_values = {"lt": "<", "lte": "<=", "exact": "=", "gte": ">=", "gt": ">"}

    def iter(self, index="PRIMARY", where=None, chunk_size=100, reverse=False):
        if reverse:
            mode = "last"
        else:
            mode = "first"

        if where is not None:
            # Pre-convert so each iteration doesn't have to repeatedly parse
            # the SQL
            where = self._extract_where(where)

        while True:
            count = 0
            for obj in self.read(index=index, where=where, mode=mode, limit=chunk_size):
                count += 1
                yield obj

            if count < chunk_size:
                return

            if reverse:
                mode = "prev"
            else:
                mode = "next"

    # Internal methods

    @classmethod
    def _extract_where(cls, queryset):
        """
        Was this a queryset with filters/excludes/expressions set? If so,
        extract the WHERE clause from the ORM output so we can use it in the
        handler queries.
        """
        if not cls._is_simple_query(queryset.query):
            raise ValueError(
                "This QuerySet's WHERE clause is too complex to " "be used in a HANDLER"
            )

        sql, params = queryset.query.sql_with_params()
        where_pos = sql.find("WHERE ")
        if where_pos != -1:
            # Cut the query to extract just its WHERE clause
            where_clause = sql[where_pos:]
            # Replace absolute table.column references with relative ones
            # since that is all HANDLER can work with
            # This is a bit flakey - if you inserted extra SQL with extra() or
            # an expression or something it might break.
            where_clause, _ = cls.absolute_col_re.subn(r"\1", where_clause)
            return (where_clause, params)
        else:
            return ("", ())

    # For modifying the queryset SQL. Attempts to match the TABLE.COLUMN
    # pattern that Django compiles. Clearly not perfect.
    absolute_col_re = re.compile("`[^`]+`.(`[^`]+`)")

    @classmethod
    def _is_simple_query(cls, query):
        """
        Inspect the internals of the Query and say if we think its WHERE clause
        can be used in a HANDLER statement
        """
        return (
            not query.low_mark
            and not query.high_mark
            and not query.select
            and not query.group_by
            and not query.distinct
            and not query.order_by
            and len(query.alias_map) <= 1
        )
