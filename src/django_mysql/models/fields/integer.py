from __future__ import annotations

from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.models import PositiveSmallIntegerField
from django.db.models import SmallIntegerField
from django.utils.translation import gettext_lazy as _


class TinyIntegerField(SmallIntegerField):
    description = _("Small integer")

    def db_type(self, connection: BaseDatabaseWrapper) -> str:
        return "tinyint"


class PositiveTinyIntegerField(PositiveSmallIntegerField):
    description = _("Positive small integer")

    def db_type(self, connection: BaseDatabaseWrapper) -> str:
        return "tinyint unsigned"
