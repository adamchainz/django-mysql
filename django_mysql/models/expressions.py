from django.db.models.expressions import BaseExpression, F, Value

from django_mysql.utils import collapse_spaces


class SetF(object):

    def __init__(self, field_name):
        self.field = F(field_name)

    def add(self, value):
        if not hasattr(value, 'as_sql'):
            value = Value(value)
        return AppendSetF(self.field, value)

    def remove(self, value):
        if not hasattr(value, 'as_sql'):
            value = Value(value)
        return RemoveSetF(self.field, value)


class BaseSetF(BaseExpression):

    def __init__(self, lhs, rhs):
        super(BaseSetF, self).__init__()
        self.lhs = lhs
        self.rhs = rhs

    def get_source_expressions(self):
        return [self.lhs, self.rhs]

    def set_source_expressions(self, exprs):
        self.lhs, self.rhs = exprs


class AppendSetF(BaseSetF):

    sql_expression = collapse_spaces("""
        (
            IF(
                FIND_IN_SET(the_value, the_field),
                the_field,
                CONCAT_WS(
                    ',',
                    IF(CHAR_LENGTH(the_field), the_field, NULL),
                    the_value
                )
            )
        )
    """).replace('the_field', '%s').replace('the_value', '%s')

    def as_sql(self, compiler, connection):
        field, field_params = compiler.compile(self.lhs)
        value, value_params = compiler.compile(self.rhs)

        sql = self.sql_expression % (value, field, field, field, field, value)

        params = []
        # Once for each mention
        params.extend(value_params)
        params.extend(field_params)
        params.extend(field_params)
        params.extend(field_params)
        params.extend(field_params)
        params.extend(value_params)

        return sql, params


class RemoveSetF(BaseSetF):

    sql_expression = collapse_spaces("""
        (
            IF(
                @pos:=FIND_IN_SET(the_value, the_field),
                CONCAT_WS(
                    ",",
                    LEAST(
                        @num_items:=(
                            CHAR_LENGTH(the_field) -
                            CHAR_LENGTH(REPLACE(the_field, ',', '')) +
                            IF(CHAR_LENGTH(the_field), 1, 0)
                        ),
                        NULL
                    ),
                    NULLIF(SUBSTRING_INDEX(the_field, ",", @pos - 1), ''),
                    NULLIF(
                        SUBSTRING_INDEX(the_field, ",", -(@num_items - @pos)),
                        '')
                ),
                the_field
            )
        )
    """).replace("the_field", "%s").replace("the_value", "%s")

    def as_sql(self, compiler, connection):
        field, field_params = compiler.compile(self.lhs)
        value, value_params = compiler.compile(self.rhs)

        sql = self.sql_expression % (value, field, field, field, field, field,
                                     field, field)

        params = []
        # Once for each mention
        params.extend(value_params)
        params.extend(field_params)
        params.extend(field_params)
        params.extend(field_params)
        params.extend(field_params)
        params.extend(field_params)
        params.extend(field_params)
        params.extend(field_params)

        return sql, params
