import argparse
from typing import Any, List

from django.conf import settings
from django.core.cache import InvalidCacheBackendError, caches
from django.core.management import BaseCommand, CommandError

from django_mysql.cache import MySQLCache
from django_mysql.utils import collapse_spaces


class Command(BaseCommand):
    args = "<optional cache aliases>"

    help = collapse_spaces(
        """
        Runs cache.cull() on all your MySQLCache caches, or only those
        specified aliases.
    """
    )

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "aliases",
            metavar="aliases",
            nargs="*",
            help="Specify the cache alias(es) to cull.",
        )

    def handle(
        self, *args: Any, verbosity: int, aliases: List[str], **options: Any
    ) -> None:
        if not aliases:
            aliases = list(settings.CACHES)

        for alias in aliases:
            try:
                cache = caches[alias]
            except InvalidCacheBackendError:
                raise CommandError(f"Cache '{alias}' does not exist")

            if not isinstance(cache, MySQLCache):  # pragma: no cover
                continue

            if verbosity >= 1:
                self.stdout.write(f"Deleting from cache '{alias}'... ", ending="")
            num_deleted = cache.cull()
            if verbosity >= 1:
                self.stdout.write(f"{num_deleted} entries deleted.")
