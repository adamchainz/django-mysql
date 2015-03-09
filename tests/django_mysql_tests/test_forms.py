# -*- coding:utf-8 -*-
from django import forms
from django.core import exceptions
from django.test import TestCase

from django_mysql.forms import SimpleSetField


class TestSimpleFormField(TestCase):

    def test_valid(self):
        field = SimpleSetField(forms.CharField())
        value = field.clean('a,b,c')
        self.assertEqual(value, {'a', 'b', 'c'})

    def test_to_python_fail(self):
        field = SimpleSetField(forms.IntegerField())
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean('a,b,9')
        self.assertEqual(
            cm.exception.messages[0],
            'Item 0 in the set did not validate: Enter a whole number.'
        )

    def test_validate_fail(self):
        field = SimpleSetField(forms.CharField(required=True))
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean('a,b,')
        self.assertEqual(
            cm.exception.messages[0],
            'Item "" in the set did not validate: This field is required.'
        )

    def test_validators_fail(self):
        field = SimpleSetField(forms.RegexField('[a-e]{2}'))
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean('a,bc,de')
        self.assertEqual(
            cm.exception.messages[0],
            'Item "a" in the set did not validate: Enter a valid value.'
        )

    def test_prepare_value(self):
        field = SimpleSetField(forms.CharField())
        value = field.prepare_value({'a', 'b', 'c'})
        self.assertEqual(
            list(sorted(value.split(','))),
            ['a', 'b', 'c']
        )

    def test_max_length(self):
        field = SimpleSetField(forms.CharField(), max_length=2)
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean('a,b,c')
        self.assertEqual(
            cm.exception.messages[0],
            'Set contains 3 items, it should contain no more than 2.'
        )

    def test_min_length(self):
        field = SimpleSetField(forms.CharField(), min_length=4)
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean('a,b,c')
        self.assertEqual(
            cm.exception.messages[0],
            'Set contains 3 items, it should contain no fewer than 4.'
        )

    def test_required(self):
        field = SimpleSetField(forms.CharField(), required=True)
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean('')
        self.assertEqual(cm.exception.messages[0], 'This field is required.')
