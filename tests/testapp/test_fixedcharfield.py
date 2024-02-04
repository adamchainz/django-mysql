from __future__ import annotations

import pytest
from django.core.management import call_command
from django.db import connection
from django.db import models
from django.db.utils import DataError
from django.test import SimpleTestCase
from django.test import TestCase
from django.test import TransactionTestCase
from django.test import override_settings
from django.test.utils import isolate_apps
from django_mysql.models import FixedCharField

from tests.testapp.models import FixedCharModel


class TestSaveLoad(TestCase):
    def test_success_exact(self):
        instance = FixedCharModel.objects.create(zip_code="0" * 10)
        assert instance.zip_code == "0" * 10
        instance = FixedCharModel.objects.get(id=instance.id)
        assert instance.zip_code == "0" * 10

    def test_success_shorter(self):
        FixedCharModel.objects.create(zip_code="0" * 9)
        m = FixedCharModel.objects.get()
        assert m.zip_code == "0" * 9

    def test_invalid_too_long(self):
        with pytest.raises(DataError) as excinfo:
            FixedCharModel.objects.create(zip_code="0" * 11)

        assert excinfo.value.args == (
            1406,
            "Data too long for column 'zip_code' at row 1",
        )

    def test_exact_lookup(self):
        FixedCharModel.objects.create(zip_code="0" * 10)

        count = FixedCharModel.objects.filter(zip_code="0" * 10).count()

        assert count == 1


class SubFixedCharField(FixedCharField):
    """
    Used below, has a different path for deconstruct()
    """


class TestDeconstruct(TestCase):
    def test_deconstruct(self):
        field = FixedCharField(max_length=1)
        name, path, args, kwargs = field.deconstruct()
        assert path == "django_mysql.models.FixedCharField"
        assert kwargs["max_length"] == 1
        FixedCharField(*args, **kwargs)

    def test_subclass_deconstruct(self):
        field = SubFixedCharField(max_length=1)
        name, path, args, kwargs = field.deconstruct()
        assert path == "tests.testapp.test_fixedcharfield.SubFixedCharField"


@isolate_apps("tests.testapp")
class TestCheck(SimpleTestCase):
    def test_length_too_small(self):
        class Invalid(models.Model):
            field = FixedCharField(max_length=-1)

        errors = Invalid.check()
        assert len(errors) == 2
        assert errors[0].id == "fields.E121"
        assert errors[0].msg == "'max_length' must be a positive integer."
        assert errors[1].id == "django_mysql.E015"
        assert errors[1].msg == "'max_length' must be between 0 and 255."

    def test_length_too_large(self):
        class Invalid(models.Model):
            field = FixedCharField(max_length=256)

        errors = Invalid.check()
        assert len(errors) == 1
        assert errors[0].id == "django_mysql.E015"
        assert errors[0].msg == "'max_length' must be between 0 and 255."


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
