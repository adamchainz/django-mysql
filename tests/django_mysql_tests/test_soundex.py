# -*- coding:utf-8 -*-
from django.test import TestCase

from django_mysql_tests.models import Author


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
        author = Author.objects.create(name='hi')
        self.assertEqual(Author.objects.get(name__soundex='H000'), author)
