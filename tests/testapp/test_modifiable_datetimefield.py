from datetime import datetime
from unittest import mock

import django
from django.core.management import call_command
from django.db import connection
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from tests.testapp.models import ModifiableDatetimeModel

from django_mysql.models import DatetimeField


class TestModifiableDatetimeField(TestCase):
    def test_default_on_update_current_timestamp_option(self):
        field = DatetimeField()
        assert field.on_update_current_timestamp is True

    def test_auto_now_add_and_on_update_current_timestamp_option_are_mutually_exclusive(
        self,
    ):

        field = DatetimeField(auto_now_add=True, on_update_current_timestamp=True)
        errors = field.check()
        assert errors[0].id == "Error"

    def test_allow_datetime_field_argument(self):
        field1 = DatetimeField(auto_now_add=False, on_update_current_timestamp=True)
        field2 = DatetimeField(auto_add=True, on_update_current_timestamp=True)
        field3 = DatetimeField(default=timezone.now, on_update_current_timestamp=True)
        assert hasattr(field1, "auto_now_add")
        assert hasattr(field2, "auto_add")
        assert hasattr(field3, "default")

    @mock.patch(
        "django.db.models.fields.timezone.now", return_value=datetime(2020, 6, 13)
    )
    def test_save_modifiable_datetime_field_should_be_updated_to_current_timestamp(
        self,
    ):
        s1 = ModifiableDatetimeModel.objects.create(
            model_char="test_char", on_update_datetime=datetime(2020, 6, 13),
        )
        s1.save(model_char="updated_char")
        s1 = ModifiableDatetimeModel.objects.get(id=s1.id)

        assert s1.on_update_datetime != datetime(2020, 6, 13)
        assert s1.on_update_datetime_false != datetime(2020, 6, 13)
        assert s1.on_update_datetime_auto_now == datetime(2020, 6, 13)

    @mock.patch(
        "django.db.models.fields.timezone.now", return_value=datetime(2020, 6, 13)
    )
    def test_update_modifiable_datetime_field_should_be_updated_to_current_timestamp(
        self,
    ):
        s1 = ModifiableDatetimeModel.objects.create(
            model_char="test_char", on_update_datetime=datetime(2020, 6, 13),
        )
        ModifiableDatetimeModel.objects.filter(id=s1.id).update(
            model_char="updated_char"
        )

        s1 = ModifiableDatetimeModel.objects.get(id=s1.id)
        assert s1.on_update_datetime != datetime(2020, 6, 13)
        assert s1.on_update_datetime_false == datetime(2020, 6, 13)
        assert s1.on_update_datetime_auto_now != datetime(2020, 6, 13)


class TestCheck(TestCase):

    if django.VERSION >= (2, 2):
        databases = ["default", "other"]
    else:
        multi_db = True

    def test_check(self):
        errors = ModifiableDatetimeModel.check()
        assert errors == []


class TestDeconstruct(TestCase):
    def test_deconstruct(self):
        field = DatetimeField()
        name, path, args, kwargs = field.deconstruct()
        assert path == "django_mysql.models.DatetimeField"
        assert "on_update_current_timestamp" in kwargs


class TestMigrations(TransactionTestCase):
    @override_settings(
        MIGRATION_MODULES={"testapp": "tests.testapp.datetime_default_migrations"}
    )
    def test_adding_field_with_default(self):
        table_name = "testapp_modifiabledatetimemodel"
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
