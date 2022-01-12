import pytest
from django.core.management import call_command
from django.db import connection
from django.test import TestCase, TransactionTestCase, override_settings

from django_mysql.models import FixedCharField


class TestFixedCharField(TestCase):
    def test_invalid_length_type(self):
        with pytest.raises(TypeError) as exc_info:
            FixedCharField(length="4")
        assert "Expected integer value." in str(exc_info.value)

    def test_invalid_length_too_short(self):
        with pytest.raises(ValueError) as exc_info:
            FixedCharField(length=-1)
        assert "Length must be in the range" in str(exc_info.value)

    def test_invalid_length_too_long(self):
        with pytest.raises(ValueError) as exc_info:
            FixedCharField(length=256)
        assert "Length must be in the range" in str(exc_info.value)

    def test_invalid_max_length(self):
        with pytest.raises(TypeError) as exc_info:
            FixedCharField(length=4, max_length=100)
        assert '"max_length" is not a valid argument' in str(exc_info.value)


class TestDeconstruct(TestCase):
    def test_deconstruct(self):
        field = FixedCharField()
        name, path, args, kwargs = field.deconstruct()
        assert path == "django_mysql.models.FixedCharField"
        assert kwargs["length"] == 1
        assert "max_length" not in kwargs
        FixedCharField(*args, **kwargs)


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
