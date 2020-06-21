from django.core import checks
from django.db.models import DateTimeField as DjangoDateTimeField
from django.utils import timezone


class DateTimeField(DjangoDateTimeField):
    def __init__(self, on_update_current_timestamp=False, **kwargs):
        self.on_update_current_timestamp = on_update_current_timestamp
        super(DateTimeField, self).__init__(**kwargs)

    def db_type_suffix(self, connection):
        db_type_suffix = super().db_type_suffix(connection)
        if self.on_update_current_timestamp:
            if db_type_suffix is None:
                db_type_suffix = "ON UPDATE CURRENT_TIMESTAMP(6)"
            else:
                db_type_suffix += "ON UPDATE CURRENT_TIMESTAMP(6)"
        return db_type_suffix

    def pre_save(self, model_instance, add):
        if self.auto_now or (self.default and add) or self.on_update_current_timestamp:
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
            "django_mysql.models.fields.datetime.DateTimeField",
            "django_mysql.models.fields.DateTimeField",
        )
        if path in bad_paths:
            path = "django_mysql.models.DateTimeField"
        return name, path, args, kwargs

    def _check_mutually_exclusive_options(self):
        # auto_now, on_upd and default are mutually exclusive
        # options. The use of more than one of these options together
        # will trigger an Error
        # and django_mysql.models.DateTimeField should not be enabled 'auto_now_add=True'
        mutually_exclusive_options = [
            self.auto_now,
            self.on_update_current_timestamp,
            self.has_default(),
        ]
        enabled_options = [
            option not in (None, False) for option in mutually_exclusive_options
        ].count(True)
        if enabled_options > 1:
            return [
                checks.Error(
                    "The options auto_now, on_update_current_timestamp, and default "
                    "are mutually exclusive. Only one of these options "
                    "may be present. "
                    "Recommend 'on_update_current_timestamp=True' ",
                    obj=self,
                    id="fields.E160",
                )
            ]
        elif self.auto_now_add:
            return [
                checks.Error(
                    "The options auto_now_add would not use with django_mysql.models.DateTimeField "
                    "fix 'auto_now_add=True' to 'auto_now_add=False' "
                    "or Use 'auto_now_add=True' with django.db.models.DateTimeField. ",
                    obj=self,
                    id="django_mysql.E015",
                )
            ]
        else:
            return []
