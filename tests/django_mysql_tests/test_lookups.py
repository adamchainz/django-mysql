# -*- coding:utf-8 -*-
from django.test import TestCase

from django_mysql_tests.models import Author


class CaseExactTests(TestCase):

    def test_charfield(self):
        dickie = Author.objects.create(name="Dickens")

        authors = Author.objects.filter(name__case_exact="dickens")
        self.assertEqual(list(authors), [])

        authors = Author.objects.filter(name__case_exact="Dickens")
        self.assertEqual(list(authors), [dickie])

        authors = Author.objects.filter(name__case_exact="DICKENS")
        self.assertEqual(list(authors), [])

    def test_charfield_lowercase(self):
        dickie = Author.objects.create(name="dickens")

        authors = Author.objects.filter(name__case_exact="dickens")
        self.assertEqual(list(authors), [dickie])

        authors = Author.objects.filter(name__case_exact="Dickens")
        self.assertEqual(list(authors), [])

    def test_textfield(self):
        dickie = Author.objects.create(name="Dickens", bio="Aged 10, bald.")

        authors = Author.objects.filter(bio__case_exact="Aged 10, bald.")
        self.assertEqual(list(authors), [dickie])

        authors = Author.objects.filter(bio__case_exact="Aged 10, BALD.")
        self.assertEqual(list(authors), [])


class SoundexTests(TestCase):

    def test_sounds_like_lookup(self):
        principles = ["principle", "principal", "princpl"]
        created = {Author.objects.create(name=name) for name in principles}

        for name in principles:
            sounding = Author.objects.filter(name__sounds_like=name)
            self.assertEqual(set(sounding), created)

        sounding = Author.objects.filter(name__sounds_like='')
        self.assertEqual(set(sounding), set())

        sounding = Author.objects.filter(name__sounds_like='nothing')
        self.assertEqual(set(sounding), set())

    def test_soundex_strings(self):
        author = Author.objects.create(name='Robert')
        self.assertEqual(Author.objects.get(name__soundex='R163'), author)
