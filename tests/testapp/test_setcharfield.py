# -*- coding:utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import json
import re

import pytest
from django import forms
from django.core import exceptions, serializers
from django.core.management import call_command
from django.db import connection, models
from django.db.migrations.writer import MigrationWriter
from django.db.models import Q
from django.test import (
    SimpleTestCase, TestCase, TransactionTestCase, override_settings
)

from django_mysql.forms import SimpleSetField
from django_mysql.models import SetCharField, SetF
from django_mysql.test.utils import override_mysql_variables
from testapp.models import (
    CharSetDefaultModel, CharSetModel, IntSetModel, TemporaryModel
)


class TestSaveLoad(TestCase):

    def test_char_easy(self):
        s = CharSetModel.objects.create(field={"big", "comfy"})
        assert s.field == {"comfy", "big"}
        s = CharSetModel.objects.get(id=s.id)
        assert s.field == {"comfy", "big"}

        s.field.add("round")
        s.save()
        assert s.field == {"comfy", "big", "round"}
        s = CharSetModel.objects.get(id=s.id)
        assert s.field == {"comfy", "big", "round"}

    def test_char_string_direct(self):
        s = CharSetModel.objects.create(field="big,bad")
        s = CharSetModel.objects.get(id=s.id)
        assert s.field == {'big', 'bad'}

    def test_is_a_set_immediately(self):
        s = CharSetModel()
        assert s.field == set()
        s.field.add("bold")
        s.field.add("brave")
        s.save()
        assert s.field == {"bold", "brave"}
        s = CharSetModel.objects.get(id=s.id)
        assert s.field == {"bold", "brave"}

    def test_empty(self):
        s = CharSetModel.objects.create()
        assert s.field == set()
        s = CharSetModel.objects.get(id=s.id)
        assert s.field == set()

    def test_char_cant_create_sets_with_empty_string(self):
        with pytest.raises(ValueError):
            CharSetModel.objects.create(field={""})

    def test_char_cant_create_sets_with_commas(self):
        with pytest.raises(ValueError):
            CharSetModel.objects.create(field={"co,mma", "contained"})

    def test_char_basic_lookup(self):
        mymodel = CharSetModel.objects.create()
        empty = CharSetModel.objects.filter(field="")

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
        mymodel = CharSetModel.objects.create(field={"mouldy", "rotten"})

        mouldy = CharSetModel.objects.filter(**{lname: "mouldy"})
        assert mouldy.count() == 1
        assert mouldy[0] == mymodel

        rotten = CharSetModel.objects.filter(**{lname: "rotten"})
        assert rotten.count() == 1
        assert rotten[0] == mymodel

        clean = CharSetModel.objects.filter(**{lname: "clean"})
        assert clean.count() == 0

        with pytest.raises(ValueError):
            list(CharSetModel.objects.filter(**{lname: {"a", "b"}}))

        both = CharSetModel.objects.filter(
            Q(**{lname: "mouldy"}) & Q(**{lname: "rotten"})
        )
        assert both.count() == 1
        assert both[0] == mymodel

        either = CharSetModel.objects.filter(
            Q(**{lname: "mouldy"}) | Q(**{lname: "clean"})
        )
        assert either.count() == 1

        not_clean = CharSetModel.objects.exclude(**{lname: "clean"})
        assert not_clean.count() == 1

        not_mouldy = CharSetModel.objects.exclude(**{lname: "mouldy"})
        assert not_mouldy.count() == 0

    def test_char_len_lookup_empty(self):
        mymodel = CharSetModel.objects.create(field=set())

        empty = CharSetModel.objects.filter(field__len=0)
        assert empty.count() == 1
        assert empty[0] == mymodel

        one = CharSetModel.objects.filter(field__len=1)
        assert one.count() == 0

        one_or_more = CharSetModel.objects.filter(field__len__gte=0)
        assert one_or_more.count() == 1

    def test_char_len_lookup(self):
        mymodel = CharSetModel.objects.create(field={"red", "expensive"})

        empty = CharSetModel.objects.filter(field__len=0)
        assert empty.count() == 0

        one_or_more = CharSetModel.objects.filter(field__len__gte=1)
        assert one_or_more.count() == 1
        assert one_or_more[0] == mymodel

        two = CharSetModel.objects.filter(field__len=2)
        assert two.count() == 1
        assert two[0] == mymodel

        three = CharSetModel.objects.filter(field__len=3)
        assert three.count() == 0

    def test_char_default(self):
        mymodel = CharSetDefaultModel.objects.create()
        assert mymodel.field == {"a", "d"}

        mymodel = CharSetDefaultModel.objects.get(id=mymodel.id)
        assert mymodel.field == {"a", "d"}

    def test_int_easy(self):
        mymodel = IntSetModel.objects.create(field={1, 2})
        assert mymodel.field == {1, 2}
        mymodel = IntSetModel.objects.get(id=mymodel.id)
        assert mymodel.field == {1, 2}

    def test_int_contains_lookup(self):
        onetwo = IntSetModel.objects.create(field={1, 2})

        ones = IntSetModel.objects.filter(field__contains=1)
        assert ones.count() == 1
        assert ones[0] == onetwo

        twos = IntSetModel.objects.filter(field__contains=2)
        assert twos.count() == 1
        assert twos[0] == onetwo

        threes = IntSetModel.objects.filter(field__contains=3)
        assert threes.count() == 0

        with pytest.raises(ValueError):
            list(IntSetModel.objects.filter(field__contains={1, 2}))

        ones_and_twos = IntSetModel.objects.filter(
            Q(field__contains=1) & Q(field__contains=2)
        )
        assert ones_and_twos.count() == 1
        assert ones_and_twos[0] == onetwo

        ones_and_threes = IntSetModel.objects.filter(
            Q(field__contains=1) & Q(field__contains=3)
        )
        assert ones_and_threes.count() == 0

        ones_or_threes = IntSetModel.objects.filter(
            Q(field__contains=1) | Q(field__contains=3)
        )
        assert ones_or_threes.count() == 1

        no_three = IntSetModel.objects.exclude(field__contains=3)
        assert no_three.count() == 1

        no_one = IntSetModel.objects.exclude(field__contains=1)
        assert no_one.count() == 0


class TestSetF(TestCase):

    def test_add_to_none(self):
        CharSetModel.objects.create(field=set())
        CharSetModel.objects.update(field=SetF('field').add('first'))
        model = CharSetModel.objects.get()
        assert model.field == {"first"}

    def test_add_to_one(self):
        CharSetModel.objects.create(field={"big"})
        CharSetModel.objects.update(field=SetF('field').add('bad'))
        model = CharSetModel.objects.get()
        assert model.field == {"big", "bad"}

    def test_add_to_some(self):
        CharSetModel.objects.create(field={"big", "blue"})
        CharSetModel.objects.update(field=SetF('field').add('round'))
        model = CharSetModel.objects.get()
        assert model.field == {"big", "blue", "round"}

    def test_add_to_multiple_objects(self):
        CharSetModel.objects.create(field={"mouse"})
        CharSetModel.objects.create(field={"keyboard"})
        CharSetModel.objects.update(field=SetF('field').add("screen"))
        first, second = tuple(CharSetModel.objects.all())
        assert first.field == {"mouse", "screen"}
        assert second.field == {"keyboard", "screen"}

    def test_add_exists(self):
        CharSetModel.objects.create(field={"nice"})
        CharSetModel.objects.update(field=SetF('field').add("nice"))
        model = CharSetModel.objects.get()
        assert model.field == {"nice"}

    @override_mysql_variables(SQL_MODE="ANSI")
    def test_add_works_in_ansi_mode(self):
        CharSetModel.objects.create()
        CharSetModel.objects.update(field=SetF('field').add('big'))
        CharSetModel.objects.update(field=SetF('field').add('bad'))
        model = CharSetModel.objects.get()
        assert model.field == {"big", "bad"}

    def test_add_assignment(self):
        model = CharSetModel.objects.create(field={"red"})
        model.field = SetF('field').add('blue')
        model.save()
        model = CharSetModel.objects.get()
        assert model.field == {'red', 'blue'}

    def test_remove_one(self):
        CharSetModel.objects.create(field={"dopey", "knifey"})
        CharSetModel.objects.update(field=SetF('field').remove('knifey'))
        model = CharSetModel.objects.get()
        assert model.field == {"dopey"}

    def test_remove_only_one(self):
        CharSetModel.objects.create(field={"pants"})
        CharSetModel.objects.update(field=SetF('field').remove('pants'))
        model = CharSetModel.objects.get()
        assert model.field == set()

    def test_remove_from_none(self):
        CharSetModel.objects.create(field=set())
        CharSetModel.objects.update(field=SetF("field").remove("jam"))
        model = CharSetModel.objects.get()
        assert model.field == set()

    def test_remove_first(self):
        CharSetModel.objects.create()
        CharSetModel.objects.update(field="a,b,c")
        CharSetModel.objects.update(field=SetF('field').remove('a'))
        model = CharSetModel.objects.get()
        assert model.field == {"b", "c"}

    def test_remove_middle(self):
        CharSetModel.objects.create()
        CharSetModel.objects.update(field="a,b,c")
        CharSetModel.objects.update(field=SetF('field').remove('b'))
        model = CharSetModel.objects.get()
        assert model.field == {"a", "c"}

    def test_remove_last(self):
        CharSetModel.objects.create()
        CharSetModel.objects.update(field="a,b,c")
        CharSetModel.objects.update(field=SetF('field').remove('c'))
        model = CharSetModel.objects.get()
        assert model.field == {"a", "b"}

    def test_remove_not_exists(self):
        CharSetModel.objects.create(field={"nice"})
        CharSetModel.objects.update(field=SetF("field").remove("naughty"))
        model = CharSetModel.objects.get()
        assert model.field == {"nice"}

    def test_remove_from_multiple_objects(self):
        CharSetModel.objects.create(field={"mouse", "chair"})
        CharSetModel.objects.create(field={"keyboard", "chair"})
        CharSetModel.objects.update(field=SetF('field').remove("chair"))
        first, second = tuple(CharSetModel.objects.all())
        assert first.field == {"mouse"}
        assert second.field == {"keyboard"}

    @override_mysql_variables(SQL_MODE="ANSI")
    def test_remove_works_in_ansi_mode(self):
        CharSetModel.objects.create(field={"bold"})
        CharSetModel.objects.update(field=SetF('field').remove('big'))
        CharSetModel.objects.update(field=SetF('field').remove('bold'))
        CharSetModel.objects.update(field=SetF('field').remove('bad'))
        model = CharSetModel.objects.get()
        assert model.field == set()

    def test_remove_assignment(self):
        model = IntSetModel.objects.create(field={24, 89})
        model.field = SetF('field').remove(89)
        model.save()
        model = IntSetModel.objects.get()
        assert model.field == {24}

    def test_works_with_two_fields(self):
        CharSetModel.objects.create(field={"snickers", "lion"},
                                    field2={"apple", "orange"})

        # Concurrent add
        CharSetModel.objects.update(field=SetF('field').add("mars"),
                                    field2=SetF('field2').add("banana"))
        model = CharSetModel.objects.get()
        assert model.field == {"snickers", "lion", "mars"}
        assert model.field2 == {"apple", "orange", "banana"}

        # Concurrent add and remove
        CharSetModel.objects.update(field=SetF('field').add("reeses"),
                                    field2=SetF('field2').remove("banana"))
        model = CharSetModel.objects.get()
        assert model.field == {"snickers", "lion", "mars", "reeses"}
        assert model.field2 == {"apple", "orange"}

        # Swap
        CharSetModel.objects.update(field=SetF('field').remove("lion"),
                                    field2=SetF('field2').remove("apple"))
        model = CharSetModel.objects.get()
        assert model.field == {"snickers", "mars", "reeses"}
        assert model.field2 == {"orange"}


class TestValidation(SimpleTestCase):

    def test_max_length(self):
        field = SetCharField(
            models.CharField(max_length=32),
            size=3,
            max_length=32
        )

        field.clean({'a', 'b', 'c'}, None)

        with pytest.raises(exceptions.ValidationError) as excinfo:
            field.clean({'a', 'b', 'c', 'd'}, None)
        assert (
            excinfo.value.messages[0] ==
            'Set contains 4 items, it should contain no more than 3.'
        )


class TestCheck(SimpleTestCase):

    def test_model_set(self):
        field = IntSetModel._meta.get_field('field')
        assert field.model == IntSetModel
        # I think this is a side effect of migrations being run in tests -
        # the base_field.model is the __fake__ model
        assert field.base_field.model.__name__ == 'IntSetModel'

    def test_base_field_checks(self):
        class InvalidSetCharFieldModel(TemporaryModel):
            field = SetCharField(models.CharField(), max_length=32)

        errors = InvalidSetCharFieldModel.check(actually_check=True)
        assert len(errors) == 1
        assert errors[0].id == 'django_mysql.E001'
        assert 'Base field for set has errors' in errors[0].msg
        assert 'max_length' in errors[0].msg

    def test_invalid_base_fields(self):
        class InvalidSetCharFieldModel(TemporaryModel):
            field = SetCharField(
                models.ForeignKey('testapp.Author'),
                max_length=32
            )

        errors = InvalidSetCharFieldModel.check(actually_check=True)
        assert len(errors) == 1
        assert errors[0].id == 'django_mysql.E002'
        assert 'Base field for set must be' in errors[0].msg

    def test_max_length_including_base(self):
        class InvalidSetCharFieldModel(TemporaryModel):
            field = SetCharField(
                models.CharField(max_length=32),
                size=2, max_length=32)

        errors = InvalidSetCharFieldModel.check(actually_check=True)
        assert len(errors) == 1
        assert errors[0].id == 'django_mysql.E003'
        assert 'Field can overrun' in errors[0].msg


class TestDeconstruct(TestCase):

    def test_deconstruct(self):
        field = SetCharField(models.IntegerField(), max_length=32)
        name, path, args, kwargs = field.deconstruct()
        new = SetCharField(*args, **kwargs)
        assert new.base_field.__class__ == field.base_field.__class__

    def test_deconstruct_with_size(self):
        field = SetCharField(models.IntegerField(), size=3, max_length=32)
        name, path, args, kwargs = field.deconstruct()
        new = SetCharField(*args, **kwargs)
        assert new.size == field.size

    def test_deconstruct_args(self):
        field = SetCharField(models.CharField(max_length=5), max_length=32)
        name, path, args, kwargs = field.deconstruct()
        new = SetCharField(*args, **kwargs)
        assert new.base_field.max_length == field.base_field.max_length

    def test_makemigrations(self):
        field = SetCharField(models.CharField(max_length=5), max_length=32)
        statement, imports = MigrationWriter.serialize(field)

        # The order of the output max_length/size statements varies by
        # python version, hence a little regexp to match them
        assert re.compile(
            r"""^django_mysql\.models\.SetCharField\(
                models\.CharField\(max_length=5\),\ # space here
                (
                    max_length=32,\ size=None|
                    size=None,\ max_length=32
                )
                \)$
            """,
            re.VERBOSE
        ).match(statement)


class TestMigrationWriter(TestCase):

    def test_makemigrations_with_size(self):
        field = SetCharField(
            models.CharField(max_length=5),
            max_length=32,
            size=5
        )
        statement, imports = MigrationWriter.serialize(field)

        # The order of the output max_length/size statements varies by
        # python version, hence a little regexp to match them
        assert re.compile(
            r"""^django_mysql\.models\.SetCharField\(
                models\.CharField\(max_length=5\),\ # space here
                (
                    max_length=32,\ size=5|
                    size=5,\ max_length=32
                )
                \)$
            """,
            re.VERBOSE
        ).match(statement)


class TestMigrations(TransactionTestCase):

    @override_settings(MIGRATION_MODULES={
        "testapp": "testapp.set_default_migrations",
    })
    def test_adding_field_with_default(self):
        table_name = 'testapp_intsetdefaultmodel'
        table_names = connection.introspection.table_names
        with connection.cursor() as cursor:
            assert table_name not in table_names(cursor)

        call_command('migrate', 'testapp',
                     verbosity=0, skip_checks=True, interactive=False)
        with connection.cursor() as cursor:
            assert table_name in table_names(cursor)

        call_command('migrate', 'testapp', 'zero',
                     verbosity=0, skip_checks=True, interactive=False)
        with connection.cursor() as cursor:
            assert table_name not in table_names(cursor)


class TestSerialization(SimpleTestCase):

    def test_dumping(self):
        instance = CharSetModel(field={"big", "comfy"})
        data = json.loads(serializers.serialize('json', [instance]))[0]
        field = data['fields']['field']
        assert sorted(field.split(',')) == ["big", "comfy"]

    def test_loading(self):
        test_data = '''
            [{"fields": {"field": "big,leather,comfy"},
             "model": "testapp.CharSetModel", "pk": null}]
        '''
        objs = list(serializers.deserialize('json', test_data))
        instance = objs[0].object
        assert instance.field == {"big", "leather", "comfy"}


class TestDescription(SimpleTestCase):

    def test_char(self):
        field = SetCharField(models.CharField(max_length=5), max_length=32)
        assert field.description == "Set of String (up to %(max_length)s)"

    def test_int(self):
        field = SetCharField(models.IntegerField(), max_length=32)
        assert field.description == "Set of Integer"


class TestFormField(SimpleTestCase):

    def test_model_field_formfield(self):
        model_field = SetCharField(models.CharField(max_length=27))
        form_field = model_field.formfield()
        assert isinstance(form_field, SimpleSetField)
        assert isinstance(form_field.base_field, forms.CharField)
        assert form_field.base_field.max_length == 27

    def test_model_field_formfield_size(self):
        model_field = SetCharField(models.IntegerField(), size=4)
        form_field = model_field.formfield()
        assert isinstance(form_field, SimpleSetField)
        assert form_field.max_length == 4
