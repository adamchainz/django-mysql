# -*- coding:utf-8 -*-
import json
import re

from django import forms
from django.core import exceptions, serializers
from django.core.management import call_command
from django.db import models, connection
from django.db.models import Q
from django.db.migrations.writer import MigrationWriter
from django.test import TestCase, override_settings

from django_mysql.models import SetCharField
from django_mysql.forms import SimpleSetField

from django_mysql_tests.models import (
    CharSetModel, CharSetDefaultModel, IntSetModel
)


class TestSaveLoad(TestCase):

    def test_char_easy(self):
        s = CharSetModel.objects.create(field={"big", "comfy"})
        self.assertSetEqual(s.field, {"comfy", "big"})
        s = CharSetModel.objects.get(id=s.id)
        self.assertSetEqual(s.field, {"comfy", "big"})

    def test_char_cant_create_sets_with_commas(self):
        with self.assertRaises(ValueError):
            CharSetModel.objects.create(field={"co,mma", "contained"})

    def test_char_contains_lookup(self):
        mymodel = CharSetModel.objects.create(field={"mouldy", "rotten"})

        mouldy = CharSetModel.objects.filter(field__contains="mouldy")
        self.assertEqual(mouldy.count(), 1)
        self.assertEqual(mouldy[0], mymodel)

        rotten = CharSetModel.objects.filter(field__contains="rotten")
        self.assertEqual(rotten.count(), 1)
        self.assertEqual(rotten[0], mymodel)

        clean = CharSetModel.objects.filter(field__contains="clean")
        self.assertEqual(clean.count(), 0)

        with self.assertRaises(ValueError):
            list(CharSetModel.objects.filter(field__contains={"a", "b"}))

        both = CharSetModel.objects.filter(
            Q(field__contains="mouldy") & Q(field__contains="rotten")
        )
        self.assertEqual(both.count(), 1)
        self.assertEqual(both[0], mymodel)

        either = CharSetModel.objects.filter(
            Q(field__contains="mouldy") | Q(field__contains="clean")
        )
        self.assertEqual(either.count(), 1)

        not_clean = CharSetModel.objects.exclude(field__contains="clean")
        self.assertEqual(not_clean.count(), 1)

        not_mouldy = CharSetModel.objects.exclude(field__contains="mouldy")
        self.assertEqual(not_mouldy.count(), 0)

    def test_char_len_lookup_empty(self):
        mymodel = CharSetModel.objects.create(field=set())

        empty = CharSetModel.objects.filter(field__len=0)
        self.assertEqual(empty.count(), 1)
        self.assertEqual(empty[0], mymodel)

        one = CharSetModel.objects.filter(field__len=1)
        self.assertEqual(one.count(), 0)

        one_or_more = CharSetModel.objects.filter(field__len__gte=0)
        self.assertEqual(one_or_more.count(), 1)

    def test_char_len_lookup(self):
        mymodel = CharSetModel.objects.create(field={"red", "expensive"})

        empty = CharSetModel.objects.filter(field__len=0)
        self.assertEqual(empty.count(), 0)

        one_or_more = CharSetModel.objects.filter(field__len__gte=1)
        self.assertEqual(one_or_more.count(), 1)
        self.assertEqual(one_or_more[0], mymodel)

        two = CharSetModel.objects.filter(field__len=2)
        self.assertEqual(two.count(), 1)
        self.assertEqual(two[0], mymodel)

        three = CharSetModel.objects.filter(field__len=3)
        self.assertEqual(three.count(), 0)

    def test_char_default(self):
        mymodel = CharSetDefaultModel.objects.create()
        self.assertEqual(mymodel.field, {"a", "d"})

        mymodel = CharSetDefaultModel.objects.get(id=mymodel.id)
        self.assertEqual(mymodel.field, {"a", "d"})

    def test_int_easy(self):
        mymodel = IntSetModel.objects.create(field={1, 2})
        self.assertSetEqual(mymodel.field, {1, 2})
        mymodel = IntSetModel.objects.get(id=mymodel.id)
        self.assertSetEqual(mymodel.field, {1, 2})

    def test_int_contains_lookup(self):
        onetwo = IntSetModel.objects.create(field={1, 2})

        ones = IntSetModel.objects.filter(field__contains=1)
        self.assertEqual(ones.count(), 1)
        self.assertEqual(ones[0], onetwo)

        twos = IntSetModel.objects.filter(field__contains=2)
        self.assertEqual(twos.count(), 1)
        self.assertEqual(twos[0], onetwo)

        threes = IntSetModel.objects.filter(field__contains=3)
        self.assertEqual(threes.count(), 0)

        with self.assertRaises(ValueError):
            list(IntSetModel.objects.filter(field__contains={1, 2}))

        ones_and_twos = IntSetModel.objects.filter(
            Q(field__contains=1) & Q(field__contains=2)
        )
        self.assertEqual(ones_and_twos.count(), 1)
        self.assertEqual(ones_and_twos[0], onetwo)

        ones_and_threes = IntSetModel.objects.filter(
            Q(field__contains=1) & Q(field__contains=3)
        )
        self.assertEqual(ones_and_threes.count(), 0)

        ones_or_threes = IntSetModel.objects.filter(
            Q(field__contains=1) | Q(field__contains=3)
        )
        self.assertEqual(ones_or_threes.count(), 1)

        no_three = IntSetModel.objects.exclude(field__contains=3)
        self.assertEqual(no_three.count(), 1)

        no_one = IntSetModel.objects.exclude(field__contains=1)
        self.assertEqual(no_one.count(), 0)


class TestValidation(TestCase):

    def test_max_length(self):
        field = SetCharField(
            models.CharField(max_length=32),
            size=3,
            max_length=32
        )

        field.clean({'a', 'b', 'c'}, None)

        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean({'a', 'b', 'c', 'd'}, None)
        self.assertEqual(
            cm.exception.messages[0],
            'Set contains 4 items, it should contain no more than 3.'
        )


class TestCheck(TestCase):

    def test_field_checks(self):
        field = SetCharField(models.CharField(), max_length=32)
        field.set_attributes_from_name('field')
        errors = field.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'django_mysql.E001')

    def test_invalid_base_fields(self):
        field = SetCharField(
            models.ForeignKey('django_mysql_tests.Author'),
            max_length=32
        )
        field.set_attributes_from_name('field')
        errors = field.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'django_mysql.E002')

    def test_max_length_including_base(self):
        field = SetCharField(
            models.CharField(max_length=32),
            size=2, max_length=32)
        field.set_attributes_from_name('field')
        errors = field.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'django_mysql.E003')


class TestMigrations(TestCase):

    def test_deconstruct(self):
        field = SetCharField(models.IntegerField(), max_length=32)
        name, path, args, kwargs = field.deconstruct()
        new = SetCharField(*args, **kwargs)
        self.assertEqual(type(new.base_field), type(field.base_field))

    def test_deconstruct_with_size(self):
        field = SetCharField(models.IntegerField(), size=3, max_length=32)
        name, path, args, kwargs = field.deconstruct()
        new = SetCharField(*args, **kwargs)
        self.assertEqual(new.size, field.size)

    def test_deconstruct_args(self):
        field = SetCharField(models.CharField(max_length=5), max_length=32)
        name, path, args, kwargs = field.deconstruct()
        new = SetCharField(*args, **kwargs)
        self.assertEqual(
            new.base_field.max_length,
            field.base_field.max_length
        )

    def test_makemigrations(self):
        field = SetCharField(models.CharField(max_length=5), max_length=32)
        statement, imports = MigrationWriter.serialize(field)

        # The order of the output max_length/size statements varies by
        # python version, hence a little regexp to match them
        self.assertRegexpMatches(
            statement,
            re.compile(
                r"""^django_mysql\.models\.SetCharField\(
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
        field = SetCharField(
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
                r"""^django_mysql\.models\.SetCharField\(
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

    @override_settings(MIGRATION_MODULES={
        "django_mysql_tests": "django_mysql_tests.set_default_migrations",
    })
    def test_adding_field_with_default(self):
        table_name = 'django_mysql_tests_intsetdefaultmodel'
        with connection.cursor() as cursor:
            self.assertNotIn(
                table_name,
                connection.introspection.table_names(cursor)
            )

        call_command('migrate', 'django_mysql_tests', verbosity=0)
        with connection.cursor() as cursor:
            self.assertIn(
                table_name,
                connection.introspection.table_names(cursor)
            )

        call_command('migrate', 'django_mysql_tests', 'zero', verbosity=0)
        with connection.cursor() as cursor:
            self.assertNotIn(
                table_name,
                connection.introspection.table_names(cursor)
            )


class TestSerialization(TestCase):

    def test_dumping(self):
        instance = CharSetModel(field={"big", "comfy"})
        data = json.loads(serializers.serialize('json', [instance]))[0]
        field = data['fields']['field']
        self.assertEqual(sorted(field.split(',')), ["big", "comfy"])

    def test_loading(self):
        test_data = '''
            [{"fields": {"field": "big,leather,comfy"},
             "model": "django_mysql_tests.CharSetModel", "pk": null}]
        '''
        objs = list(serializers.deserialize('json', test_data))
        instance = objs[0].object
        self.assertEqual(instance.field, set(["big", "leather", "comfy"]))


class TestFormField(TestCase):

    def test_model_field_formfield(self):
        model_field = SetCharField(models.CharField(max_length=27))
        form_field = model_field.formfield()
        self.assertIsInstance(form_field, SimpleSetField)
        self.assertIsInstance(form_field.base_field, forms.CharField)
        self.assertEqual(form_field.base_field.max_length, 27)

    def test_model_field_formfield_size(self):
        model_field = SetCharField(models.CharField(max_length=27), size=4)
        form_field = model_field.formfield()
        self.assertIsInstance(form_field, SimpleSetField)
        self.assertEqual(form_field.max_length, 4)
