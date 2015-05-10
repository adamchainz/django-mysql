import django
from django.db.models import Aggregate, CharField
from django.db.models.sql.aggregates import Aggregate as SQLAggregate
from django.utils.functional import cached_property

__all__ = ('BitAnd', 'GroupConcat',)

# Major aggregate simplification from 1.7 to 1.8. However it makes implementing
# the one class for each side a pain, so do everything twice...

if django.VERSION < (1, 8):

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

else:

    class BitAnd(Aggregate):
        function = 'BIT_AND'
        name = 'bitand'


class GroupConcat(Aggregate):
    def add_to_query(self, query, alias, col, source, is_summary):
        query.aggregates[alias] = SQLGroupConcat(
            col,
            source=source,
            is_summary=is_summary,
            **self.extra
        )


class SQLGroupConcat(SQLAggregate):

    def __init__(self, col, distinct=False, separator=None, **extra):
        super(SQLGroupConcat, self).__init__(col, **extra)

        self.distinct = distinct
        self.separator = separator

        # This can/will be improved to SetTextField or ListTextField
        self.field = CharField()

    sql_function = 'GROUP_CONCAT'

    @cached_property
    def sql_template(self):
        # Constructing a template...

        template = ["%(function)s("]

        if self.distinct:
            template.append("DISTINCT ")

        template.append("%(field)s")

        if self.separator is not None:
            template.append(' SEPARATOR "{}"'.format(self.separator))

        template.append(")")

        return "".join(template)
