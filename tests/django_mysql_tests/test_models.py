# -*- coding:utf-8 -*-
from django.template import Context, Template
from django.test import TransactionTestCase

from django_mysql_tests.models import Author


class ApproximateCountTests(TransactionTestCase):

    def setUp(self):
        super(ApproximateCountTests, self).setUp()
        Author.objects.bulk_create([Author() for i in range(10)])

    def test_approx_count(self):
        # Theoretically this varies 30-50% of the table size
        # For a fresh table with 10 items we seem to always get back the actual
        # count, but to be sure we'll just assert it's within 55%
        approx_count = Author.objects.approx_count(min_size=1)
        self.assertGreaterEqual(approx_count, 4)
        self.assertLessEqual(approx_count, 16)

    def test_activation_deactivation(self):
        qs = Author.objects.all()
        self.assertFalse(qs._count_tries_approx)

        qs2 = qs.count_tries_approx(min_size=2)
        self.assertNotEqual(qs, qs2)
        self.assertTrue(qs2._count_tries_approx)

        qs3 = qs2.count_tries_approx(False)
        self.assertNotEqual(qs2, qs3)
        self.assertFalse(qs3._count_tries_approx)

    def test_output_in_templates(self):
        approx_count = Author.objects.approx_count(min_size=1)
        text = Template('{{ var }}').render(Context({'var': approx_count}))
        self.assertTrue(text.startswith('Approximately '))

        approx_count2 = Author.objects.approx_count(
            min_size=1,
            return_approx_int=False
        )
        text = Template('{{ var }}').render(Context({'var': approx_count2}))
        self.assertFalse(text.startswith('Approximately '))

    def test_fallback_with_filters(self):
        filtered = Author.objects.filter(name='')
        self.assertEqual(filtered.approx_count(fall_back=True), 10)
        with self.assertRaises(ValueError):
            filtered.approx_count(fall_back=False)

    def test_fallback_with_slice(self):
        self.assertEqual(Author.objects.all()[:100].approx_count(), 10)
        with self.assertRaises(ValueError):
            Author.objects.all()[:100].approx_count(fall_back=False)

    def test_fallback_with_distinct(self):
        self.assertEqual(Author.objects.distinct().approx_count(), 10)
        with self.assertRaises(ValueError):
            Author.objects.distinct().approx_count(fall_back=False)
