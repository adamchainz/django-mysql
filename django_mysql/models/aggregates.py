import django
from django.db.models import Aggregate, CharField
from django.utils.functional import cached_property

# Major aggregate simplification from 1.7 to 1.8 - it's easier to implement
# each twice than try fudge a class that works before and after

if django.VERSION[:2] < (1, 8):

    from django.db.models.sql.aggregates import Aggregate as SQLAggregate

    class BitAnd(Aggregate):
        name = 'BitAnd'

        def add_to_query(self, query, alias, col, source, is_summary):
            query.aggregates[alias] = BitAndSQL(
                col,
                source=source,
                is_summary=is_summary,
                **self.extra
            )

    class BitAndSQL(SQLAggregate):
        sql_function = 'BIT_AND'
        is_ordinal = True  # is an integer

    class BitOr(Aggregate):
        name = 'BitOr'

        def add_to_query(self, query, alias, col, source, is_summary):
            query.aggregates[alias] = BitOrSQL(
                col,
                source=source,
                is_summary=is_summary,
                **self.extra
            )

    class BitOrSQL(SQLAggregate):
        sql_function = 'BIT_OR'
        is_ordinal = True  # is an integer

    class BitXor(Aggregate):
        name = 'BitXor'

        def add_to_query(self, query, alias, col, source, is_summary):
            query.aggregates[alias] = BitXorSQL(
                col,
                source=source,
                is_summary=is_summary,
                **self.extra
            )

    class BitXorSQL(SQLAggregate):
        sql_function = 'BIT_XOR'
        is_ordinal = True  # is an integer

    class GroupConcat(Aggregate):
        def add_to_query(self, query, alias, col, source, is_summary):
            query.aggregates[alias] = SQLGroupConcat(
                col,
                source=source,
                is_summary=is_summary,
                **self.extra
            )

    class SQLGroupConcat(SQLAggregate):

        def __init__(self, col, distinct=False, separator=None,
                     ordering=None, **extra):
            super(SQLGroupConcat, self).__init__(col, **extra)

            self.distinct = distinct
            self.separator = separator

            # This can/will be improved to SetTextField or ListTextField
            self.field = CharField()

            if ordering not in ('asc', 'desc', None):
                raise ValueError(
                    "'ordering' must be one of 'asc', 'desc', or None")
            self.ordering = ordering

        sql_function = 'GROUP_CONCAT'

        @cached_property
        def sql_template(self):
            # Constructing a template...

            template = ["%(function)s("]

            if self.distinct:
                template.append("DISTINCT ")

            template.append("%(field)s")

            if self.separator is not None:
                template.append(" SEPARATOR '{}'".format(self.separator))

            if self.ordering is not None:
                template.append(" ORDER BY %(field)s " + self.ordering.upper())

            template.append(")")

            return "".join(template)


else:

    class BitAnd(Aggregate):
        function = 'BIT_AND'
        name = 'bitand'

    class BitOr(Aggregate):
        function = 'BIT_OR'
        name = 'bitor'

    class BitXor(Aggregate):
        function = 'BIT_XOR'
        name = 'bitxor'

    class GroupConcat(Aggregate):
        function = 'GROUP_CONCAT'

        def __init__(self, expression, distinct=False, separator=None,
                     ordering=None, **extra):

            if 'output_field' not in extra:
                # This can/will be improved to SetTextField or ListTextField
                extra['output_field'] = CharField()

            super(GroupConcat, self).__init__(expression, **extra)

            self.distinct = distinct
            self.separator = separator

            if ordering not in ('asc', 'desc', None):
                raise ValueError(
                    "'ordering' must be one of 'asc', 'desc', or None")
            self.ordering = ordering

        def as_sql(self, compiler, connection, function=None, template=None):
            connection.ops.check_expression_support(self)
            sql = ["GROUP_CONCAT("]
            if self.distinct:
                sql.append("DISTINCT ")

            expr_parts = []
            params = []
            for arg in self.source_expressions:
                arg_sql, arg_params = compiler.compile(arg)
                expr_parts.append(arg_sql)
                params.extend(arg_params)
            expr_sql = self.arg_joiner.join(expr_parts)

            sql.append(expr_sql)

            if self.separator is not None:
                sql.append(" SEPARATOR '{}'".format(self.separator))

            if self.ordering is not None:
                sql.append(" ORDER BY ")
                sql.append(expr_sql)
                params.extend(params[:])
                sql.append(" ")
                sql.append(self.ordering.upper())

            sql.append(")")

            return "".join(sql), params
