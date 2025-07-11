from __future__ import annotations

import datetime as dt
import json
from unittest import SkipTest, mock

import mariadb_dyncol
import pytest
from django.core import serializers
from django.core.exceptions import FieldError
from django.db import connection, connections, models
from django.db.migrations.writer import MigrationWriter
from django.db.models import CharField, Transform
from django.test import TestCase
from django.test.utils import isolate_apps

from django_mysql.models import DynamicField
from django_mysql.models.fields.dynamic import KeyTransform
from tests.testapp.models import DynamicModel, SpeclessDynamicModel


class DynColTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        if not connection.mysql_is_mariadb:
            raise SkipTest("Dynamic Columns require MariaDB")
        super().setUpClass()


class TestSaveLoad(DynColTestCase):
    def test_save_and_mutations(self):
        s = DynamicModel.objects.create()
        assert s.attrs == {}

        s = DynamicModel.objects.get()
        assert s.attrs == {}

        s.attrs["key"] = "value!"
        s.attrs["2key"] = 23
        s.save()
        s = DynamicModel.objects.get()
        assert s.attrs == {"key": "value!", "2key": 23}

        del s.attrs["key"]
        s.save()
        s = DynamicModel.objects.get()
        assert s.attrs == {"2key": 23}

        del s.attrs["2key"]
        s.save()
        s = DynamicModel.objects.get()
        assert s.attrs == {}

    def test_create(self):
        DynamicModel.objects.create(attrs={"a": "value"})
        s = DynamicModel.objects.get()
        assert s.attrs == {"a": "value"}

    def test_create_succeeds_specced_field(self):
        DynamicModel.objects.create(attrs={"inty": 1})
        s = DynamicModel.objects.get()
        assert s.attrs == {"inty": 1}

    def test_create_fails_bad_value(self):
        with pytest.raises(TypeError):
            DynamicModel.objects.create(attrs={"inty": 1.0})

    def test_bulk_create(self):
        DynamicModel.objects.bulk_create(
            [DynamicModel(attrs={"a": "value"}), DynamicModel(attrs={"b": "value2"})]
        )
        dm1, dm2 = DynamicModel.objects.order_by("id")
        assert dm1.attrs == {"a": "value"}
        assert dm2.attrs == {"b": "value2"}


class SpecTests(DynColTestCase):
    def test_spec_empty(self):
        DynamicField.validate_spec({}, {})  # no errors

    def test_spec_dict_type(self):
        DynamicField.validate_spec({"a": dict}, {"a": {"this": "that"}})  # no errors

    def test_illegal_int(self):
        m = DynamicModel(attrs={"inty": 1.0})
        with pytest.raises(TypeError) as excinfo:
            m.save()
        assert "Key 'inty' should be of type int" in str(excinfo.value)

    def test_illegal_nested(self):
        m = DynamicModel(attrs={"nesty": {"level2": 1}})
        with pytest.raises(TypeError) as excinfo:
            m.save()
        assert "Key 'nesty.level2' should be of type " in str(excinfo.value)

    def test_illegal_nested_type(self):
        m = DynamicModel(attrs={"nesty": []})
        with pytest.raises(TypeError) as excinfo:
            m.save()
        assert "Key 'nesty' should be of type dict" in str(excinfo.value)


class DumbTransform(Transform):
    """
    Used to test existing transform behaviour. Really dumb, returns the string
    'dumb' always.
    """

    lookup_name = "dumb"
    output_field = CharField()

    def as_sql(self, compiler, connection):
        lhs, params = compiler.compile(self.lhs)
        return "%s", ["dumb"]


DynamicField.register_lookup(DumbTransform)


class QueryTests(DynColTestCase):
    objs: list[DynamicModel]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        DynamicModel.objects.bulk_create(
            [
                DynamicModel(attrs={"a": "b"}),
                DynamicModel(attrs={"a": "b", "c": "d"}),
                DynamicModel(attrs={"c": "d"}),
                DynamicModel(attrs={}),
                DynamicModel(
                    attrs={
                        "datetimey": dt.datetime(2001, 1, 4, 14, 15, 16),
                        "datey": dt.date(2001, 1, 4),
                        "floaty": 128.5,
                        "inty": 9001,
                        "stry": "strvalue",
                        "str_underscorey": "strvalue2",
                        "timey": dt.time(14, 15, 16),
                        "nesty": {"level2": "chirp"},
                    }
                ),
            ]
        )
        cls.objs = list(DynamicModel.objects.order_by("id"))

    def test_equal(self):
        assert list(DynamicModel.objects.filter(attrs={"a": "b"})) == self.objs[:1]

    def test_exact(self):
        assert (
            list(DynamicModel.objects.filter(attrs__exact={"a": "b"})) == self.objs[:1]
        )

    def test_preexisting_transforms_work_fine(self):
        assert list(DynamicModel.objects.filter(attrs__dumb="notdumb")) == []

    def test_non_existent_transform(self):
        with pytest.raises(FieldError):
            DynamicModel.objects.filter(attrs__nonexistent="notdumb")

    def test_has_key(self):
        assert list(DynamicModel.objects.filter(attrs__has_key="c")) == self.objs[1:3]

    def test_key_transform_initialize_bad_type(self):
        with pytest.raises(ValueError) as excinfo:
            KeyTransform("x", "unknown")

        assert str(excinfo.value) == "Invalid data_type 'unknown'"

    def test_key_transform_datey(self):
        assert list(DynamicModel.objects.filter(attrs__datey=dt.date(2001, 1, 4))) == [
            self.objs[4]
        ]

    def test_key_transform_datey_DATE(self):
        assert list(
            DynamicModel.objects.filter(attrs__datey_DATE=dt.date(2001, 1, 4))
        ) == [self.objs[4]]

    def test_key_transform_datetimey(self):
        assert list(
            DynamicModel.objects.filter(
                attrs__datetimey=dt.datetime(
                    2001, 1, 4, 14, 15, 16, tzinfo=dt.timezone.utc
                )
            )
        ) == [self.objs[4]]

    def test_key_transform_datetimey__year(self):
        assert list(DynamicModel.objects.filter(attrs__datetimey__year=2001)) == [
            self.objs[4]
        ]

    def test_key_transform_datetimey_DATETIME(self):
        assert list(
            DynamicModel.objects.filter(
                attrs__datetimey_DATETIME=dt.datetime(
                    2001, 1, 4, 14, 15, 16, tzinfo=dt.timezone.utc
                )
            )
        ) == [self.objs[4]]

    def test_key_transform_floaty(self):
        assert list(DynamicModel.objects.filter(attrs__floaty__gte=128.0)) == [
            self.objs[4]
        ]

    def test_key_transform_floaty_DOUBLE(self):
        assert list(DynamicModel.objects.filter(attrs__floaty_DOUBLE=128.5)) == [
            self.objs[4]
        ]

    def test_key_transform_inty(self):
        assert list(DynamicModel.objects.filter(attrs__inty=9001)) == [self.objs[4]]

    def test_key_transform_inty_INTEGER(self):
        assert list(DynamicModel.objects.filter(attrs__inty_INTEGER=9001)) == [
            self.objs[4]
        ]

    def test_key_transform_inty_no_results(self):
        assert list(DynamicModel.objects.filter(attrs__inty=12991)) == []

    def test_key_transform_inty_in_subquery(self):
        assert list(
            DynamicModel.objects.filter(
                id__in=DynamicModel.objects.filter(attrs__inty=9001)
            )
        ) == [self.objs[4]]

    def test_key_transform_miss_CHAR_isnull(self):
        assert (
            list(DynamicModel.objects.filter(attrs__miss_CHAR__isnull=True))
            == self.objs
        )

    def test_key_transform_stry(self):
        assert list(DynamicModel.objects.filter(attrs__stry="strvalue")) == [
            self.objs[4]
        ]

    def test_key_transform_stry_CHAR(self):
        assert list(DynamicModel.objects.filter(attrs__stry_CHAR="strvalue")) == [
            self.objs[4]
        ]

    def test_key_transform_str_underscorey_CHAR(self):
        # Check that underscores in key names are parsed fine
        assert list(
            DynamicModel.objects.filter(attrs__str_underscorey_CHAR="strvalue2")
        ) == [self.objs[4]]

    def test_key_transform_timey(self):
        assert list(DynamicModel.objects.filter(attrs__timey=dt.time(14, 15, 16))) == [
            self.objs[4]
        ]

    def test_key_transform_timey_TIME(self):
        assert list(
            DynamicModel.objects.filter(attrs__timey_TIME=dt.time(14, 15, 16))
        ) == [self.objs[4]]

    def test_key_transform_nesty__level2(self):
        assert list(DynamicModel.objects.filter(attrs__nesty__level2="chirp")) == [
            self.objs[4]
        ]

    def test_key_transform_nesty__level2__startswith(self):
        assert list(
            DynamicModel.objects.filter(attrs__nesty__level2__startswith="chi")
        ) == [self.objs[4]]


class SpeclessQueryTests(DynColTestCase):
    objs: list[SpeclessDynamicModel]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        SpeclessDynamicModel.objects.bulk_create(
            [
                SpeclessDynamicModel(attrs={"a": "b"}),
                SpeclessDynamicModel(attrs={"a": "c"}),
            ]
        )
        cls.objs = list(SpeclessDynamicModel.objects.order_by("id"))

    def test_simple(self):
        assert list(SpeclessDynamicModel.objects.filter(attrs__a_CHAR="b")) == [
            self.objs[0]
        ]


@isolate_apps("tests.testapp")
class TestCheck(DynColTestCase):
    databases = {"default", "other"}

    def test_db_not_mariadb(self):
        class Valid(models.Model):
            field = DynamicField()

        mock_default = mock.patch.object(
            connections["default"], "mysql_is_mariadb", False
        )
        mock_other = mock.patch.object(connections["other"], "mysql_is_mariadb", False)

        with mock_default, mock_other:
            errors = Valid.check()

        assert len(errors) == 1
        assert errors[0].id == "django_mysql.E013"
        assert "MariaDB is required" in errors[0].msg

    @mock.patch(DynamicField.__module__ + ".mariadb_dyncol", new=None)
    def test_mariadb_dyncol_missing(self):
        errors = DynamicModel.check()
        assert len(errors) == 1
        assert errors[0].id == "django_mysql.E012"
        assert "'mariadb_dyncol' is required" in errors[0].msg

    def test_character_set_not_utf8_compatible(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT @@character_set_client")
            orig_charset = cursor.fetchone()[0]
            cursor.execute("SET NAMES 'latin1'")
            try:
                errors = DynamicModel.check()
            finally:
                cursor.execute(f"SET NAMES '{orig_charset}'")  # noqa: B028

        assert len(errors) == 1
        assert errors[0].id == "django_mysql.E014"
        assert "The MySQL charset must be 'utf8'" in errors[0].msg

    def test_spec_not_dict(self):
        class Invalid(models.Model):
            field = DynamicField(spec=["woops", "a", "list"])  # type: ignore [arg-type]

        errors = Invalid.check()
        assert len(errors) == 1
        assert errors[0].id == "django_mysql.E009"
        assert "'spec' must be a dict" in errors[0].msg
        hint = errors[0].hint
        assert hint is not None
        assert "The value passed is of type list" in hint

    def test_spec_key_not_valid(self):
        class Invalid(models.Model):
            field = DynamicField(spec={2.0: str})  # type: ignore [dict-item]

        errors = Invalid.check()
        assert len(errors) == 1
        assert errors[0].id == "django_mysql.E010"
        assert "The key '2.0' in 'spec' is not a string" in errors[0].msg
        hint = errors[0].hint
        assert hint is not None
        assert "'spec' keys must be of type " in hint
        assert "'2.0' is of type float" in hint

    def test_spec_value_not_valid(self):
        class Invalid(models.Model):
            field = DynamicField(spec={"bad": list})  # type: ignore [dict-item]

        errors = Invalid.check()
        assert len(errors) == 1
        assert errors[0].id == "django_mysql.E011"
        assert "The value for 'bad' in 'spec' is not an allowed type" in errors[0].msg
        hint = errors[0].hint
        assert hint is not None
        assert (
            "'spec' values must be one of the following types: date, datetime" in hint
        )

    def test_spec_nested_value_not_valid(self):
        class Invalid(models.Model):
            field = DynamicField(
                spec={"l1": {"bad": tuple}},  # type: ignore [dict-item]
            )

        errors = Invalid.check()
        assert len(errors) == 1
        assert errors[0].id == "django_mysql.E011"
        assert (
            "The value for 'bad' in 'spec.l1' is not an allowed type" in errors[0].msg
        )
        hint = errors[0].hint
        assert hint is not None
        assert (
            "'spec' values must be one of the following types: date, datetime" in hint
        )


class TestToPython(TestCase):
    def test_mariadb_dyncol_value(self):
        value = mariadb_dyncol.pack({"foo": "bar"})
        result = DynamicField().to_python(value)
        assert result == {"foo": "bar"}

    def test_json(self):
        value = str(json.dumps({"foo": "bar"}))
        result = DynamicField().to_python(value)
        assert result == {"foo": "bar"}

    def test_pass_through(self):
        value = {"foo": "bar"}
        result = DynamicField().to_python(value)
        assert result == {"foo": "bar"}


def make_default():  # pragma: no cover
    """
    Use for below, alternative default function.
    """
    return {}


class SubDynamicField(DynamicField):
    """
    Used below, has a different path for deconstruct()
    """


class TestDeconstruct(TestCase):
    def test_deconstruct(self):
        field = DynamicField()
        name, path, args, kwargs = field.deconstruct()
        DynamicField(*args, **kwargs)

    def test_deconstruct_default(self):
        field = DynamicField(default=make_default)
        name, path, args, kwargs = field.deconstruct()
        assert kwargs["default"] is make_default
        DynamicField(*args, **kwargs)

    def test_deconstruct_blank(self):
        field = DynamicField(blank=False)
        name, path, args, kwargs = field.deconstruct()
        assert kwargs["blank"] is False
        DynamicField(*args, **kwargs)

    def test_deconstruct_spec(self):
        field = DynamicField(spec={"this": int, "that": float})
        name, path, args, kwargs = field.deconstruct()
        assert path == "django_mysql.models.DynamicField"
        DynamicField(*args, **kwargs)

    def test_bad_import_deconstruct(self):
        from django_mysql.models.fields import DynamicField as DField

        field = DField()
        name, path, args, kwargs = field.deconstruct()
        assert path == "django_mysql.models.DynamicField"

    def test_bad_import2_deconstruct(self):
        from django_mysql.models.fields.dynamic import DynamicField as DField

        field = DField()
        name, path, args, kwargs = field.deconstruct()
        assert path == "django_mysql.models.DynamicField"

    def test_subclass_deconstruct(self):
        field = SubDynamicField()
        name, path, args, kwargs = field.deconstruct()
        assert path == "tests.testapp.test_dynamicfield.SubDynamicField"


class TestMigrations(DynColTestCase):
    def test_makemigrations(self):
        field = DynamicField(spec={"a": int})
        statement, imports = MigrationWriter.serialize(field)
        # 'spec' should not appear since that would trigger needless ALTERs
        assert statement == "django_mysql.models.DynamicField()"


class TestSerialization(DynColTestCase):
    test_data = """
        [{"fields": {"attrs": "{\\"a\\": \\"b\\"}"},
          "model": "testapp.dynamicmodel", "pk": null}]
    """

    def test_dumping(self):
        instance = DynamicModel(attrs={"a": "b"})
        data = serializers.serialize("json", [instance])
        assert json.loads(data) == json.loads(self.test_data)

    def test_loading(self):
        deserialized = list(serializers.deserialize("json", self.test_data))
        instance = deserialized[0].object
        assert instance.attrs == {"a": "b"}


class TestFormfield(DynColTestCase):
    def test_formfield(self):
        model_field = DynamicField()
        form_field = model_field.formfield()
        self.assertIsNone(form_field)
