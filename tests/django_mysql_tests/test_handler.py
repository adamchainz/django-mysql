# -*- coding:utf-8 -*-
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
