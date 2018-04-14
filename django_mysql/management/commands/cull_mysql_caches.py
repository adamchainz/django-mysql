# -*- coding: utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)

import django
from django.conf import settings
from django.core.cache import InvalidCacheBackendError, caches
from django.core.management import BaseCommand, CommandError

from django_mysql.cache import MySQLCache
from django_mysql.utils import collapse_spaces


class Command(BaseCommand):
    args = "<optional cache aliases>"

    help = collapse_spaces("""
        Runs cache.cull() on all your MySQLCache caches, or only those
        specified aliases.
    """)

    if django.VERSION[:2] >= (1, 10):

        def add_arguments(self, parser):
            parser.add_argument(
                'aliases', metavar='aliases', nargs='*',
                help='Specify the cache alias(es) to cull.',
            )

    def handle(self, *args, **options):
        verbosity = options.get('verbosity')

        if django.VERSION[:2] >= (1, 10):
            aliases = set(options['aliases'])
        else:
            aliases = set(args)

        if not aliases:
            aliases = settings.CACHES

        for alias in aliases:
            try:
                cache = caches[alias]
            except InvalidCacheBackendError:
                raise CommandError("Cache '{}' does not exist".format(alias))

            if not isinstance(cache, MySQLCache):  # pragma: no cover
                continue

            if verbosity >= 1:
                self.stdout.write(
                    "Deleting from cache '{}'... ".format(alias),
                    ending='',
                )
            num_deleted = cache.cull()
            if verbosity >= 1:
                self.stdout.write("{} entries deleted.".format(num_deleted))
