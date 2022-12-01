from __future__ import annotations

from django.db import models
from django.db.models.expressions import OuterRef, Subquery
from django.test import TestCase

from django_mysql.models import GroupConcat, ListCharField
from tests.testapp.models import Author, Book


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

        sounding = Author.objects.filter(name__sounds_like="")
        assert set(sounding) == set()

        sounding = Author.objects.filter(name__sounds_like="nothing")
        assert set(sounding) == set()

    def test_soundex_strings(self):
        author = Author.objects.create(name="Robert")
        assert Author.objects.get(name__soundex="R163") == author


class SetContainsTests(TestCase):
    def test_group_concat_contains(self):
        tolkien = Author.objects.create(name="Tolkien")
        the_lotr = Book.objects.create(title="The Lord of the Rings", author=tolkien)
        the_hobbit = Book.objects.create(title="The Hobbit", author=tolkien)
        Book.objects.create(title="Unfinished Tales", author=tolkien)

        starting_with_the = Book.objects.filter(title__startswith='The', author=OuterRef('pk')).order_by().values('author')
        concatenated_titles = starting_with_the.annotate(the_titles=GroupConcat('title', output_field=ListCharField(models.CharField()))).values('the_titles')
        qs = Author.objects.annotate(titles=Subquery(concatenated_titles)).filter(titles__contains='The Hobbit')
        tolkien_with_titles = qs.get()

        assert len(tolkien_with_titles.titles) == 2
        assert tolkien_with_titles.titles == [the_lotr.title, the_hobbit.title]
