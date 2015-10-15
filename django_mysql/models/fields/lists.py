# -*- coding:utf-8 -*-
from __future__ import absolute_import

from django.core import checks
from django.db.models import CharField, IntegerField, Lookup, TextField
from django.utils import six
from django.utils.translation import ugettext_lazy as _

from django_mysql.compat import field_class
from django_mysql.forms import SimpleListField
from django_mysql.models.lookups import SetContains, SetIContains
from django_mysql.models.transforms import SetLength
from django_mysql.validators import ListMaxLengthValidator


class ListFieldMixin(object):

    def __init__(self, base_field, size=None, **kwargs):
        self.base_field = base_field
        self.size = size

        super(ListFieldMixin, self).__init__(**kwargs)

        if self.size:
            self.validators.append(ListMaxLengthValidator(int(self.size)))

    def get_default(self):
        default = super(ListFieldMixin, self).get_default()
        if default == '':
            return []
        else:
            return default

    def check(self, **kwargs):
        errors = super(ListFieldMixin, self).check(**kwargs)
        if not isinstance(self.base_field, (CharField, IntegerField)):
            errors.append(
                checks.Error(
                    'Base field for list must be a CharField or IntegerField.',
                    hint=None,
                    obj=self,
                    id='django_mysql.E005'
                )
            )
            return errors

        # Remove the field name checks as they are not needed here.
        base_errors = self.base_field.check()
        if base_errors:
            messages = '\n    '.join(
                '%s (%s)' % (error.msg, error.id)
                for error in base_errors
            )
            errors.append(
                checks.Error(
                    'Base field for list has errors:\n    %s' % messages,
                    hint=None,
                    obj=self,
                    id='django_mysql.E004'
                )
            )
        return errors

    @property
    def description(self):
        return _('List of %(base_description)s') % {
            'base_description': self.base_field.description
        }

    def set_attributes_from_name(self, name):
        super(ListFieldMixin, self).set_attributes_from_name(name)
        self.base_field.set_attributes_from_name(name)

    def deconstruct(self):
        name, path, args, kwargs = super(ListFieldMixin, self).deconstruct()

        bad_paths = (
            'django_mysql.models.fields.lists.' + self.__class__.__name__,
            'django_mysql.models.fields.' + self.__class__.__name__
        )
        if path in bad_paths:
            path = 'django_mysql.models.' + self.__class__.__name__

        args.insert(0, self.base_field)
        kwargs['size'] = self.size
        return name, path, args, kwargs

    def to_python(self, value):
        if isinstance(value, six.string_types):
            if not len(value):
                value = []
            else:
                value = [self.base_field.to_python(v) for
                         v in value.split(',')]
        return value

    def from_db_value(self, value, expression, connection, context):
        # Similar to to_python, for Django 1.8+
        if isinstance(value, six.string_types):
            if not len(value):
                value = []
            else:
                value = [self.base_field.to_python(v) for
                         v in value.split(',')]
        return value

    def get_prep_value(self, value):
        if isinstance(value, list):
            value = [
                six.text_type(self.base_field.get_prep_value(v))
                for v in value
            ]
            for v in value:
                if ',' in v:
                    raise ValueError(
                        "List members in {klass} {name} cannot contain commas"
                        .format(klass=self.__class__.__name__,
                                name=self.name)
                    )
                elif not len(v):
                    raise ValueError(
                        "The empty string cannot be stored in {klass} {name}"
                        .format(klass=self.__class__.__name__,
                                name=self.name)
                    )
            return ','.join(value)
        return value

    def get_lookup(self, lookup_name):
        lookup = super(ListFieldMixin, self).get_lookup(lookup_name)
        if lookup:
            return lookup

        try:
            index = int(lookup_name)
        except ValueError:
            pass
        else:
            index += 1  # MySQL uses 1-indexing
            return IndexLookupFactory(index)

        return lookup

    def get_db_prep_lookup(self, lookup_type, value, connection,
                           prepared=False):
        if lookup_type in ('contains', 'icontains'):
            # Avoid the default behaviour of adding wildcards on either side of
            # what we're searching for, because FIND_IN_SET is doing that
            # implicitly
            if isinstance(value, list):
                # Can't do multiple contains without massive ORM hackery
                # (ANDing all the FIND_IN_SET calls), so just reject them
                raise ValueError(
                    "Can't do contains with a list and {klass}, you should "
                    "pass them as separate filters."
                    .format(klass=self.__class__.__name__)
                )
            return [six.text_type(self.base_field.get_prep_value(value))]

        return super(ListFieldMixin, self).get_db_prep_lookup(
            lookup_type, value, connection, prepared)

    def value_to_string(self, obj):
        vals = self._get_val_from_obj(obj)
        return self.get_prep_value(vals)

    def formfield(self, **kwargs):
        defaults = {
            'form_class': SimpleListField,
            'base_field': self.base_field.formfield(),
            'max_length': self.size,
        }
        defaults.update(kwargs)
        return super(ListFieldMixin, self).formfield(**defaults)

    def contribute_to_class(self, cls, name, **kwargs):
        super(ListFieldMixin, self).contribute_to_class(cls, name, **kwargs)
        self.base_field.model = cls


class ListCharField(field_class(ListFieldMixin, CharField)):
    """
    A subclass of CharField for using MySQL's handy FIND_IN_SET function with.
    """
    def check(self, **kwargs):
        errors = super(ListCharField, self).check(**kwargs)

        # Unfortunately this check can't really be done for IntegerFields since
        # they have boundless length
        has_base_error = any(e.id == 'django_mysql.E004' for e in errors)
        if (
            not has_base_error and
            isinstance(self.base_field, CharField) and
            self.size
        ):
            max_size = (
                # The chars used
                (self.size * (self.base_field.max_length)) +
                # The commas
                self.size - 1
            )
            if max_size > self.max_length:
                errors.append(
                    checks.Error(
                        'Field can overrun - set contains CharFields of max '
                        'length %s, leading to a comma-combined max length of '
                        '%s, which is greater than the space reserved for the '
                        'set - %s' %
                        (self.base_field.max_length, max_size,
                            self.max_length),
                        hint=None,
                        obj=self,
                        id='django_mysql.E006'
                    )
                )
        return errors


class ListTextField(field_class(ListFieldMixin, TextField)):
    pass


ListCharField.register_lookup(SetContains)
ListTextField.register_lookup(SetContains)

ListCharField.register_lookup(SetIContains)
ListTextField.register_lookup(SetIContains)

ListCharField.register_lookup(SetLength)
ListTextField.register_lookup(SetLength)


class IndexLookup(Lookup):

    def __init__(self, index, *args, **kwargs):
        super(IndexLookup, self).__init__(*args, **kwargs)
        self.index = index

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        # Put rhs on the left since that's the order FIND_IN_SET uses
        return '(FIND_IN_SET(%s, %s) = %s)' % (rhs, lhs, self.index), params


class IndexLookupFactory(object):

    def __init__(self, index):
        self.index = index

    def __call__(self, *args, **kwargs):
        return IndexLookup(self.index, *args, **kwargs)
