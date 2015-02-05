# -*- coding: utf-8 -*-
# -*- coding:utf-8 -*-
from django.db.models import (CharField, IntegerField, Lookup, SubfieldBase,
                              Transform)
from django.utils import six


class SetCharField(six.with_metaclass(SubfieldBase, CharField)):
    """
    A subclass of CharField for using MySQL's handy FIND_IN_SET function with.
    """
    def to_python(self, value):
        if isinstance(value, six.string_types):
            value = set(value.split(','))
        return value

    def get_prep_value(self, value):
        if isinstance(value, set):
            value = {six.u(i) for i in value}
            for i in value:
                assert ',' not in i
            value = ','.join(value)
        return value


@SetCharField.register_lookup
class FindInSet(Lookup):
    lookup_name = 'has'

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        # Yes we're putting rhs on the left hand side since that's the order
        # FIND_IN_SET expects
        return 'FIND_IN_SET(%s, %s)' % (rhs, lhs), params


@SetCharField.register_lookup
class SetLength(Transform):
    lookup_name = 'len'
    output_field = IntegerField()

    def as_sql(self, compiler, connection):
        lhs, params = compiler.compile(self.lhs)
        expr = "(1 + CHAR_LENGTH(%s) - CHAR_LENGTH(REPLACE(%s, ',', '')))"
        return expr % (lhs, lhs), params
