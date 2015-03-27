# -*- coding:utf-8 -*-
from django.test import TestCase

from django_mysql.models import GroupConcat

from django_mysql_tests.models import Author


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
