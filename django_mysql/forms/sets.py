# -*- coding:utf-8 -*-
from __future__ import absolute_import

from django import forms
from django.core import validators
from django.core.exceptions import ValidationError
from django.utils import six
from django.utils.translation import string_concat, ugettext_lazy as _

from django_mysql.validators import (
    SetMaxLengthValidator, SetMinLengthValidator
)


class SimpleSetField(forms.CharField):
    empty_values = list(validators.EMPTY_VALUES) + [set()]

    default_error_messages = {
        'item_invalid': _('Item "%(item)s" in the set did not validate: '),
        'item_n_invalid': _('Item %(nth)s in the set did not validate: '),
    }

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
            return ",".join(
                six.text_type(self.base_field.prepare_value(v))
                for v in value
            )
        return value

    def to_python(self, value):
        if value and len(value):
            items = value.split(",")
        else:
            items = []

        errors = []
        values = set()
        for i, item in enumerate(items):
            try:
                values.add(self.base_field.to_python(item))
            except ValidationError as e:
                for error in e.error_list:
                    errors.append(ValidationError(
                        string_concat(self.error_messages['item_n_invalid'],
                                      error.message),
                        code='item_n_invalid',
                        params={'nth': i},
                    ))

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
                    errors.append(ValidationError(
                        string_concat(self.error_messages['item_invalid'],
                                      error.message),
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
                    errors.append(ValidationError(
                        string_concat(self.error_messages['item_invalid'],
                                      error.message),
                        code='item_invalid',
                        params={'item': item}
                    ))
        if errors:
            raise ValidationError(errors)
