# -*- coding:utf-8 -*-
from django.test import TestCase

from django_mysql.models import BitAnd, BitOr, GroupConcat
from django_mysql_tests.models import Alphabet, Author


class BitAndTests(TestCase):

    def test_implicit_name(self):
        Alphabet.objects.bulk_create([Alphabet(a=29), Alphabet(a=15)])
        out = Alphabet.objects.all().aggregate(BitAnd('a'))
        self.assertEqual(out, {'a__bitand': 13})

    def test_explicit_name(self):
        Alphabet.objects.bulk_create([Alphabet(a=11), Alphabet(a=24)])
        out = Alphabet.objects.all().aggregate(aaa=BitAnd('a'))
        self.assertEqual(out, {'aaa': 8})

    def test_no_rows(self):
        out = Alphabet.objects.all().aggregate(BitAnd('a'))
        # Manual:
        # "This function returns 18446744073709551615 if there were no matching
        # rows. (This is the value of an unsigned BIGINT value with all bits
        # set to 1.)"
        self.assertEqual(out, {'a__bitand': 18446744073709551615})


class BitOrTests(TestCase):

    def test_implicit_name(self):
        Alphabet.objects.bulk_create([Alphabet(a=1), Alphabet(a=84)])
        out = Alphabet.objects.all().aggregate(BitOr('a'))
        self.assertEqual(out, {'a__bitor': 85})

    def test_explicit_name(self):
        Alphabet.objects.bulk_create([Alphabet(a=29), Alphabet(a=15)])
        out = Alphabet.objects.all().aggregate(aaa=BitOr('a'))
        self.assertEqual(out, {'aaa': 31})

    def test_no_rows(self):
        out = Alphabet.objects.all().aggregate(BitOr('a'))
        # Manual:
        # "This function returns 0 if there were no matching rows."
        self.assertEqual(out, {'a__bitor': 0})


class GroupConcatTests(TestCase):

    def setUp(self):
        self.shakes = Author.objects.create(name='William Shakespeare')
        self.jk = Author.objects.create(name='JK Rowling', tutor=self.shakes)
        self.grisham = Author.objects.create(name='Grisham', tutor=self.shakes)

        self.str_tutee_ids = [str(self.jk.id), str(self.grisham.id)]

    def test_basic_aggregate_ids(self):
        out = self.shakes.tutees.aggregate(tids=GroupConcat('id'))
        concatted_ids = ",".join(self.str_tutee_ids)
        self.assertEqual(out, {'tids': concatted_ids})

    def test_basic_annotate_ids(self):
        concat = GroupConcat('tutees__id')
        shakey = Author.objects.annotate(tids=concat).get(id=self.shakes.id)
        concatted_ids = ",".join(self.str_tutee_ids)
        self.assertEqual(shakey.tids, concatted_ids)

    def test_separator(self):
        concat = GroupConcat('id', separator=':')
        out = self.shakes.tutees.aggregate(tids=concat)
        concatted_ids = ":".join(self.str_tutee_ids)
        self.assertEqual(out, {'tids': concatted_ids})

    def test_separator_empty(self):
        concat = GroupConcat('id', separator='')
        out = self.shakes.tutees.aggregate(tids=concat)
        concatted_ids = "".join(self.str_tutee_ids)
        self.assertEqual(out, {'tids': concatted_ids})

    def test_separator_big(self):
        concat = GroupConcat('id', separator='BIG')
        out = self.shakes.tutees.aggregate(tids=concat)
        concatted_ids = "BIG".join(self.str_tutee_ids)
        self.assertEqual(out, {'tids': concatted_ids})

    def test_order(self):
        out = (
            Author.objects
                  .exclude(id=self.shakes.id)
                  .aggregate(tids=GroupConcat('tutor_id', distinct=True))
        )
        self.assertEqual(out, {'tids': str(self.shakes.id)})
