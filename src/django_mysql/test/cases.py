from __future__ import unicode_literals

import sys

from django.apps import apps
from django.db import connections, transaction
from django.db.models.fields import AutoField
from django.core.management.base import CommandError
from django.core.management import call_command
from django.test import TransactionTestCase
from django.utils import six


models_without_auto_inc = []


def find_models_without_auto_inc():
    all_models = apps.get_models()
    for model in all_models:
        fields = model._meta.fields
        has_auto = False
        for field in fields:
            if isinstance(field, AutoField):
                has_auto = True
                break
        if not has_auto:
            models_without_auto_inc.append(model._meta.db_table)


if not models_without_auto_inc:
    find_models_without_auto_inc()


class FasterTransactionTestCase(TransactionTestCase):
    def _fixture_teardown(self):
        # Allow TRUNCATE ... CASCADE and don't emit the post_migrate signal
        # when flushing only a subset of the apps
        for db_name in self._databases_names(include_mirrors=False):
            # Flush the database
            inhibit_post_migrate = (
                self.available_apps is not None or (
                    # Inhibit the post_migrate signal when using serialized
                    # rollback to avoid trying to recreate the serialized data.
                    self.serialized_rollback and
                    hasattr(connections[db_name], '_test_serialized_contents')
                )
            )
            connection = connections[db_name]
            if "mysql" in connection.settings_dict['ENGINE']:
                tables = connection.introspection.django_table_names(only_existing=True, include_views=False)
                schema_name = connection.settings_dict['NAME']

                # auto_increment is reliable, but table_rows isn't
                # if we have a table without an auto_incrementing field then
                # do a COUNT and only TRUNCATE if it has rows
                used_tables_sql = """
                   SELECT table_name
                   FROM information_schema.tables
                   WHERE (auto_increment IS NOT NULL AND auto_increment > 1) OR table_rows > 0
                     AND table_schema = %s"""
                used_tables_set = set()
                with connection.cursor() as cursor:
                    cursor.execute(used_tables_sql, (schema_name, ))
                    used_tables = cursor.fetchall()
                for used_table in used_tables:
                    used_tables_set.add(used_table[0])

                for model_name in models_without_auto_inc:
                    if model_name in tables:
                        with connection.cursor() as cursor:
                            cursor.execute("SELECT COUNT(1) FROM {}".format(model_name))
                            count = cursor.fetchone()
                        if count[0] > 0:
                            used_tables_set.add(model_name)

                sql_list = ['SET FOREIGN_KEY_CHECKS=0;']
                for table in tables:
                    if table in used_tables_set:
                        sql_list.append("TRUNCATE %s;" % table)
                sql_list.append('SET FOREIGN_KEY_CHECKS=1;')

                try:
                    with transaction.atomic(using=db_name,
                                            savepoint=connection.features.can_rollback_ddl):
                        with connection.cursor() as cursor:
                            for sql in sql_list:
                                cursor.execute(sql)
                except Exception as e:
                    new_msg = (
                        "Database %s couldn't be flushed. Possible reasons:\n"
                        "  * The database isn't running or isn't configured correctly.\n"
                        "  * At least one of the expected database tables doesn't exist.\n"
                        "  * The SQL was invalid.\n"
                        "Hint: Look at the output of 'django-admin sqlflush'. "
                        "That's the SQL this command wasn't able to run.\n"
                        "The full error: %s") % (connection.settings_dict['NAME'], e)
                    six.reraise(CommandError, CommandError(new_msg), sys.exc_info()[2])
            else:
                call_command('flush', verbosity=0, interactive=False,
                             database=db_name, reset_sequences=False,
                             allow_cascade=self.available_apps is not None,
                             inhibit_post_migrate=inhibit_post_migrate)
