# -*- coding:utf-8 -*-
import json
import re
from unittest import skipIf

import django
from django import forms
from django.core import exceptions, serializers
from django.core.management import call_command
from django.db import models, connection
from django.db.models import Q
from django.db.migrations.writer import MigrationWriter
from django.test import TestCase, override_settings

import ddt

from django_mysql.models import SetCharField, SetF
from django_mysql.forms import SimpleSetField
from django_mysql.test.utils import override_mysql_variables

from django_mysql_tests.models import (
    CharSetModel, CharSetDefaultModel, IntSetModel
)


@ddt.ddt
class TestSaveLoad(TestCase):

    def test_char_easy(self):
        s = CharSetModel.objects.create(field={"big", "comfy"})
        self.assertEqual(s.field, {"comfy", "big"})
        s = CharSetModel.objects.get(id=s.id)
        self.assertEqual(s.field, {"comfy", "big"})

        s.field.add("round")
        s.save()
        self.assertEqual(s.field, {"comfy", "big", "round"})
        s = CharSetModel.objects.get(id=s.id)
        self.assertEqual(s.field, {"comfy", "big", "round"})

    def test_char_string_direct(self):
        s = CharSetModel.objects.create(field="big,bad")
        s = CharSetModel.objects.get(id=s.id)
        self.assertEqual(s.field, {'big', 'bad'})

    def test_is_a_set_immediately(self):
        s = CharSetModel()
        self.assertEqual(s.field, set())
        s.field.add("bold")
        s.field.add("brave")
        s.save()
        self.assertEqual(s.field, {"bold", "brave"})
        s = CharSetModel.objects.get(id=s.id)
        self.assertEqual(s.field, {"bold", "brave"})

    def test_empty(self):
        s = CharSetModel.objects.create()
        self.assertEqual(s.field, set())
        s = CharSetModel.objects.get(id=s.id)
        self.assertEqual(s.field, set())

    def test_char_cant_create_sets_with_empty_string(self):
        with self.assertRaises(ValueError):
            CharSetModel.objects.create(field={""})

    def test_char_cant_create_sets_with_commas(self):
        with self.assertRaises(ValueError):
            CharSetModel.objects.create(field={"co,mma", "contained"})

    def test_char_basic_lookup(self):
        mymodel = CharSetModel.objects.create()
        empty = CharSetModel.objects.filter(field="")

        self.assertEqual(empty.count(), 1)
        self.assertEqual(empty[0], mymodel)

        mymodel.delete()

        self.assertEqual(empty.count(), 0)

    @ddt.data('contains', 'icontains')
    def test_char_lookup(self, lookup):
        lname = 'field__' + lookup
        mymodel = CharSetModel.objects.create(field={"mouldy", "rotten"})

        mouldy = CharSetModel.objects.filter(**{lname: "mouldy"})
        self.assertEqual(mouldy.count(), 1)
        self.assertEqual(mouldy[0], mymodel)

        rotten = CharSetModel.objects.filter(**{lname: "rotten"})
        self.assertEqual(rotten.count(), 1)
        self.assertEqual(rotten[0], mymodel)

        clean = CharSetModel.objects.filter(**{lname: "clean"})
        self.assertEqual(clean.count(), 0)

        with self.assertRaises(ValueError):
            list(CharSetModel.objects.filter(**{lname: {"a", "b"}}))

        both = CharSetModel.objects.filter(
            Q(**{lname: "mouldy"}) & Q(**{lname: "rotten"})
        )
        self.assertEqual(both.count(), 1)
        self.assertEqual(both[0], mymodel)

        either = CharSetModel.objects.filter(
            Q(**{lname: "mouldy"}) | Q(**{lname: "clean"})
        )
        self.assertEqual(either.count(), 1)

        not_clean = CharSetModel.objects.exclude(**{lname: "clean"})
        self.assertEqual(not_clean.count(), 1)

        not_mouldy = CharSetModel.objects.exclude(**{lname: "mouldy"})
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
        self.assertEqual(mymodel.field, {1, 2})
        mymodel = IntSetModel.objects.get(id=mymodel.id)
        self.assertEqual(mymodel.field, {1, 2})

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


@skipIf(django.VERSION <= (1, 8),
        "Requires Expressions from Django 1.8+")
class TestSetF(TestCase):

    def test_add_to_none(self):
        CharSetModel.objects.create(field=set())
        CharSetModel.objects.update(field=SetF('field').add('first'))
        model = CharSetModel.objects.get()
        self.assertEqual(model.field, {"first"})

    def test_add_to_one(self):
        CharSetModel.objects.create(field={"big"})
        CharSetModel.objects.update(field=SetF('field').add('bad'))
        model = CharSetModel.objects.get()
        self.assertEqual(model.field, {"big", "bad"})

    def test_add_to_some(self):
        CharSetModel.objects.create(field={"big", "blue"})
        CharSetModel.objects.update(field=SetF('field').add('round'))
        model = CharSetModel.objects.get()
        self.assertEqual(model.field, {"big", "blue", "round"})

    def test_add_to_multiple_objects(self):
        CharSetModel.objects.create(field={"mouse"})
        CharSetModel.objects.create(field={"keyboard"})
        CharSetModel.objects.update(field=SetF('field').add("screen"))
        first, second = tuple(CharSetModel.objects.all())
        self.assertEqual(first.field, {"mouse", "screen"})
        self.assertEqual(second.field, {"keyboard", "screen"})

    def test_add_exists(self):
        CharSetModel.objects.create(field={"nice"})
        CharSetModel.objects.update(field=SetF('field').add("nice"))
        model = CharSetModel.objects.get()
        self.assertEqual(model.field, {"nice"})

    @override_mysql_variables(SQL_MODE="ANSI")
    def test_add_works_in_ansi_mode(self):
        CharSetModel.objects.create()
        CharSetModel.objects.update(field=SetF('field').add('big'))
        CharSetModel.objects.update(field=SetF('field').add('bad'))
        model = CharSetModel.objects.get()
        self.assertEqual(model.field, {"big", "bad"})

    def test_add_assignment(self):
        model = CharSetModel.objects.create(field={"red"})
        model.field = SetF('field').add('blue')
        model.save()
        model = CharSetModel.objects.get()
        self.assertEqual(model.field, {'red', 'blue'})

    def test_remove_one(self):
        CharSetModel.objects.create(field={"dopey", "knifey"})
        CharSetModel.objects.update(field=SetF('field').remove('knifey'))
        model = CharSetModel.objects.get()
        self.assertEqual(model.field, {"dopey"})

    def test_remove_only_one(self):
        CharSetModel.objects.create(field={"pants"})
        CharSetModel.objects.update(field=SetF('field').remove('pants'))
        model = CharSetModel.objects.get()
        self.assertEqual(model.field, set())

    def test_remove_from_none(self):
        CharSetModel.objects.create(field=set())
        CharSetModel.objects.update(field=SetF("field").remove("jam"))
        model = CharSetModel.objects.get()
        self.assertEqual(model.field, set())

    def test_remove_first(self):
        CharSetModel.objects.create()
        CharSetModel.objects.update(field="a,b,c")
        CharSetModel.objects.update(field=SetF('field').remove('a'))
        model = CharSetModel.objects.get()
        self.assertEqual(model.field, {"b", "c"})

    def test_remove_middle(self):
        CharSetModel.objects.create()
        CharSetModel.objects.update(field="a,b,c")
        CharSetModel.objects.update(field=SetF('field').remove('b'))
        model = CharSetModel.objects.get()
        self.assertEqual(model.field, {"a", "c"})

    def test_remove_last(self):
        CharSetModel.objects.create()
        CharSetModel.objects.update(field="a,b,c")
        CharSetModel.objects.update(field=SetF('field').remove('c'))
        model = CharSetModel.objects.get()
        self.assertEqual(model.field, {"a", "b"})

    def test_remove_not_exists(self):
        CharSetModel.objects.create(field={"nice"})
        CharSetModel.objects.update(field=SetF("field").remove("naughty"))
        model = CharSetModel.objects.get()
        self.assertEqual(model.field, {"nice"})

    def test_remove_from_multiple_objects(self):
        CharSetModel.objects.create(field={"mouse", "chair"})
        CharSetModel.objects.create(field={"keyboard", "chair"})
        CharSetModel.objects.update(field=SetF('field').remove("chair"))
        first, second = tuple(CharSetModel.objects.all())
        self.assertEqual(first.field, {"mouse"})
        self.assertEqual(second.field, {"keyboard"})

    @override_mysql_variables(SQL_MODE="ANSI")
    def test_remove_works_in_ansi_mode(self):
        CharSetModel.objects.create(field={"bold"})
        CharSetModel.objects.update(field=SetF('field').remove('big'))
        CharSetModel.objects.update(field=SetF('field').remove('bold'))
        CharSetModel.objects.update(field=SetF('field').remove('bad'))
        model = CharSetModel.objects.get()
        self.assertEqual(model.field, set())

    def test_remove_assignment(self):
        model = IntSetModel.objects.create(field={24, 89})
        model.field = SetF('field').remove(89)
        model.save()
        model = IntSetModel.objects.get()
        self.assertEqual(model.field, {24})

    def test_works_with_two_fields(self):
        CharSetModel.objects.create(field={"snickers", "lion"},
                                    field2={"apple", "orange"})

        # Concurrent add
        CharSetModel.objects.update(field=SetF('field').add("mars"),
                                    field2=SetF('field2').add("banana"))
        model = CharSetModel.objects.get()
        self.assertEqual(model.field, {"snickers", "lion", "mars"})
        self.assertEqual(model.field2, {"apple", "orange", "banana"})

        # Concurrent add and remove
        CharSetModel.objects.update(field=SetF('field').add("reeses"),
                                    field2=SetF('field2').remove("banana"))
        model = CharSetModel.objects.get()
        self.assertEqual(model.field, {"snickers", "lion", "mars", "reeses"})
        self.assertEqual(model.field2, {"apple", "orange"})

        # Swap
        CharSetModel.objects.update(field=SetF('field').remove("lion"),
                                    field2=SetF('field2').remove("apple"))
        model = CharSetModel.objects.get()
        self.assertEqual(model.field, {"snickers", "mars", "reeses"})
        self.assertEqual(model.field2, {"orange"})


@skipIf(django.VERSION >= (1, 8),
        "Requires old Django version without Expressions")
class TestSetFFails(TestCase):

    def test_cannot_instantiate(self):
        with self.assertRaises(ValueError):
            SetF('field').add("something")


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
        self.assertIn('Base field for set has errors', errors[0].msg)
        self.assertIn('max_length', errors[0].msg)

    def test_invalid_base_fields(self):
        field = SetCharField(
            models.ForeignKey('django_mysql_tests.Author'),
            max_length=32
        )
        field.set_attributes_from_name('field')
        errors = field.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'django_mysql.E002')
        self.assertIn('Base field for set must be', errors[0].msg)

    def test_max_length_including_base(self):
        field = SetCharField(
            models.CharField(max_length=32),
            size=2, max_length=32)
        field.set_attributes_from_name('field')
        errors = field.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'django_mysql.E003')
        self.assertIn('Field can overrun', errors[0].msg)


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
        self.assertEqual(instance.field, {"big", "leather", "comfy"})


class TestDescription(TestCase):

    def test_char(self):
        field = SetCharField(models.CharField(max_length=5), max_length=32)
        self.assertEqual(
            field.description,
            "Set of String (up to %(max_length)s)"
        )

    def test_int(self):
        field = SetCharField(models.IntegerField(), max_length=32)
        self.assertEqual(field.description, "Set of Integer")


class TestFormField(TestCase):

    def test_model_field_formfield(self):
        model_field = SetCharField(models.CharField(max_length=27))
        form_field = model_field.formfield()
        self.assertIsInstance(form_field, SimpleSetField)
        self.assertIsInstance(form_field.base_field, forms.CharField)
        self.assertEqual(form_field.base_field.max_length, 27)

    def test_model_field_formfield_size(self):
        model_field = SetCharField(models.IntegerField(), size=4)
        form_field = model_field.formfield()
        self.assertIsInstance(form_field, SimpleSetField)
        self.assertEqual(form_field.max_length, 4)
