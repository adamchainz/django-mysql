# -*- coding:utf-8 -*-
from __future__ import absolute_import

from django import forms
from django.core import validators
from django.core.exceptions import ValidationError
from django.utils import six
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import string_concat

from django_mysql.validators import (
    ListMaxLengthValidator, ListMinLengthValidator, SetMaxLengthValidator,
    SetMinLengthValidator
)

__all__ = ('SimpleListField', 'SimpleSetField')


class SimpleListField(forms.CharField):

    # These bits can be overridden to change the way the field serializes and
    # deserializes for the user, e.g. line-delimited, json, etc.

    default_error_messages = {
        'item_n_invalid': _('Item %(nth)s in the list did not validate: '),
        'items_no_commas': _('No leading, trailing, or double commas.'),
        # The 'empty' message is the same as 'no commas' by default, since the
        # only reason empty strings could arise with the basic comma-splitting
        # logic is with extra commas. This may not be true in custom subclasses
        # however.
        'items_no_empty': _('No leading, trailing, or double commas.'),
    }

    def prepare_value_serialize(self, values):
        return ",".join(values)

    def to_python_deserialize(self, value):
        if not value:
            return []
        else:
            return value.split(",")

    # Internals

    def __init__(self, base_field, max_length=None, min_length=None,
                 *args, **kwargs):
        self.base_field = base_field
        super(SimpleListField, self).__init__(*args, **kwargs)
        if max_length is not None:
            self.max_length = max_length
            self.validators.append(ListMaxLengthValidator(int(max_length)))
        if min_length is not None:
            self.min_length = min_length
            self.validators.append(ListMinLengthValidator(int(min_length)))

    def prepare_value(self, value):
        if isinstance(value, list):
            return self.prepare_value_serialize(
                (six.text_type(self.base_field.prepare_value(v))
                 for v in value)
            )
        return value

    def to_python(self, value):
        items = self.to_python_deserialize(value)

        errors = []
        values = []
        for i, item in enumerate(items, start=1):
            if not len(item):
                errors.append(ValidationError(
                    self.error_messages['items_no_empty'],
                    code='items_no_empty',
                ))
                continue

            if ',' in item:
                errors.append(ValidationError(
                    self.error_messages['items_no_commas'],
                    code='items_no_commas',
                ))
                continue

            try:
                value = self.base_field.to_python(item)
            except ValidationError as e:
                for error in e.error_list:
                    errors.append(ValidationError(
                        string_concat(self.error_messages['item_n_invalid'],
                                      error.message),
                        code='item_n_invalid',
                        params={'nth': i},
                    ))

            values.append(value)

        if errors:
            raise ValidationError(errors)

        return values

    def validate(self, value):
        super(SimpleListField, self).validate(value)
        errors = []
        for i, item in enumerate(value, start=1):
            try:
                self.base_field.validate(item)
            except ValidationError as e:
                for error in e.error_list:
                    for message in error.messages:
                        errors.append(ValidationError(
                            string_concat(
                                self.error_messages['item_n_invalid'],
                                message),
                            code='item_invalid',
                            params={'nth': i}
                        ))
        if errors:
            raise ValidationError(errors)

    def run_validators(self, value):
        super(SimpleListField, self).run_validators(value)
        errors = []
        for i, item in enumerate(value, start=1):
            try:
                self.base_field.run_validators(item)
            except ValidationError as e:
                for error in e.error_list:
                    for message in error.messages:
                        errors.append(ValidationError(
                            string_concat(
                                self.error_messages['item_n_invalid'],
                                message),
                            code='item_n_invalid',
                            params={'nth': i}
                        ))
        if errors:
            raise ValidationError(errors)


class SimpleSetField(forms.CharField):

    # These bits can be overridden to change the way the field serializes and
    # deserializes for the user, e.g. line-delimited, json, etc.

    default_error_messages = {
        'item_invalid': _('Item "%(item)s" in the set did not validate: '),
        'item_n_invalid': _('Item %(nth)s in the set did not validate: '),
        'no_duplicates': _("Duplicates are not supported. "
                           "'%(item)s' appears twice or more."),
        'items_no_commas': _('No leading, trailing, or double commas.'),
        # The 'empty' message is the same as 'no commas' by default, since the
        # only reason empty strings could arise with the basic comma-splitting
        # logic is with extra commas. This may not be true in custom subclasses
        # however.
        'items_no_empty': _('No leading, trailing, or double commas.'),
    }

    def prepare_value_serialize(self, values):
        return ",".join(values)

    def to_python_deserialize(self, value):
        if not value:
            return []
        else:
            return value.split(",")

    # Internals

    empty_values = list(validators.EMPTY_VALUES) + [set()]

    def __init__(self, base_field, max_length=None, min_length=None,
                 *args, **kwargs):
        self.base_field = base_field
        super(SimpleSetField, self).__init__(*args, **kwargs)
        if max_length is not None:
            self.max_length = max_length
            self.validators.append(SetMaxLengthValidator(int(max_length)))
        if min_length is not None:
            self.min_length = min_length
            self.validators.append(SetMinLengthValidator(int(min_length)))

    def prepare_value(self, value):
        if isinstance(value, set):
            return self.prepare_value_serialize(
                (six.text_type(self.base_field.prepare_value(v))
                 for v in value)
            )
        return value

    def to_python(self, value):
        items = self.to_python_deserialize(value)

        errors = []
        values = set()
        for i, item in enumerate(items, start=1):
            if not len(item):
                errors.append(ValidationError(
                    self.error_messages['items_no_empty'],
                    code='items_no_empty',
                ))
                continue

            if ',' in item:
                errors.append(ValidationError(
                    self.error_messages['items_no_commas'],
                    code='items_no_commas',
                ))
                continue

            try:
                value = self.base_field.to_python(item)
            except ValidationError as e:
                for error in e.error_list:
                    errors.append(ValidationError(
                        string_concat(self.error_messages['item_n_invalid'],
                                      error.message),
                        code='item_n_invalid',
                        params={'nth': i},
                    ))

            if value in values:
                errors.append(ValidationError(
                    self.error_messages['no_duplicates'],
                    code='no_duplicates',
                    params={'item': item}
                ))
            else:
                values.add(value)

        if errors:
            raise ValidationError(errors)

        return values

    def validate(self, value):
        super(SimpleSetField, self).validate(value)
        errors = []
        for item in value:
            try:
                self.base_field.validate(item)
            except ValidationError as e:
                for error in e.error_list:
                    for message in error.messages:
                        errors.append(ValidationError(
                            string_concat(self.error_messages['item_invalid'],
                                          message),
                            code='item_invalid',
                            params={'item': item}
                        ))
        if errors:
            raise ValidationError(errors)

    def run_validators(self, value):
        super(SimpleSetField, self).run_validators(value)
        errors = []
        for item in value:
            try:
                self.base_field.run_validators(item)
            except ValidationError as e:
                for error in e.error_list:
                    for message in error.messages:
                        errors.append(ValidationError(
                            string_concat(self.error_messages['item_invalid'],
                                          message),
                            code='item_invalid',
                            params={'item': item}
                        ))
        if errors:
            raise ValidationError(errors)
