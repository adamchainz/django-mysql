# -*- coding:utf-8 -*-
import json
import re

from django import forms
from django.core import exceptions, serializers
from django.db import models
from django.db.models import Q
from django.db.migrations.writer import MigrationWriter
from django.test import TestCase

import ddt

from django_mysql.models import ListTextField
from django_mysql.forms import SimpleListField

from django_mysql_tests.models import BigCharListModel, BigIntListModel


@ddt.ddt
class TestSaveLoad(TestCase):

    def test_char_easy(self):
        s = BigCharListModel.objects.create(field=["comfy", "big"])
        self.assertEqual(s.field, ["comfy", "big"])
        s = BigCharListModel.objects.get(id=s.id)
        self.assertEqual(s.field, ["comfy", "big"])

        s.field.append("round")
        s.save()
        self.assertEqual(s.field, ["comfy", "big", "round"])
        s = BigCharListModel.objects.get(id=s.id)
        self.assertEqual(s.field, ["comfy", "big", "round"])

    def test_char_string_direct(self):
        s = BigCharListModel.objects.create(field="big,bad")
        s = BigCharListModel.objects.get(id=s.id)
        self.assertEqual(s.field, ['big', 'bad'])

    def test_is_a_list_immediately(self):
        s = BigCharListModel()
        self.assertEqual(s.field, [])
        s.field.append("bold")
        s.field.append("brave")
        s.save()
        self.assertEqual(s.field, ["bold", "brave"])
        s = BigCharListModel.objects.get(id=s.id)
        self.assertEqual(s.field, ["bold", "brave"])

    def test_empty(self):
        s = BigCharListModel.objects.create()
        self.assertEqual(s.field, [])
        s = BigCharListModel.objects.get(id=s.id)
        self.assertEqual(s.field, [])

    def test_char_cant_create_lists_with_empty_string(self):
        with self.assertRaises(ValueError):
            BigCharListModel.objects.create(field=[""])

    def test_char_cant_create_sets_with_commas(self):
        with self.assertRaises(ValueError):
            BigCharListModel.objects.create(field=["co,mma", "contained"])

    def test_char_basic_lookup(self):
        mymodel = BigCharListModel.objects.create()
        empty = BigCharListModel.objects.filter(field="")

        self.assertEqual(empty.count(), 1)
        self.assertEqual(empty[0], mymodel)

        mymodel.delete()

        self.assertEqual(empty.count(), 0)

    @ddt.data('contains', 'icontains')
    def test_char_lookup(self, lookup):
        lname = 'field__' + lookup
        mymodel = BigCharListModel.objects.create(field=["mouldy", "rotten"])

        mouldy = BigCharListModel.objects.filter(**{lname: "mouldy"})
        self.assertEqual(mouldy.count(), 1)
        self.assertEqual(mouldy[0], mymodel)

        rotten = BigCharListModel.objects.filter(**{lname: "rotten"})
        self.assertEqual(rotten.count(), 1)
        self.assertEqual(rotten[0], mymodel)

        clean = BigCharListModel.objects.filter(**{lname: "clean"})
        self.assertEqual(clean.count(), 0)

        with self.assertRaises(ValueError):
            list(BigCharListModel.objects.filter(**{lname: ["a", "b"]}))

        both = BigCharListModel.objects.filter(
            Q(**{lname: "mouldy"}) & Q(**{lname: "rotten"})
        )
        self.assertEqual(both.count(), 1)
        self.assertEqual(both[0], mymodel)

        either = BigCharListModel.objects.filter(
            Q(**{lname: "mouldy"}) | Q(**{lname: "clean"})
        )
        self.assertEqual(either.count(), 1)

        not_clean = BigCharListModel.objects.exclude(**{lname: "clean"})
        self.assertEqual(not_clean.count(), 1)

        not_mouldy = BigCharListModel.objects.exclude(**{lname: "mouldy"})
        self.assertEqual(not_mouldy.count(), 0)

    def test_char_len_lookup_empty(self):
        mymodel = BigCharListModel.objects.create(field=[])

        empty = BigCharListModel.objects.filter(field__len=0)
        self.assertEqual(empty.count(), 1)
        self.assertEqual(empty[0], mymodel)

        one = BigCharListModel.objects.filter(field__len=1)
        self.assertEqual(one.count(), 0)

        one_or_more = BigCharListModel.objects.filter(field__len__gte=0)
        self.assertEqual(one_or_more.count(), 1)

    def test_char_len_lookup(self):
        mymodel = BigCharListModel.objects.create(field=["red", "expensive"])

        empty = BigCharListModel.objects.filter(field__len=0)
        self.assertEqual(empty.count(), 0)

        one_or_more = BigCharListModel.objects.filter(field__len__gte=1)
        self.assertEqual(one_or_more.count(), 1)
        self.assertEqual(one_or_more[0], mymodel)

        two = BigCharListModel.objects.filter(field__len=2)
        self.assertEqual(two.count(), 1)
        self.assertEqual(two[0], mymodel)

        three = BigCharListModel.objects.filter(field__len=3)
        self.assertEqual(three.count(), 0)

    def test_char_position_lookup(self):
        mymodel = BigCharListModel.objects.create(field=["red", "blue"])

        blue0 = BigCharListModel.objects.filter(field__0="blue")
        self.assertEqual(blue0.count(), 0)

        red0 = BigCharListModel.objects.filter(field__0="red")
        self.assertEqual(list(red0), [mymodel])

        red0_red1 = BigCharListModel.objects.filter(field__0="red",
                                                    field__1="red")
        self.assertEqual(red0_red1.count(), 0)

        red0_blue1 = BigCharListModel.objects.filter(field__0="red",
                                                     field__1="blue")
        self.assertEqual(list(red0_blue1), [mymodel])

        red0_or_blue0 = BigCharListModel.objects.filter(
            Q(field__0="red") | Q(field__0="blue")
        )
        self.assertEqual(list(red0_or_blue0), [mymodel])

    def test_int_easy(self):
        mymodel = BigIntListModel.objects.create(field=[1, 2])
        self.assertEqual(mymodel.field, [1, 2])
        mymodel = BigIntListModel.objects.get(id=mymodel.id)
        self.assertEqual(mymodel.field, [1, 2])

    def test_int_contains_lookup(self):
        onetwo = BigIntListModel.objects.create(field=[1, 2])

        ones = BigIntListModel.objects.filter(field__contains=1)
        self.assertEqual(ones.count(), 1)
        self.assertEqual(ones[0], onetwo)

        twos = BigIntListModel.objects.filter(field__contains=2)
        self.assertEqual(twos.count(), 1)
        self.assertEqual(twos[0], onetwo)

        threes = BigIntListModel.objects.filter(field__contains=3)
        self.assertEqual(threes.count(), 0)

        with self.assertRaises(ValueError):
            list(BigIntListModel.objects.filter(field__contains=[1, 2]))

        ones_and_twos = BigIntListModel.objects.filter(
            Q(field__contains=1) & Q(field__contains=2)
        )
        self.assertEqual(ones_and_twos.count(), 1)
        self.assertEqual(ones_and_twos[0], onetwo)

        ones_and_threes = BigIntListModel.objects.filter(
            Q(field__contains=1) & Q(field__contains=3)
        )
        self.assertEqual(ones_and_threes.count(), 0)

        ones_or_threes = BigIntListModel.objects.filter(
            Q(field__contains=1) | Q(field__contains=3)
        )
        self.assertEqual(ones_or_threes.count(), 1)

        no_three = BigIntListModel.objects.exclude(field__contains=3)
        self.assertEqual(no_three.count(), 1)

        no_one = BigIntListModel.objects.exclude(field__contains=1)
        self.assertEqual(no_one.count(), 0)

    def test_int_position_lookup(self):
        onetwo = BigIntListModel.objects.create(field=[1, 2])

        one0 = BigIntListModel.objects.filter(field__0=1)
        self.assertEqual(list(one0), [onetwo])

        two0 = BigIntListModel.objects.filter(field__0=2)
        self.assertEqual(two0.count(), 0)

        one0two1 = BigIntListModel.objects.filter(field__0=1, field__1=2)
        self.assertEqual(list(one0two1), [onetwo])


class TestValidation(TestCase):

    def test_max_length(self):
        field = ListTextField(
            models.CharField(max_length=32),
            size=3,
            max_length=32
        )

        field.clean({'a', 'b', 'c'}, None)

        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean({'a', 'b', 'c', 'd'}, None)
        self.assertEqual(
            cm.exception.messages[0],
            'List contains 4 items, it should contain no more than 3.'
        )


class TestCheck(TestCase):

    def test_field_checks(self):
        field = ListTextField(models.CharField(), max_length=32)
        field.set_attributes_from_name('field')
        errors = field.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'django_mysql.E004')
        self.assertIn('Base field for list has errors', errors[0].msg)
        self.assertIn('max_length', errors[0].msg)

    def test_invalid_base_fields(self):
        field = ListTextField(
            models.ForeignKey('django_mysql_tests.Author'),
            max_length=32
        )
        field.set_attributes_from_name('field')
        errors = field.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'django_mysql.E005')
        self.assertIn('Base field for list must be', errors[0].msg)


class TestMigrations(TestCase):

    def test_deconstruct(self):
        field = ListTextField(models.IntegerField(), max_length=32)
        name, path, args, kwargs = field.deconstruct()
        new = ListTextField(*args, **kwargs)
        self.assertEqual(type(new.base_field), type(field.base_field))

    def test_deconstruct_with_size(self):
        field = ListTextField(models.IntegerField(), size=3, max_length=32)
        name, path, args, kwargs = field.deconstruct()
        new = ListTextField(*args, **kwargs)
        self.assertEqual(new.size, field.size)

    def test_deconstruct_args(self):
        field = ListTextField(models.CharField(max_length=5), max_length=32)
        name, path, args, kwargs = field.deconstruct()
        new = ListTextField(*args, **kwargs)
        self.assertEqual(
            new.base_field.max_length,
            field.base_field.max_length
        )

    def test_makemigrations(self):
        field = ListTextField(models.CharField(max_length=5), max_length=32)
        statement, imports = MigrationWriter.serialize(field)

        # The order of the output max_length/size statements varies by
        # python version, hence a little regexp to match them
        self.assertRegexpMatches(
            statement,
            re.compile(
                r"""^django_mysql\.models\.ListTextField\(
                    models\.CharField\(max_length=5\),\ # space here
                    (
                        max_length=32,\ size=None|
                        size=None,\ max_length=32
                    )
                    \)$
                """,
                re.VERBOSE
            )
        )

    def test_makemigrations_with_size(self):
        field = ListTextField(
            models.CharField(max_length=5),
            max_length=32,
            size=5
        )
        statement, imports = MigrationWriter.serialize(field)

        # The order of the output max_length/size statements varies by
        # python version, hence a little regexp to match them
        self.assertRegexpMatches(
            statement,
            re.compile(
                r"""^django_mysql\.models\.ListTextField\(
                    models\.CharField\(max_length=5\),\ # space here
                    (
                        max_length=32,\ size=5|
                        size=5,\ max_length=32
                    )
                    \)$
                """,
                re.VERBOSE
            )
        )


class TestSerialization(TestCase):

    def test_dumping(self):
        instance = BigCharListModel(field=["big", "comfy"])
        data = json.loads(serializers.serialize('json', [instance]))[0]
        field = data['fields']['field']
        self.assertEqual(sorted(field.split(',')), ["big", "comfy"])

    def test_loading(self):
        test_data = '''
            [{"fields": {"field": "big,leather,comfy"},
             "model": "django_mysql_tests.BigCharListModel", "pk": null}]
        '''
        objs = list(serializers.deserialize('json', test_data))
        instance = objs[0].object
        self.assertEqual(instance.field, ["big", "leather", "comfy"])


class TestDescription(TestCase):

    def test_char(self):
        field = ListTextField(models.CharField(max_length=5), max_length=32)
        self.assertEqual(
            field.description,
            "List of String (up to %(max_length)s)"
        )

    def test_int(self):
        field = ListTextField(models.IntegerField(), max_length=32)
        self.assertEqual(field.description, "List of Integer")


class TestFormField(TestCase):

    def test_model_field_formfield(self):
        model_field = ListTextField(models.CharField(max_length=27))
        form_field = model_field.formfield()
        self.assertIsInstance(form_field, SimpleListField)
        self.assertIsInstance(form_field.base_field, forms.CharField)
        self.assertEqual(form_field.base_field.max_length, 27)

    def test_model_field_formfield_size(self):
        model_field = ListTextField(models.IntegerField(), size=4)
        form_field = model_field.formfield()
        self.assertIsInstance(form_field, SimpleListField)
        self.assertEqual(form_field.max_length, 4)
