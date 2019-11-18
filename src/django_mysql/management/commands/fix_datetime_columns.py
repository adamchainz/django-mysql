from django.apps import apps
from django.core.management import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.utils import ConnectionDoesNotExist

from django_mysql.utils import collapse_spaces


class Command(BaseCommand):
    args = "<optional connection alias>"

    help = collapse_spaces(
        """
        Detects DateTimeFields with column type 'datetime' instead of
        'datetime(6)' and outputs the SQL to fix them.
    """
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "alias",
            metavar="alias",
            nargs="?",
            default=DEFAULT_DB_ALIAS,
            help="Specify the database connection alias to output " "parameters for.",
        )

    def handle(self, *args, **options):
        alias = options["alias"]

        try:
            connection = connections[alias]
        except ConnectionDoesNotExist:
            raise CommandError("Connection '{}' does not exist".format(alias))

        if connection.vendor != "mysql":
            raise CommandError("{} is not a MySQL database connection".format(alias))

        sqls = []
        with connection.cursor() as cursor:
            for table_name in self.all_table_names():
                sql = self.datetime_fix_sql(connection, cursor, table_name)
                if sql:
                    sqls.append(sql)

        for sql in sqls:
            self.stdout.write(sql)

    def all_table_names(self):
        table_names = set()
        for app_config in apps.get_app_configs():
            for model in app_config.get_models():
                table_names.add(model._meta.db_table)
        return sorted(table_names)

    def datetime_fix_sql(self, connection, cursor, table_name):
        cursor.execute(
            """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND
                  TABLE_NAME = %s AND
                  DATA_TYPE = 'datetime' AND
                  DATETIME_PRECISION = 0
            ORDER BY COLUMN_NAME
            """,
            (table_name,),
        )
        bad_column_names = [r[0] for r in cursor.fetchall()]
        if not bad_column_names:
            return

        qn = connection.ops.quote_name

        cursor.execute("SHOW CREATE TABLE {}".format(qn(table_name)))
        create_table = cursor.fetchone()[1]
        column_specs = parse_create_table(create_table)

        modify_columns = []

        for column_name in bad_column_names:
            column_spec = column_specs[column_name]

            new_column_spec = column_spec.replace("datetime", "datetime(6)", 1)
            modify_columns.append(
                "MODIFY COLUMN {} {}".format(qn(column_name), new_column_spec)
            )

        return "ALTER TABLE {table_name}\n    {columns};".format(
            table_name=qn(table_name), columns=",\n    ".join(modify_columns)
        )


def parse_create_table(sql):
    """
    Split output of SHOW CREATE TABLE into {column: column_spec}
    """
    column_types = {}
    for line in sql.splitlines()[1:]:  # first line = CREATE TABLE
        sline = line.strip()

        if not sline.startswith("`"):
            # We've finished parsing the columns
            break

        bits = sline.split("`")
        assert len(bits) == 3
        column_name = bits[1]
        column_spec = bits[2].lstrip().rstrip(",")

        column_types[column_name] = column_spec
    return column_types
