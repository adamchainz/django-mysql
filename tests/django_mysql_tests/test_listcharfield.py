# -*- coding:utf-8 -*-
import json
import re
from unittest import skip, skipIf

import django
from django import forms
from django.core import exceptions, serializers
from django.core.management import call_command
from django.db import models, connection
from django.db.models import Q
from django.db.migrations.writer import MigrationWriter
from django.test import TestCase, override_settings

import ddt

from django_mysql.forms import SimpleListField
from django_mysql.models import ListCharField, ListF
from django_mysql.test.utils import override_mysql_variables

from django_mysql_tests.models import (
    CharListModel, CharListDefaultModel, IntListModel
)


@ddt.ddt
class TestSaveLoad(TestCase):

    def test_char_easy(self):
        s = CharListModel.objects.create(field=["comfy", "big"])
        self.assertEqual(s.field, ["comfy", "big"])
        s = CharListModel.objects.get(id=s.id)
        self.assertEqual(s.field, ["comfy", "big"])

        s.field.append("round")
        s.save()
        self.assertEqual(s.field, ["comfy", "big", "round"])
        s = CharListModel.objects.get(id=s.id)
        self.assertEqual(s.field, ["comfy", "big", "round"])

    def test_char_string_direct(self):
        s = CharListModel.objects.create(field="big,bad")
        s = CharListModel.objects.get(id=s.id)
        self.assertEqual(s.field, ['big', 'bad'])

    def test_is_a_list_immediately(self):
        s = CharListModel()
        self.assertEqual(s.field, [])
        s.field.append("bold")
        s.field.append("brave")
        s.save()
        self.assertEqual(s.field, ["bold", "brave"])
        s = CharListModel.objects.get(id=s.id)
        self.assertEqual(s.field, ["bold", "brave"])

    def test_empty(self):
        s = CharListModel.objects.create()
        self.assertEqual(s.field, [])
        s = CharListModel.objects.get(id=s.id)
        self.assertEqual(s.field, [])

    def test_char_cant_create_lists_with_empty_string(self):
        with self.assertRaises(ValueError):
            CharListModel.objects.create(field=[""])

    def test_char_cant_create_sets_with_commas(self):
        with self.assertRaises(ValueError):
            CharListModel.objects.create(field=["co,mma", "contained"])

    def test_char_basic_lookup(self):
        mymodel = CharListModel.objects.create()
        empty = CharListModel.objects.filter(field="")

        self.assertEqual(empty.count(), 1)
        self.assertEqual(empty[0], mymodel)

        mymodel.delete()

        self.assertEqual(empty.count(), 0)

    @ddt.data('contains', 'icontains')
    def test_char_lookup(self, lookup):
        lname = 'field__' + lookup
        mymodel = CharListModel.objects.create(field=["mouldy", "rotten"])

        mouldy = CharListModel.objects.filter(**{lname: "mouldy"})
        self.assertEqual(mouldy.count(), 1)
        self.assertEqual(mouldy[0], mymodel)

        rotten = CharListModel.objects.filter(**{lname: "rotten"})
        self.assertEqual(rotten.count(), 1)
        self.assertEqual(rotten[0], mymodel)

        clean = CharListModel.objects.filter(**{lname: "clean"})
        self.assertEqual(clean.count(), 0)

        with self.assertRaises(ValueError):
            list(CharListModel.objects.filter(**{lname: ["a", "b"]}))

        both = CharListModel.objects.filter(
            Q(**{lname: "mouldy"}) & Q(**{lname: "rotten"})
        )
        self.assertEqual(both.count(), 1)
        self.assertEqual(both[0], mymodel)

        either = CharListModel.objects.filter(
            Q(**{lname: "mouldy"}) | Q(**{lname: "clean"})
        )
        self.assertEqual(either.count(), 1)

        not_clean = CharListModel.objects.exclude(**{lname: "clean"})
        self.assertEqual(not_clean.count(), 1)

        not_mouldy = CharListModel.objects.exclude(**{lname: "mouldy"})
        self.assertEqual(not_mouldy.count(), 0)

    def test_char_len_lookup_empty(self):
        mymodel = CharListModel.objects.create(field=[])

        empty = CharListModel.objects.filter(field__len=0)
        self.assertEqual(empty.count(), 1)
        self.assertEqual(empty[0], mymodel)

        one = CharListModel.objects.filter(field__len=1)
        self.assertEqual(one.count(), 0)

        one_or_more = CharListModel.objects.filter(field__len__gte=0)
        self.assertEqual(one_or_more.count(), 1)

    def test_char_len_lookup(self):
        mymodel = CharListModel.objects.create(field=["red", "expensive"])

        empty = CharListModel.objects.filter(field__len=0)
        self.assertEqual(empty.count(), 0)

        one_or_more = CharListModel.objects.filter(field__len__gte=1)
        self.assertEqual(one_or_more.count(), 1)
        self.assertEqual(one_or_more[0], mymodel)

        two = CharListModel.objects.filter(field__len=2)
        self.assertEqual(two.count(), 1)
        self.assertEqual(two[0], mymodel)

        three = CharListModel.objects.filter(field__len=3)
        self.assertEqual(three.count(), 0)

    def test_char_default(self):
        mymodel = CharListDefaultModel.objects.create()
        self.assertEqual(mymodel.field, ["a", "d"])

        mymodel = CharListDefaultModel.objects.get(id=mymodel.id)
        self.assertEqual(mymodel.field, ["a", "d"])

    def test_char_position_lookup(self):
        mymodel = CharListModel.objects.create(field=["red", "blue"])

        blue0 = CharListModel.objects.filter(field__0="blue")
        self.assertEqual(blue0.count(), 0)

        red0 = CharListModel.objects.filter(field__0="red")
        self.assertEqual(list(red0), [mymodel])

        red0_red1 = CharListModel.objects.filter(field__0="red",
                                                 field__1="red")
        self.assertEqual(red0_red1.count(), 0)

        red0_blue1 = CharListModel.objects.filter(field__0="red",
                                                  field__1="blue")
        self.assertEqual(list(red0_blue1), [mymodel])

        red0_or_blue0 = CharListModel.objects.filter(
            Q(field__0="red") | Q(field__0="blue")
        )
        self.assertEqual(list(red0_or_blue0), [mymodel])

    def test_char_position_lookup_repeat_fails(self):
        """
        FIND_IN_SET returns the *first* position so repeats are not dealt with
        """
        CharListModel.objects.create(field=["red", "red", "blue"])

        red1 = CharListModel.objects.filter(field__1="red")
        self.assertEqual(list(red1), [])  # should be 'red'

    def test_char_position_lookup_too_long(self):
        CharListModel.objects.create(field=["red", "blue"])

        red1 = CharListModel.objects.filter(field__2="blue")
        self.assertEqual(list(red1), [])

    def test_int_easy(self):
        mymodel = IntListModel.objects.create(field=[1, 2])
        self.assertEqual(mymodel.field, [1, 2])
        mymodel = IntListModel.objects.get(id=mymodel.id)
        self.assertEqual(mymodel.field, [1, 2])

    def test_int_contains_lookup(self):
        onetwo = IntListModel.objects.create(field=[1, 2])

        ones = IntListModel.objects.filter(field__contains=1)
        self.assertEqual(ones.count(), 1)
        self.assertEqual(ones[0], onetwo)

        twos = IntListModel.objects.filter(field__contains=2)
        self.assertEqual(twos.count(), 1)
        self.assertEqual(twos[0], onetwo)

        threes = IntListModel.objects.filter(field__contains=3)
        self.assertEqual(threes.count(), 0)

        with self.assertRaises(ValueError):
            list(IntListModel.objects.filter(field__contains=[1, 2]))

        ones_and_twos = IntListModel.objects.filter(
            Q(field__contains=1) & Q(field__contains=2)
        )
        self.assertEqual(ones_and_twos.count(), 1)
        self.assertEqual(ones_and_twos[0], onetwo)

        ones_and_threes = IntListModel.objects.filter(
            Q(field__contains=1) & Q(field__contains=3)
        )
        self.assertEqual(ones_and_threes.count(), 0)

        ones_or_threes = IntListModel.objects.filter(
            Q(field__contains=1) | Q(field__contains=3)
        )
        self.assertEqual(ones_or_threes.count(), 1)

        no_three = IntListModel.objects.exclude(field__contains=3)
        self.assertEqual(no_three.count(), 1)

        no_one = IntListModel.objects.exclude(field__contains=1)
        self.assertEqual(no_one.count(), 0)

    def test_int_position_lookup(self):
        onetwo = IntListModel.objects.create(field=[1, 2])

        one0 = IntListModel.objects.filter(field__0=1)
        self.assertEqual(list(one0), [onetwo])

        two0 = IntListModel.objects.filter(field__0=2)
        self.assertEqual(two0.count(), 0)

        one0two1 = IntListModel.objects.filter(field__0=1, field__1=2)
        self.assertEqual(list(one0two1), [onetwo])


@skipIf(django.VERSION <= (1, 8),
        "Requires Expressions from Django 1.8+")
class TestListF(TestCase):

    def test_append_to_none(self):
        CharListModel.objects.create(field=[])
        CharListModel.objects.update(field=ListF('field').append('first'))
        model = CharListModel.objects.get()
        self.assertEqual(model.field, ["first"])

    def test_append_to_one(self):
        CharListModel.objects.create(field=["big"])
        CharListModel.objects.update(field=ListF('field').append('bad'))
        model = CharListModel.objects.get()
        self.assertEqual(model.field, ["big", "bad"])

    def test_append_to_some(self):
        CharListModel.objects.create(field=["big", "blue"])
        CharListModel.objects.update(field=ListF('field').append('round'))
        model = CharListModel.objects.get()
        self.assertEqual(model.field, ["big", "blue", "round"])

    def test_append_to_multiple_objects(self):
        CharListModel.objects.create(field=["mouse"])
        CharListModel.objects.create(field=["keyboard"])
        CharListModel.objects.update(field=ListF('field').append("screen"))
        first, second = tuple(CharListModel.objects.all())
        self.assertEqual(first.field, ["mouse", "screen"])
        self.assertEqual(second.field, ["keyboard", "screen"])

    def test_append_exists(self):
        CharListModel.objects.create(field=["nice"])
        CharListModel.objects.update(field=ListF('field').append("nice"))
        model = CharListModel.objects.get()
        self.assertEqual(model.field, ["nice", "nice"])

    @override_mysql_variables(SQL_MODE="ANSI")
    def test_append_works_in_ansi_mode(self):
        CharListModel.objects.create()
        CharListModel.objects.update(field=ListF('field').append('big'))
        CharListModel.objects.update(field=ListF('field').append('bad'))
        model = CharListModel.objects.get()
        self.assertEqual(model.field, ["big", "bad"])

    def test_append_assignment(self):
        model = CharListModel.objects.create(field=["red"])
        model.field = ListF('field').append('blue')
        model.save()
        model = CharListModel.objects.get()
        self.assertEqual(model.field, ['red', 'blue'])

    def test_appendleft_to_none(self):
        CharListModel.objects.create(field=[])
        CharListModel.objects.update(field=ListF('field').appendleft('first'))
        model = CharListModel.objects.get()
        self.assertEqual(model.field, ["first"])

    def test_appendleft_to_one(self):
        CharListModel.objects.create(field=["big"])
        CharListModel.objects.update(field=ListF('field').appendleft('bad'))
        model = CharListModel.objects.get()
        self.assertEqual(model.field, ["bad", "big"])

    def test_appendleft_to_some(self):
        CharListModel.objects.create(field=["big", "blue"])
        CharListModel.objects.update(field=ListF('field').appendleft('round'))
        model = CharListModel.objects.get()
        self.assertEqual(model.field, ["round", "big", "blue"])

    def test_appendleft_to_multiple_objects(self):
        CharListModel.objects.create(field=["mouse"])
        CharListModel.objects.create(field=["keyboard"])
        CharListModel.objects.update(field=ListF('field').appendleft("screen"))
        first, second = tuple(CharListModel.objects.all())
        self.assertEqual(first.field, ["screen", "mouse"])
        self.assertEqual(second.field, ["screen", "keyboard"])

    def test_appendleft_exists(self):
        CharListModel.objects.create(field=["nice"])
        CharListModel.objects.update(field=ListF('field').appendleft("nice"))
        model = CharListModel.objects.get()
        self.assertEqual(model.field, ["nice", "nice"])

    @override_mysql_variables(SQL_MODE="ANSI")
    def test_appendleft_works_in_ansi_mode(self):
        CharListModel.objects.create()
        CharListModel.objects.update(field=ListF('field').appendleft('big'))
        CharListModel.objects.update(field=ListF('field').appendleft('bad'))
        model = CharListModel.objects.get()
        self.assertEqual(model.field, ["bad", "big"])

    def test_appendleft_assignment(self):
        model = CharListModel.objects.create(field=["red"])
        model.field = ListF('field').appendleft('blue')
        model.save()
        model = CharListModel.objects.get()
        self.assertEqual(model.field, ['blue', 'red'])

    def test_pop_none(self):
        CharListModel.objects.create(field=[])
        CharListModel.objects.update(field=ListF('field').pop())
        model = CharListModel.objects.get()
        self.assertEqual(model.field, [])

    def test_pop_one(self):
        CharListModel.objects.create(field=["red"])
        CharListModel.objects.update(field=ListF('field').pop())
        model = CharListModel.objects.get()
        self.assertEqual(model.field, [])

    def test_pop_two(self):
        CharListModel.objects.create(field=["red", "blue"])
        CharListModel.objects.update(field=ListF('field').pop())
        model = CharListModel.objects.get()
        self.assertEqual(model.field, ["red"])

    def test_pop_three(self):
        CharListModel.objects.create(field=["green", "yellow", "p"])
        CharListModel.objects.update(field=ListF('field').pop())
        model = CharListModel.objects.get()
        self.assertEqual(model.field, ["green", "yellow"])

    def test_popleft_none(self):
        CharListModel.objects.create(field=[])
        CharListModel.objects.update(field=ListF('field').popleft())
        model = CharListModel.objects.get()
        self.assertEqual(model.field, [])

    def test_popleft_one(self):
        CharListModel.objects.create(field=["red"])
        CharListModel.objects.update(field=ListF('field').popleft())
        model = CharListModel.objects.get()
        self.assertEqual(model.field, [])

    def test_popleft_two(self):
        CharListModel.objects.create(field=["red", "blue"])
        CharListModel.objects.update(field=ListF('field').popleft())
        model = CharListModel.objects.get()
        self.assertEqual(model.field, ["blue"])

    def test_popleft_three(self):
        CharListModel.objects.create(field=["green", "yellow", "p"])
        CharListModel.objects.update(field=ListF('field').popleft())
        model = CharListModel.objects.get()
        self.assertEqual(model.field, ["yellow", "p"])


class TestValidation(TestCase):

    def test_max_length(self):
        field = ListCharField(
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
        field = ListCharField(models.CharField(), max_length=32)
        field.set_attributes_from_name('field')
        errors = field.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'django_mysql.E004')
        self.assertIn('Base field for list has errors', errors[0].msg)
        self.assertIn('max_length', errors[0].msg)

    def test_invalid_base_fields(self):
        field = ListCharField(
            models.ForeignKey('django_mysql_tests.Author'),
            max_length=32
        )
        field.set_attributes_from_name('field')
        errors = field.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'django_mysql.E005')
        self.assertIn('Base field for list must be', errors[0].msg)

    def test_max_length_including_base(self):
        field = ListCharField(
            models.CharField(max_length=32),
            size=2, max_length=32)
        field.set_attributes_from_name('field')
        errors = field.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'django_mysql.E006')
        self.assertIn('Field can overrun', errors[0].msg)


class TestMigrations(TestCase):

    def test_deconstruct(self):
        field = ListCharField(models.IntegerField(), max_length=32)
        name, path, args, kwargs = field.deconstruct()
        new = ListCharField(*args, **kwargs)
        self.assertEqual(type(new.base_field), type(field.base_field))

    def test_deconstruct_with_size(self):
        field = ListCharField(models.IntegerField(), size=3, max_length=32)
        name, path, args, kwargs = field.deconstruct()
        new = ListCharField(*args, **kwargs)
        self.assertEqual(new.size, field.size)

    def test_deconstruct_args(self):
        field = ListCharField(models.CharField(max_length=5), max_length=32)
        name, path, args, kwargs = field.deconstruct()
        new = ListCharField(*args, **kwargs)
        self.assertEqual(
            new.base_field.max_length,
            field.base_field.max_length
        )

    def test_makemigrations(self):
        field = ListCharField(models.CharField(max_length=5), max_length=32)
        statement, imports = MigrationWriter.serialize(field)

        # The order of the output max_length/size statements varies by
        # python version, hence a little regexp to match them
        self.assertRegexpMatches(
            statement,
            re.compile(
                r"""^django_mysql\.models\.ListCharField\(
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
        field = ListCharField(
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
                r"""^django_mysql\.models\.ListCharField\(
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

    @skip("Unforunately this and the SetCharField equivalent interfere with "
          "each other - the migrations don't seem to roll back smoothly.")
    @override_settings(MIGRATION_MODULES={
        "django_mysql_tests": "django_mysql_tests.list_default_migrations",
    })
    def test_adding_field_with_default(self):
        table_name = 'django_mysql_tests_intlistdefaultmodel'
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
        instance = CharListModel(field=["big", "comfy"])
        data = json.loads(serializers.serialize('json', [instance]))[0]
        field = data['fields']['field']
        self.assertEqual(sorted(field.split(',')), ["big", "comfy"])

    def test_loading(self):
        test_data = '''
            [{"fields": {"field": "big,leather,comfy"},
             "model": "django_mysql_tests.CharListModel", "pk": null}]
        '''
        objs = list(serializers.deserialize('json', test_data))
        instance = objs[0].object
        self.assertEqual(instance.field, ["big", "leather", "comfy"])


class TestDescription(TestCase):

    def test_char(self):
        field = ListCharField(models.CharField(max_length=5), max_length=32)
        self.assertEqual(
            field.description,
            "List of String (up to %(max_length)s)"
        )

    def test_int(self):
        field = ListCharField(models.IntegerField(), max_length=32)
        self.assertEqual(field.description, "List of Integer")


class TestFormField(TestCase):

    def test_model_field_formfield(self):
        model_field = ListCharField(models.CharField(max_length=27))
        form_field = model_field.formfield()
        self.assertIsInstance(form_field, SimpleListField)
        self.assertIsInstance(form_field.base_field, forms.CharField)
        self.assertEqual(form_field.base_field.max_length, 27)

    def test_model_field_formfield_size(self):
        model_field = ListCharField(models.IntegerField(), size=4)
        form_field = model_field.formfield()
        self.assertIsInstance(form_field, SimpleListField)
        self.assertEqual(form_field.max_length, 4)
