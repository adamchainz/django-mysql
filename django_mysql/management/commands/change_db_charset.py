# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import logging
import re
import textwrap

import django
from django.apps import apps
from django.core.management import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.utils import ConnectionDoesNotExist, ProgrammingError
from django.utils import timezone

from django_mysql.utils import collapse_spaces

try:
    from shlex import quote as shell_quote
except ImportError:
    from pipes import quote as shell_quote


INNODB_INDEX_BYTE_LIMIT = 767
logger = logging.getLogger(__name__)

class AlterDB(object):
    def __init__(self, connection, db_name, sql):
        self.connection = connection
        self.db_name = db_name
        self.sql = sql

    def __repr__(self):
        return 'AlterDB({!r}, {!r})'.format(self.db_name, self.sql)

    def as_sql(self):
        return 'ALTER DATABASE {} {};'.format(
            self.connection.ops.quote_name(self.db_name),
            self.sql,
        )


class AlterTable(object):
    def __init__(self, connection, db_name, table_name, sql):
        self.connection = connection
        self.db_name = db_name
        self.table_name = table_name
        self.sql = sql

    def __repr__(self):
        return 'AlterTable({!r}, {!r}, {!r}, {!r})'.format(
            self.connection, self.db_name,
            self.table_name, self.sql,
        )

    def __add__(self, other):
        if not isinstance(other, AlterTable):
            raise TypeError('Can only join another AlterTable to this AlterTable instance, not {}'.format(other))

        if self.db_name != other.db_name or self.table_name != other.table_name:
            raise ValueError("Can't join AlterTable instances for different tables (left is for {}.{}, right is for {}.{})".format(
                self.db_name, self.table_name, other.db_name, other.table_name,
            ))

        return AlterTable(self.connection, self.db_name, self.table_name, self.sql + ', ' + other.sql)

    def as_sql(self):
        return 'ALTER TABLE {}.{} {};'.format(
            self.connection.ops.quote_name(self.db_name),
            self.connection.ops.quote_name(self.table_name),
            self.sql,
        ).encode('utf-8')


class Comment(object):
    def __init__(self, comment):
        self.comment = comment

    def __repr__(self):
        return 'Comment({!r})'.format(self.comment)

    line_max_width = 100

    def as_sql(self):
        lines = textwrap.wrap(self.comment, self.line_max_width - 3)
        wrapped = '\n'.join('-- ' + line for line in lines)
        if len(lines) > 1:
            wrapped += '\n\n'
        return wrapped.encode('utf-8')


class Command(BaseCommand):
    help = collapse_spaces("""
        Detects columns, rows, and indexes with incorrect charset and
        collation and outputs the SQL to fix them.
    """)

    def add_arguments(self, parser):
        parser.add_argument(
            'alias', nargs='?',
            default=DEFAULT_DB_ALIAS,
            help='Specify the database connection alias to output parameters for.',
        )

        parser.add_argument(
            '--charset', default='utf8mb4', nargs='?',
            help='Specify the correct charset (default `utf8mb4`)',
        )

        parser.add_argument(
            '--collation', default='utf8mb4_unicode_ci', nargs='?',
            help='Specify the correct charset (default `utf8mb4_unicode_ci`)',
        )

    def handle(self, **options):
        alias = options['alias']

        try:
            connection = connections[alias]
        except ConnectionDoesNotExist:
            raise CommandError("Connection '{}' does not exist".format(alias))

        if connection.vendor != 'mysql':
            raise CommandError('{} is not a MySQL database connection'.format(alias))

        self.new_charset = options['charset']
        self.new_collation = options['collation']

        actions = []
        with connection.cursor() as cursor:
            # Validate charset and collation choice
            charset_widths = self.charset_widths(cursor)
            if self.new_charset not in charset_widths:
                raise CommandError('{} is not a valid charset for this database (expected one of {})'.format(
                    self.new_charset, ', '.join(sorted(charset_widths.keys())),
                ))

            valid_collations = self.valid_collations_for_new_charset(cursor)
            if self.new_collation not in valid_collations:
                raise CommandError('{} is not a valid collation for charset {} (expected one of {})'.format(
                    self.new_collation, self.new_charset,
                    ', '.join(sorted(valid_collations)),
                ))

            cursor.execute("""SELECT DATABASE()""")
            (self.db_name,) = cursor.fetchone()

            database_defaults_fixes = self.database_defaults_fixes(connection, cursor)
            if database_defaults_fixes:
                actions.extend(database_defaults_fixes)

            for table_name in self.all_table_names():
                table_fixes = self.table_fixes(connection, cursor, table_name)
                if table_fixes:
                    actions.extend(table_fixes)

        actions = self.combine_alter_tables(actions)
        self.output_sql(actions)

    def all_table_names(self):
        table_names = set()
        for app_config in apps.get_app_configs():
            for model in app_config.get_models():
                table_names.add(model._meta.db_table)
        return list(sorted(table_names))

    def database_defaults_fixes(self, connection, cursor):
        cursor.execute("""\
SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME
FROM INFORMATION_SCHEMA.SCHEMATA
WHERE SCHEMA_NAME = DATABASE()
""")
        ((old_default_charset, old_default_collation),) = cursor.fetchall()
        if old_default_charset == self.new_charset and old_default_collation == self.new_collation:
            return []

        return [
            Comment('Previous character set: {}'.format(old_default_charset or '<Unknown>')),
            Comment('Previous collation: {}'.format(
                old_default_collation
                or (old_default_charset
                    and self.default_collation_for_charset(cursor, old_default_charset))
                or '<Unknown>',
            )),
            AlterDB(connection, self.db_name, 'CHARACTER SET = {} COLLATE = {}'.format(self.new_charset, self.new_collation)),
        ]

    def table_fixes(self, connection, cursor, table_name):
        table_actions = []
        index_actions = []

        qn = connection.ops.quote_name

        # First check the table's defaults
        try:
            cursor.execute("""SHOW CREATE TABLE {}""".format(qn(table_name)))
        except ProgrammingError as e:
            if e.args[0] == 1146:
                return []
            raise
        create_table = parse_create_table(cursor.fetchone()[1])

        if create_table['default_charset'] != self.new_charset or create_table['default_collation'] != self.new_collation:
            table_actions.append(Comment('Previous character set: {}'.format(create_table['default_charset'] or '<Unknown>')))
            table_actions.append(Comment('Previous collation: {}'.format(
                create_table['default_collation']
                or (create_table['default_charset']
                    and self.default_collation_for_charset(cursor, create_table['default_charset']))
                or '<Unknown>',
            )))
            table_actions.append(AlterTable(
                connection, self.db_name, table_name,
                'CONVERT TO CHARACTER SET {} COLLATE {}'.format(self.new_charset, self.new_collation),
            ))

        # Next, get all of the columns that need to be resized.
        bad_columns = self.get_bad_columns(cursor, table_name)

        # Indexes have to be adjusted as well, since the bytes per character may
        # have changed. InnoDB allows a maximum of 767 bytes for an index. Either
        # the indexes need to be rebuilt or the constraints need to change the
        # correct character lengths.
        indexes = self.build_index_map_for_table(create_table)

        for column_name, column_spec in create_table['column_types'].iteritems():
            if column_name not in bad_columns:
                continue

            bad_columns[column_name]['spec'] = column_spec

            spec_no_charset = re.sub(r' CHARACTER SET \w+', '', column_spec, flags=re.IGNORECASE)
            spec_no_charset_or_collate = re.sub(r' COLLATE \w+', '', spec_no_charset, flags=re.IGNORECASE)

            logger.debug('Setting charset and collation on column %s.%s', qn(table_name), qn(column_name))
            table_actions.append(AlterTable(connection, self.db_name, table_name, 'CHANGE {} {} {} CHARACTER SET {} COLLATE {}'.format(
                qn(column_name), qn(column_name), spec_no_charset_or_collate,
                self.new_charset, self.new_collation,
            )))

            index_actions.extend(self.rebuild_indexes_for_column(
                connection, cursor, table_name,
                bad_columns[column_name], indexes,
            ))

        if index_actions:
            logger.debug('Indexes for table %s:', table_name, extra=indexes['by_name'])

        return table_actions + index_actions

    def get_bad_columns(self, cursor, table_name):
        cursor.execute("""\
SELECT COLUMN_NAME, CHARACTER_SET_NAME, COLLATION_NAME
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = %s
  AND (CHARACTER_SET_NAME != %s OR COLLATION_NAME = %s)
ORDER BY COLUMN_NAME
""", (table_name, self.new_charset, self.new_collation))
        return {r[0]: {'name': r[0], 'charset': r[1], 'collation': r[2]} for r in cursor.fetchall()}

    def build_index_map_for_table(self, create_table):
        bad_indexes = {}
        bad_indexes_by_column = {}
        for index_name, columns in create_table['keys'].iteritems():
            if index_name not in bad_indexes:
                bad_indexes[index_name] = []

            for column_info in columns:
                bad_indexes[index_name].append(column_info)

                if column_info['name'] not in bad_indexes_by_column:
                    bad_indexes_by_column[column_info['name']] = set()
                bad_indexes_by_column[column_info['name']].add(index_name)

        return {
            'by_name': bad_indexes,
            'by_column': bad_indexes_by_column,
        }

    _text_column_type_regex = re.compile(
r"""^(?:                                # Start searching at the start of the definition
(?:TINY|MEDIUM|LONG)?TEXT               # TINY = 2^8, <none> = 2^16, MEDIUM = 2^24, LONG = 2^32
| (?:VAR)?CHAR\((?P<char_count>\d+)\)   # Charwidth * N bytes
)""", re.IGNORECASE | re.VERBOSE)
    _text_col_sizes = {
        'TINYTEXT': 2 ** 8,
        'TEXT': 2 ** 16,
        'MEDIUMTEXT': 2 ** 24,
        'LONGTEXT': 2 ** 32,
    }
    def rebuild_indexes_for_column(self, connection, cursor, table_name, column, indexes):
        actions = []

        if column['name'] not in indexes['by_column']:
            # Don't need to bother with length recalculations here since
            # this column isn't indexed.
            return actions

        match = self._text_column_type_regex.match(column['spec'].upper())
        if not match:
            raise ValueError('Unknown column spec {!r} for bad column {} in table {}'.format(column['spec'], column['name'], table_name))

        charset_widths = self.charset_widths(cursor)

        col_type = match.group(0).upper()
        old_char_count = match.group('char_count')
        if not old_char_count:
            bytes_per_char = charset_widths[column['charset']]
            old_char_count = self._text_col_sizes[col_type] // bytes_per_char

        old_char_count = int(old_char_count)
        new_size_in_bytes = old_char_count * charset_widths[self.new_charset]
        if new_size_in_bytes > INNODB_INDEX_BYTE_LIMIT:
            index_size_chars = INNODB_INDEX_BYTE_LIMIT // charset_widths[self.new_charset]
            qn = connection.ops.quote_name
            for index_name in indexes['by_column'][column['name']]:
                index_columns = indexes['by_name'][index_name]
                if len(index_columns) > 1:
                    logger.warning('TODO: Need to deal with composite key %s on table %s', index_name, table_name)
                    actions.append(Comment("""\
After this migration runs, you'll need to manually migrate the {} \
index, because django_mysql's change_db_charset command doesn't \
currently support composite keys.""".format(
                        qn(index_name),
                    )))
                    continue

                logger.debug('Rebuilding key %s on table %s', index_name, table_name)
                actions.append(AlterTable(connection, self.db_name, table_name, 'DROP KEY {}'.format(qn(index_name))))
                actions.append(AlterTable(connection, self.db_name, table_name, 'ADD KEY  {} ({}({}))'.format(qn(index_name), qn(column['name']), index_size_chars)))

        return actions

    def charset_widths(self, cursor):
        if not hasattr(self, '_cached_charset_widths'):
            logger.debug('Getting charset widths from the database')
            cursor.execute("""SELECT CHARACTER_SET_NAME, MAXLEN FROM information_schema.CHARACTER_SETS""")
            self._cached_charset_widths = {charset: maxlen for (charset, maxlen) in cursor.fetchall()}

        return self._cached_charset_widths

    def valid_collations_for_new_charset(self, cursor):
        if not hasattr(self, '_cached_valid_collations'):
            logger.debug('Getting valid collations for charset %r from the database', self.new_charset)
            self._cached_valid_collations = set()
            self._cached_default_collations = {}
            cursor.execute("""\
SELECT CHARACTER_SET_NAME, COLLATION_NAME, IS_DEFAULT
FROM information_schema.COLLATIONS
""")
            for (charset, collation, is_default) in cursor.fetchall():
                if charset == self.new_charset:
                    # We only need to know the valid collations for the
                    # destination charset. The existing charsets are obviously
                    # valid.
                    self._cached_valid_collations.add(collation)
                if is_default:
                    self._cached_default_collations[charset] = collation

        return self._cached_valid_collations

    def default_collation_for_charset(self, cursor, charset):
        if not hasattr(self, '_cached_default_collations'):
            # These two things populate at the same time.
            _ = self.valid_collations_for_new_charset(cursor)
        return self._cached_default_collations[charset]

    def combine_alter_tables(self, actions):
        combined_actions = []
        for action in actions:
            if combined_actions and isinstance(action, AlterTable):
                last = combined_actions.pop()
                if isinstance(last, AlterTable) and action.db_name == last.db_name and action.table_name == last.table_name:
                    # Consume the popped action to build a new combined action.
                    action = last + action
                else:
                    # Not a match, so put `last` back in place and deal with action normally.
                    combined_actions.append(last)

            combined_actions.append(action)

        return combined_actions

    def output_sql(self, actions):
        self.stdout.write("-- Generated by django_mysql's change_db_charset command on {}\n\n".format(
            timezone.now().replace(microsecond=0),
        ))

        for action in actions:
            logger.debug('Getting SQL for action %r', action)
            sql = action.as_sql()
            if sql.endswith('\n'):
                # Django's self.stdout strips tailing newlines if there's
                # exactly one present.
                sql += '\n'
            self.stdout.write(sql)

def parse_create_table(sql):
    """
    Split output of SHOW CREATE TABLE into {column: column_spec}
    """
    table_info = {
        'column_types': {},
        'default_charset': None,
        'default_collation': None,
        'keys': {},
    }

    # first line = CREATE TABLE `...` (
    # last line = ) ENGINE = ... AUTOINCREMENT = ... DEFAULT CHARSET = ...
    slines = [line.strip() for line in sql.splitlines()[:-1]]
    create_line_regex = re.compile(r'^CREATE TABLE `(.+)` \($', re.IGNORECASE)
    table_info['name'] = create_line_regex.match(slines.pop(0)).group(1)

    while slines:
        sline = slines.pop(0)
        if not sline.startswith('`'):
            # We've finished parsing the columns
            slines.insert(0, sline)
            break

        bits = sline.split('`')
        assert len(bits) == 3
        column_name = bits[1]
        column_spec = bits[2].lstrip().rstrip(',')

        table_info['column_types'][column_name] = column_spec

    key_regex = re.compile(r'^KEY `(?P<key_name>[^`]+)` \(`(?P<cols>.+)\),?$')
    key_col_size_regex = re.compile(r'^\((\d+)\)')
    while slines:
        sline = slines.pop(0)
        if not sline.startswith('KEY'):
            continue

        match = key_regex.match(sline)
        assert match, 'Failed to match key line {!r}'.format(sline)
        key_name = match.group('key_name')
        assert key_name not in table_info['keys'], 'Found duplicate key name `{}`'.format(match.group('key_name'))
        col_pieces = match.group('cols').split('`')
        cols = []
        while col_pieces:
            col_name = col_pieces.pop(0)
            col_size = None
            if col_pieces:
                sep = col_pieces.pop(0)
                match = key_col_size_regex.match(sep)
                if match:
                    col_size = int(match.group(1))
            cols.append({'name': col_name, 'size': col_size})

        table_info['keys'][key_name] = cols

    stats_line = sql.splitlines()[-1].strip()
    charset_match = re.search(r'DEFAULT CHARSET=(\w+)', stats_line)
    if charset_match:
        table_info['default_charset'] = charset_match.group(1)
    collation_match = re.search(r'DEFAULT COLLATE=(\w+)', stats_line)
    if collation_match:
        table_info['default_collation'] = collation_match.group(1)

    return table_info
