from __future__ import annotations

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.models import IntegerField, PositiveIntegerField
from django.utils.translation import gettext_lazy as _


class TinyIntegerField(IntegerField):
    description = _("Small integer")
    default_validators = [MinValueValidator(-128), MaxValueValidator(127)]

    def db_type(self, connection: BaseDatabaseWrapper) -> str:
        return "tinyint"


class PositiveTinyIntegerField(PositiveIntegerField):
    description = _("Positive small integer")
    default_validators = [MinValueValidator(0), MaxValueValidator(255)]

    def db_type(self, connection: BaseDatabaseWrapper) -> str:
        return "tinyint unsigned"
