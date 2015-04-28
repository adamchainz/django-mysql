from unittest import SkipTest

from django.db import connection
from django.db.migrations.state import ProjectState
from django.test import TransactionTestCase

from django_mysql.operations import InstallPlugin, InstallSOName


class OperationTests(TransactionTestCase):

    @classmethod
    def setUpClass(cls):
        super(OperationTests, cls).setUpClass()
        has_metadata_lock_plugin = (
            (connection.is_mariadb and connection.mysql_version >= (10, 0, 7))
        )
        if not has_metadata_lock_plugin:
            raise SkipTest("The metadata_lock_info plugin is required")

    def test_install_plugin(self):
        """
        Test we can load the example plugin that every version of MySQL ships
        with.
        """
        self.assertPluginNotExists("metadata_lock_info")

        state = ProjectState()
        operation = InstallPlugin("metadata_lock_info",
                                  "metadata_lock_info.so")
        self.assertEqual(
            operation.describe(),
            "Installs plugin metadata_lock_info from metadata_lock_info.so"
        )
        new_state = state.clone()
        with connection.schema_editor() as editor:
            operation.database_forwards("django_mysql_tests", editor,
                                        state, new_state)

        self.assertPluginExists("metadata_lock_info")

        new_state = state.clone()
        with connection.schema_editor() as editor:
            operation.database_backwards("django_mysql_tests", editor,
                                         new_state, state)

        self.assertPluginNotExists("metadata_lock_info")

    def test_install_soname(self):
        """
        Test we can load the 'metadata_lock_info' library.
        """
        self.assertPluginNotExists("metadata_lock_info")

        state = ProjectState()
        operation = InstallSOName("metadata_lock_info.so")
        self.assertEqual(
            operation.describe(),
            "Installs library metadata_lock_info.so"
        )

        new_state = state.clone()
        with connection.schema_editor() as editor:
            operation.database_forwards("django_mysql_tests", editor,
                                        state, new_state)
        self.assertPluginExists("metadata_lock_info")

        new_state = state.clone()
        with connection.schema_editor() as editor:
            operation.database_backwards("django_mysql_tests", editor,
                                         new_state, state)
        self.assertPluginNotExists("metadata_lock_info")

    def assertPluginExists(self, plugin_name):
        self.assertEqual(self.plugin_count(plugin_name), 1,
                         "Plugin %s is not loaded!" % plugin_name)

    def assertPluginNotExists(self, plugin_name):
        self.assertEqual(self.plugin_count(plugin_name), 0,
                         "Plugin %s is loaded!" % plugin_name)

    def plugin_count(self, plugin_name):
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT COUNT(*) FROM INFORMATION_SCHEMA.PLUGINS
                   WHERE PLUGIN_NAME = %s""",
                (plugin_name,)
            )
            return cursor.fetchone()[0]
