# -*- coding:utf-8 -*-
from django.db.models import F
from django.test import TestCase

from django_mysql_tests.models import Author


class HandlerTests(TestCase):
    def setUp(self):
        Author.objects.create(name='JK Rowling')
        Author.objects.create(name='John Grisham')

    def test_simple(self):
        qs_all = list(Author.objects.order_by('id'))

        with Author.objects.handler() as handler:
            handler_all = list(handler.read(limit=10000))

        self.assertEqual(handler_all, qs_all)

    def test_limit(self):
        qs_first = Author.objects.earliest('id')

        with Author.objects.handler() as handler:
            handler_first = handler.read(limit=1)[0]

        self.assertEqual(handler_first, qs_first)

    def test_filter(self):
        qs = Author.objects.filter(name__startswith='John')

        with qs._clone().handler() as handler:
            handler_all = list(handler.read())
        qs_all = list(qs._clone())

        self.assertEqual(handler_all, qs_all)

    def test_exclude(self):
        qs = Author.objects.filter(name__contains='JK')
        qs_all = list(qs._clone())

        with qs._clone().handler() as handler:
            handler_all = list(handler.read())

        self.assertEqual(handler_all, qs_all)

    def test_filter_sql_name(self):
        # Check that params are kept as params and no SQL injection occurs
        table_col = "`something`.`something`"
        author = Author.objects.create(name=table_col)
        qs = Author.objects.filter(name=table_col)

        with qs.handler() as handler:
            handler_all = list(handler.read(limit=100))

        self.assertEqual(handler_all, [author])

    def test_bad_read_unopened(self):
        handler = Author.objects.all().handler()
        with self.assertRaises(RuntimeError):
            handler.read()

    def test_bad_read_mode(self):
        with Author.objects.all().handler() as handler:
            with self.assertRaises(ValueError):
                handler.read(mode='non-existent')

    def test_iter(self):
        qs = Author.objects.all()

        with qs.handler() as handler:
            seen_pks = []
            for author in handler.iter(chunk_size=1):
                seen_pks.append(author.pk)

        all_pks = qs.values_list('id', flat=True)
        self.assertEqual(seen_pks, list(sorted(all_pks)))

    def test_iter_reverse(self):
        qs = Author.objects.all()

        with qs.handler() as handler:
            seen_pks = []
            for author in handler.iter(chunk_size=1, forwards=False):
                seen_pks.append(author.pk)

        all_pks = qs.values_list('id', flat=True)
        self.assertEqual(seen_pks, list(sorted(all_pks, reverse=True)))

    def test_filter_f_expression(self):
        qs = Author.objects.filter(name=F('name'))

        with qs.handler() as handler:
            handler_all = list(handler.read(limit=100))

        self.assertEqual(len(handler_all), 2)

    def test_bad_filter_joins_not_allowed(self):
        qs = Author.objects.filter(tutor__name='A')
        with self.assertRaises(ValueError):
            qs.handler()

    def test_bad_filter_limit_not_allowed(self):
        qs = Author.objects.all()[:100]
        with self.assertRaises(ValueError):
            qs.handler()
