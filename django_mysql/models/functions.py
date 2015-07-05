from django.db import DEFAULT_DB_ALIAS, connections
from django.db.models import CharField, IntegerField, TextField

from django_mysql.compat import Func, Value


class SingleArgFunc(Func):

    output_field_class = None

    def __init__(self, expression):
        super(SingleArgFunc, self).__init__(expression)
        if self.output_field_class is not None:
            self.output_field = self.output_field_class()


class MultiArgFunc(Func):
    def __init__(self, *expressions):
        super(MultiArgFunc, self).__init__(*expressions)


# Comparison Functions


class Greatest(MultiArgFunc):
    function = 'GREATEST'


class Least(MultiArgFunc):
    function = 'LEAST'


# Numeric Functions


class Abs(SingleArgFunc):
    function = 'ABS'
    output_field_class = IntegerField


class Ceiling(SingleArgFunc):
    function = 'CEILING'
    output_field_class = IntegerField


class CRC32(SingleArgFunc):
    function = 'CRC32'
    output_field_class = IntegerField


class Floor(SingleArgFunc):
    function = 'FLOOR'
    output_field_class = IntegerField


class Round(Func):
    function = 'ROUND'
    output_field_class = IntegerField

    def __init__(self, expression, places=0):
        super(Round, self).__init__(expression, places)


class Sign(SingleArgFunc):
    function = 'SIGN'
    output_field_class = IntegerField


# String Functions

class ConcatWS(Func):
    """
    Stands for CONCAT_With-Separator
    """
    function = 'CONCAT_WS'

    def __init__(self, *expressions, **kwargs):
        separator = kwargs.pop('separator', ',')
        if len(kwargs) > 0:
            raise ValueError("Invalid keyword arguments for ConcatWS: {}"
                             .format(",".join(kwargs.keys())))

        if len(expressions) < 2:
            raise ValueError('ConcatWS must take at least two expressions')

        if not hasattr(separator, 'resolve_expression'):
            separator = Value(separator)

        # N.B. if separator is "," we could potentially use list field
        output_field = TextField()
        super(ConcatWS, self).__init__(separator, *expressions,
                                       output_field=output_field)


class ELT(Func):
    function = 'ELT'

    def __init__(self, num, expressions):
        value_exprs = []
        for v in expressions:
            if not hasattr(v, 'resolve_expression'):
                v = Value(v)
            value_exprs.append(v)

        super(ELT, self).__init__(num, *value_exprs, output_field=CharField())


class Field(Func):
    function = 'FIELD'

    def __init__(self, field, values, **kwargs):
        values_exprs = []
        for v in values:
            if not hasattr(v, 'resolve_expression'):
                v = Value(v)
            values_exprs.append(v)

        super(Field, self).__init__(field, *values_exprs)


# Encryption Functions


class MD5(SingleArgFunc):
    function = 'MD5'
    output_field_class = CharField


class SHA1(SingleArgFunc):
    function = 'SHA1'
    output_field_class = CharField


class SHA2(Func):
    function = 'SHA2'
    hash_lens = (224, 256, 384, 512)

    def __init__(self, expression, hash_len=512):
        if hash_len not in self.hash_lens:
            raise ValueError(
                "hash_len must be one of {}"
                .format(",".join(str(x) for x in self.hash_lens))
            )
        super(SHA2, self).__init__(expression, Value(hash_len))


# Information Functions

class LastInsertId(Func):
    function = 'LAST_INSERT_ID'

    def __init__(self, expression=None):
        if expression is not None:
            super(LastInsertId, self).__init__(expression)
        else:
            super(LastInsertId, self).__init__()

        self.output_field = IntegerField()

    @classmethod
    def get(cls, using=DEFAULT_DB_ALIAS):
        # N.B. did try getting it from connection.connection.insert_id() (The
        # MySQLdb query-free method) but it did not work with non-default
        # database connections in Django, and the reason was not clear
        with connections[using].cursor() as cursor:
            cursor.execute("SELECT LAST_INSERT_ID()")
            return cursor.fetchone()[0]


# MariaDB Regexp Functions

class RegexpInstr(Func):
    function = 'REGEXP_INSTR'

    def __init__(self, expression, regex):
        if not hasattr(regex, 'resolve_expression'):
            regex = Value(regex)

        super(RegexpInstr, self).__init__(expression, regex,
                                          output_field=IntegerField())


class RegexpReplace(Func):
    function = 'REGEXP_REPLACE'

    def __init__(self, expression, regex, replace):
        if not hasattr(regex, 'resolve_expression'):
            regex = Value(regex)

        if not hasattr(replace, 'resolve_expression'):
            replace = Value(replace)

        super(RegexpReplace, self).__init__(expression, regex, replace,
                                            output_field=CharField())


class RegexpSubstr(Func):
    function = 'REGEXP_SUBSTR'

    def __init__(self, expression, regex):
        if not hasattr(regex, 'resolve_expression'):
            regex = Value(regex)

        super(RegexpSubstr, self).__init__(expression, regex,
                                           output_field=CharField())
