from django.db.models import BooleanField, NullBooleanField


class Bit1Mixin:
    def db_type(self, connection):
        return "bit(1)"

    def from_db_value(self, value, expression, connection):
        # Meant to be binary/bytes but can come back as unicode strings
        if isinstance(value, bytes):
            value = value == b"\x01"
        elif isinstance(value, str):
            # Only on older versions of mysqlclient and Py 2.7
            value = value == "\x01"  # pragma: no cover
        return value

    def get_prep_value(self, value):
        if value is None:
            return value
        else:
            return 1 if value else 0


class Bit1BooleanField(Bit1Mixin, BooleanField):
    pass


class NullBit1BooleanField(Bit1Mixin, NullBooleanField):
    pass
