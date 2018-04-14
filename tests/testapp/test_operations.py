# -*- coding:utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)

from unittest import SkipTest

import pytest
from django.db import connection, migrations, models, transaction
from django.db.migrations.state import ProjectState
from django.test import TransactionTestCase
from django.test.utils import CaptureQueriesContext

from django_mysql.operations import (
    AlterStorageEngine, InstallPlugin, InstallSOName,
)
from django_mysql.test.utils import override_mysql_variables
from django_mysql.utils import connection_is_mariadb


def plugin_exists(plugin_name):
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT COUNT(*) FROM INFORMATION_SCHEMA.PLUGINS
               WHERE PLUGIN_NAME = %s""",
            (plugin_name,),
        )
        return (cursor.fetchone()[0] > 0)


def table_storage_engine(table_name):
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT ENGINE FROM INFORMATION_SCHEMA.TABLES
               WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s""",
            (table_name,),
        )
        return cursor.fetchone()[0]


class PluginOperationTests(TransactionTestCase):

    @classmethod
    def setUpClass(cls):
        super(PluginOperationTests, cls).setUpClass()
        has_metadata_lock_plugin = (
            connection_is_mariadb(connection) and
            connection.mysql_version >= (10, 0, 7)
        )
        if not has_metadata_lock_plugin:
            raise SkipTest("The metadata_lock_info plugin is required")

    def test_install_plugin(self):
        """
        Test we can load the example plugin that every version of MySQL ships
        with.
        """
        assert not plugin_exists("metadata_lock_info")

        state = ProjectState()
        operation = InstallPlugin("metadata_lock_info",
                                  "metadata_lock_info.so")
        assert (
            operation.describe() ==
            "Installs plugin metadata_lock_info from metadata_lock_info.so"
        )
        new_state = state.clone()
        with connection.schema_editor() as editor:
            operation.database_forwards("testapp", editor,
                                        state, new_state)

        assert plugin_exists("metadata_lock_info")

        new_state = state.clone()
        with connection.schema_editor() as editor:
            operation.database_backwards("testapp", editor,
                                         new_state, state)

        assert not plugin_exists("metadata_lock_info")

    def test_install_soname(self):
        """
        Test we can load the 'metadata_lock_info' library.
        """
        assert not plugin_exists("metadata_lock_info")

        state = ProjectState()
        operation = InstallSOName("metadata_lock_info.so")
        assert operation.describe() == "Installs library metadata_lock_info.so"

        new_state = state.clone()
        with connection.schema_editor() as editor:
            operation.database_forwards("testapp", editor,
                                        state, new_state)
        assert plugin_exists("metadata_lock_info")

        new_state = state.clone()
        with connection.schema_editor() as editor:
            operation.database_backwards("testapp", editor,
                                         new_state, state)
        assert not plugin_exists("metadata_lock_info")


class AlterStorageEngineTests(TransactionTestCase):

    def test_no_from_means_unreversible(self):
        operation = AlterStorageEngine("mymodel", to_engine="InnoDB")
        assert not operation.reversible

        with pytest.raises(NotImplementedError) as excinfo:
            operation.database_backwards(None, None, None, None)

        assert str(excinfo.value) == "You cannot reverse this operation"

    def test_from_means_reversible(self):
        operation = AlterStorageEngine("mymodel", from_engine="MyISAM",
                                       to_engine="InnoDB")
        assert operation.reversible

    def test_describe_without_from(self):
        operation = AlterStorageEngine("Pony", "InnoDB")
        assert (operation.describe() ==
                "Alter storage engine for Pony to InnoDB")

    def test_describe_with_from(self):
        operation = AlterStorageEngine("Pony", from_engine="MyISAM",
                                       to_engine="InnoDB")
        assert (operation.describe() ==
                "Alter storage engine for Pony from MyISAM to InnoDB")

    def test_references_model(self):
        operation = AlterStorageEngine("Pony", "InnoDB")
        assert operation.references_model("PONY")
        assert operation.references_model("Pony")
        assert operation.references_model("pony")
        assert not operation.references_model("poony")

    @override_mysql_variables(default_storage_engine='MyISAM')
    def test_running_with_changes(self):
        project_state = self.set_up_test_model("test_arstd")
        operation = AlterStorageEngine("Pony", from_engine="MyISAM",
                                       to_engine="InnoDB")

        assert table_storage_engine("test_arstd_pony") == "MyISAM"

        # Forwards
        new_state = project_state.clone()
        operation.state_forwards("test_arstd", new_state)
        with connection.schema_editor() as editor:
            operation.database_forwards("test_arstd", editor, project_state,
                                        new_state)
        assert table_storage_engine("test_arstd_pony") == "InnoDB"

        # Backwards
        with connection.schema_editor() as editor:
            operation.database_backwards("test_arstd", editor, new_state,
                                         project_state)
        assert table_storage_engine("test_arstd_pony") == "MyISAM"

    @override_mysql_variables(default_storage_engine='InnoDB')
    def test_running_without_changes(self):
        project_state = self.set_up_test_model("test_arstd")
        operation = AlterStorageEngine("Pony", from_engine="MyISAM",
                                       to_engine="InnoDB")

        assert table_storage_engine("test_arstd_pony") == "InnoDB"

        # Forwards - shouldn't actually do an ALTER since it is already InnoDB
        new_state = project_state.clone()
        operation.state_forwards("test_arstd", new_state)
        capturer = CaptureQueriesContext(connection)
        with capturer, connection.schema_editor() as editor:
            operation.database_forwards("test_arstd", editor, project_state,
                                        new_state)
        queries = [q['sql'] for q in capturer.captured_queries]
        assert not any(q.startswith('ALTER TABLE ') for q in queries), (
            "One of the executed queries was an unexpected ALTER TABLE:\n{}"
            .format("\n".join(queries))
        )
        assert table_storage_engine("test_arstd_pony") == "InnoDB"

        # Backwards - will actually ALTER since it is going 'back' to MyISAM
        with connection.schema_editor() as editor:
            operation.database_backwards("test_arstd", editor, new_state,
                                         project_state)
        assert table_storage_engine("test_arstd_pony") == "MyISAM"

    # Copied from django core migration tests

    def set_up_test_model(
            self, app_label, second_model=False, third_model=False,
            related_model=False, mti_model=False, proxy_model=False,
            unique_together=False, options=False, db_table=None,
            index_together=False):
        """
        Creates a test model state and database table.
        """
        # Delete the tables if they already exist
        table_names = [
            # Start with ManyToMany tables
            '_pony_stables', '_pony_vans',
            # Then standard model tables
            '_pony', '_stable', '_van',
        ]
        tables = [(app_label + table_name) for table_name in table_names]
        with connection.cursor() as cursor:
            table_names = connection.introspection.table_names(cursor)
            connection.disable_constraint_checking()
            sql_delete_table = connection.schema_editor().sql_delete_table
            with transaction.atomic():
                for table in tables:
                    if table in table_names:
                        cursor.execute(sql_delete_table % {
                            "table": connection.ops.quote_name(table),
                        })
            connection.enable_constraint_checking()

        # Make the "current" state
        model_options = {
            "swappable": "TEST_SWAP_MODEL",
            "index_together": [["weight", "pink"]] if index_together else [],
            "unique_together": [["pink", "weight"]] if unique_together else [],
        }
        if options:
            model_options["permissions"] = [("can_groom", "Can groom")]
        if db_table:
            model_options["db_table"] = db_table
        operations = [migrations.CreateModel(
            "Pony",
            [
                ("id", models.AutoField(primary_key=True)),
                ("pink", models.IntegerField(default=3)),
                ("weight", models.FloatField()),
            ],
            options=model_options,
        )]
        if second_model:
            operations.append(migrations.CreateModel(
                "Stable",
                [
                    ("id", models.AutoField(primary_key=True)),
                ],
            ))
        if third_model:
            operations.append(migrations.CreateModel(
                "Van",
                [
                    ("id", models.AutoField(primary_key=True)),
                ],
            ))
        if related_model:
            operations.append(migrations.CreateModel(
                "Rider",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("pony", models.ForeignKey("Pony")),
                    ("friend", models.ForeignKey("self")),
                ],
            ))
        if mti_model:
            operations.append(migrations.CreateModel(
                "ShetlandPony",
                fields=[
                    ('pony_ptr', models.OneToOneField(
                        auto_created=True,
                        primary_key=True,
                        to_field='id',
                        serialize=False,
                        to='Pony',
                    )),
                    ("cuteness", models.IntegerField(default=1)),
                ],
                bases=['%s.Pony' % app_label],
            ))
        if proxy_model:
            operations.append(migrations.CreateModel(
                "ProxyPony",
                fields=[],
                options={"proxy": True},
                bases=['%s.Pony' % app_label],
            ))

        return self.apply_operations(app_label, ProjectState(), operations)

    def apply_operations(self, app_label, project_state, operations):
        migration = migrations.Migration('name', app_label)
        migration.operations = operations
        with connection.schema_editor() as editor:
            return migration.apply(project_state, editor)
