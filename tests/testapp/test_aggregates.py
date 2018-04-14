# -*- coding:utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)

import pytest
from django.db.models import F
from django.test import TestCase

from django_mysql.models import BitAnd, BitOr, BitXor, GroupConcat
from django_mysql.test.utils import override_mysql_variables
from testapp.models import Alphabet, Author


class BitAndTests(TestCase):

    def test_implicit_name(self):
        Alphabet.objects.bulk_create([Alphabet(a=29), Alphabet(a=15)])
        out = Alphabet.objects.all().aggregate(BitAnd('a'))
        assert out == {'a__bitand': 13}

    def test_explicit_name(self):
        Alphabet.objects.bulk_create([Alphabet(a=11), Alphabet(a=24)])
        out = Alphabet.objects.all().aggregate(aaa=BitAnd('a'))
        assert out == {'aaa': 8}

    def test_no_rows(self):
        out = Alphabet.objects.all().aggregate(BitAnd('a'))
        # Manual:
        # "This function returns 18446744073709551615 if there were no matching
        # rows. (This is the value of an unsigned BIGINT value with all bits
        # set to 1.)"
        assert out == {'a__bitand': 18446744073709551615}


class BitOrTests(TestCase):

    def test_implicit_name(self):
        Alphabet.objects.bulk_create([Alphabet(a=1), Alphabet(a=84)])
        out = Alphabet.objects.all().aggregate(BitOr('a'))
        assert out == {'a__bitor': 85}

    def test_explicit_name(self):
        Alphabet.objects.bulk_create([Alphabet(a=29), Alphabet(a=15)])
        out = Alphabet.objects.all().aggregate(aaa=BitOr('a'))
        assert out == {'aaa': 31}

    def test_no_rows(self):
        out = Alphabet.objects.all().aggregate(BitOr('a'))
        # Manual:
        # "This function returns 0 if there were no matching rows."
        assert out == {'a__bitor': 0}


class BitXorTests(TestCase):

    def test_implicit_name(self):
        Alphabet.objects.bulk_create([Alphabet(a=11), Alphabet(a=3)])
        out = Alphabet.objects.all().aggregate(BitXor('a'))
        assert out == {'a__bitxor': 8}

    def test_explicit_name(self):
        Alphabet.objects.bulk_create([Alphabet(a=123), Alphabet(a=456)])
        out = Alphabet.objects.all().aggregate(aaa=BitXor('a'))
        assert out == {'aaa': 435}

    def test_no_rows(self):
        out = Alphabet.objects.all().aggregate(BitXor('a'))
        # Manual:
        # "This function returns 0 if there were no matching rows."
        assert out == {'a__bitxor': 0}


class GroupConcatTests(TestCase):

    def setUp(self):
        super(GroupConcatTests, self).setUp()
        self.shakes = Author.objects.create(name='William Shakespeare')
        self.jk = Author.objects.create(name='JK Rowling', tutor=self.shakes)
        self.grisham = Author.objects.create(name='Grisham', tutor=self.shakes)

        self.str_tutee_ids = [str(self.jk.id), str(self.grisham.id)]

    def test_basic_aggregate_ids(self):
        out = self.shakes.tutees.aggregate(tids=GroupConcat('id'))
        concatted_ids = ",".join(self.str_tutee_ids)
        assert out == {'tids': concatted_ids}

    def test_basic_annotate_ids(self):
        concat = GroupConcat('tutees__id')
        shakey = Author.objects.annotate(tids=concat).get(id=self.shakes.id)
        concatted_ids = ",".join(self.str_tutee_ids)
        assert shakey.tids, concatted_ids

    def test_separator(self):
        concat = GroupConcat('id', separator=':')
        out = self.shakes.tutees.aggregate(tids=concat)
        concatted_ids = ":".join(self.str_tutee_ids)
        assert out == {'tids': concatted_ids}

    def test_separator_empty(self):
        concat = GroupConcat('id', separator='')
        out = self.shakes.tutees.aggregate(tids=concat)
        concatted_ids = "".join(self.str_tutee_ids)
        assert out == {'tids': concatted_ids}

    def test_separator_big(self):
        concat = GroupConcat('id', separator='BIG')
        out = self.shakes.tutees.aggregate(tids=concat)
        concatted_ids = "BIG".join(self.str_tutee_ids)
        assert out == {'tids': concatted_ids}

    def test_expression(self):
        concat = GroupConcat(F('id') + 1)
        out = self.shakes.tutees.aggregate(tids=concat)
        concatted_ids = ",".join([
            str(self.jk.id + 1),
            str(self.grisham.id + 1),
        ])
        assert out == {'tids': concatted_ids}

    def test_application_order(self):
        out = (
            Author.objects
                  .exclude(id=self.shakes.id)
                  .aggregate(tids=GroupConcat('tutor_id', distinct=True))
        )
        assert out == {'tids': str(self.shakes.id)}

    @override_mysql_variables(SQL_MODE="ANSI")
    def test_separator_ansi_mode(self):
        concat = GroupConcat('id', separator='>>')
        out = self.shakes.tutees.aggregate(tids=concat)
        concatted_ids = ">>".join(self.str_tutee_ids)
        assert out == {'tids': concatted_ids}

    def test_ordering_invalid(self):
        with pytest.raises(ValueError) as excinfo:
            self.shakes.tutees.aggregate(
                tids=GroupConcat('id', ordering='asceding'),
            )
        assert "'ordering' must be one of" in str(excinfo.value)

    def test_ordering_asc(self):
        out = self.shakes.tutees.aggregate(
            tids=GroupConcat('id', ordering='asc'),
        )
        assert out == {'tids': ",".join(self.str_tutee_ids)}

    def test_ordering_desc(self):
        out = self.shakes.tutees.aggregate(
            tids=GroupConcat('id', ordering='desc'),
        )
        assert out == {'tids': ",".join(reversed(self.str_tutee_ids))}
