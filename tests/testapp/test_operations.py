from __future__ import annotations

from typing import Any
from unittest import SkipTest

import pytest
from django.db import connection, migrations, models, transaction
from django.db.migrations.operations.base import Operation
from django.db.migrations.state import ProjectState
from django.test import TransactionTestCase
from django.test.utils import CaptureQueriesContext

from django_mysql.operations import AlterStorageEngine, InstallPlugin, InstallSOName
from django_mysql.test.utils import override_mysql_variables
from tests.testapp.utils import conn_is_mysql


def plugin_exists(plugin_name: str) -> bool:
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT COUNT(*) FROM INFORMATION_SCHEMA.PLUGINS
               WHERE PLUGIN_NAME = %s""",
            (plugin_name,),
        )
        count: int = cursor.fetchone()[0]
        return count > 0


def table_storage_engine(table_name: str) -> str:
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT ENGINE FROM INFORMATION_SCHEMA.TABLES
               WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s""",
            (table_name,),
        )
        engine: str = cursor.fetchone()[0]
        return engine


class PluginOperationTests(TransactionTestCase):
    databases = {"default", "other"}

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        if not conn_is_mysql(connection) or not connection.mysql_is_mariadb:
            raise SkipTest("The metadata_lock_info plugin is required")

    def test_install_plugin_describe(self):
        operation = InstallPlugin("metadata_lock_info", "metadata_lock_info.so")
        assert (
            operation.describe()
            == "Installs plugin metadata_lock_info from metadata_lock_info.so"
        )

    def test_install_plugin(self):
        operation = InstallPlugin("metadata_lock_info", "metadata_lock_info.so")
        state = ProjectState()
        state2 = state.clone()

        assert not plugin_exists("metadata_lock_info")

        with connection.schema_editor() as editor:
            operation.database_forwards("testapp", editor, state, state2)
        assert plugin_exists("metadata_lock_info")

        with connection.schema_editor() as editor:
            operation.database_forwards("testapp", editor, state, state2)
        assert plugin_exists("metadata_lock_info")

        with connection.schema_editor() as editor:
            operation.database_backwards("testapp", editor, state2, state)
        assert not plugin_exists("metadata_lock_info")

        with connection.schema_editor() as editor:
            operation.database_backwards("testapp", editor, state2, state)
        assert not plugin_exists("metadata_lock_info")

    def test_install_soname(self):
        assert not plugin_exists("metadata_lock_info")

        state = ProjectState()
        operation = InstallSOName("metadata_lock_info.so")
        assert operation.describe() == "Installs library metadata_lock_info.so"

        new_state = state.clone()
        with connection.schema_editor() as editor:
            operation.database_forwards("testapp", editor, state, new_state)
        assert plugin_exists("metadata_lock_info")

        new_state = state.clone()
        with connection.schema_editor() as editor:
            operation.database_backwards("testapp", editor, new_state, state)
        assert not plugin_exists("metadata_lock_info")


class AlterStorageEngineTests(TransactionTestCase):
    def test_no_from_means_unreversible(self):
        operation = AlterStorageEngine("mymodel", to_engine="InnoDB")
        state = ProjectState()
        new_state = state.clone()
        assert not operation.reversible

        with (
            connection.schema_editor() as editor,
            pytest.raises(NotImplementedError) as excinfo,
        ):
            operation.database_backwards("testapp", editor, state, new_state)

        assert str(excinfo.value) == "You cannot reverse this operation"

    def test_from_means_reversible(self):
        operation = AlterStorageEngine(
            "mymodel", from_engine="MyISAM", to_engine="InnoDB"
        )
        assert operation.reversible

    def test_describe_without_from(self):
        operation = AlterStorageEngine("Pony", "InnoDB")
        assert operation.describe() == "Alter storage engine for Pony to InnoDB"

    def test_describe_with_from(self):
        operation = AlterStorageEngine("Pony", from_engine="MyISAM", to_engine="InnoDB")
        assert (
            operation.describe()
            == "Alter storage engine for Pony from MyISAM to InnoDB"
        )

    def test_references_model(self):
        operation = AlterStorageEngine("Pony", "InnoDB")
        assert operation.references_model("PONY")
        assert operation.references_model("Pony")
        assert operation.references_model("pony")
        assert not operation.references_model("poony")

    @override_mysql_variables(default_storage_engine="MyISAM")
    def test_running_with_changes(self):
        project_state = self.set_up_test_model("test_arstd")
        operation = AlterStorageEngine("Pony", from_engine="MyISAM", to_engine="InnoDB")

        assert table_storage_engine("test_arstd_pony") == "MyISAM"

        # Forwards
        new_state = project_state.clone()
        operation.state_forwards("test_arstd", new_state)
        with connection.schema_editor() as editor:
            operation.database_forwards("test_arstd", editor, project_state, new_state)
        assert table_storage_engine("test_arstd_pony") == "InnoDB"

        # Backwards
        with connection.schema_editor() as editor:
            operation.database_backwards("test_arstd", editor, new_state, project_state)
        assert table_storage_engine("test_arstd_pony") == "MyISAM"

    @override_mysql_variables(default_storage_engine="InnoDB")
    def test_running_without_changes(self):
        project_state = self.set_up_test_model("test_arstd")
        operation = AlterStorageEngine("Pony", from_engine="MyISAM", to_engine="InnoDB")

        assert table_storage_engine("test_arstd_pony") == "InnoDB"

        # Forwards - shouldn't actually do an ALTER since it is already InnoDB
        new_state = project_state.clone()
        operation.state_forwards("test_arstd", new_state)
        capturer = CaptureQueriesContext(connection)
        with capturer, connection.schema_editor() as editor:
            operation.database_forwards("test_arstd", editor, project_state, new_state)
        queries = [q["sql"] for q in capturer.captured_queries]
        assert not any(q.startswith("ALTER TABLE ") for q in queries)
        assert table_storage_engine("test_arstd_pony") == "InnoDB"

        # Backwards - will actually ALTER since it is going 'back' to MyISAM
        with connection.schema_editor() as editor:
            operation.database_backwards("test_arstd", editor, new_state, project_state)
        assert table_storage_engine("test_arstd_pony") == "MyISAM"

    # Adapted from django core migration tests:

    def set_up_test_model(
        self,
        app_label: str,
        *,
        proxy_model: bool = False,
        options: bool = False,
        db_table: str | None = None,
    ) -> ProjectState:  # pragma: no cover
        """
        Creates a test model state and database table.
        """
        # Delete the tables if they already exist
        table_names = [
            # Start with ManyToMany tables
            "_pony_stables",
            "_pony_vans",
            # Then standard model tables
            "_pony",
            "_stable",
            "_van",
        ]
        tables = [(app_label + table_name) for table_name in table_names]
        with connection.cursor() as cursor:
            table_names = connection.introspection.table_names(cursor)
            connection.disable_constraint_checking()
            sql_delete_table = connection.schema_editor().sql_delete_table
            with transaction.atomic():
                for table in tables:
                    if table in table_names:
                        cursor.execute(
                            sql_delete_table
                            % {"table": connection.ops.quote_name(table)}
                        )
            connection.enable_constraint_checking()

        # Make the "current" state
        model_options: dict[str, Any] = {
            "swappable": "TEST_SWAP_MODEL",
        }
        if options:
            model_options["permissions"] = [("can_groom", "Can groom")]
        if db_table:
            model_options["db_table"] = db_table
        operations: list[Operation] = [
            migrations.CreateModel(
                "Pony",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("pink", models.IntegerField(default=3)),
                    ("weight", models.FloatField()),
                ],
                options=model_options,
            )
        ]
        if proxy_model:
            operations.append(
                migrations.CreateModel(
                    "ProxyPony",
                    fields=[],
                    options={"proxy": True},
                    bases=[f"{app_label}.Pony"],
                )
            )

        return self.apply_operations(app_label, ProjectState(), operations)

    def apply_operations(
        self,
        app_label: str,
        project_state: ProjectState,
        operations: list[Operation],
    ) -> ProjectState:
        migration = migrations.Migration("name", app_label)
        migration.operations = operations
        with connection.schema_editor() as editor:
            return migration.apply(project_state, editor)
