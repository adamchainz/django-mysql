from django.core import checks
from django.db.models import DateTimeField as DjangoDateTimeField
from django.utils import timezone


class DatetimeField(DjangoDateTimeField):
    def __init__(self, on_update_current_timestamp=False, **kwargs):
        self.on_update_current_timestamp = on_update_current_timestamp
        super(DatetimeField, self).__init__(**kwargs)

    def db_type_suffix(self, connection):
        db_type_suffix = super().db_type_suffix(connection)
        if db_type_suffix is None:
            db_type_suffix = "ON UPDATE CURRENT_TIMESTAMP(6)"
        else:
            db_type_suffix += "ON UPDATE CURRENT_TIMESTAMP(6)"
        return db_type_suffix

    def pre_save(self, model_instance, add):
        if self.auto_now:
            value = timezone.now()
            setattr(model_instance, self.attname, value)
            return value
        else:
            return getattr(model_instance, self.attname)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.on_update_current_timestamp:
            kwargs["on_update_current_timestamp"] = True

        bad_paths = (
            "django_mysql.models.fields.datetime.ModifiableDatetimeField",
            "django_mysql.models.fields.ModifiableDatetimeField",
        )
        if path in bad_paths:
            path = "django_mysql.models.ModifiableDatetimeField"
        return name, path, args, kwargs

    def _check_mutually_exclusive_options(self):
        # auto_now_add, and on_update_current_timestamp are mutually exclusive
        # options. The use of more than one of these options together
        # will trigger an Error
        super()._check_mutually_exclusive_options()
        mutually_exclusive_options = [self.auto_now_add, self.on_update_current_timestamp]
        enabled_options = [option not in (None, False) for option in mutually_exclusive_options].count(True)
        if enabled_options > 1:
            return [
                checks.Error(
                    "The options auto_now_add, and on_update_current_timestamp"
                    "are mutually exclusive. Only one of these options "
                    "may be present. "
                    "Recommend auto_now_add=False",
                    obj=self,
                    id='fields.E160',
                )
            ]
        else:
            return []
