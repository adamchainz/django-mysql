from __future__ import annotations

import pytest
from django.core.management import call_command
from django.db import connection
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings

from django_mysql.models import FixedCharField
from tests.testapp.models import TemporaryModel


class TestFixedCharField(TestCase):
    def test_invalid_max_length(self):
        with pytest.raises(TypeError) as exc_info:
            FixedCharField(length=4, max_length=100)
        assert '"max_length" is not a valid argument' in str(exc_info.value)


class TestDeconstruct(TestCase):
    def test_deconstruct(self):
        field = FixedCharField(length=1)
        name, path, args, kwargs = field.deconstruct()
        assert path == "django_mysql.models.FixedCharField"
        assert kwargs["length"] == 1
        assert "max_length" not in kwargs
        FixedCharField(*args, **kwargs)


class TestCheck(SimpleTestCase):
    def test_length_too_small(self):
        class InvalidFixedCharModel1(TemporaryModel):
            field = FixedCharField(length=-1)

        errors = InvalidFixedCharModel1.check(actually_check=True)
        assert len(errors) == 2
        assert errors[0].id == "fields.E121"
        assert errors[0].msg == "'max_length' must be a positive integer."
        assert errors[1].id == "django_mysql.E015"
        assert errors[1].msg == "'length' must be between 0 and 255."

    def test_length_too_large(self):
        class InvalidFixedCharModel2(TemporaryModel):
            field = FixedCharField(length=256)

        errors = InvalidFixedCharModel2.check(actually_check=True)
        assert len(errors) == 1
        assert errors[0].id == "django_mysql.E015"
        assert errors[0].msg == "'length' must be between 0 and 255."


class TestMigrations(TransactionTestCase):
    @override_settings(
        MIGRATION_MODULES={"testapp": "tests.testapp.fixedchar_default_migrations"}
    )
    def test_adding_field_with_default(self):
        table_name = "testapp_fixedchardefaultmodel"
        table_names = connection.introspection.table_names
        with connection.cursor() as cursor:
            assert table_name not in table_names(cursor)

        call_command(
            "migrate", "testapp", verbosity=0, skip_checks=True, interactive=False
        )
        with connection.cursor() as cursor:
            assert table_name in table_names(cursor)

        call_command(
            "migrate",
            "testapp",
            "zero",
            verbosity=0,
            skip_checks=True,
            interactive=False,
        )
        with connection.cursor() as cursor:
            assert table_name not in table_names(cursor)
