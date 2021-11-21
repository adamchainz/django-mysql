from typing import Optional

from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.operations.base import Operation
from django.db.migrations.state import ModelState
from django.utils.functional import cached_property


class InstallPlugin(Operation):
    reduces_to_sql = False

    reversible = True

    def __init__(self, name: str, soname: str) -> None:
        self.name = name
        self.soname = soname

    def state_forwards(self, app_label: str, state: ModelState) -> None:
        pass  # pragma: no cover

    def database_forwards(
        self,
        app_label: str,
        schema_editor: BaseDatabaseSchemaEditor,
        from_st: ModelState,
        to_st: ModelState,
    ) -> None:
        if not self.plugin_installed(schema_editor):
            schema_editor.execute(
                f"INSTALL PLUGIN {self.name} SONAME %s", (self.soname,)
            )

    def database_backwards(
        self,
        app_label: str,
        schema_editor: BaseDatabaseSchemaEditor,
        from_st: ModelState,
        to_st: ModelState,
    ) -> None:
        if self.plugin_installed(schema_editor):
            schema_editor.execute("UNINSTALL PLUGIN %s" % self.name)

    def plugin_installed(self, schema_editor: BaseDatabaseSchemaEditor) -> bool:
        with schema_editor.connection.cursor() as cursor:
            cursor.execute(
                """SELECT COUNT(*)
                FROM INFORMATION_SCHEMA.PLUGINS
                WHERE PLUGIN_NAME LIKE %s""",
                (self.name,),
            )
            count = cursor.fetchone()[0]
            return count > 0

    def describe(self) -> str:
        return f"Installs plugin {self.name} from {self.soname}"


class InstallSOName(Operation):
    reduces_to_sql = True

    reversible = True

    def __init__(self, soname: str) -> None:
        self.soname = soname

    def state_forwards(self, app_label: str, state: ModelState) -> None:
        pass  # pragma: no cover

    def database_forwards(
        self,
        app_label: str,
        schema_editor: BaseDatabaseSchemaEditor,
        from_st: ModelState,
        to_st: ModelState,
    ) -> None:
        schema_editor.execute("INSTALL SONAME %s", (self.soname,))

    def database_backwards(
        self,
        app_label: str,
        schema_editor: BaseDatabaseSchemaEditor,
        from_st: ModelState,
        to_st: ModelState,
    ) -> None:
        schema_editor.execute("UNINSTALL SONAME %s", (self.soname,))

    def describe(self) -> str:
        return "Installs library %s" % (self.soname)


class AlterStorageEngine(Operation):
    def __init__(
        self, name: str, to_engine: str, from_engine: Optional[str] = None
    ) -> None:
        self.name = name
        self.engine = to_engine
        self.from_engine = from_engine

    @property
    def reversible(self) -> bool:
        return self.from_engine is not None

    def state_forwards(self, app_label: str, state: ModelState) -> None:
        pass

    def database_forwards(
        self,
        app_label: str,
        schema_editor: BaseDatabaseSchemaEditor,
        from_state: ModelState,
        to_state: ModelState,
    ) -> None:
        self._change_engine(app_label, schema_editor, to_state, engine=self.engine)

    def database_backwards(
        self,
        app_label: str,
        schema_editor: BaseDatabaseSchemaEditor,
        from_state: ModelState,
        to_state: ModelState,
    ) -> None:
        if self.from_engine is None:
            raise NotImplementedError("You cannot reverse this operation")

        self._change_engine(app_label, schema_editor, to_state, engine=self.from_engine)

    def _change_engine(
        self,
        app_label: str,
        schema_editor: BaseDatabaseSchemaEditor,
        to_state: ModelState,
        engine: str,
    ) -> None:
        new_model = to_state.apps.get_model(app_label, self.name)

        qn = schema_editor.connection.ops.quote_name

        if self.allow_migrate_model(  # pragma: no branch
            schema_editor.connection.alias, new_model
        ):
            with schema_editor.connection.cursor() as cursor:
                cursor.execute(
                    """SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
                       WHERE TABLE_SCHEMA=DATABASE() AND
                             TABLE_NAME = %s AND
                             ENGINE = %s""",
                    (new_model._meta.db_table, engine),
                )
                uses_engine_already = cursor.fetchone()[0] > 0

            if uses_engine_already:
                return

            schema_editor.execute(
                "ALTER TABLE {table} ENGINE={engine}".format(
                    table=qn(new_model._meta.db_table),
                    engine=engine,
                )
            )

    @cached_property
    def name_lower(self) -> str:
        return self.name.lower()

    def references_model(self, name: str, app_label: Optional[str] = None) -> bool:
        return name.lower() == self.name_lower

    def describe(self) -> str:
        if self.from_engine:
            from_clause = f" from {self.from_engine}"
        else:
            from_clause = ""
        return "Alter storage engine for {model}{from_clause} to {engine}".format(
            model=self.name, from_clause=from_clause, engine=self.engine
        )
