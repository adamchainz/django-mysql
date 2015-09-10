# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase

from django_mysql.paginator import FoundRowsPaginator
from testapp.models import Author


class FoundRowsPaginatorTests(TestCase):
    def setUp(self):
        super(FoundRowsPaginatorTests, self).setUp()
        Author.objects.bulk_create([Author() for i in range(10)])

    def test_basic(self):
        paginator = FoundRowsPaginator(Author.objects.all(), 2)
        with self.assertNumQueries(2) as cap:
            list(paginator.page(1))
        sqls = [query['sql'] for query in cap.captured_queries]
        assert sqls[1] == "SELECT FOUND_ROWS()"

        self.assertTrue(hasattr(paginator, 'found_rows'))
        self.assertEqual(paginator.found_rows, 10)
        with self.assertNumQueries(1) as cap:
            list(paginator.page(2))

        assert "SQL_CALC_FOUND_ROWS" not in cap.captured_queries[-1]['sql']

    def test_orphans(self):
        paginator = FoundRowsPaginator(Author.objects.all(), 4, orphans=2)
        with self.assertNumQueries(2) as cap:
            objs = list(paginator.page(2))
        sqls = [query['sql'] for query in cap.captured_queries]
        assert sqls[1] == "SELECT FOUND_ROWS()"
        self.assertEqual(len(objs), 6)
