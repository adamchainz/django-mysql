# -*- coding:utf-8 -*-
from django.test import TestCase

from django_mysql.utils import WeightedAverageRate


class WeightedAverageRateTests(TestCase):

    def test_constant(self):
        # If we keep achieving a rate of 100 rows in 0.5 seconds, it should
        # recommend that we keep there
        rate = WeightedAverageRate(0.5)
        self.assertEqual(rate.update(100, 0.5), 100)
        self.assertEqual(rate.update(100, 0.5), 100)
        self.assertEqual(rate.update(100, 0.5), 100)

    def test_slow(self):
        # If we keep achieving a rate of 100 rows in 1 seconds, it should
        # recommend that we move to 50
        rate = WeightedAverageRate(0.5)
        self.assertEqual(rate.update(100, 1.0), 50)
        self.assertEqual(rate.update(100, 1.0), 50)
        self.assertEqual(rate.update(100, 1.0), 50)

    def test_fast(self):
        # If we keep achieving a rate of 100 rows in 0.25 seconds, it should
        # recommend that we move to 200
        rate = WeightedAverageRate(0.5)
        self.assertEqual(rate.update(100, 0.25), 200)
        self.assertEqual(rate.update(100, 0.25), 200)
        self.assertEqual(rate.update(100, 0.25), 200)

    def test_good_guess(self):
        # If we are first slow then hit the target at 50, we should be good
        rate = WeightedAverageRate(0.5)
        self.assertEqual(rate.update(100, 1.0), 50)
        self.assertEqual(rate.update(50, 0.5), 50)
        self.assertEqual(rate.update(50, 0.5), 50)
        self.assertEqual(rate.update(50, 0.5), 50)
