from __future__ import annotations

from typing import Any

from django import forms
from django.core import validators
from django.core.exceptions import ValidationError
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from django_mysql.validators import ListMaxLengthValidator
from django_mysql.validators import ListMinLengthValidator
from django_mysql.validators import SetMaxLengthValidator
from django_mysql.validators import SetMinLengthValidator


class SimpleListField(forms.CharField):

    default_error_messages = {
        "item_n_invalid": _("Item %(nth)s in the list did not validate: "),
        "no_double_commas": _("No leading, trailing, or double commas."),
    }

    def __init__(
        self,
        base_field: forms.Field,
        max_length: int | None = None,
        min_length: int | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.base_field = base_field
        super().__init__(*args, **kwargs)
        if max_length is not None:
            self.max_length = max_length
            self.validators.append(ListMaxLengthValidator(int(max_length)))
        if min_length is not None:
            self.min_length = min_length
            self.validators.append(ListMinLengthValidator(int(min_length)))

    def prepare_value(self, value: Any) -> Any:
        if isinstance(value, list):
            return ",".join(str(self.base_field.prepare_value(v)) for v in value)
        return value

    def to_python(self, value: str) -> list[Any]:
        if value and len(value):
            items = value.split(",")
        else:
            items = []

        errors = []
        values = []
        for i, item in enumerate(items, start=1):
            if not len(item):
                errors.append(
                    ValidationError(
                        self.error_messages["no_double_commas"], code="no_double_commas"
                    )
                )
                continue

            try:
                value = self.base_field.to_python(item)
            except ValidationError as e:
                for error in e.error_list:
                    errors.append(
                        ValidationError(
                            format_lazy(
                                "{}{}",
                                self.error_messages["item_n_invalid"],
                                error.message,
                            ),
                            code="item_n_invalid",
                            params={"nth": i},
                        )
                    )

            values.append(value)

        if errors:
            raise ValidationError(errors)

        return values

    def validate(self, value: Any) -> None:
        super().validate(value)
        errors = []
        for i, item in enumerate(value, start=1):
            try:
                self.base_field.validate(item)
            except ValidationError as e:
                for error in e.error_list:
                    for message in error.messages:
                        errors.append(
                            ValidationError(
                                format_lazy(
                                    "{}{}",
                                    self.error_messages["item_n_invalid"],
                                    message,
                                ),
                                code="item_invalid",
                                params={"nth": i},
                            )
                        )
        if errors:
            raise ValidationError(errors)

    def run_validators(self, value: Any) -> None:
        super().run_validators(value)
        errors = []
        for i, item in enumerate(value, start=1):
            try:
                self.base_field.run_validators(item)
            except ValidationError as e:
                for error in e.error_list:
                    for message in error.messages:
                        errors.append(
                            ValidationError(
                                format_lazy(
                                    "{}{}",
                                    self.error_messages["item_n_invalid"],
                                    message,
                                ),
                                code="item_n_invalid",
                                params={"nth": i},
                            )
                        )
        if errors:
            raise ValidationError(errors)


class SimpleSetField(forms.CharField):
    empty_values = list(validators.EMPTY_VALUES) + [set()]

    default_error_messages = {
        "item_invalid": _('Item "%(item)s" in the set did not validate: '),
        "item_n_invalid": _("Item %(nth)s in the set did not validate: "),
        "no_double_commas": _("No leading, trailing, or double commas."),
        "no_duplicates": _(
            "Duplicates are not supported. " "'%(item)s' appears twice or more."
        ),
    }

    def __init__(
        self,
        base_field: forms.Field,
        max_length: int | None = None,
        min_length: int | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.base_field = base_field
        super().__init__(*args, **kwargs)
        if max_length is not None:
            self.max_length = max_length
            self.validators.append(SetMaxLengthValidator(int(max_length)))
        if min_length is not None:
            self.min_length = min_length
            self.validators.append(SetMinLengthValidator(int(min_length)))

    def prepare_value(self, value: Any) -> Any:
        if isinstance(value, set):
            return ",".join(str(self.base_field.prepare_value(v)) for v in value)
        return value

    def to_python(self, value: str) -> set[Any]:
        if value and len(value):
            items = value.split(",")
        else:
            items = []

        errors = []
        values = set()
        for i, item in enumerate(items, start=1):
            if not len(item):
                errors.append(
                    ValidationError(
                        self.error_messages["no_double_commas"], code="no_double_commas"
                    )
                )
                continue

            try:
                value = self.base_field.to_python(item)
            except ValidationError as e:
                for error in e.error_list:
                    errors.append(
                        ValidationError(
                            format_lazy(
                                "{}{}",
                                self.error_messages["item_n_invalid"],
                                error.message,
                            ),
                            code="item_n_invalid",
                            params={"nth": i},
                        )
                    )

            if value in values:
                errors.append(
                    ValidationError(
                        self.error_messages["no_duplicates"],
                        code="no_duplicates",
                        params={"item": item},
                    )
                )
            else:
                values.add(value)

        if errors:
            raise ValidationError(errors)

        return values

    def validate(self, value: Any) -> None:
        super().validate(value)
        errors = []
        for item in value:
            try:
                self.base_field.validate(item)
            except ValidationError as e:
                for error in e.error_list:
                    for message in error.messages:
                        errors.append(
                            ValidationError(
                                format_lazy(
                                    "{}{}", self.error_messages["item_invalid"], message
                                ),
                                code="item_invalid",
                                params={"item": item},
                            )
                        )
        if errors:
            raise ValidationError(errors)

    def run_validators(self, value: Any) -> None:
        super().run_validators(value)
        errors = []
        for item in value:
            try:
                self.base_field.run_validators(item)
            except ValidationError as e:
                for error in e.error_list:
                    for message in error.messages:
                        errors.append(
                            ValidationError(
                                format_lazy(
                                    "{}{}", self.error_messages["item_invalid"], message
                                ),
                                code="item_invalid",
                                params={"item": item},
                            )
                        )
        if errors:
            raise ValidationError(errors)
