# -*- coding:utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import json
from datetime import date, datetime, time
from unittest import SkipTest, mock

import pytest
from django.core import serializers
from django.db import connection, connections
from django.db.migrations.writer import MigrationWriter
from django.db.models import CharField, Transform
from django.test import TestCase
from django.utils import six

from django_mysql.models import DynamicField
from django_mysql.utils import connection_is_mariadb
from testapp.models import DynamicModel, TemporaryModel
from testapp.utils import requiresPython2


class DynColTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        if not (
            connection_is_mariadb(connection) and
            connection.mysql_version >= (10, 0, 1)
        ):
            raise SkipTest("Dynamic Columns require MariaDB 10.0.1+")
        super(DynColTestCase, cls).setUpClass()


class TestSaveLoad(DynColTestCase):

    def test_save_and_mutations(self):
        s = DynamicModel.objects.create()
        assert s.attrs == {}

        s = DynamicModel.objects.get()
        assert s.attrs == {}

        s.attrs['key'] = 'value!'
        s.attrs['2key'] = 23
        s.save()
        s = DynamicModel.objects.get()
        assert s.attrs == {'key': 'value!', '2key': 23}

        del s.attrs['key']
        s.save()
        s = DynamicModel.objects.get()
        assert s.attrs == {'2key': 23}

        del s.attrs['2key']
        s.save()
        s = DynamicModel.objects.get()
        assert s.attrs == {}

    def test_create(self):
        DynamicModel.objects.create(attrs={
            'a': 'value'
        })
        s = DynamicModel.objects.get()
        assert s.attrs == {'a': 'value'}

    def test_create_succeeds_specced_field(self):
        DynamicModel.objects.create(attrs={'inty': 1})
        s = DynamicModel.objects.get()
        assert s.attrs == {'inty': 1}

    def test_create_fails_bad_value(self):
        with pytest.raises(TypeError):
            DynamicModel.objects.create(attrs={'inty': 1.0})

    def test_bulk_create(self):
        DynamicModel.objects.bulk_create([
            DynamicModel(attrs={'a': 'value'}),
            DynamicModel(attrs={'b': 'value2'}),
        ])
        dm1, dm2 = DynamicModel.objects.all().order_by('id')
        assert dm1.attrs == {'a': 'value'}
        assert dm2.attrs == {'b': 'value2'}


class SpecTests(DynColTestCase):

    def test_spec_dict_type(self):
        DynamicField.validate_spec(
            {'a': dict},
            {'a': {'this': 'that'}}
        )  # no errors

    def test_illegal_int(self):
        m = DynamicModel(attrs={'inty': 1.0})
        with pytest.raises(TypeError) as excinfo:
            m.save()
        assert "Key 'inty' should be of type int" in str(excinfo.value)

    def test_illegal_nested(self):
        m = DynamicModel(attrs={'nesty': {'level2': 1}})
        with pytest.raises(TypeError) as excinfo:
            m.save()
        assert "Key 'nesty.level2' should be of type " in str(excinfo.value)

    def test_illegal_nested_type(self):
        m = DynamicModel(attrs={'nesty': []})
        with pytest.raises(TypeError) as excinfo:
            m.save()
        assert "Key 'nesty' should be of type dict" in str(excinfo.value)

    @requiresPython2
    def test_long_equivalent_to_int(self):
        from __builtin__ import long  # make source lintable on Python 3
        DynamicField.validate_spec({'a': int}, {'a': long(9001)})  # no errors

    @requiresPython2
    def test_int_equivalent_to_long(self):
        from __builtin__ import long  # make source lintable on Python 3
        DynamicField.validate_spec({'a': long}, {'a': int(9001)})  # no errors


class DumbTransform(Transform):
    """
    Used to test existing transform behaviour - by default in Django there are
    no transforms on BinaryField.
    Really dumb, returns the string 'dumb' always
    """
    lookup_name = 'dumb'
    output_field = CharField()

    def as_sql(self, compiler, connection):
        lhs, params = compiler.compile(self.lhs)
        return "%s", ['dumb']


DynamicField.register_lookup(DumbTransform)


class QueryTests(DynColTestCase):

    def setUp(self):
        super(QueryTests, self).setUp()
        self.objs = [
            DynamicModel(attrs={'a': 'b'}),
            DynamicModel(attrs={'a': 'b', 'c': 'd'}),
            DynamicModel(attrs={'c': 'd'}),
            DynamicModel(attrs={}),
            DynamicModel(attrs={
                'datetimey': datetime(2001, 1, 4, 14, 15, 16),
                'datey': date(2001, 1, 4),
                'floaty': 128.5,
                'inty': 9001,
                'stry': "strvalue",
                'str_underscorey': "strvalue2",
                'timey': time(14, 15, 16),
                'nesty': {
                    'level2': 'chirp'
                }
            }),
        ]
        DynamicModel.objects.bulk_create(self.objs)
        self.objs = list(DynamicModel.objects.all().order_by('id'))

    def test_equal(self):
        assert (
            list(DynamicModel.objects.filter(attrs={'a': 'b'})) ==
            self.objs[:1]
        )

    def test_exact(self):
        assert (
            list(DynamicModel.objects.filter(attrs__exact={'a': 'b'})) ==
            self.objs[:1]
        )

    def test_preexisting_transforms_work_fine(self):
        assert (
            list(DynamicModel.objects.filter(attrs__dumb='notdumb')) ==
            []
        )

    def test_has_key(self):
        assert (
            list(DynamicModel.objects.filter(attrs__has_key='c')) ==
            self.objs[1:3]
        )

    def test_key_transform_datey(self):
        assert (
            list(DynamicModel.objects.filter(attrs__datey=date(2001, 1, 4))) ==
            [self.objs[4]]
        )

    def test_key_transform_datey_DATE(self):
        assert (
            list(DynamicModel.objects.filter(
                attrs__datey_DATE=date(2001, 1, 4)
            )) ==
            [self.objs[4]]
        )

    def test_key_transform_datetimey(self):
        assert (
            list(DynamicModel.objects.filter(
                attrs__datetimey=datetime(2001, 1, 4, 14, 15, 16)
            )) ==
            [self.objs[4]]
        )

    def test_key_transform_datetimey__year(self):
        assert (
            list(DynamicModel.objects.filter(attrs__datetimey__year=2001)) ==
            [self.objs[4]]
        )

    def test_key_transform_datetimey_DATETIME(self):
        assert (
            list(DynamicModel.objects.filter(
                attrs__datetimey_DATETIME=datetime(2001, 1, 4, 14, 15, 16)
            )) ==
            [self.objs[4]]
        )

    def test_key_transform_floaty(self):
        assert (
            list(DynamicModel.objects.filter(attrs__floaty__gte=128.0)) ==
            [self.objs[4]]
        )

    def test_key_transform_floaty_DOUBLE(self):
        assert (
            list(DynamicModel.objects.filter(attrs__floaty_DOUBLE=128.5)) ==
            [self.objs[4]]
        )

    def test_key_transform_inty(self):
        assert (
            list(DynamicModel.objects.filter(attrs__inty=9001)) ==
            [self.objs[4]]
        )

    def test_key_transform_inty_INTEGER(self):
        assert (
            list(DynamicModel.objects.filter(attrs__inty_INTEGER=9001)) ==
            [self.objs[4]]
        )

    def test_key_transform_inty_no_results(self):
        assert (
            list(DynamicModel.objects.filter(attrs__inty=12991)) ==
            []
        )

    def test_key_transform_inty_in_subquery(self):
        assert (
            list(DynamicModel.objects.filter(
                id__in=DynamicModel.objects.filter(attrs__inty=9001),
            )) ==
            [self.objs[4]]
        )

    def test_key_transform_miss_CHAR_isnull(self):
        assert (
            list(DynamicModel.objects.filter(attrs__miss_CHAR__isnull=True)) ==
            self.objs
        )

    def test_key_transform_stry(self):
        assert (
            list(DynamicModel.objects.filter(attrs__stry="strvalue")) ==
            [self.objs[4]]
        )

    def test_key_transform_stry_CHAR(self):
        assert (
            list(DynamicModel.objects.filter(attrs__stry_CHAR="strvalue")) ==
            [self.objs[4]]
        )

    def test_key_transform_str_underscorey_CHAR(self):
        # Check that underscores in key names are parsed fine
        assert (
            list(DynamicModel.objects.filter(
                attrs__str_underscorey_CHAR="strvalue2"
            )) ==
            [self.objs[4]]
        )

    def test_key_transform_timey(self):
        assert (
            list(DynamicModel.objects.filter(attrs__timey=time(14, 15, 16))) ==
            [self.objs[4]]
        )

    def test_key_transform_timey_TIME(self):
        assert (
            list(DynamicModel.objects.filter(
                attrs__timey_TIME=time(14, 15, 16)
            )) ==
            [self.objs[4]]
        )

    def test_key_transform_nesty__level2(self):
        assert (
            list(DynamicModel.objects.filter(
                attrs__nesty__level2='chirp'
            )) ==
            [self.objs[4]]
        )

    def test_key_transform_nesty__level2__startswith(self):
        assert (
            list(DynamicModel.objects.filter(
                attrs__nesty__level2__startswith='chi'
            )) ==
            [self.objs[4]]
        )


class TestCheck(DynColTestCase):

    @mock.patch('django_mysql.models.fields.dynamic.connection_is_mariadb')
    def test_db_not_mariadb(self, is_mariadb):
        is_mariadb.return_value = False

        class ValidDynamicModel(TemporaryModel):
            field = DynamicField()

        errors = ValidDynamicModel.check(actually_check=True)
        assert len(errors) == 1
        assert errors[0].id == 'django_mysql.E013'
        assert "MariaDB 10.0.1+ is required" in errors[0].msg

    wrapper_path = 'django.db.backends.mysql.base.DatabaseWrapper'

    @mock.patch(wrapper_path + '.mysql_version', new=(5, 5, 3))
    def test_mariadb_old_version(self):
        # Uncache cached_property
        for db in connections:
            if 'mysql_version' in connections[db].__dict__:
                del connections[db].__dict__['mysql_version']

        class ValidDynamicModel(TemporaryModel):
            field = DynamicField()

        errors = ValidDynamicModel.check(actually_check=True)
        assert len(errors) == 1
        assert errors[0].id == 'django_mysql.E013'
        assert "MariaDB 10.0.1+ is required" in errors[0].msg

    @mock.patch(DynamicField.__module__ + '.mariadb_dyncol', new=None)
    def test_mariadb_dyncol_missing(self):
        errors = DynamicModel.check()
        assert len(errors) == 1
        assert errors[0].id == 'django_mysql.E012'
        assert "'mariadb_dyncol' is required" in errors[0].msg

    def test_character_set_not_utf8_compatible(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT @@character_set_client")
            orig_charset = cursor.fetchone()[0]
            cursor.execute("SET NAMES 'latin1'")
            try:
                errors = DynamicModel.check()
            finally:
                cursor.execute("SET NAMES '{}'".format(orig_charset))

        assert len(errors) == 1
        assert errors[0].id == 'django_mysql.E014'
        assert "The MySQL charset must be 'utf8'" in errors[0].msg

    def test_spec_not_dict(self):
        class InvalidDynamicModel(TemporaryModel):
            field = DynamicField(spec=['woops', 'a', 'list'])

        errors = InvalidDynamicModel.check(actually_check=True)
        assert len(errors) == 1
        assert errors[0].id == 'django_mysql.E009'
        assert "'spec' must be a dict" in errors[0].msg
        assert "The value passed is of type list" in errors[0].hint

    def test_spec_key_not_valid(self):
        class InvalidDynamicModel(TemporaryModel):
            field = DynamicField(spec={
                2.0: six.text_type
            })

        errors = InvalidDynamicModel.check(actually_check=True)
        assert len(errors) == 1
        assert errors[0].id == 'django_mysql.E010'
        assert "The key '2.0' in 'spec' is not a string" in errors[0].msg
        assert "'spec' keys must be of type " in errors[0].hint
        assert "'2.0' is of type float" in errors[0].hint

    def test_spec_value_not_valid(self):
        class InvalidDynamicModel(TemporaryModel):
            field = DynamicField(spec={'bad': list})

        errors = InvalidDynamicModel.check(actually_check=True)
        assert len(errors) == 1
        assert errors[0].id == 'django_mysql.E011'
        assert (
            "The value for 'bad' in 'spec' is not an allowed type" in
            errors[0].msg
        )
        assert (
            "'spec' values must be one of the following types: "
            "date, datetime" in
            errors[0].hint
        )

    def test_spec_nested_value_not_valid(self):
        class InvalidDynamicModel(TemporaryModel):
            field = DynamicField(spec={
                'l1': {
                    'bad': tuple
                }
            })

        errors = InvalidDynamicModel.check(actually_check=True)
        assert len(errors) == 1
        assert errors[0].id == 'django_mysql.E011'
        assert (
            "The value for 'bad' in 'spec.l1' is not an allowed type" in
            errors[0].msg
        )
        assert (
            "'spec' values must be one of the following types: "
            "date, datetime" in
            errors[0].hint
        )


class SubDynamicField(DynamicField):
    """
    Used below, has a different path for deconstruct()
    """


class TestDeconstruct(TestCase):

    def test_deconstruct(self):
        field = DynamicField()
        name, path, args, kwargs = field.deconstruct()
        DynamicField(*args, **kwargs)

    def test_deconstruct_spec(self):
        field = DynamicField(spec={'this': int, 'that': float})
        name, path, args, kwargs = field.deconstruct()
        assert path == 'django_mysql.models.DynamicField'
        DynamicField(*args, **kwargs)

    def test_bad_import_deconstruct(self):
        from django_mysql.models.fields import DynamicField as DField
        field = DField()
        name, path, args, kwargs = field.deconstruct()
        assert path == 'django_mysql.models.DynamicField'

    def test_bad_import2_deconstruct(self):
        from django_mysql.models.fields.dynamic import DynamicField as DField
        field = DField()
        name, path, args, kwargs = field.deconstruct()
        assert path == 'django_mysql.models.DynamicField'

    def test_subclass_deconstruct(self):
        field = SubDynamicField()
        name, path, args, kwargs = field.deconstruct()
        assert path == 'tests.testapp.test_dynamicfield.SubDynamicField'


class TestMigrations(DynColTestCase):

    def test_makemigrations(self):
        field = DynamicField(spec={'a': 'beta'})
        statement, imports = MigrationWriter.serialize(field)
        # 'spec' should not appear since that would trigger needless ALTERs
        assert statement == "django_mysql.models.DynamicField()"


class TestSerialization(DynColTestCase):
    test_data = '''
        [{"fields": {"attrs": "{\\"a\\": \\"b\\"}"},
          "model": "testapp.dynamicmodel", "pk": null}]
    '''

    def test_dumping(self):
        instance = DynamicModel(attrs={'a': 'b'})
        data = serializers.serialize('json', [instance])
        assert json.loads(data) == json.loads(self.test_data)

    def test_loading(self):
        deserialized = list(serializers.deserialize('json', self.test_data))
        instance = deserialized[0].object
        assert instance.attrs == {'a': 'b'}


class TestFormfield(DynColTestCase):
    def test_formfield(self):
        model_field = DynamicField()
        form_field = model_field.formfield()
        self.assertIsNone(form_field)
