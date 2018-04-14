# -*- coding:utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)

import json
import re

import pytest
from django import forms
from django.core import exceptions, serializers
from django.db import models
from django.db.migrations.writer import MigrationWriter
from django.db.models import Q
from django.test import SimpleTestCase, TestCase

from django_mysql.forms import SimpleListField
from django_mysql.models import ListTextField
from testapp.models import BigCharListModel, BigIntListModel, TemporaryModel


class TestSaveLoad(TestCase):

    def test_char_easy(self):
        s = BigCharListModel.objects.create(field=["comfy", "big"])
        assert s.field == ["comfy", "big"]
        s = BigCharListModel.objects.get(id=s.id)
        assert s.field == ["comfy", "big"]

        s.field.append("round")
        s.save()
        assert s.field == ["comfy", "big", "round"]
        s = BigCharListModel.objects.get(id=s.id)
        assert s.field == ["comfy", "big", "round"]

    def test_char_string_direct(self):
        s = BigCharListModel.objects.create(field="big,bad")
        s = BigCharListModel.objects.get(id=s.id)
        assert s.field == ['big', 'bad']

    def test_is_a_list_immediately(self):
        s = BigCharListModel()
        assert s.field == []
        s.field.append("bold")
        s.field.append("brave")
        s.save()
        assert s.field == ["bold", "brave"]
        s = BigCharListModel.objects.get(id=s.id)
        assert s.field == ["bold", "brave"]

    def test_empty(self):
        s = BigCharListModel.objects.create()
        assert s.field == []
        s = BigCharListModel.objects.get(id=s.id)
        assert s.field == []

    def test_char_cant_create_lists_with_empty_string(self):
        with pytest.raises(ValueError):
            BigCharListModel.objects.create(field=[""])

    def test_char_cant_create_sets_with_commas(self):
        with pytest.raises(ValueError):
            BigCharListModel.objects.create(field=["co,mma", "contained"])

    def test_char_basic_lookup(self):
        mymodel = BigCharListModel.objects.create()
        empty = BigCharListModel.objects.filter(field="")

        assert empty.count() == 1
        assert empty[0] == mymodel

        mymodel.delete()

        assert empty.count() == 0

    def test_char_lookup_contains(self):
        self.check_char_lookup('contains')

    def test_char_lookup_icontains(self):
        self.check_char_lookup('icontains')

    def check_char_lookup(self, lookup):
        lname = 'field__' + lookup
        mymodel = BigCharListModel.objects.create(field=["mouldy", "rotten"])

        mouldy = BigCharListModel.objects.filter(**{lname: "mouldy"})
        assert mouldy.count() == 1
        assert mouldy[0] == mymodel

        rotten = BigCharListModel.objects.filter(**{lname: "rotten"})
        assert rotten.count() == 1
        assert rotten[0] == mymodel

        clean = BigCharListModel.objects.filter(**{lname: "clean"})
        assert clean.count() == 0

        with pytest.raises(ValueError):
            list(BigCharListModel.objects.filter(**{lname: ["a", "b"]}))

        both = BigCharListModel.objects.filter(
            Q(**{lname: "mouldy"}) & Q(**{lname: "rotten"}),
        )
        assert both.count() == 1
        assert both[0] == mymodel

        either = BigCharListModel.objects.filter(
            Q(**{lname: "mouldy"}) | Q(**{lname: "clean"}),
        )
        assert either.count() == 1

        not_clean = BigCharListModel.objects.exclude(**{lname: "clean"})
        assert not_clean.count() == 1

        not_mouldy = BigCharListModel.objects.exclude(**{lname: "mouldy"})
        assert not_mouldy.count() == 0

    def test_char_len_lookup_empty(self):
        mymodel = BigCharListModel.objects.create(field=[])

        empty = BigCharListModel.objects.filter(field__len=0)
        assert empty.count() == 1
        assert empty[0] == mymodel

        one = BigCharListModel.objects.filter(field__len=1)
        assert one.count() == 0

        one_or_more = BigCharListModel.objects.filter(field__len__gte=0)
        assert one_or_more.count() == 1

    def test_char_len_lookup(self):
        mymodel = BigCharListModel.objects.create(field=["red", "expensive"])

        empty = BigCharListModel.objects.filter(field__len=0)
        assert empty.count() == 0

        one_or_more = BigCharListModel.objects.filter(field__len__gte=1)
        assert one_or_more.count() == 1
        assert one_or_more[0] == mymodel

        two = BigCharListModel.objects.filter(field__len=2)
        assert two.count() == 1
        assert two[0] == mymodel

        three = BigCharListModel.objects.filter(field__len=3)
        assert three.count() == 0

    def test_char_position_lookup(self):
        mymodel = BigCharListModel.objects.create(field=["red", "blue"])

        blue0 = BigCharListModel.objects.filter(field__0="blue")
        assert blue0.count() == 0

        red0 = BigCharListModel.objects.filter(field__0="red")
        assert list(red0) == [mymodel]

        red0_red1 = BigCharListModel.objects.filter(field__0="red",
                                                    field__1="red")
        assert red0_red1.count() == 0

        red0_blue1 = BigCharListModel.objects.filter(field__0="red",
                                                     field__1="blue")
        assert list(red0_blue1) == [mymodel]

        red0_or_blue0 = BigCharListModel.objects.filter(
            Q(field__0="red") | Q(field__0="blue"),
        )
        assert list(red0_or_blue0) == [mymodel]

    def test_int_easy(self):
        mymodel = BigIntListModel.objects.create(field=[1, 2])
        assert mymodel.field == [1, 2]
        mymodel = BigIntListModel.objects.get(id=mymodel.id)
        assert mymodel.field == [1, 2]

    def test_int_contains_lookup(self):
        onetwo = BigIntListModel.objects.create(field=[1, 2])

        ones = BigIntListModel.objects.filter(field__contains=1)
        assert ones.count() == 1
        assert ones[0] == onetwo

        twos = BigIntListModel.objects.filter(field__contains=2)
        assert twos.count() == 1
        assert twos[0] == onetwo

        threes = BigIntListModel.objects.filter(field__contains=3)
        assert threes.count() == 0

        with pytest.raises(ValueError):
            list(BigIntListModel.objects.filter(field__contains=[1, 2]))

        ones_and_twos = BigIntListModel.objects.filter(
            Q(field__contains=1) & Q(field__contains=2),
        )
        assert ones_and_twos.count() == 1
        assert ones_and_twos[0] == onetwo

        ones_and_threes = BigIntListModel.objects.filter(
            Q(field__contains=1) & Q(field__contains=3),
        )
        assert ones_and_threes.count() == 0

        ones_or_threes = BigIntListModel.objects.filter(
            Q(field__contains=1) | Q(field__contains=3),
        )
        assert ones_or_threes.count() == 1

        no_three = BigIntListModel.objects.exclude(field__contains=3)
        assert no_three.count() == 1

        no_one = BigIntListModel.objects.exclude(field__contains=1)
        assert no_one.count() == 0

    def test_int_position_lookup(self):
        onetwo = BigIntListModel.objects.create(field=[1, 2])

        one0 = BigIntListModel.objects.filter(field__0=1)
        assert list(one0) == [onetwo]

        two0 = BigIntListModel.objects.filter(field__0=2)
        assert two0.count() == 0

        one0two1 = BigIntListModel.objects.filter(field__0=1, field__1=2)
        assert list(one0two1) == [onetwo]


class TestValidation(SimpleTestCase):

    def test_max_length(self):
        field = ListTextField(
            models.CharField(max_length=32),
            size=3,
            max_length=32,
        )

        field.clean({'a', 'b', 'c'}, None)

        with pytest.raises(exceptions.ValidationError) as excinfo:
            field.clean({'a', 'b', 'c', 'd'}, None)
        assert (
            excinfo.value.messages[0] ==
            'List contains 4 items, it should contain no more than 3.'
        )


class TestCheck(SimpleTestCase):

    def test_field_checks(self):
        class InvalidListTextModel1(TemporaryModel):
            field = ListTextField(models.CharField(), max_length=32)

        errors = InvalidListTextModel1.check(actually_check=True)
        assert len(errors) == 1
        assert errors[0].id == 'django_mysql.E004'
        assert 'Base field for list has errors' in errors[0].msg
        assert 'max_length' in errors[0].msg

    def test_invalid_base_fields(self):
        class InvalidListTextModel2(TemporaryModel):
            field = ListTextField(
                models.ForeignKey('testapp.Author', on_delete=models.CASCADE),
                max_length=32,
            )

        errors = InvalidListTextModel2.check(actually_check=True)
        assert len(errors) == 1
        assert errors[0].id == 'django_mysql.E005'
        assert 'Base field for list must be' in errors[0].msg


class ListTextFieldSubclass(ListTextField):
    """
    Used below, has a different path for deconstruct()
    """


class TestDeconstruct(TestCase):

    def test_deconstruct(self):
        field = ListTextField(models.IntegerField(), max_length=32)
        name, path, args, kwargs = field.deconstruct()
        new = ListTextField(*args, **kwargs)
        assert new.base_field.__class__ == field.base_field.__class__

    def test_deconstruct_with_size(self):
        field = ListTextField(models.IntegerField(), size=3, max_length=32)
        name, path, args, kwargs = field.deconstruct()
        new = ListTextField(*args, **kwargs)
        assert new.size == field.size

    def test_deconstruct_args(self):
        field = ListTextField(models.CharField(max_length=5), max_length=32)
        name, path, args, kwargs = field.deconstruct()
        new = ListTextField(*args, **kwargs)
        assert new.base_field.max_length == field.base_field.max_length

    def test_bad_import_deconstruct(self):
        from django_mysql.models.fields import ListTextField as LTField
        field = LTField(models.IntegerField())
        name, path, args, kwargs = field.deconstruct()
        assert path == 'django_mysql.models.ListTextField'

    def test_bad_import2_deconstruct(self):
        from django_mysql.models.fields.lists import ListTextField as LTField
        field = LTField(models.IntegerField())
        name, path, args, kwargs = field.deconstruct()
        assert path == 'django_mysql.models.ListTextField'

    def test_subclass_deconstruct(self):
        field = ListTextFieldSubclass(models.IntegerField())
        name, path, args, kwargs = field.deconstruct()
        assert path == 'tests.testapp.test_listtextfield.ListTextFieldSubclass'


class TestMigrationWriter(TestCase):

    def test_makemigrations(self):
        field = ListTextField(models.CharField(max_length=5), max_length=32)
        statement, imports = MigrationWriter.serialize(field)

        # The order of the output max_length/size statements varies by
        # python version, hence a little regexp to match them
        assert re.compile(
            r"""^django_mysql\.models\.ListTextField\(
                models\.CharField\(max_length=5\),\ # space here
                (
                    max_length=32,\ size=None|
                    size=None,\ max_length=32
                )
                \)$
            """,
            re.VERBOSE,
        ).match(statement)

    def test_makemigrations_with_size(self):
        field = ListTextField(
            models.CharField(max_length=5),
            max_length=32,
            size=5,
        )
        statement, imports = MigrationWriter.serialize(field)

        # The order of the output max_length/size statements varies by
        # python version, hence a little regexp to match them
        assert re.compile(
            r"""^django_mysql\.models\.ListTextField\(
                models\.CharField\(max_length=5\),\ # space here
                (
                    max_length=32,\ size=5|
                    size=5,\ max_length=32
                )
                \)$
            """,
            re.VERBOSE,
        ).match(statement)


class TestSerialization(SimpleTestCase):

    def test_dumping(self):
        instance = BigCharListModel(field=["big", "comfy"])
        data = json.loads(serializers.serialize('json', [instance]))[0]
        field = data['fields']['field']
        assert sorted(field.split(',')) == ["big", "comfy"]

    def test_loading(self):
        test_data = '''
            [{"fields": {"field": "big,leather,comfy"},
             "model": "testapp.BigCharListModel", "pk": null}]
        '''
        objs = list(serializers.deserialize('json', test_data))
        instance = objs[0].object
        assert instance.field == ["big", "leather", "comfy"]

    def test_dumping_loading_empty(self):
        instance = BigCharListModel(field=[])
        data = serializers.serialize('json', [instance])
        objs = list(serializers.deserialize('json', data))
        instance = objs[0].object
        assert instance.field == []


class TestDescription(SimpleTestCase):

    def test_char(self):
        field = ListTextField(models.CharField(max_length=5), max_length=32)
        assert field.description == "List of String (up to %(max_length)s)"

    def test_int(self):
        field = ListTextField(models.IntegerField(), max_length=32)
        assert field.description == "List of Integer"


class TestFormField(SimpleTestCase):

    def test_model_field_formfield(self):
        model_field = ListTextField(models.CharField(max_length=27))
        form_field = model_field.formfield()
        assert isinstance(form_field, SimpleListField)
        assert isinstance(form_field.base_field, forms.CharField)
        assert form_field.base_field.max_length == 27

    def test_model_field_formfield_size(self):
        model_field = ListTextField(models.IntegerField(), size=4)
        form_field = model_field.formfield()
        assert isinstance(form_field, SimpleListField)
        assert form_field.max_length == 4
