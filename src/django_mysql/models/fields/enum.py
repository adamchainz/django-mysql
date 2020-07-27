from django.db.models import CharField
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _


class EnumField(CharField):
    description = _("Enumeration")

    def __init__(self, *args, **kwargs):
        if "choices" not in kwargs or len(kwargs["choices"]) == 0:
            raise ValueError('"choices" argument must be be a non-empty list')

        choices = []
        for choice in kwargs["choices"]:
            if isinstance(choice, tuple):
                choices.append(choice)
            elif isinstance(choice, str):
                choices.append((choice, choice))
            else:
                raise TypeError(
                    'Invalid choice "{choice}". '
                    "Expected string or tuple as elements in choices".format(
                        choice=choice
                    )
                )

        kwargs["choices"] = choices

        if "max_length" in kwargs:
            raise TypeError('"max_length" is not a valid argument')
        # Massive to avoid problems with validation - let MySQL handle the
        # maximum string length
        kwargs["max_length"] = int(2 ** 32)

        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()

        bad_paths = (
            "django_mysql.models.fields.enum.EnumField",
            "django_mysql.models.fields.EnumField",
        )
        if path in bad_paths:
            path = "django_mysql.models.EnumField"

        kwargs["choices"] = self.choices
        del kwargs["max_length"]

        return name, path, args, kwargs

    def db_type(self, connection):
        connection.ensure_connection()
        values = [connection.connection.escape_string(c) for c, _ in self.flatchoices]
        # Use force_str because MySQLdb escape_string() returns bytes, but
        # pymysql returns str
        return "enum(%s)" % ",".join("'%s'" % force_str(v) for v in values)
