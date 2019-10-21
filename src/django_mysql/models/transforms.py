from django.db.models import IntegerField, Transform

from django_mysql.utils import collapse_spaces


class SetLength(Transform):
    lookup_name = "len"
    output_field = IntegerField()

    # No str.count equivalent in MySQL :(
    expr = collapse_spaces(
        """
        (
            CHAR_LENGTH(%s) -
            CHAR_LENGTH(REPLACE(%s, ',', '')) +
            IF(CHAR_LENGTH(%s), 1, 0)
        )
    """
    )

    def as_sql(self, compiler, connection):
        lhs, params = compiler.compile(self.lhs)
        return self.expr % (lhs, lhs, lhs), params
