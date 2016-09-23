# -*- coding:utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from django.test import TestCase

from testapp.models import Author


class CaseExactTests(TestCase):

    def test_charfield(self):
        dickie = Author.objects.create(name="Dickens")

        authors = Author.objects.filter(name__case_exact="dickens")
        assert list(authors) == []

        authors = Author.objects.filter(name__case_exact="Dickens")
        assert list(authors) == [dickie]

        authors = Author.objects.filter(name__case_exact="DICKENS")
        assert list(authors) == []

    def test_charfield_lowercase(self):
        dickie = Author.objects.create(name="dickens")

        authors = Author.objects.filter(name__case_exact="dickens")
        assert list(authors) == [dickie]

        authors = Author.objects.filter(name__case_exact="Dickens")
        assert list(authors) == []

    def test_textfield(self):
        dickie = Author.objects.create(name="Dickens", bio="Aged 10, bald.")

        authors = Author.objects.filter(bio__case_exact="Aged 10, bald.")
        assert list(authors) == [dickie]

        authors = Author.objects.filter(bio__case_exact="Aged 10, BALD.")
        assert list(authors) == []


class SoundexTests(TestCase):

    def test_sounds_like_lookup(self):
        principles = ["principle", "principal", "princpl"]
        created = {Author.objects.create(name=name) for name in principles}

        for name in principles:
            sounding = Author.objects.filter(name__sounds_like=name)
            assert set(sounding) == created

        sounding = Author.objects.filter(name__sounds_like='')
        assert set(sounding) == set()

        sounding = Author.objects.filter(name__sounds_like='nothing')
        assert set(sounding) == set()

    def test_soundex_strings(self):
        author = Author.objects.create(name='Robert')
        assert Author.objects.get(name__soundex='R163') == author
