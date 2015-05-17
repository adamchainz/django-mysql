# -*- coding:utf-8 -*-
"""
Implements a function for hoisting specially constructed comments in SQL
queries and using them to rewrite that query. This is done to support query
hints whilst obviating patching Django's ORM in complex ways.
"""
from __future__ import unicode_literals

import operator
import re
from collections import OrderedDict

from django.utils import six

# The rewrite comments contain a single quote mark that would need be escaped
# if entered in a column name or something like that. We aren't too worried
# about SQL injection since data is not in given the statement - it's still in
# params
REWRITE_MARKER = "/*QueryRewrite':"

# Regex to match a rewrite rule
query_rewrite_re = re.compile(r"/\*QueryRewrite':(.*?)\*/")


def rewrite_query(sql):
    comments = []
    hints = []
    for match in query_rewrite_re.findall(sql):
        if match in SELECT_HINT_TOKENS:
            hints.append(match)
        elif match.startswith('label='):
            comments.append(match[6:])

        # Silently fail on unrecognized rewrite requests

    # Delete all rewrite comments
    sql = query_rewrite_re.sub('', sql)

    if comments or hints:  # If nothing to do, don't bother
        sql = modify_sql(sql, comments, hints)

    return sql


# A translation of the grammar for SELECT - all the possible hints that can
# appear afterwards
SELECT_HINTS = OrderedDict([
    ('distinctness', ('ALL', 'DISTINCT', 'DISTINCTROW',)),
    ('priority', ('HIGH_PRIORITY',)),
    ('join_order', ('STRAIGHT_JOIN',)),
    ('result_size', ('SQL_SMALL_RESULT', 'SQL_BIG_RESULT',)),
    ('buffer_result', ('SQL_BUFFER_RESULT',)),
    ('query_cache', ('SQL_CACHE', 'SQL_NO_CACHE',)),
    ('found_rows', ('SQL_CALC_FOUND_ROWS',)),
])

# Any pre-expression tokens that are query hints
SELECT_HINT_TOKENS = frozenset(
    six.moves.reduce(operator.add, SELECT_HINTS.values())
)

# Don't go crazy reading this - it's just templating a piece of the below regex
hints_re_piece = '\n'.join(
    r'(?P<{group_name}>({tokens})\s+)?'.format(
        group_name=group_name,
        tokens='|'.join(token_set)
    )
    for group_name, token_set in six.iteritems(SELECT_HINTS)
)


# This is the one big regex that parses the start of the SQL statement
# It makes a few assumptions that are valid for queries from the Django ORM but
# may not be for other queries - for example, comments are only searched for
# immediately after the first token, pretty much assuming they could only have
# come from add_sql_piece
query_start_re = re.compile(
    r"""
        ^
        \s*
        (?P<keyword>SELECT|UPDATE|DELETE)
        # comments - N times /*a*/whitespace
        (?P<comments>(\s*/\*.*?\*/\s*)+|\s+)
    """ + hints_re_piece,
    re.VERBOSE | re.IGNORECASE
)


def modify_sql(sql, add_comments, add_hints):
    """
    Parse the start of the SQL, injecting each string in add_comments in
    individual SQL comments after the first keyword, and adding the named
    SELECT hints from add_hints, taking the latest in the list in cases of
    multiple mutually exclusive hints being given
    """
    match = query_start_re.match(sql)
    if not match:
        # We don't understand what kind of query this is, don't rewrite it
        return sql

    tokens = [match.group('keyword')]
    comments = match.group('comments').strip()
    if comments:
        tokens.append(comments)

    # Inject comments after all existing comments
    for comment in add_comments:
        tokens.append('/*{}*/'.format(comment))

    # Don't bother with SELECT rewrite rules on non-SELECT queries
    if tokens[0] == "SELECT":

        for group_name, hint_set in six.iteritems(SELECT_HINTS):

            try:
                # Take the last hint we were told to add from this hint_set
                to_add = [hint for hint in add_hints if hint in hint_set][-1]
                tokens.append(to_add)
            except IndexError:
                # We weren't told to add any, so just add any hint from this
                # set that was already there
                existing = match.group(group_name)
                if existing is not None:
                    tokens.append(existing.rstrip())

    # Add the remainder of the statement and join it all up
    tokens.append(sql[match.end():])
    return ' '.join(tokens)
