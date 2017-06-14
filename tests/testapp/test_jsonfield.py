# -*- coding:utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import json
from unittest import SkipTest, mock

import pytest
from django.core import serializers
from django.db import connection, connections
from django.db.models import F
from django.test import TestCase

from django_mysql import forms
from django_mysql.models import JSONField
from django_mysql.utils import connection_is_mariadb
from testapp.models import JSONModel, TemporaryModel
from testapp.utils import print_all_queries


class JSONFieldTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        if not (
            not connection_is_mariadb(connection) and
            connection.mysql_version >= (5, 7)
        ):
            raise SkipTest("JSONField requires MySQL 5.7+")
        super(JSONFieldTestCase, cls).setUpClass()


class TestSaveLoad(JSONFieldTestCase):

    def test_empty_dict(self):
        m = JSONModel()
        assert m.attrs == {}
        m.save()
        m = JSONModel.objects.get()
        assert m.attrs == {}

    def test_values(self):
        m = JSONModel(attrs={'key': 'value'})
        assert m.attrs == {'key': 'value'}
        m.save()
        m = JSONModel.objects.get()
        assert m.attrs == {'key': 'value'}

    def test_string(self):
        m = JSONModel(attrs='value')
        assert m.attrs == 'value'
        m.save()
        m = JSONModel.objects.get()
        assert m.attrs == 'value'

    def test_json_dumps_string(self):
        json_string = json.dumps({'foo': 'bar'})
        m = JSONModel(attrs=json_string)
        assert m.attrs == json_string
        m.save()
        m = JSONModel.objects.get()
        assert m.attrs == json_string

    def test_awkward_1(self):
        m = JSONModel(attrs='"')
        assert m.attrs == '"'
        m.save()
        m = JSONModel.objects.get()
        assert m.attrs == '"'

    def test_awkward_2(self):
        m = JSONModel(attrs='\\')
        assert m.attrs == '\\'
        m.save()
        m = JSONModel.objects.get()
        assert m.attrs == '\\'

    def test_list(self):
        m = JSONModel(attrs=[1, 2, 4])
        assert m.attrs == [1, 2, 4]
        m.save()
        m = JSONModel.objects.get()
        assert m.attrs == [1, 2, 4]

    def test_true(self):
        m = JSONModel(attrs=True)
        assert m.attrs is True
        m.save()
        m = JSONModel.objects.get()
        assert m.attrs is True

    def test_false(self):
        m = JSONModel(attrs=False)
        assert m.attrs is False
        m.save()
        m = JSONModel.objects.get()
        assert m.attrs is False

    def test_null(self):
        m = JSONModel(attrs=None)
        assert m.attrs is None
        m.save()
        m = JSONModel.objects.get()
        assert m.attrs is None

    def test_control_characters(self):
        chars = ''.join(chr(i) for i in range(32))
        m = JSONModel(attrs=[chars])
        assert m.attrs == [chars]
        m.save()
        m = JSONModel.objects.get()
        assert m.attrs == [chars]

    def test_nan_raises_valueerror(self):
        m = JSONModel(attrs=float('nan'))
        with pytest.raises(ValueError):
            m.save()


class QueryTests(JSONFieldTestCase):

    def setUp(self):
        super(QueryTests, self).setUp()
        JSONModel.objects.bulk_create([
            JSONModel(attrs={'a': 'b'}),
            JSONModel(attrs=1337),
            JSONModel(attrs=['an', 'array']),
            JSONModel(attrs=None),
            JSONModel(attrs='foo'),
        ])
        self.objs = list(JSONModel.objects.all().order_by('id'))

    def test_equal(self):
        assert (
            list(JSONModel.objects.filter(attrs={'a': 'b'})) ==
            [self.objs[0]]
        )

    def test_equal_value(self):
        assert (
            list(JSONModel.objects.filter(attrs=1337)) ==
            [self.objs[1]]
        )

    def test_equal_string(self):
        assert (
            list(JSONModel.objects.filter(attrs='foo')) ==
            [self.objs[4]]
        )

    def test_equal_array(self):
        assert (
            list(JSONModel.objects.filter(attrs=['an', 'array'])) ==
            [self.objs[2]]
        )

    def test_equal_no_match(self):
        assert (
            list(JSONModel.objects.filter(attrs={'c': 'z'})) ==
            []
        )

    def test_equal_F_attrs(self):
        assert (
            list(JSONModel.objects.filter(attrs=F('attrs'))) ==
            [self.objs[0], self.objs[1], self.objs[2], self.objs[4]]
        )

    def test_isnull_True(self):
        assert (
            list(JSONModel.objects.filter(attrs__isnull=True)) ==
            [self.objs[3]]
        )

    def test_isnull_False(self):
        assert (
            list(JSONModel.objects.filter(attrs__isnull=False)) ==
            [self.objs[0], self.objs[1], self.objs[2], self.objs[4]]
        )

    def test_range_broken(self):
        with pytest.raises(NotImplementedError) as excinfo:
            JSONModel.objects.filter(attrs__range=[1, 2])

        assert (
            "Lookup 'range' doesn't work with JSONField" in str(excinfo.value)
        )


class ArrayQueryTests(JSONFieldTestCase):

    def setUp(self):
        super(ArrayQueryTests, self).setUp()
        JSONModel.objects.bulk_create([
            JSONModel(attrs=[1, 3]),
            JSONModel(attrs=[1, 3, 3]),
            JSONModel(attrs=[1, 3, 3, 7]),
            JSONModel(attrs=[2, 4]),
        ])
        self.objs = list(JSONModel.objects.all().order_by('id'))

    def test_lt_1(self):
        assert (
            list(JSONModel.objects.filter(attrs__lt=[1])) ==
            []
        )

    def test_lt_3(self):
        assert (
            list(JSONModel.objects.filter(attrs__lt=[3])) ==
            self.objs
        )

    def test_lte_1_3_3(self):
        assert (
            list(JSONModel.objects.filter(attrs__lte=[1, 3, 3])) ==
            [self.objs[0], self.objs[1]]
        )

    def test_lte_1(self):
        assert (
            list(JSONModel.objects.filter(attrs__lte=[1])) ==
            []
        )

    def test_gt_1(self):
        assert (
            list(JSONModel.objects.filter(attrs__gt=[1])) ==
            self.objs
        )

    def test_gt_1_3(self):
        assert (
            list(JSONModel.objects.filter(attrs__gt=[1, 3])) ==
            self.objs[1:]
        )

    def test_gt_2_5(self):
        assert (
            list(JSONModel.objects.filter(attrs__gt=[2, 5])) ==
            []
        )

    def test_gte_1_3(self):
        assert (
            list(JSONModel.objects.filter(attrs__gte=[1, 3])) ==
            self.objs
        )

    def test_gte_2(self):
        assert (
            list(JSONModel.objects.filter(attrs__gte=[2])) ==
            [self.objs[3]]
        )


class ExtraLookupsQueryTests(JSONFieldTestCase):

    def setUp(self):
        super(ExtraLookupsQueryTests, self).setUp()

        self.objs = [
            JSONModel.objects.create(attrs={}),
            JSONModel.objects.create(attrs={
                'a': 'b',
                'c': 1,
                '"': 'awkward',
                '\n': 'super awkward'
            }),
            JSONModel.objects.create(attrs={
                'a': 'b',
                'c': 1,
                'd': ['e', {'f': 'g'}],
                'h': True,
                'i': False,
                'j': None,
                'k': {'l': 'm'},
            }),
            JSONModel.objects.create(attrs=[1, [2]]),
            JSONModel.objects.create(attrs={
                'k': True,
                'l': False,
                '\\': 'awkward'
            }),
        ]

    def test_has_key_invalid_type(self):
        with pytest.raises(ValueError) as excinfo:
            JSONModel.objects.filter(attrs__has_key=1)
        assert "'has_key' lookup only works with" in str(excinfo.value)

    def test_has_key(self):
        assert (
            list(JSONModel.objects.filter(attrs__has_key='a')) ==
            [self.objs[1], self.objs[2]]
        )

    def test_has_key_2(self):
        assert (
            list(JSONModel.objects.filter(attrs__has_key='l')) ==
            [self.objs[4]]
        )

    def test_has_key_awkward(self):
        assert (
            list(JSONModel.objects.filter(attrs__has_key='"')) ==
            [self.objs[1]]
        )

    def test_has_key_awkward_2(self):
        assert (
            list(JSONModel.objects.filter(attrs__has_key='\n')) ==
            [self.objs[1]]
        )

    def test_has_key_awkward_3(self):
        assert (
            list(JSONModel.objects.filter(attrs__has_key='\\')) ==
            [self.objs[4]]
        )

    def test_has_keys_invalid_type(self):
        with pytest.raises(ValueError) as excinfo:
            JSONModel.objects.filter(attrs__has_keys={'a': 'b'})
        assert "only works with Sequences" in str(excinfo.value)

    def test_has_keys(self):
        with print_all_queries():
            assert (
                list(JSONModel.objects.filter(attrs__has_keys=['a', 'c'])) ==
                [self.objs[1], self.objs[2]]
            )

    def test_has_keys_2(self):
        assert (
            list(JSONModel.objects.filter(attrs__has_keys=['l'])) ==
            [self.objs[4]]
        )

    def test_has_keys_awkward(self):
        assert (
            list(JSONModel.objects.filter(attrs__has_keys=['\n', '"'])) ==
            [self.objs[1]]
        )

    def test_has_any_keys_invalid_type(self):
        with pytest.raises(ValueError) as excinfo:
            JSONModel.objects.filter(attrs__has_any_keys={'a': 'b'})
        assert "only works with Sequences" in str(excinfo.value)

    def test_has_any_keys(self):
        assert (
            list(JSONModel.objects.filter(attrs__has_any_keys=['a', 'k'])) ==
            [self.objs[1], self.objs[2], self.objs[4]]
        )

    def test_has_any_keys_awkward(self):
        assert (
            list(JSONModel.objects.filter(attrs__has_any_keys=['\\'])) ==
            [self.objs[4]]
        )

    def test_contains(self):
        assert (
            list(JSONModel.objects.filter(attrs__contains={'a': 'b'})) ==
            [self.objs[1], self.objs[2]]
        )

    def test_contains_2(self):
        assert (
            list(JSONModel.objects.filter(attrs__contains={'l': False})) ==
            [self.objs[4]]
        )

    def test_contains_array(self):
        assert (
            list(JSONModel.objects.filter(attrs__contains=[[2]])) ==
            [self.objs[3]]
        )

    def test_contained_by(self):
        assert (
            list(JSONModel.objects.filter(attrs__contained_by={
                'k': True,
                'l': False,
                '\\': 'awkward',
                'spare_key': ['unused', 'array'],
            })) ==
            [self.objs[0], self.objs[4]]
        )

    def test_contained_by_array(self):
        assert (
            list(JSONModel.objects.filter(attrs__contained_by=[1, [2], 3])) ==
            [self.objs[3]]
        )

    def test_length_lookup(self):
        assert (
            list(JSONModel.objects.filter(attrs__length=0)) ==
            [self.objs[0]]
        )

    def test_length_lookup_2(self):
        assert (
            list(JSONModel.objects.filter(attrs__length=2)) ==
            [self.objs[3]]
        )

    def test_length_lookup_chains(self):
        assert (
            list(JSONModel.objects.filter(attrs__length__range=[0, 10])) ==
            self.objs
        )

    def test_shallow_list_lookup(self):
        assert (
            list(JSONModel.objects.filter(attrs__0=1)) ==
            [self.objs[3]]
        )

    def test_shallow_obj_lookup(self):
        assert (
            list(JSONModel.objects.filter(attrs__a='b')) ==
            [self.objs[1], self.objs[2]]
        )

    def test_deep_lookup_objs(self):
        assert (
            list(JSONModel.objects.filter(attrs__k__l='m')) ==
            [self.objs[2]]
        )

    def test_shallow_lookup_obj_target(self):
        assert (
            list(JSONModel.objects.filter(attrs__k={'l': 'm'})) ==
            [self.objs[2]]
        )

    def test_deep_lookup_array(self):
        assert (
            list(JSONModel.objects.filter(attrs__1__0=2)) ==
            [self.objs[3]]
        )

    def test_deep_lookup_mixed(self):
        assert (
            list(JSONModel.objects.filter(attrs__d__1__f='g')) ==
            [self.objs[2]]
        )

    def test_deep_lookup_gt(self):
        assert (
            list(JSONModel.objects.filter(attrs__c__gt=1)) ==
            []
        )
        assert (
            list(JSONModel.objects.filter(attrs__c__lt=5)) ==
            [self.objs[1], self.objs[2]]
        )

    def test_usage_in_subquery(self):
        assert (
            list(JSONModel.objects.filter(
                id__in=JSONModel.objects.filter(attrs__c=1)
            )) ==
            [self.objs[1], self.objs[2]]
        )


class TestCheck(JSONFieldTestCase):

    def test_mutable_default_list(self):
        class InvalidJSONModel(TemporaryModel):
            field = JSONField(default=[])

        errors = InvalidJSONModel.check(actually_check=True)
        assert len(errors) == 1
        assert errors[0].id == 'django_mysql.E017'
        assert 'Do not use mutable defaults for JSONField' in errors[0].msg

    def test_mutable_default_dict(self):
        class InvalidJSONModel(TemporaryModel):
            field = JSONField(default=[])

        errors = InvalidJSONModel.check(actually_check=True)
        assert len(errors) == 1
        assert errors[0].id == 'django_mysql.E017'
        assert 'Do not use mutable defaults for JSONField' in errors[0].msg

    @mock.patch('django_mysql.models.fields.json.connection_is_mariadb')
    def test_db_not_mysql(self, is_mariadb):
        is_mariadb.return_value = True

        class InvalidJSONModel(TemporaryModel):
            field = JSONField()

        errors = InvalidJSONModel.check(actually_check=True)
        assert len(errors) == 1
        assert errors[0].id == 'django_mysql.E016'
        assert "MySQL 5.7+ is required" in errors[0].msg

    wrapper_path = 'django.db.backends.mysql.base.DatabaseWrapper'

    @mock.patch(wrapper_path + '.mysql_version', new=(5, 5, 3))
    def test_mysql_old_version(self):
        # Uncache cached_property
        for db in connections:
            if 'mysql_version' in connections[db].__dict__:
                del connections[db].__dict__['mysql_version']

        class InvalidJSONModel(TemporaryModel):
            field = JSONField()

        errors = InvalidJSONModel.check(actually_check=True)
        assert len(errors) == 1
        assert errors[0].id == 'django_mysql.E016'
        assert "MySQL 5.7+ is required" in errors[0].msg


class TestFormField(JSONFieldTestCase):

    def test_model_field_formfield(self):
        model_field = JSONField()
        form_field = model_field.formfield()
        assert isinstance(form_field, forms.JSONField)


class TestSerialization(JSONFieldTestCase):
    test_data = '''[
        {
            "fields": {
                "attrs": {"a": "b", "c": null}
            },
            "model": "testapp.jsonmodel",
            "pk": null
        }
    ]'''

    def test_dumping(self):
        instance = JSONModel(attrs={'a': 'b', 'c': None})
        data = serializers.serialize('json', [instance])
        assert json.loads(data) == json.loads(self.test_data)

    def test_loading(self):
        instances = list(serializers.deserialize('json', self.test_data))
        instance = instances[0].object
        assert instance.attrs == {'a': 'b', 'c': None}
