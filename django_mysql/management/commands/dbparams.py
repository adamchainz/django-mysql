# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.db import connections, DEFAULT_DB_ALIAS

from django_mysql.utils import settings_to_cmd_args


class Command(BaseCommand):
    help = ("Outputs text representing database connection suitable for "
            "inclusion in various tools' commandlines")

    option_list = BaseCommand.option_list + (
        make_option(
            '--percona',
            action='store_true',
            dest='percona',
            default=False,
            help='Output for percona tools (pt-online-schema-change etc.)'
        ),
        make_option(
            '--mysql',
            action='store_true',
            dest='mysql',
            default=False,
            help='Output for mysql tools (mysql, mysqldump, mydumper, etc.)'
        ),
    )

    def handle(self, *args, **options):
        if len(args) > 1:
            raise CommandError("Cannot output the parameters for more than "
                               "one database.")
        elif len(args) == 0:
            alias = DEFAULT_DB_ALIAS
        else:
            alias = args[0]
        db_settings = connections[alias].settings_dict

        if options['percona'] and options['mysql']:
            raise CommandError("Pass only one of --mysql and --percona")

        if options['percona']:
            self.stdout.write("percona\n")
        else:
            args = settings_to_cmd_args(db_settings)
            args = args[1:]  # Delete the 'mysql' at the start
            self.stdout.write(" ".join(args))
