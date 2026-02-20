from __future__ import annotations

from django.db import connection
from django.test import SimpleTestCase, TransactionTestCase

from django_mysql.models.indexes import ColumnPrefixIndex
from tests.testapp.models import CharSetModel


class ColumnPrefixIndexTests(SimpleTestCase):
    def test_deconstruct(self):
        index = ColumnPrefixIndex(
            fields=["field", "field2"],
            prefix_lengths=(10, 20),
            name="dm_field_field2_pfx",
        )
        path, args, kwargs = index.deconstruct()
        self.assertEqual(path, "django_mysql.models.indexes.ColumnPrefixIndex")
        self.assertEqual(args, ())
        self.assertEqual(
            kwargs,
            {
                "name": "dm_field_field2_pfx",
                "fields": ["field", "field2"],
                "prefix_lengths": (10, 20),
            },
        )


class SchemaTests(TransactionTestCase):
    def get_constraints(self, table):
        return connection.introspection.get_constraints(connection.cursor(), table)

    def test_column_prefix_index_create_sql(self):
        index = ColumnPrefixIndex(
            fields=["field", "field2"],
            prefix_lengths=(10, 20),
            name="dm_name_email_pfx",
        )
        with connection.schema_editor() as editor:
            statement = index.create_sql(CharSetModel, editor)
            sql = str(statement)

        self.assertIn("`field`(10)", sql)
        self.assertIn("`field2`(20)", sql)

    def test_column_prefix_index(self):
        table = CharSetModel._meta.db_table
        index_name = "dm_name_email_pfx"
        index = ColumnPrefixIndex(
            fields=["field", "field2"], prefix_lengths=(10, 20), name=index_name
        )

        # Ensure the table is there and doesn't have an index.
        self.assertNotIn(index_name, self.get_constraints(table))

        # Add the index.
        with connection.schema_editor() as editor:
            editor.add_index(CharSetModel, index)

        constraints = self.get_constraints(table)
        self.assertIn(index_name, constraints)
        self.assertEqual(constraints[index_name]["type"], ColumnPrefixIndex.suffix)

        # Drop the index.
        with connection.schema_editor() as editor:
            editor.remove_index(CharSetModel, index)
        self.assertNotIn(index_name, self.get_constraints(table))
