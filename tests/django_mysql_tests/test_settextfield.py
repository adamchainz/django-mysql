# -*- coding:utf-8 -*-
from django.db.models import Q
from django.test import TestCase

from django_mysql_tests.models import BigCharSetModel


class TestSaveLoad(TestCase):

    def test_char_easy(self):
        s = BigCharSetModel.objects.create(field={"big", "comfy"})
        self.assertSetEqual(s.field, {"comfy", "big"})
        s = BigCharSetModel.objects.get(id=s.id)
        self.assertSetEqual(s.field, {"comfy", "big"})

    def test_char_cant_create_sets_with_commas(self):
        with self.assertRaises(ValueError):
            BigCharSetModel.objects.create(field={"co,mma", "contained"})

    def test_char_contains_lookup(self):
        mymodel = BigCharSetModel.objects.create(field={"mouldy", "rotten"})

        mouldy = BigCharSetModel.objects.filter(field__contains="mouldy")
        self.assertEqual(mouldy.count(), 1)
        self.assertEqual(mouldy[0], mymodel)

        rotten = BigCharSetModel.objects.filter(field__contains="rotten")
        self.assertEqual(rotten.count(), 1)
        self.assertEqual(rotten[0], mymodel)

        clean = BigCharSetModel.objects.filter(field__contains="clean")
        self.assertEqual(clean.count(), 0)

        with self.assertRaises(ValueError):
            list(BigCharSetModel.objects.filter(field__contains={"a", "b"}))

        both = BigCharSetModel.objects.filter(
            Q(field__contains="mouldy") & Q(field__contains="rotten")
        )
        self.assertEqual(both.count(), 1)
        self.assertEqual(both[0], mymodel)

        either = BigCharSetModel.objects.filter(
            Q(field__contains="mouldy") | Q(field__contains="clean")
        )
        self.assertEqual(either.count(), 1)

        not_clean = BigCharSetModel.objects.exclude(field__contains="clean")
        self.assertEqual(not_clean.count(), 1)

        not_mouldy = BigCharSetModel.objects.exclude(field__contains="mouldy")
        self.assertEqual(not_mouldy.count(), 0)

    def test_char_len_lookup_empty(self):
        mymodel = BigCharSetModel.objects.create(field=set())

        empty = BigCharSetModel.objects.filter(field__len=0)
        self.assertEqual(empty.count(), 1)
        self.assertEqual(empty[0], mymodel)

        one = BigCharSetModel.objects.filter(field__len=1)
        self.assertEqual(one.count(), 0)

        one_or_more = BigCharSetModel.objects.filter(field__len__gte=0)
        self.assertEqual(one_or_more.count(), 1)

    def test_char_len_lookup(self):
        mymodel = BigCharSetModel.objects.create(field={"red", "expensive"})

        empty = BigCharSetModel.objects.filter(field__len=0)
        self.assertEqual(empty.count(), 0)

        one_or_more = BigCharSetModel.objects.filter(field__len__gte=1)
        self.assertEqual(one_or_more.count(), 1)
        self.assertEqual(one_or_more[0], mymodel)

        two = BigCharSetModel.objects.filter(field__len=2)
        self.assertEqual(two.count(), 1)
        self.assertEqual(two[0], mymodel)

        three = BigCharSetModel.objects.filter(field__len=3)
        self.assertEqual(three.count(), 0)
