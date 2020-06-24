import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import connection
from django.db.utils import DataError
from django.test import TestCase, TransactionTestCase, override_settings

from django_mysql.models import EnumField
from tests.testapp.models import EnumModel, NullableEnumModel


class TestEnumField(TestCase):
    def test_empty_choices(self):
        with pytest.raises(ValueError):
            EnumField(choices=[])

    def test_no_choices(self):
        with pytest.raises(ValueError):
            EnumField()

    def test_invalid_choices(self):
        with pytest.raises(TypeError) as exc_info:
            EnumField(choices=["red", 10])
        assert 'Invalid choice "10"' in str(exc_info.value)

    def test_invalid_max_length(self):
        with pytest.raises(TypeError) as exc_info:
            EnumField(choices=["red"], max_length=100)
        assert '"max_length" is not a valid argument' in str(exc_info.value)

    def test_correct(self):
        s = EnumModel.objects.create(field="red")
        assert s.field == "red"
        s = EnumModel.objects.get(id=s.id)
        assert s.field == "red"

    def test_invalid_value(self):
        with pytest.raises(DataError):
            EnumModel.objects.create(field="elephant")

    def test_empty(self):
        with pytest.raises(DataError):
            EnumModel.objects.create()

    def test_null_storage(self):
        s = NullableEnumModel.objects.create()
        assert s.field is None
        s = NullableEnumModel.objects.get(id=s.id)
        assert s.field is None

    def test_isnull_lookup(self):
        NullableEnumModel.objects.create(field="goat")
        s = NullableEnumModel.objects.create()
        actual = NullableEnumModel.objects.filter(field__isnull=True)
        expected = [s]

        assert list(actual) == expected

    def test_basic_lookup(self):
        s1 = EnumModel.objects.create(field="green")
        EnumModel.objects.create(field="red")
        s2 = EnumModel.objects.create(field="green")

        actual = EnumModel.objects.filter(field="green")
        expected = [s1, s2]

        assert list(actual) == expected

    def test_in_lookup(self):
        s1 = EnumModel.objects.create(field="green")
        EnumModel.objects.create(field="red")
        s2 = EnumModel.objects.create(field="green")

        actual = EnumModel.objects.filter(field__in=["green"])
        expected = [s1, s2]

        assert list(actual) == expected

    def test_icontains_lookup(self):
        s1 = EnumModel.objects.create(field="coralBlue")
        s2 = EnumModel.objects.create(field="blue")
        EnumModel.objects.create(field="green")

        actual = EnumModel.objects.filter(field__icontains="Blue")
        expected = [s1, s2]

        assert list(actual) == expected

    def test_contains_lookup(self):
        s1 = EnumModel.objects.create(field="coralblue")
        s2 = EnumModel.objects.create(field="blue")
        EnumModel.objects.create(field="green")

        actual = EnumModel.objects.filter(field__contains="blue")
        expected = [s1, s2]

        assert list(actual) == expected


class TestCheck(TestCase):

    databases = ["default", "other"]

    def test_check(self):
        errors = EnumModel.check()
        assert errors == []


class TestDeconstruct(TestCase):
    def test_deconstruct(self):
        field = EnumField(choices=["a", "b"])
        name, path, args, kwargs = field.deconstruct()
        assert path == "django_mysql.models.EnumField"
        assert "max_length" not in kwargs
        EnumField(*args, **kwargs)


class TestMigrations(TransactionTestCase):
    @override_settings(
        MIGRATION_MODULES={"testapp": "tests.testapp.enum_default_migrations"}
    )
    def test_adding_field_with_default(self):
        table_name = "testapp_enumdefaultmodel"
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


class TestFormfield(TestCase):
    def test_formfield(self):
        model_field = EnumField(choices=["this", "that"])
        form_field = model_field.formfield()

        assert form_field.clean("this") == "this"
        assert form_field.clean("that") == "that"

        with pytest.raises(ValidationError):
            form_field.clean("")

        with pytest.raises(ValidationError):
            form_field.clean("invalid")
