from django.core import checks
from django.db.models import BinaryField, TextField


class SizedBinaryField(BinaryField):
    def __init__(self, *args, **kwargs):
        self.size_class = kwargs.pop('size_class', 4)
        super(SizedBinaryField, self).__init__(*args, **kwargs)

    def check(self, **kwargs):
        errors = super(SizedBinaryField, self).check(**kwargs)
        if self.size_class not in (1, 2, 3, 4):
            errors.append(
                checks.Error(
                    'size_class must be 1, 2, 3, or 4',
                    hint=None,
                    obj=self,
                    id='django_mysql.E007',
                ),
            )
        return errors

    def deconstruct(self):
        name, path, args, kwargs = super(SizedBinaryField, self).deconstruct()

        bad_paths = (
            'django_mysql.models.fields.sizes.SizedBinaryField',
            'django_mysql.models.fields.SizedBinaryField',
        )
        if path in bad_paths:
            path = 'django_mysql.models.SizedBinaryField'

        kwargs['size_class'] = self.size_class
        return name, path, args, kwargs

    def db_type(self, connection):
        if self.size_class == 1:
            return 'tinyblob'
        elif self.size_class == 2:
            return 'blob'
        elif self.size_class == 3:
            return 'mediumblob'
        else:  # don't check size_class == 4 as a safeguard for invalid values
            return 'longblob'


class SizedTextField(TextField):
    def __init__(self, *args, **kwargs):
        self.size_class = kwargs.pop('size_class', 4)
        super(SizedTextField, self).__init__(*args, **kwargs)

    def check(self, **kwargs):
        errors = super(SizedTextField, self).check(**kwargs)
        if self.size_class not in (1, 2, 3, 4):
            errors.append(
                checks.Error(
                    'size_class must be 1, 2, 3, or 4',
                    hint=None,
                    obj=self,
                    id='django_mysql.E008',
                ),
            )
        return errors

    def deconstruct(self):
        name, path, args, kwargs = super(SizedTextField, self).deconstruct()

        bad_paths = (
            'django_mysql.models.fields.sizes.SizedTextField',
            'django_mysql.models.fields.SizedTextField',
        )
        if path in bad_paths:
            path = 'django_mysql.models.SizedTextField'

        kwargs['size_class'] = self.size_class
        return name, path, args, kwargs

    def db_type(self, connection):
        if self.size_class == 1:
            return 'tinytext'
        elif self.size_class == 2:
            return 'text'
        elif self.size_class == 3:
            return 'mediumtext'
        else:  # don't check size_class == 4 as a safeguard for invalid values
            return 'longtext'
