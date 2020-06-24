from io import StringIO
from textwrap import dedent
from unittest import SkipTest, mock

import pytest
from django.core.management import CommandError, call_command
from django.db import connection
from django.db.utils import ConnectionHandler
from django.test import SimpleTestCase, TestCase, TransactionTestCase

from django_mysql.management.commands.fix_datetime_columns import parse_create_table
from django_mysql.utils import connection_is_mariadb

# Can't use @override_settings to swap out DATABASES, instead just mock.patch
# a new ConnectionHandler into the command module

command_connections = (
    "django_mysql.management.commands.fix_datetime_columns.connections"
)

sqlite = ConnectionHandler({"default": {"ENGINE": "django.db.backends.sqlite3"}})


def run_it(*args, **kwargs):
    run_args = ["fix_datetime_columns"]
    run_args.extend(args)

    out = StringIO()
    run_kwargs = {"stdout": out, "skip_checks": True}
    run_kwargs.update(kwargs)

    call_command(*run_args, **run_kwargs)

    return out.getvalue()


class Datetime6TestMixin:
    @classmethod
    def setUpClass(cls):
        if connection_is_mariadb(connection) or connection.mysql_version[:2] < (5, 6):
            raise SkipTest("Django only uses datetime(6) columns on MySQL 5.6+")
        super().setUpClass()


class FixDatetimeColumnsTests(Datetime6TestMixin, TestCase):

    databases = ["default", "other"]

    def test_nothing_by_default(self):
        assert run_it() == ""

    def test_nothing_by_default_alternative_connection(self):
        assert run_it("other") == ""

    def test_invalid_database(self):
        with pytest.raises(CommandError) as excinfo:
            run_it("bla")

        assert "does not exist" in str(excinfo.value)

    @mock.patch(command_connections, sqlite)
    def test_invalid_not_mysql(self):
        with pytest.raises(CommandError) as excinfo:
            run_it()
        assert "not a MySQL database connection" in str(excinfo.value)


class SlowFixDatetimeColumnsTests(Datetime6TestMixin, TransactionTestCase):
    def test_with_one_column_to_migrate(self):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                ALTER TABLE testapp_author
                    MODIFY COLUMN birthday datetime DEFAULT NULL
            """
            )
            try:
                out = run_it()
            finally:
                cursor.execute(
                    """
                    ALTER TABLE testapp_author
                        MODIFY COLUMN birthday datetime(6) DEFAULT NULL
                """
                )
        assert out == dedent(
            """\
            ALTER TABLE `testapp_author`
                MODIFY COLUMN `birthday` datetime(6) DEFAULT NULL;
            """
        )

    def test_with_two_columns_to_migrate(self):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                ALTER TABLE testapp_author
                    MODIFY COLUMN birthday datetime DEFAULT NULL,
                    MODIFY COLUMN deathday datetime DEFAULT NULL
            """
            )
            try:
                out = run_it()
            finally:
                cursor.execute(
                    """
                    ALTER TABLE testapp_author
                        MODIFY COLUMN birthday datetime(6) DEFAULT NULL,
                        MODIFY COLUMN deathday datetime(6) DEFAULT NULL
                """
                )
        assert out == dedent(
            """\
            ALTER TABLE `testapp_author`
                MODIFY COLUMN `birthday` datetime(6) DEFAULT NULL,
                MODIFY COLUMN `deathday` datetime(6) DEFAULT NULL;
            """
        )


class ParseCreateTableTests(SimpleTestCase):
    def test_large_normalish_table(self):
        sql = (
            "CREATE TABLE `example` (\n"
            + "  `id` int(11) NOT NULL AUTO_INCREMENT,\n"
            + "  `varchary` varchar(255) NOT NULL,\n"
            + "  `texty` longtext NOT NULL,\n"
            + "  `inty` int(11) DEFAULT NULL,\n"
            + "  `datetimey` datetime NOT NULL,\n"
            + "  PRIMARY KEY (`id`),\n"
            + "  KEY `example_abcdef` (`varchary`),\n"
            + "  KEY `example_123456` (`inty`)\n"
            + "  CONSTRAINT `example_constraint` FOREIGN KEY (`id`) "
            + "REFERENCES `other` (`id`)\n"
            + ") ENGINE=InnoDB AUTO_INCREMENT=999999 DEFAULT CHARSET=utf8mb4 "
            + "ROW_FORMAT=COMPRESSED\n"
        )

        assert parse_create_table(sql) == {
            "id": "int(11) NOT NULL AUTO_INCREMENT",
            "varchary": "varchar(255) NOT NULL",
            "texty": "longtext NOT NULL",
            "inty": "int(11) DEFAULT NULL",
            "datetimey": "datetime NOT NULL",
        }

    def test_single_column(self):
        sql = (
            "CREATE TABLE `example_table` (\n"
            + "  `the_data` longtext COLLATE utf8mb4_unicode_ci NOT NULL\n"
            + ") ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 "
            + "COLLATE=utf8mb4_unicode_ci COMMENT='hi mum';"
        )

        assert parse_create_table(sql) == {
            "the_data": "longtext COLLATE utf8mb4_unicode_ci NOT NULL"
        }
