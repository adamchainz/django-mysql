# -*- coding: utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import django
from django.conf import settings
from django.core.cache import InvalidCacheBackendError, caches
from django.core.management import BaseCommand, CommandError

from django_mysql.cache import MySQLCache
from django_mysql.utils import collapse_spaces


class Command(BaseCommand):
    args = "<app_name>"

    help = collapse_spaces("""
        Outputs a migration that will create a table.
    """)

    if django.VERSION[:2] >= (1, 10):

        def add_arguments(self, parser):
            parser.add_argument(
                'aliases', metavar='aliases', nargs='*',
                help='Specify the cache alias(es) to create migrations for.'
            )

    def handle(self, *args, **options):
        if django.VERSION[:2] >= (1, 10):
            aliases = set(options['aliases'])
        else:
            aliases = set(args)

        if not aliases:
            aliases = settings.CACHES

        tables = set()
        for alias in aliases:
            try:
                cache = caches[alias]
            except InvalidCacheBackendError:
                raise CommandError("Cache '{}' does not exist".format(alias))

            if not isinstance(cache, MySQLCache):  # pragma: no cover
                continue

            tables.add(cache._table)

        if not tables:
            self.stderr.write("No MySQLCache instances in CACHES")
            return

        migration = self.render_migration(tables)
        self.stdout.write(migration)

    def render_migration(self, tables):
        # This used to use a Django template, but we can't instantiate them
        # direct now, as the user may not have the django template engine
        # defined in TEMPLATES
        out = [header]
        for table in tables:
            out.append(
                table_operation.replace('{{ table }}', table)
            )
        out.append(footer)
        return ''.join(out)


header = '''
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        # Add a dependency in here on an existing migration in the app you
        # put this migration in, for example:
        # ('myapp', '0001_initial'),
    ]

    operations = [
'''.strip()

create_table_sql = '\n'.join(
    '    ' * 3 + line
    for line in MySQLCache.create_table_sql.splitlines()
).format(table_name='{{ table }}')


table_operation = '''
        migrations.RunSQL(
            """
''' + create_table_sql + '''
            """,
            "DROP TABLE `{{ table }}`"
        ),
'''.rstrip()


footer = '''
    ]
'''
