# -*- coding:utf-8 -*-
from django.test import TestCase

from django_mysql_tests.models import Settee


class SetCharFieldTests(TestCase):

    def test_easy(self):
        s = Settee.objects.create(features={"big", "comfy"})
        self.assertSetEqual(s.features, {"comfy", "big"})
        s = Settee.objects.get(id=s.id)
        self.assertSetEqual(s.features, {"comfy", "big"})

    def test_cant_create_sets_with_commas(self):
        with self.assertRaises(AssertionError):
            Settee.objects.create(features={"co,ma", "contained"})

    def test_has_lookup(self):
        sofa = Settee.objects.create(features={"mouldy", "rotten"})

        mouldy = Settee.objects.filter(features__has="mouldy")
        self.assertEqual(mouldy.count(), 1)
        self.assertEqual(mouldy[0], sofa)

        rotten = Settee.objects.filter(features__has="rotten")
        self.assertEqual(rotten.count(), 1)
        self.assertEqual(rotten[0], sofa)

        clean = Settee.objects.filter(features__has="clean")
        self.assertEqual(clean.count(), 0)

        clean = Settee.objects.filter(features__has={"mouldy", "rotten"})
        self.assertEqual(clean.count(), 0)

    def test_len_lookup(self):
        sofa = Settee.objects.create(features={"leather", "expensive"})

        empty = Settee.objects.filter(features__len=0)
        self.assertEqual(empty.count(), 0)

        one_or_more = Settee.objects.filter(features__len__gte=1)
        self.assertEqual(one_or_more.count(), 1)
        self.assertEqual(one_or_more[0], sofa)

        two = Settee.objects.filter(features__len=2)
        self.assertEqual(two.count(), 1)
        self.assertEqual(two[0], sofa)

        three = Settee.objects.filter(features__len=3)
        self.assertEqual(three.count(), 0)
