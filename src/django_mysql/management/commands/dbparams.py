import argparse
from typing import Any, Dict, List, Union

import django
from django.core.management import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.utils import ConnectionDoesNotExist

from django_mysql.utils import settings_to_cmd_args


class Command(BaseCommand):
    args = "<optional connection alias>"

    help = (
        "Outputs shell parameters representing database connection "
        "suitable for inclusion in various tools' commandlines. The "
        "connection alias should be a name from DATABASES - defaults to "
        "'{default}'."
    ).format(default=DEFAULT_DB_ALIAS)

    requires_system_checks: Union[List[str], bool]
    if django.VERSION >= (3, 2):
        requires_system_checks = []
    else:
        requires_system_checks = False

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "alias",
            metavar="alias",
            nargs="?",
            default=DEFAULT_DB_ALIAS,
            help="Specify the database connection alias to output " "parameters for.",
        )

        parser.add_argument(
            "--mysql",
            action="store_true",
            dest="show_mysql",
            default=False,
            help="Outputs flags for tools that take parameters in the "
            "same format as the mysql client, e.g. mysql "
            "$(./manage.py dbparams --mysql)",
        )
        parser.add_argument(
            "--dsn",
            action="store_true",
            dest="show_dsn",
            default=False,
            help="Output a DSN for e.g. percona tools, e.g. "
            "pt-online-schema-change $(./manage.py dbparams --dsn)",
        )

    def handle(
        self, *args: Any, alias: str, show_mysql: bool, show_dsn: bool, **options: Any
    ) -> None:
        try:
            connection = connections[alias]
        except ConnectionDoesNotExist:
            raise CommandError(f"Connection '{alias}' does not exist")
        if connection.vendor != "mysql":
            raise CommandError(f"{alias} is not a MySQL database connection")

        if show_mysql and show_dsn:
            raise CommandError("Pass only one of --mysql and --dsn")
        elif not show_mysql and not show_dsn:
            show_mysql = True

        settings_dict: Dict[str, Any] = connection.settings_dict

        if show_mysql:
            self.output_for_mysql(settings_dict)
        elif show_dsn:
            self.output_for_dsn(settings_dict)
        else:  # pragma: no cover
            raise AssertionError("Impossible")

    def output_for_mysql(self, settings_dict: Dict[str, Any]) -> None:
        args = settings_to_cmd_args(settings_dict)
        args = args[1:]  # Delete the 'mysql' at the start
        self.stdout.write(" ".join(args), ending="")

    def output_for_dsn(self, settings_dict: Dict[str, Any]) -> None:
        cert = settings_dict["OPTIONS"].get("ssl", {}).get("ca")
        if cert:
            self.stderr.write(
                "Warning: SSL params can't be passed in the DSN syntax; you "
                "must pass them in your my.cnf. See: "
                "https://www.percona.com/blog/2014/10/16/percona-toolkit-for-"
                "mysql-with-mysql-ssl-connections/"
            )

        db = settings_dict["OPTIONS"].get("db", settings_dict["NAME"])
        user = settings_dict["OPTIONS"].get("user", settings_dict["USER"])
        passwd = settings_dict["OPTIONS"].get("passwd", settings_dict["PASSWORD"])
        host = settings_dict["OPTIONS"].get("host", settings_dict["HOST"])
        port = settings_dict["OPTIONS"].get("port", settings_dict["PORT"])
        defaults_file = settings_dict["OPTIONS"].get("read_default_file")

        args = []
        if defaults_file:
            args.append(f"F={defaults_file}")
        if user:
            args.append(f"u={user}")
        if passwd:
            args.append(f"p={passwd}")
        if host:
            if "/" in host:
                args.append(f"S={host}")
            else:
                args.append(f"h={host}")
        if port:
            args.append(f"P={port}")
        if db:
            args.append(f"D={db}")

        dsn = ",".join(args)
        self.stdout.write(dsn, ending="")
