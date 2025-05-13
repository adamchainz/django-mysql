from __future__ import annotations

import pytest
from django.core.management import call_command
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import connection
from django.db.utils import DataError
from django.test import TestCase
from django.test import TransactionTestCase
from django.test import override_settings

from tests.testapp.models import TinyIntegerModel


class TestSaveLoad(TestCase):
    def test_success(self):
        TinyIntegerModel.objects.create(tiny_signed=-128, tiny_unsigned=0)
        TinyIntegerModel.objects.create(tiny_signed=127, tiny_unsigned=255)

    def test_invalid_too_long_signed(self):
        with pytest.raises(DataError) as excinfo:
            TinyIntegerModel.objects.create(tiny_signed=128)

        assert excinfo.value.args == (
            1264,
            "Out of range value for column 'tiny_signed' at row 1",
        )

    def test_invalid_too_long_unsigned(self):
        with pytest.raises(DataError) as excinfo:
            TinyIntegerModel.objects.create(tiny_unsigned=256)

        assert excinfo.value.args == (
            1264,
            "Out of range value for column 'tiny_unsigned' at row 1",
        )

    def test_invalid_too_short_signed(self):
        with pytest.raises(DataError) as excinfo:
            TinyIntegerModel.objects.create(tiny_signed=-129)

        assert excinfo.value.args == (
            1264,
            "Out of range value for column 'tiny_signed' at row 1",
        )

    def test_invalid_too_short_unsigned(self):
        with pytest.raises(DataError) as excinfo:
            TinyIntegerModel.objects.create(tiny_unsigned=-1)

        assert excinfo.value.args == (
            1264,
            "Out of range value for column 'tiny_unsigned' at row 1",
        )


class TestMigrations(TransactionTestCase):
    @override_settings(
        MIGRATION_MODULES={"testapp": "tests.testapp.tinyinteger_default_migrations"}
    )
    def test_adding_field_with_default(self):
        table_name = "testapp_tinyintegerdefaultmodel"
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


class TestFormValidation(TestCase):
    def test_signed_validators(self):
        validators = TinyIntegerModel._meta.get_field("tiny_signed").validators
        assert len(validators) == 2
        assert isinstance(validators[0], MinValueValidator)
        assert validators[0].limit_value == -128
        assert isinstance(validators[1], MaxValueValidator)
        assert validators[1].limit_value == 127

    def test_unsigned_validators(self):
        validators = TinyIntegerModel._meta.get_field("tiny_unsigned").validators
        assert len(validators) == 2
        assert isinstance(validators[0], MinValueValidator)
        assert validators[0].limit_value == 0
        assert isinstance(validators[1], MaxValueValidator)
        assert validators[1].limit_value == 255
