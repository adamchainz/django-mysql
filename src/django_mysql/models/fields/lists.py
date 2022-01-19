from __future__ import annotations

from typing import Any, Callable, Iterable, cast

from django.core import checks
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.models import CharField, Field, IntegerField, Lookup, Model, TextField
from django.db.models.expressions import BaseExpression
from django.forms import Field as FormField
from django.utils.translation import gettext_lazy as _

from django_mysql.forms import SimpleListField
from django_mysql.models.lookups import SetContains, SetIContains
from django_mysql.models.transforms import SetLength
from django_mysql.typing import DeconstructResult
from django_mysql.validators import ListMaxLengthValidator


class ListFieldMixin(Field):
    def __init__(
        self, base_field: Field, size: int | None = None, **kwargs: Any
    ) -> None:
        self.base_field = base_field
        self.size = size

        super().__init__(**kwargs)

        if self.size:
            self.validators.append(ListMaxLengthValidator(int(self.size)))

    def get_default(self) -> Any:
        default = super().get_default()
        if default == "":
            return []
        else:
            return default

    def check(self, **kwargs: Any) -> list[checks.CheckMessage]:
        errors = super().check(**kwargs)
        if not isinstance(self.base_field, (CharField, IntegerField)):
            errors.append(
                checks.Error(
                    "Base field for list must be a CharField or IntegerField.",
                    hint=None,
                    obj=self,
                    id="django_mysql.E005",
                )
            )
            return errors

        # Remove the field name checks as they are not needed here.
        base_errors = self.base_field.check()
        if base_errors:
            messages = "\n    ".join(
                f"{error.msg} ({error.id})" for error in base_errors
            )
            errors.append(
                checks.Error(
                    "Base field for list has errors:\n    %s" % messages,
                    hint=None,
                    obj=self,
                    id="django_mysql.E004",
                )
            )
        return errors

    @property
    def description(self) -> Any:
        return _("List of %(base_description)s") % {
            "base_description": self.base_field.description
        }

    def set_attributes_from_name(self, name: str) -> None:
        super().set_attributes_from_name(name)
        self.base_field.set_attributes_from_name(name)

    def deconstruct(self) -> DeconstructResult:
        name, path, args, kwargs = cast(DeconstructResult, super().deconstruct())
        args = list(args)

        bad_paths = (
            "django_mysql.models.fields.lists." + self.__class__.__name__,
            "django_mysql.models.fields." + self.__class__.__name__,
        )
        if path in bad_paths:
            path = "django_mysql.models." + self.__class__.__name__

        args.insert(0, self.base_field)
        kwargs["size"] = self.size
        return name, path, args, kwargs

    def to_python(self, value: Any) -> Any:
        if isinstance(value, str):
            if not len(value):
                value = []
            else:
                value = [self.base_field.to_python(v) for v in value.split(",")]
        return value

    def from_db_value(
        self, value: Any, expression: BaseExpression, connection: BaseDatabaseWrapper
    ) -> Any:
        if isinstance(value, str):  # pragma: no branch
            if not len(value):
                value = []
            else:
                value = [self.base_field.to_python(v) for v in value.split(",")]
        return value

    def get_prep_value(self, value: Any) -> Any:
        if isinstance(value, list):
            value = [str(self.base_field.get_prep_value(v)) for v in value]
            for v in value:
                if "," in v:
                    raise ValueError(
                        "List members in {klass} {name} cannot contain commas".format(
                            klass=self.__class__.__name__, name=self.name
                        )
                    )
                elif not len(v):
                    raise ValueError(
                        "The empty string cannot be stored in {klass} {name}".format(
                            klass=self.__class__.__name__, name=self.name
                        )
                    )
            return ",".join(value)
        return value

    def get_lookup(self, lookup_name: str) -> type[Lookup] | Callable[..., Lookup]:
        lookup = super().get_lookup(lookup_name)
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

    def value_to_string(self, obj: Any) -> str:
        vals = self.value_from_object(obj)
        return self.get_prep_value(vals)

    def formfield(self, **kwargs: Any) -> FormField:
        defaults = {
            "form_class": SimpleListField,
            "base_field": self.base_field.formfield(),
            "max_length": self.size,
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def contribute_to_class(self, cls: type[Model], name: str, **kwargs: Any) -> None:
        super().contribute_to_class(cls, name, **kwargs)
        self.base_field.model = cls


class ListCharField(ListFieldMixin, CharField):
    """
    A subclass of CharField for using MySQL's handy FIND_IN_SET function with.
    """

    def check(self, **kwargs: Any) -> list[checks.CheckMessage]:
        errors = super().check(**kwargs)

        # Unfortunately this check can't really be done for IntegerFields since
        # they have boundless length
        has_base_error = any(e.id == "django_mysql.E004" for e in errors)
        if (
            not has_base_error
            and self.max_length is not None
            and isinstance(self.base_field, CharField)
            and self.size
        ):
            max_size = (
                # The chars used
                (self.size * (self.base_field.max_length))
                # The commas
                + self.size
                - 1
            )
            if max_size > self.max_length:
                errors.append(
                    checks.Error(
                        "Field can overrun - set contains CharFields of max "
                        "length %s, leading to a comma-combined max length of "
                        "%s, which is greater than the space reserved for the "
                        "set - %s"
                        % (self.base_field.max_length, max_size, self.max_length),
                        hint=None,
                        obj=self,
                        id="django_mysql.E006",
                    )
                )
        return errors


class ListTextField(ListFieldMixin, TextField):
    pass


ListCharField.register_lookup(SetContains)
ListTextField.register_lookup(SetContains)

ListCharField.register_lookup(SetIContains)
ListTextField.register_lookup(SetIContains)

ListCharField.register_lookup(SetLength)
ListTextField.register_lookup(SetLength)


class IndexLookup(Lookup):
    def __init__(self, index: int, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.index = index

    def as_sql(
        self, qn: Callable[[str], str], connection: BaseDatabaseWrapper
    ) -> tuple[str, Iterable[Any]]:
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = tuple(lhs_params) + tuple(rhs_params)
        # Put rhs on the left since that's the order FIND_IN_SET uses
        return f"(FIND_IN_SET({rhs}, {lhs}) = {self.index})", params


class IndexLookupFactory:
    def __init__(self, index: int) -> None:
        self.index = index

    def __call__(self, *args: Any, **kwargs: Any) -> IndexLookup:
        return IndexLookup(self.index, *args, **kwargs)
