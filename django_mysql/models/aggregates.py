import django
from django.db.models import Aggregate, CharField
from django.db.models.sql.aggregates import Aggregate as SQLAggregate
from django.utils.functional import cached_property

from django_mysql.models.fields import ListTextField

__all__ = ('GroupConcat',)


if django.VERSION < (1, 8):

    class GroupConcat(Aggregate):
        def add_to_query(self, query, alias, col, source, is_summary):
            query.aggregates[alias] = SQLGroupConcat(
                col,
                source=source,
                is_summary=is_summary,
                **self.extra
            )

else:

    class GroupConcat(Aggregate):
        function = 'GROUP_CONCAT'
        name = 'GroupConcat'
        template = '%(function)s(%(distinct)s%(expressions)s%(separator)s)'

        def __init__(self, expression, distinct=False, separator=',', **extra):
            self.distinct = distinct
            self.separator = separator

            self.template = self.compile_template()

            super(GroupConcat, self).__init__(expression, **extra)

        @property
        def output_field(self):
            safe_input = isinstance(self.input_field.output_field,
                                    ListTextField.ALLOWED_BASE_FIELDS)
            if self.separator == ',' and safe_input:
                return ListTextField(base_field=self.input_field.output_field)
            else:
                return CharField()

        def compile_template(self):
            template = ["%(function)s("]

            if self.distinct:
                template.append("DISTINCT ")

            template.append("%(field)s")

            if self.separator != ',':
                template.append(' SEPARATOR "{}"'.format(self.separator))

            template.append(")")

            return "".join(template)


class SQLGroupConcat(SQLAggregate):

    def __init__(self, col, distinct=False, separator=',', **extra):
        super(SQLGroupConcat, self).__init__(col, **extra)

        self.distinct = distinct
        self.separator = separator

    sql_function = 'GROUP_CONCAT'

    @cached_property
    def sql_template(self):
        # Constructing a template...

        template = ["%(function)s("]

        if self.distinct:
            template.append("DISTINCT ")

        template.append("%(field)s")

        template.append(' SEPARATOR "{}"'.format(self.separator))

        template.append(")")

        return "".join(template)
