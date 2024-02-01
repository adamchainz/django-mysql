"""
Implements a function for hoisting specially constructed comments in SQL
queries and using them to rewrite that query. This is done to support query
hints whilst obviating patching Django's ORM in complex ways.
"""

from __future__ import annotations

import operator
import re
from collections import OrderedDict
from functools import reduce

# The rewrite comments contain a single quote mark that would need be escaped
# if entered in a column name or something like that. We aren't too worried
# about SQL injection since data is not in given the statement - it's still in
# params
REWRITE_MARKER = "/*QueryRewrite':"

# Regex to match a rewrite rule
query_rewrite_re = re.compile(r"/\*QueryRewrite':(.*?)\*/")
# Regex to parse an index hint into a tuple
index_rule_re = re.compile(
    r"""
    index=
    (?P<table_name>`[^`]+`)
    \ # space
    (?P<rule>USE|IGNORE|FORCE)
    \ # space
    (
        FOR
        \ # space
        (?P<for_what>JOIN|ORDER\ BY|GROUP\ BY)
        \ # space
    )?
    (?P<index_names>(`[^`]+`(,`[^`]+`)*)|NONE)
    """,
    re.VERBOSE,
)


def rewrite_query(sql: str) -> str:
    comments: list[str] = []
    hints: list[str] = []
    index_hints: list[tuple[str, str, str, str]] = []
    for match in query_rewrite_re.findall(sql):
        if match in SELECT_HINT_TOKENS:
            hints.append(match)
        elif match.startswith("label="):
            comments.append(match[6:])
        elif match.startswith("index="):
            # Extra parsing
            index_match = index_rule_re.match(match)
            if index_match:
                index_hints.append(
                    (
                        index_match.group("table_name"),
                        index_match.group("rule"),
                        index_match.group("index_names"),
                        index_match.group("for_what"),
                    )
                )

        # Silently fail on unrecognized rewrite requests

    # Delete all rewrite comments
    sql = query_rewrite_re.sub("", sql)

    if comments or hints or index_hints:  # If nothing to do, don't bother
        sql = modify_sql(sql, comments, hints, index_hints)

    return sql


# A translation of the grammar for SELECT - all the possible hints that can
# appear afterwards
SELECT_HINTS = OrderedDict(
    [
        ("distinctness", ("ALL", "DISTINCT", "DISTINCTROW")),
        ("priority", ("HIGH_PRIORITY",)),
        ("join_order", ("STRAIGHT_JOIN",)),
        ("result_size", ("SQL_SMALL_RESULT", "SQL_BIG_RESULT")),
        ("buffer_result", ("SQL_BUFFER_RESULT",)),
        ("query_cache", ("SQL_CACHE", "SQL_NO_CACHE")),
        ("found_rows", ("SQL_CALC_FOUND_ROWS",)),
    ]
)

# Any pre-expression tokens that are query hints
SELECT_HINT_TOKENS = frozenset(reduce(operator.add, SELECT_HINTS.values()))

# Don't go crazy reading this - it's just templating a piece of the below regex
hints_re_piece = "\n".join(
    r"(?P<{group_name}>({tokens})\s+)?".format(
        group_name=group_name, tokens="|".join(token_set)
    )
    for group_name, token_set in SELECT_HINTS.items()
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
    """
    + hints_re_piece,
    re.VERBOSE | re.IGNORECASE,
)


def modify_sql(
    sql: str,
    add_comments: list[str],
    add_hints: list[str],
    add_index_hints: list[tuple[str, str, str, str]],
) -> str:
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

    tokens = [match.group("keyword")]
    comments = match.group("comments").strip()
    if comments:
        tokens.append(comments)

    # Inject comments after all existing comments
    for comment in add_comments:
        tokens.append(f"/*{comment}*/")

    # Don't bother with SELECT rewrite rules on non-SELECT queries
    if tokens[0] == "SELECT":
        for group_name, hint_set in SELECT_HINTS.items():
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

    # Maybe rewrite the remainder of the statement for index hints
    remainder = sql[match.end() :]

    if tokens[0] == "SELECT" and add_index_hints:
        for index_hint in add_index_hints:
            remainder = modify_sql_index_hints(remainder, *index_hint)

    # Join everything
    tokens.append(remainder)
    return " ".join(tokens)


table_spec_re_template = r"""
    \b(?P<operator>FROM|JOIN)
    \s+
    (?P<table_name_with_alias>{table_name}(\s+[A-Z]+[0-9]+)?)
    \s+
"""

replacement_template = (
    r"\g<operator> \g<table_name_with_alias> "
    r"{rule} INDEX {for_section}({index_names}) "
)


def modify_sql_index_hints(
    sql: str,
    table_name: str,
    rule: str,
    index_names: str,
    for_what: str,
) -> str:
    table_spec_re = table_spec_re_template.format(table_name=table_name)
    if for_what:
        for_section = f"FOR {for_what} "
    else:
        for_section = ""
    replacement = replacement_template.format(
        rule=rule,
        for_section=for_section,
        index_names=("" if index_names == "NONE" else index_names),
    )
    return re.sub(table_spec_re, replacement, sql, count=1, flags=re.VERBOSE)
