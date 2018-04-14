# -*- coding:utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)

import json

import pytest
from django import forms
from django.core import exceptions, serializers
from django.db import models
from django.db.migrations.writer import MigrationWriter
from django.db.models import Q
from django.test import SimpleTestCase, TestCase
from django.utils import six

from django_mysql.forms import SimpleSetField
from django_mysql.models import SetTextField
from testapp.models import BigCharSetModel, BigIntSetModel, TemporaryModel


class TestSaveLoad(TestCase):

    def test_char_easy(self):
        big_set = {six.text_type(i ** 2) for i in six.moves.range(1000)}
        s = BigCharSetModel.objects.create(field=big_set)
        assert s.field == big_set
        s = BigCharSetModel.objects.get(id=s.id)
        assert s.field == big_set

        letters = set('abcdefghi')
        bigger_set = big_set | letters
        s.field.update(letters)
        assert s.field == bigger_set
        s.save()
        s = BigCharSetModel.objects.get(id=s.id)
        assert s.field == bigger_set

    def test_char_string_direct(self):
        big_set = {six.text_type(i ** 2) for i in six.moves.range(1000)}
        big_str = ','.join(big_set)
        s = BigCharSetModel.objects.create(field=big_str)
        s = BigCharSetModel.objects.get(id=s.id)
        assert s.field == big_set

    def test_is_a_set_immediately(self):
        s = BigCharSetModel()
        assert s.field == set()
        s.field.add("bold")
        s.field.add("brave")
        s.save()
        assert s.field == {"bold", "brave"}
        s = BigCharSetModel.objects.get(id=s.id)
        assert s.field == {"bold", "brave"}

    def test_empty(self):
        s = BigCharSetModel.objects.create()
        assert s.field == set()
        s = BigCharSetModel.objects.get(id=s.id)
        assert s.field == set()

    def test_char_cant_create_sets_with_commas(self):
        with pytest.raises(ValueError):
            BigCharSetModel.objects.create(field={"co,mma", "contained"})

    def test_char_cant_create_sets_with_empty_string(self):
        with pytest.raises(ValueError):
            BigCharSetModel.objects.create(field={""})

    def test_char_basic_lookup(self):
        mymodel = BigCharSetModel.objects.create()
        empty = BigCharSetModel.objects.filter(field="")

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
        mymodel = BigCharSetModel.objects.create(field={"mouldy", "rotten"})

        mouldy = BigCharSetModel.objects.filter(**{lname: "mouldy"})
        assert mouldy.count() == 1
        assert mouldy[0] == mymodel

        rotten = BigCharSetModel.objects.filter(**{lname: "rotten"})
        assert rotten.count() == 1
        assert rotten[0] == mymodel

        clean = BigCharSetModel.objects.filter(**{lname: "clean"})
        assert clean.count() == 0

        with pytest.raises(ValueError):
            list(BigCharSetModel.objects.filter(**{lname: {"a", "b"}}))

        both = BigCharSetModel.objects.filter(
            Q(**{lname: "mouldy"}) & Q(**{lname: "rotten"}),
        )
        assert both.count() == 1
        assert both[0] == mymodel

        either = BigCharSetModel.objects.filter(
            Q(**{lname: "mouldy"}) | Q(**{lname: "clean"}),
        )
        assert either.count() == 1

        not_clean = BigCharSetModel.objects.exclude(**{lname: "clean"})
        assert not_clean.count() == 1

        not_mouldy = BigCharSetModel.objects.exclude(**{lname: "mouldy"})
        assert not_mouldy.count() == 0

    def test_char_len_lookup_empty(self):
        mymodel = BigCharSetModel.objects.create(field=set())

        empty = BigCharSetModel.objects.filter(field__len=0)
        assert empty.count() == 1
        assert empty[0] == mymodel

        one = BigCharSetModel.objects.filter(field__len=1)
        assert one.count() == 0

        one_or_more = BigCharSetModel.objects.filter(field__len__gte=0)
        assert one_or_more.count() == 1

    def test_char_len_lookup(self):
        mymodel = BigCharSetModel.objects.create(field={"red", "expensive"})

        empty = BigCharSetModel.objects.filter(field__len=0)
        assert empty.count() == 0

        one_or_more = BigCharSetModel.objects.filter(field__len__gte=1)
        assert one_or_more.count() == 1
        assert one_or_more[0] == mymodel

        two = BigCharSetModel.objects.filter(field__len=2)
        assert two.count() == 1
        assert two[0] == mymodel

        three = BigCharSetModel.objects.filter(field__len=3)
        assert three.count() == 0

    def test_int_easy(self):
        big_set = {i ** 2 for i in six.moves.range(1000)}
        mymodel = BigIntSetModel.objects.create(field=big_set)
        assert mymodel.field == big_set
        mymodel = BigIntSetModel.objects.get(id=mymodel.id)
        assert mymodel.field == big_set

    def test_int_contains_lookup(self):
        onetwo = BigIntSetModel.objects.create(field={1, 2})

        ones = BigIntSetModel.objects.filter(field__contains=1)
        assert ones.count() == 1
        assert ones[0] == onetwo

        twos = BigIntSetModel.objects.filter(field__contains=2)
        assert twos.count() == 1
        assert twos[0] == onetwo

        threes = BigIntSetModel.objects.filter(field__contains=3)
        assert threes.count() == 0

        with pytest.raises(ValueError):
            list(BigIntSetModel.objects.filter(field__contains={1, 2}))

        ones_and_twos = BigIntSetModel.objects.filter(
            Q(field__contains=1) & Q(field__contains=2),
        )
        assert ones_and_twos.count() == 1
        assert ones_and_twos[0] == onetwo

        ones_and_threes = BigIntSetModel.objects.filter(
            Q(field__contains=1) & Q(field__contains=3),
        )
        assert ones_and_threes.count() == 0

        ones_or_threes = BigIntSetModel.objects.filter(
            Q(field__contains=1) | Q(field__contains=3),
        )
        assert ones_or_threes.count() == 1

        no_three = BigIntSetModel.objects.exclude(field__contains=3)
        assert no_three.count() == 1

        no_one = BigIntSetModel.objects.exclude(field__contains=1)
        assert no_one.count() == 0


class TestValidation(SimpleTestCase):

    def test_max_length(self):
        field = SetTextField(models.CharField(max_length=32), size=3)

        field.clean({'a', 'b', 'c'}, None)

        with pytest.raises(exceptions.ValidationError) as excinfo:
            field.clean({'a', 'b', 'c', 'd'}, None)
        assert (
            excinfo.value.messages[0] ==
            'Set contains 4 items, it should contain no more than 3.'
        )


class TestCheck(SimpleTestCase):

    def test_model_set(self):
        field = BigIntSetModel._meta.get_field('field')
        assert field.model == BigIntSetModel
        # I think this is a side effect of migrations being run in tests -
        # the base_field.model is the __fake__ model
        assert field.base_field.model.__name__ == 'BigIntSetModel'

    def test_base_field_checks(self):
        class InvalidSetTextModel1(TemporaryModel):
            field = SetTextField(models.CharField())

        errors = InvalidSetTextModel1.check(actually_check=True)
        assert len(errors) == 1
        assert errors[0].id == 'django_mysql.E001'
        assert 'Base field for set has errors' in errors[0].msg
        assert 'max_length' in errors[0].msg

    def test_invalid_base_fields(self):
        class InvalidSetTextModel2(TemporaryModel):
            field = SetTextField(
                models.ForeignKey('testapp.Author', on_delete=models.CASCADE),
            )

        errors = InvalidSetTextModel2.check(actually_check=True)
        assert len(errors) == 1
        assert errors[0].id == 'django_mysql.E002'
        assert 'Base field for set must be' in errors[0].msg


class SetTextFieldSubclass(SetTextField):
    """
    Used below, has a different path for deconstruct()
    """


class TestDeconstruct(TestCase):

    def test_deconstruct(self):
        field = SetTextField(models.IntegerField(), max_length=32)
        name, path, args, kwargs = field.deconstruct()
        new = SetTextField(*args, **kwargs)
        assert new.base_field.__class__ == field.base_field.__class__

    def test_deconstruct_with_size(self):
        field = SetTextField(models.IntegerField(), size=3, max_length=32)
        name, path, args, kwargs = field.deconstruct()
        new = SetTextField(*args, **kwargs)
        assert new.size == field.size

    def test_deconstruct_args(self):
        field = SetTextField(models.CharField(max_length=5), max_length=32)
        name, path, args, kwargs = field.deconstruct()
        new = SetTextField(*args, **kwargs)
        assert new.base_field.max_length == field.base_field.max_length

    def test_bad_import_deconstruct(self):
        from django_mysql.models.fields import SetTextField as STField
        field = STField(models.IntegerField())
        name, path, args, kwargs = field.deconstruct()
        assert path == 'django_mysql.models.SetTextField'

    def test_bad_import2_deconstruct(self):
        from django_mysql.models.fields.sets import SetTextField as STField
        field = STField(models.IntegerField())
        name, path, args, kwargs = field.deconstruct()
        assert path == 'django_mysql.models.SetTextField'

    def test_subclass_deconstruct(self):
        field = SetTextFieldSubclass(models.IntegerField())
        name, path, args, kwargs = field.deconstruct()
        assert path == 'tests.testapp.test_settextfield.SetTextFieldSubclass'


class TestMigrationWriter(TestCase):

    def test_makemigrations(self):
        field = SetTextField(models.CharField(max_length=5))
        statement, imports = MigrationWriter.serialize(field)

        assert (
            statement ==
            "django_mysql.models.SetTextField("
            "models.CharField(max_length=5), "
            "size=None"
            ")"
        )

    def test_makemigrations_with_size(self):
        field = SetTextField(models.CharField(max_length=5), size=5)
        statement, imports = MigrationWriter.serialize(field)

        assert (
            statement ==
            "django_mysql.models.SetTextField("
            "models.CharField(max_length=5), "
            "size=5"
            ")"
        )


class TestSerialization(SimpleTestCase):

    def test_dumping(self):
        big_set = {six.text_type(i ** 2) for i in six.moves.range(1000)}
        instance = BigCharSetModel(field=big_set)
        data = json.loads(serializers.serialize('json', [instance]))[0]
        field = data['fields']['field']
        assert sorted(field.split(',')) == sorted(big_set)

    def test_loading(self):
        test_data = '''
            [{"fields": {"field": "big,leather,comfy"},
             "model": "testapp.BigCharSetModel", "pk": null}]
        '''
        objs = list(serializers.deserialize('json', test_data))
        instance = objs[0].object
        assert instance.field == {"big", "leather", "comfy"}

    def test_empty(self):
        instance = BigCharSetModel(field=set())
        data = serializers.serialize('json', [instance])
        objs = list(serializers.deserialize('json', data))
        instance = objs[0].object
        assert instance.field == set()


class TestDescription(SimpleTestCase):

    def test_char(self):
        field = SetTextField(models.CharField(max_length=5), max_length=32)
        assert field.description == "Set of String (up to %(max_length)s)"

    def test_int(self):
        field = SetTextField(models.IntegerField(), max_length=32)
        assert field.description == "Set of Integer"


class TestFormField(SimpleTestCase):

    def test_model_field_formfield(self):
        model_field = SetTextField(models.CharField(max_length=27))
        form_field = model_field.formfield()
        assert isinstance(form_field, SimpleSetField)
        assert isinstance(form_field.base_field, forms.CharField)
        assert form_field.base_field.max_length == 27

    def test_model_field_formfield_size(self):
        model_field = SetTextField(models.IntegerField(), size=400)
        form_field = model_field.formfield()
        assert isinstance(form_field, SimpleSetField)
        assert form_field.max_length == 400
