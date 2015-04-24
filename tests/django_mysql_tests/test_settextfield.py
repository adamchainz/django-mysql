# -*- coding:utf-8 -*-
import json

from django import forms
from django.core import exceptions, serializers
from django.db import models
from django.db.migrations.writer import MigrationWriter
from django.db.models import Q
from django.utils import six
from django.test import TestCase

import ddt

from django_mysql.forms import SimpleSetField
from django_mysql.models import SetTextField

from django_mysql_tests.models import BigCharSetModel, BigIntSetModel


@ddt.ddt
class TestSaveLoad(TestCase):

    def test_char_easy(self):
        big_set = {six.text_type(i ** 2) for i in six.moves.range(1000)}
        s = BigCharSetModel.objects.create(field=big_set)
        self.assertSetEqual(s.field, big_set)
        s = BigCharSetModel.objects.get(id=s.id)
        self.assertSetEqual(s.field, big_set)

        letters = set('abcdefghi')
        bigger_set = big_set | letters
        s.field.update(letters)
        self.assertEqual(s.field, bigger_set)
        s.save()
        s = BigCharSetModel.objects.get(id=s.id)
        self.assertEqual(s.field, bigger_set)

    def test_char_string_direct(self):
        big_set = {six.text_type(i ** 2) for i in six.moves.range(1000)}
        big_str = ','.join(big_set)
        s = BigCharSetModel.objects.create(field=big_str)
        s = BigCharSetModel.objects.get(id=s.id)
        self.assertEqual(s.field, big_set)

    def test_is_a_set_immediately(self):
        s = BigCharSetModel()
        self.assertEqual(s.field, set())
        s.field.add("bold")
        s.field.add("brave")
        s.save()
        self.assertEqual(s.field, {"bold", "brave"})
        s = BigCharSetModel.objects.get(id=s.id)
        self.assertEqual(s.field, {"bold", "brave"})

    def test_empty(self):
        s = BigCharSetModel.objects.create()
        self.assertEqual(s.field, set())
        s = BigCharSetModel.objects.get(id=s.id)
        self.assertEqual(s.field, set())

    def test_char_cant_create_sets_with_commas(self):
        with self.assertRaises(ValueError):
            BigCharSetModel.objects.create(field={"co,mma", "contained"})

    def test_char_cant_create_sets_with_empty_string(self):
        with self.assertRaises(ValueError):
            BigCharSetModel.objects.create(field={""})

    def test_char_basic_lookup(self):
        mymodel = BigCharSetModel.objects.create()
        empty = BigCharSetModel.objects.filter(field="")

        self.assertEqual(empty.count(), 1)
        self.assertEqual(empty[0], mymodel)

        mymodel.delete()

        self.assertEqual(empty.count(), 0)

    @ddt.data('contains', 'icontains')
    def test_char_contains_lookup(self, lookup):
        lname = 'field__' + lookup
        mymodel = BigCharSetModel.objects.create(field={"mouldy", "rotten"})

        mouldy = BigCharSetModel.objects.filter(**{lname: "mouldy"})
        self.assertEqual(mouldy.count(), 1)
        self.assertEqual(mouldy[0], mymodel)

        rotten = BigCharSetModel.objects.filter(**{lname: "rotten"})
        self.assertEqual(rotten.count(), 1)
        self.assertEqual(rotten[0], mymodel)

        clean = BigCharSetModel.objects.filter(**{lname: "clean"})
        self.assertEqual(clean.count(), 0)

        with self.assertRaises(ValueError):
            list(BigCharSetModel.objects.filter(**{lname: {"a", "b"}}))

        both = BigCharSetModel.objects.filter(
            Q(**{lname: "mouldy"}) & Q(**{lname: "rotten"})
        )
        self.assertEqual(both.count(), 1)
        self.assertEqual(both[0], mymodel)

        either = BigCharSetModel.objects.filter(
            Q(**{lname: "mouldy"}) | Q(**{lname: "clean"})
        )
        self.assertEqual(either.count(), 1)

        not_clean = BigCharSetModel.objects.exclude(**{lname: "clean"})
        self.assertEqual(not_clean.count(), 1)

        not_mouldy = BigCharSetModel.objects.exclude(**{lname: "mouldy"})
        self.assertEqual(not_mouldy.count(), 0)

    def test_char_len_lookup_empty(self):
        mymodel = BigCharSetModel.objects.create(field=set())

        empty = BigCharSetModel.objects.filter(field__len=0)
        self.assertEqual(empty.count(), 1)
        self.assertEqual(empty[0], mymodel)

        one = BigCharSetModel.objects.filter(field__len=1)
        self.assertEqual(one.count(), 0)

        one_or_more = BigCharSetModel.objects.filter(field__len__gte=0)
        self.assertEqual(one_or_more.count(), 1)

    def test_char_len_lookup(self):
        mymodel = BigCharSetModel.objects.create(field={"red", "expensive"})

        empty = BigCharSetModel.objects.filter(field__len=0)
        self.assertEqual(empty.count(), 0)

        one_or_more = BigCharSetModel.objects.filter(field__len__gte=1)
        self.assertEqual(one_or_more.count(), 1)
        self.assertEqual(one_or_more[0], mymodel)

        two = BigCharSetModel.objects.filter(field__len=2)
        self.assertEqual(two.count(), 1)
        self.assertEqual(two[0], mymodel)

        three = BigCharSetModel.objects.filter(field__len=3)
        self.assertEqual(three.count(), 0)

    def test_int_easy(self):
        big_set = {i ** 2 for i in six.moves.range(1000)}
        mymodel = BigIntSetModel.objects.create(field=big_set)
        self.assertSetEqual(mymodel.field, big_set)
        mymodel = BigIntSetModel.objects.get(id=mymodel.id)
        self.assertSetEqual(mymodel.field, big_set)

    def test_int_contains_lookup(self):
        onetwo = BigIntSetModel.objects.create(field={1, 2})

        ones = BigIntSetModel.objects.filter(field__contains=1)
        self.assertEqual(ones.count(), 1)
        self.assertEqual(ones[0], onetwo)

        twos = BigIntSetModel.objects.filter(field__contains=2)
        self.assertEqual(twos.count(), 1)
        self.assertEqual(twos[0], onetwo)

        threes = BigIntSetModel.objects.filter(field__contains=3)
        self.assertEqual(threes.count(), 0)

        with self.assertRaises(ValueError):
            list(BigIntSetModel.objects.filter(field__contains={1, 2}))

        ones_and_twos = BigIntSetModel.objects.filter(
            Q(field__contains=1) & Q(field__contains=2)
        )
        self.assertEqual(ones_and_twos.count(), 1)
        self.assertEqual(ones_and_twos[0], onetwo)

        ones_and_threes = BigIntSetModel.objects.filter(
            Q(field__contains=1) & Q(field__contains=3)
        )
        self.assertEqual(ones_and_threes.count(), 0)

        ones_or_threes = BigIntSetModel.objects.filter(
            Q(field__contains=1) | Q(field__contains=3)
        )
        self.assertEqual(ones_or_threes.count(), 1)

        no_three = BigIntSetModel.objects.exclude(field__contains=3)
        self.assertEqual(no_three.count(), 1)

        no_one = BigIntSetModel.objects.exclude(field__contains=1)
        self.assertEqual(no_one.count(), 0)


class TestValidation(TestCase):

    def test_max_length(self):
        field = SetTextField(models.CharField(max_length=32), size=3)

        field.clean({'a', 'b', 'c'}, None)

        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean({'a', 'b', 'c', 'd'}, None)
        self.assertEqual(
            cm.exception.messages[0],
            'Set contains 4 items, it should contain no more than 3.'
        )


class TestCheck(TestCase):

    def test_field_checks(self):
        field = SetTextField(models.CharField())
        field.set_attributes_from_name('field')
        errors = field.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'django_mysql.E001')
        self.assertIn('Base field for set has errors', errors[0].msg)
        self.assertIn('max_length', errors[0].msg)

    def test_invalid_base_fields(self):
        field = SetTextField(models.ForeignKey('django_mysql_tests.Author'))
        field.set_attributes_from_name('field')
        errors = field.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'django_mysql.E002')
        self.assertIn('Base field for set must be', errors[0].msg)


class TestMigrations(TestCase):

    def test_deconstruct(self):
        field = SetTextField(models.IntegerField(), max_length=32)
        name, path, args, kwargs = field.deconstruct()
        new = SetTextField(*args, **kwargs)
        self.assertEqual(type(new.base_field), type(field.base_field))

    def test_deconstruct_with_size(self):
        field = SetTextField(models.IntegerField(), size=3, max_length=32)
        name, path, args, kwargs = field.deconstruct()
        new = SetTextField(*args, **kwargs)
        self.assertEqual(new.size, field.size)

    def test_deconstruct_args(self):
        field = SetTextField(models.CharField(max_length=5), max_length=32)
        name, path, args, kwargs = field.deconstruct()
        new = SetTextField(*args, **kwargs)
        self.assertEqual(
            new.base_field.max_length,
            field.base_field.max_length
        )

    def test_makemigrations(self):
        field = SetTextField(models.CharField(max_length=5))
        statement, imports = MigrationWriter.serialize(field)

        self.assertEqual(
            statement,
            "django_mysql.models.SetTextField("
            "models.CharField(max_length=5), "
            "size=None"
            ")"
        )

    def test_makemigrations_with_size(self):
        field = SetTextField(models.CharField(max_length=5), size=5)
        statement, imports = MigrationWriter.serialize(field)

        self.assertEqual(
            statement,
            "django_mysql.models.SetTextField("
            "models.CharField(max_length=5), "
            "size=5"
            ")"
        )


class TestSerialization(TestCase):

    def test_dumping(self):
        big_set = {six.text_type(i ** 2) for i in six.moves.range(1000)}
        instance = BigCharSetModel(field=big_set)
        data = json.loads(serializers.serialize('json', [instance]))[0]
        field = data['fields']['field']
        self.assertEqual(sorted(field.split(',')), sorted(big_set))

    def test_loading(self):
        test_data = '''
            [{"fields": {"field": "big,leather,comfy"},
             "model": "django_mysql_tests.BigCharSetModel", "pk": null}]
        '''
        objs = list(serializers.deserialize('json', test_data))
        instance = objs[0].object
        self.assertEqual(instance.field, {"big", "leather", "comfy"})


class TestDescription(TestCase):

    def test_char(self):
        field = SetTextField(models.CharField(max_length=5), max_length=32)
        self.assertEqual(
            field.description,
            "Set of String (up to %(max_length)s)"
        )

    def test_int(self):
        field = SetTextField(models.IntegerField(), max_length=32)
        self.assertEqual(field.description, "Set of Integer")


class TestFormField(TestCase):

    def test_model_field_formfield(self):
        model_field = SetTextField(models.CharField(max_length=27))
        form_field = model_field.formfield()
        self.assertIsInstance(form_field, SimpleSetField)
        self.assertIsInstance(form_field.base_field, forms.CharField)
        self.assertEqual(form_field.base_field.max_length, 27)

    def test_model_field_formfield_size(self):
        model_field = SetTextField(models.IntegerField(), size=400)
        form_field = model_field.formfield()
        self.assertIsInstance(form_field, SimpleSetField)
        self.assertEqual(form_field.max_length, 400)
