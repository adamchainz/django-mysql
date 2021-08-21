from django.db.models import CharField, Lookup, Transform
from django.db.models.lookups import BuiltinLookup


class CaseSensitiveExact(BuiltinLookup):
    lookup_name = "case_exact"

    def get_rhs_op(self, connection, rhs):
        return "= BINARY %s" % rhs


class SoundsLike(Lookup):
    lookup_name = "sounds_like"

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = tuple(lhs_params) + tuple(rhs_params)
        return f"{lhs} SOUNDS LIKE {rhs}", params


class Soundex(Transform):
    lookup_name = "soundex"
    output_field = CharField()

    def as_sql(self, compiler, connection):
        lhs, params = compiler.compile(self.lhs)
        return "SOUNDEX(%s)" % lhs, params


# Custom field class lookups


# Set{Char,Text}Field


class SetContains(Lookup):
    lookup_name = "contains"

    def get_prep_lookup(self):
        if isinstance(self.rhs, (list, set, tuple)):
            # Can't do multiple contains without massive ORM hackery
            # (ANDing all the FIND_IN_SET calls), so just reject them
            raise ValueError(
                "Can't do contains with a set and {klass}, you should "
                "pass them as separate filters.".format(
                    klass=self.lhs.__class__.__name__
                )
            )
        return super().get_prep_lookup()

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = tuple(lhs_params) + tuple(rhs_params)
        # Put rhs on the left since that's the order FIND_IN_SET uses
        return f"FIND_IN_SET({rhs}, {lhs})", params


class SetIContains(SetContains):
    lookup_name = "icontains"


# DynamicField


class DynColHasKey(Lookup):
    lookup_name = "has_key"

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = tuple(lhs_params) + tuple(rhs_params)
        return f"COLUMN_EXISTS({lhs}, {rhs})", params
