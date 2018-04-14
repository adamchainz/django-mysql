# -*- coding:utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)

from unittest import skipUnless

import django
import pytest
from django import forms
from django.core import exceptions
from django.test import SimpleTestCase
from django.utils.html import escape

from django_mysql.forms import JSONField, SimpleListField, SimpleSetField


class TestSimpleListField(SimpleTestCase):

    def test_valid(self):
        field = SimpleListField(forms.CharField())
        value = field.clean('a,b,c')
        assert value == ['a', 'b', 'c']

    def test_to_python_no_leading_commas(self):
        field = SimpleListField(forms.IntegerField())
        with pytest.raises(exceptions.ValidationError) as excinfo:
            field.clean(',1')
        assert (
            excinfo.value.messages[0] ==
            'No leading, trailing, or double commas.'
        )

    def test_to_python_no_trailing_commas(self):
        field = SimpleListField(forms.IntegerField())
        with pytest.raises(exceptions.ValidationError) as excinfo:
            field.clean('1,')
        assert (
            excinfo.value.messages[0] ==
            'No leading, trailing, or double commas.'
        )

    def test_to_python_no_double_commas(self):
        field = SimpleListField(forms.IntegerField())
        with pytest.raises(exceptions.ValidationError) as excinfo:
            field.clean('1,,2')
        assert (
            excinfo.value.messages[0] ==
            'No leading, trailing, or double commas.'
        )

    def test_to_python_base_field_does_not_validate(self):
        field = SimpleListField(forms.IntegerField())
        with pytest.raises(exceptions.ValidationError) as excinfo:
            field.clean('a,b,9')
        assert (
            excinfo.value.messages[0] ==
            'Item 1 in the list did not validate: Enter a whole number.'
        )

    def test_validate_fail(self):
        field = SimpleListField(
            forms.ChoiceField(choices=(('a', 'The letter A'),
                                       ('b', 'The letter B'))),
        )
        with pytest.raises(exceptions.ValidationError) as excinfo:
            field.clean('a,c')
        assert (
            excinfo.value.messages[0] ==
            'Item 2 in the list did not validate: '
            'Select a valid choice. c is not one of the available choices.'
        )

    def test_validators_fail(self):
        field = SimpleListField(forms.RegexField('[a-e]{2}'))
        with pytest.raises(exceptions.ValidationError) as excinfo:
            field.clean('a,bc,de')
        assert (
            excinfo.value.messages[0] ==
            'Item 1 in the list did not validate: Enter a valid value.'
        )

    def test_validators_fail_base_max_length(self):
        field = SimpleListField(forms.CharField(max_length=5))
        with pytest.raises(exceptions.ValidationError) as excinfo:
            field.clean('longer,yes')
        assert (
            excinfo.value.messages[0] ==
            'Item 1 in the list did not validate: '
            'Ensure this value has at most 5 characters (it has 6).'
        )

    def test_validators_fail_base_min_max_length(self):
        # there's just no satisfying some people...
        field = SimpleListField(forms.CharField(min_length=10, max_length=8))
        with pytest.raises(exceptions.ValidationError) as excinfo:
            field.clean('undefined')
        assert (
            excinfo.value.messages[0] ==
            'Item 1 in the list did not validate: '
            'Ensure this value has at least 10 characters (it has 9).'
        )
        assert (
            excinfo.value.messages[1] ==
            'Item 1 in the list did not validate: '
            'Ensure this value has at most 8 characters (it has 9).'
        )

    def test_prepare_value(self):
        field = SimpleListField(forms.CharField())
        value = field.prepare_value(['a', 'b', 'c'])
        assert value.split(',') == ['a', 'b', 'c']

        assert field.prepare_value('1,a') == '1,a'

    def test_max_length(self):
        field = SimpleListField(forms.CharField(), max_length=2)
        with pytest.raises(exceptions.ValidationError) as excinfo:
            field.clean('a,b,c')
        assert (
            excinfo.value.messages[0] ==
            'List contains 3 items, it should contain no more than 2.'
        )

    def test_min_length(self):
        field = SimpleListField(forms.CharField(), min_length=4)
        with pytest.raises(exceptions.ValidationError) as excinfo:
            field.clean('a,b,c')
        assert (
            excinfo.value.messages[0] ==
            'List contains 3 items, it should contain no fewer than 4.'
        )

    def test_required(self):
        field = SimpleListField(forms.CharField(), required=True)
        with pytest.raises(exceptions.ValidationError) as excinfo:
            field.clean('')
        assert excinfo.value.messages[0] == 'This field is required.'


class TestSimpleSetField(SimpleTestCase):

    def test_valid(self):
        field = SimpleSetField(forms.CharField())
        value = field.clean('a,b,c')
        assert value == {'a', 'b', 'c'}

    def test_to_python_no_leading_commas(self):
        field = SimpleSetField(forms.IntegerField())
        with pytest.raises(exceptions.ValidationError) as excinfo:
            field.clean(',1')
        assert (
            excinfo.value.messages[0] ==
            'No leading, trailing, or double commas.'
        )

    def test_to_python_no_trailing_commas(self):
        field = SimpleSetField(forms.IntegerField())
        with pytest.raises(exceptions.ValidationError) as excinfo:
            field.clean('1,')
        assert (
            excinfo.value.messages[0] ==
            'No leading, trailing, or double commas.'
        )

    def test_to_python_no_double_commas(self):
        field = SimpleSetField(forms.IntegerField())
        with pytest.raises(exceptions.ValidationError) as excinfo:
            field.clean('1,,2')
        assert (
            excinfo.value.messages[0] ==
            'No leading, trailing, or double commas.'
        )

    def test_to_python_base_field_does_not_validate(self):
        field = SimpleSetField(forms.IntegerField())
        with pytest.raises(exceptions.ValidationError) as excinfo:
            field.clean('a,b,9')
        assert (
            excinfo.value.messages[0] ==
            'Item 1 in the set did not validate: Enter a whole number.'
        )

    def test_to_python_duplicates_not_allowed(self):
        field = SimpleSetField(forms.IntegerField())
        with pytest.raises(exceptions.ValidationError) as excinfo:
            field.clean('1,1')
        assert (
            excinfo.value.messages[0] ==
            "Duplicates are not supported. '1' appears twice or more."
        )

    def test_to_python_two_duplicates_not_allowed(self):
        field = SimpleSetField(forms.IntegerField())
        with pytest.raises(exceptions.ValidationError) as excinfo:
            field.clean('1,2,1,2')
        assert (
            excinfo.value.messages[0] ==
            "Duplicates are not supported. '1' appears twice or more."
        )
        assert (
            excinfo.value.messages[1] ==
            "Duplicates are not supported. '2' appears twice or more."
        )

    def test_validate_fail(self):
        field = SimpleSetField(
            forms.ChoiceField(choices=(('a', 'The letter A'),
                                       ('b', 'The letter B'))),
        )
        with pytest.raises(exceptions.ValidationError) as excinfo:
            field.clean('a,c')
        assert (
            excinfo.value.messages[0] ==
            'Item "c" in the set did not validate: '
            'Select a valid choice. c is not one of the available choices.'
        )

    def test_validators_fail(self):
        field = SimpleSetField(forms.RegexField('[a-e]{2}'))
        with pytest.raises(exceptions.ValidationError) as excinfo:
            field.clean('a,bc,de')
        assert (
            excinfo.value.messages[0] ==
            'Item "a" in the set did not validate: Enter a valid value.'
        )

    def test_validators_fail_base_max_length(self):
        field = SimpleSetField(forms.CharField(max_length=5))
        with pytest.raises(exceptions.ValidationError) as excinfo:
            field.clean('longer,yes')
        assert (
            excinfo.value.messages[0] ==
            'Item "longer" in the set did not validate: '
            'Ensure this value has at most 5 characters (it has 6).'
        )

    def test_validators_fail_base_min_max_length(self):
        # there's just no satisfying some people...
        field = SimpleSetField(forms.CharField(min_length=10, max_length=8))
        with pytest.raises(exceptions.ValidationError) as excinfo:
            field.clean('undefined')
        assert (
            excinfo.value.messages[0] ==
            'Item "undefined" in the set did not validate: '
            'Ensure this value has at least 10 characters (it has 9).'
        )
        assert (
            excinfo.value.messages[1] ==
            'Item "undefined" in the set did not validate: '
            'Ensure this value has at most 8 characters (it has 9).'
        )

    def test_prepare_value(self):
        field = SimpleSetField(forms.CharField())
        value = field.prepare_value({'a', 'b', 'c'})
        assert (
            list(sorted(value.split(','))) ==
            ['a', 'b', 'c']
        )

        assert field.prepare_value('1,a') == '1,a'

    def test_max_length(self):
        field = SimpleSetField(forms.CharField(), max_length=2)
        with pytest.raises(exceptions.ValidationError) as excinfo:
            field.clean('a,b,c')
        assert (
            excinfo.value.messages[0] ==
            'Set contains 3 items, it should contain no more than 2.'
        )

    def test_min_length(self):
        field = SimpleSetField(forms.CharField(), min_length=4)
        with pytest.raises(exceptions.ValidationError) as excinfo:
            field.clean('a,b,c')
        assert (
            excinfo.value.messages[0] ==
            'Set contains 3 items, it should contain no fewer than 4.'
        )

    def test_required(self):
        field = SimpleSetField(forms.CharField(), required=True)
        with pytest.raises(exceptions.ValidationError) as excinfo:
            field.clean('')
        assert excinfo.value.messages[0] == 'This field is required.'


class TestJSONField(SimpleTestCase):

    def test_valid(self):
        field = JSONField()
        value = field.clean('{"a": "b"}')
        assert value == {'a': 'b'}

    def test_valid_empty(self):
        field = JSONField(required=False)
        value = field.clean('')
        assert value is None

    def test_invalid(self):
        field = JSONField()
        with pytest.raises(exceptions.ValidationError) as excinfo:
            field.clean('{some badly formed: json}')
        assert (
            excinfo.value.messages[0] ==
            "'{some badly formed: json}' value must be valid JSON."
        )

    def test_prepare_value(self):
        field = JSONField()
        assert field.prepare_value({'a': 'b'}) == '{"a": "b"}'
        assert field.prepare_value(['a', 'b']) == '["a", "b"]'
        assert field.prepare_value(True) == 'true'
        assert field.prepare_value(False) == 'false'
        assert field.prepare_value(3.14) == '3.14'
        assert field.prepare_value(None) == 'null'
        assert field.prepare_value('foo') == '"foo"'

    def test_redisplay_wrong_input(self):
        """
        When displaying a bound form (typically due to invalid input), the form
        should not overquote JSONField inputs.
        """
        class JsonForm(forms.Form):
            name = forms.CharField(max_length=2)
            jfield = JSONField()

        # JSONField input is fine, name is too long
        form = JsonForm({'name': 'xyz', 'jfield': '["foo"]'})
        assert '[&quot;foo&quot;]</textarea>' in form.as_p()

        # This time, the JSONField input is wrong
        form = JsonForm({'name': 'xy', 'jfield': '{"foo"}'})
        # Appears once in the textarea and once in the error message
        assert form.as_p().count(escape('{"foo"}')) == 2

    def test_already_converted_value(self):
        field = JSONField(required=False)
        tests = [
            '["a", "b", "c"]',
            '{"a": 1, "b": 2}',
            '1',
            '1.5',
            '"foo"',
            'true',
            'false',
            'null',
        ]
        for json_string in tests:
            val = field.clean(json_string)
            assert field.clean(val) == val

    @skipUnless(django.VERSION[:2] >= (1, 9),
                "Requires Django 1.9+ for Field.disabled")
    def test_disabled(self):
        class JsonForm(forms.Form):
            jfield = JSONField(disabled=True)

        form = JsonForm({'jfield': '["bar"]'}, initial={'jfield': ['foo']})
        assert '[&quot;foo&quot;]</textarea>' in form.as_p()
