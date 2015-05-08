from django.db.migrations.operations.base import Operation
from django.utils.functional import cached_property


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


class AlterStorageEngine(Operation):

    def __init__(self, name, to_engine, from_engine=None):
        self.name = name
        self.engine = to_engine
        self.from_engine = from_engine

    @property
    def reversible(self):
        return (self.from_engine is not None)

    def state_forwards(self, app_label, state):
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state,
                          engine=None):
        if engine is None:
            engine = self.engine

        if hasattr(to_state, 'render'):
            apps = to_state.render()  # Django 1.7
        else:
            apps = to_state.apps  # Django 1.8+

        new_model = apps.get_model(app_label, self.name)

        if hasattr(self, 'allowed_to_migrate'):
            allowed = self.allowed_to_migrate  # Django 1.7
        else:
            allowed = self.allow_migrate_model  # Django 1.8+

        qn = schema_editor.connection.ops.quote_name

        if allowed(schema_editor.connection.alias, new_model):
            with schema_editor.connection.cursor() as cursor:
                cursor.execute(
                    """SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
                       WHERE TABLE_SCHEMA=DATABASE() AND
                             TABLE_NAME = %s AND
                             ENGINE = %s""",
                    (new_model._meta.db_table, engine)
                )
                uses_engine_already = (cursor.fetchone()[0] > 0)

            if uses_engine_already:
                return

            schema_editor.execute(
                "ALTER TABLE {table} ENGINE={engine}".format(
                    table=qn(new_model._meta.db_table),
                    engine=engine
                )
            )

    def database_backwards(self, app_label, schema_editor, from_state,
                           to_state):
        if self.from_engine is None:
            raise NotImplementedError("You cannot reverse this operation")

        return self.database_forwards(app_label, schema_editor, from_state,
                                      to_state, engine=self.from_engine)

    @cached_property
    def name_lower(self):
        return self.name.lower()

    def references_model(self, name, app_label=None):
        return name.lower() == self.name_lower

    def describe(self):
        if self.from_engine:
            from_clause = " from {}".format(self.from_engine)
        else:
            from_clause = ""
        return "Alter storage engine for {model}{from_clause} to {engine}" \
               .format(
                   model=self.name,
                   from_clause=from_clause,
                   engine=self.engine
               )
