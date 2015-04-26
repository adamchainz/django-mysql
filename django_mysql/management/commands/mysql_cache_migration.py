# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.core.cache import InvalidCacheBackendError, caches
from django.core.management import BaseCommand, CommandError
from django.template import Context, Template

from django_mysql.cache import MySQLCache
from django_mysql.utils import collapse_spaces


class Command(BaseCommand):
    args = "<app_name>"

    help = collapse_spaces("""
        Outputs a migration that will create a table.
    """)

    def handle(self, *aliases, **options):
        if aliases:
            names = set(aliases)
        else:
            names = settings.CACHES

        tables = []
        for alias in names:
            try:
                cache = caches[alias]
            except InvalidCacheBackendError:
                raise CommandError("Cache '{}' does not exist".format(alias))

            if not isinstance(cache, MySQLCache):  # pragma: no cover
                continue

            tables.append({'name': cache._table})

        if not tables:
            self.stderr.write("No MySQLCache instances in CACHES")
            return

        context = Context({'tables': tables})
        migration = migration_template.render(context)
        self.stdout.write(migration)


create_table_sql = '\n'.join(
    '    ' * 3 + line
    for line in MySQLCache.create_table_sql.splitlines()
).format(table_name='{{ table.name }}')

migration_template = Template('''
from django.db import migrations


class Migration(migrations.Migration):

    operations = [{% for table in tables %}
        migrations.RunSQL(
            """
            {create_table}
            """,
            "DROP TABLE `{{ table.name }}`;"
        ),{% endfor %}
    ]
'''.lstrip().replace('{create_table}', create_table_sql))
