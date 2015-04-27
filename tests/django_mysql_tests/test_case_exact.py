# -*- coding:utf-8 -*-
from django.test import TestCase

from django_mysql_tests.models import Author


class CaseExactTests(TestCase):

    def test_case_sensitive_exact(self):
        dickie = Author.objects.create(name="Dickens")

        authors = Author.objects.filter(name__case_exact="dickens")
        self.assertEqual(list(authors), [])

        authors = Author.objects.filter(name__case_exact="Dickens")
        self.assertEqual(list(authors), [dickie])

        authors = Author.objects.filter(name__case_exact="DICKENS")
        self.assertEqual(list(authors), [])
