from django.db.migrations.operations.base import Operation


class InstallPlugin(Operation):
    reduces_to_sql = False

    reversible = True

    def __init__(self, name, soname):
        self.name = name
        self.soname = soname

    def state_forwards(self, app_label, state):
        pass  # pragma: no cover

    def database_forwards(self, app_label, schema_editor, from_st, to_st):
        if not self.plugin_installed(schema_editor):
            schema_editor.execute(
                "INSTALL PLUGIN {} SONAME %s".format(self.name),
                (self.soname,),
            )

    def database_backwards(self, app_label, schema_editor, from_st, to_st):
        if self.plugin_installed(schema_editor):
            schema_editor.execute("UNINSTALL PLUGIN %s" % self.name)

    def plugin_installed(self, schema_editor):
        with schema_editor.connection.cursor() as cursor:
            cursor.execute(
                """SELECT COUNT(*)
                FROM INFORMATION_SCHEMA.PLUGINS
                WHERE PLUGIN_NAME LIKE %s""",
                (self.name,)
            )
            count = cursor.fetchone()[0]
            return (count > 0)

    def describe(self):
        return "Installs plugin %s from %s" % (self.name, self.soname)


class InstallSOName(Operation):
    reduces_to_sql = True

    reversible = True

    def __init__(self, soname):
        self.soname = soname

    def state_forwards(self, app_label, state):
        pass  # pragma: no cover

    def database_forwards(self, app_label, schema_editor, from_st, to_st):
        schema_editor.execute("INSTALL SONAME %s", (self.soname,))

    def database_backwards(self, app_label, schema_editor, from_st, to_st):
        schema_editor.execute("UNINSTALL SONAME %s", (self.soname,))

    def describe(self):
        return "Installs library %s" % (self.soname)
