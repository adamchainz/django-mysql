# -*- coding:utf-8 -*-
import json

from django.db.models import CharField, Lookup, Transform
from django.db.models.lookups import BuiltinLookup


class CaseSensitiveExact(BuiltinLookup):
    lookup_name = 'case_exact'

    def get_rhs_op(self, connection, rhs):
        return '= BINARY %s' % rhs


class SoundsLike(Lookup):
    lookup_name = 'sounds_like'

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        return '%s SOUNDS LIKE %s' % (lhs, rhs), params


class Soundex(Transform):
    lookup_name = 'soundex'
    output_field = CharField()

    def as_sql(self, compiler, connection):
        lhs, params = compiler.compile(self.lhs)
        return "SOUNDEX(%s)" % lhs, params


# Custom field class lookups


# JSONField


class JSONContainedBy(Lookup):
    lookup_name = 'contained_by'

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = rhs_params + lhs_params
        return 'JSON_CONTAINS({}, {})'.format(rhs, lhs), params


class JSONContains(Lookup):
    lookup_name = 'contains'

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        return 'JSON_CONTAINS({}, {})'.format(lhs, rhs), params


class JSONHasKey(Lookup):
    lookup_name = 'has_key'

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        key_name = self.rhs
        path = '$.{}'.format(json.dumps(key_name))
        params = lhs_params + [path]
        return "JSON_CONTAINS_PATH({}, 'one', %s)".format(lhs), params


class JSONHasKeys(Lookup):
    lookup_name = 'has_keys'

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        paths = [
            '$.{}'.format(json.dumps(key_name))
            for key_name in self.rhs
        ]
        params = lhs_params + paths

        sql = ['JSON_CONTAINS_PATH(', lhs, ", 'all', "]
        sql.append(', '.join('%s' for _ in paths))
        sql.append(')')
        return ''.join(sql), params


class JSONHasAnyKeys(Lookup):
    lookup_name = 'has_any_keys'

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        paths = [
            '$.{}'.format(json.dumps(key_name))
            for key_name in self.rhs
        ]
        params = lhs_params + paths

        sql = ['JSON_CONTAINS_PATH(', lhs, ", 'one', "]
        sql.append(', '.join('%s' for _ in paths))
        sql.append(')')
        return ''.join(sql), params


# Set{Char,Text}Field


class SetContains(Lookup):
    lookup_name = 'contains'

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        # Put rhs on the left since that's the order FIND_IN_SET uses
        return 'FIND_IN_SET(%s, %s)' % (rhs, lhs), params


class SetIContains(SetContains):
    lookup_name = 'icontains'


# DynamicField


class DynColHasKey(Lookup):
    lookup_name = 'has_key'

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        return 'COLUMN_EXISTS(%s, %s)' % (lhs, rhs), params
