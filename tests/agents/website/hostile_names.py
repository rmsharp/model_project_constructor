"""Metric and query names that a Python string literal must survive.

``templates._str_list_literal`` writes ``evaluation_metrics`` and the primary query names into
``REQUESTED_METRICS`` and ``PRIMARY_QUERY_NAMES`` in a generated project. Neither string is
constrained by the schemas (Session 294's scouts read both), so a name can hold anything.
Before Session 294 the writer was ``f'"{item}"'``: a double quote, a newline or a NUL made the
generated module a syntax error, a backslash changed the value, and ``a"+str(1+1)+"b`` was an
expression that ran when the module was imported.

Each pair is ``(id, value)``. The set is the hostile values of Session 294's scouting that
mattered, plus the choices a writer makes (which quote, when). The lone surrogate is in it on
purpose: it cannot travel through the agent (a checkpoint or a hash refuses it first), but the
renderer is a plain function and a lone surrogate must come out as an ASCII escape, not as a
character no file can hold.
"""

from __future__ import annotations

HOSTILE_NAMES: list[tuple[str, str]] = [
    ("double_quote", 'AUC "weighted"'),
    ("single_quote", "Brier's score"),
    ("only_a_double_quote", '"'),
    ("only_a_single_quote", "'"),
    ("equal_quotes", "a'b\"c"),
    ("more_doubles_than_singles", "a\"\"b'c"),
    ("more_singles_than_doubles", "a'b'c\"d"),
    ("triple_quote", '"""'),
    ("backslash", "a\\b"),
    ("backslash_then_n", "a\\nb"),
    ("backslash_then_capital_n", "a\\Nb"),
    ("backslash_then_u", "a\\u0041b"),
    ("trailing_backslash", "a\\"),
    ("newline", "a\nb"),
    ("carriage_return", "a\rb"),
    ("crlf", "a\r\nb"),
    ("tab", "a\tb"),
    ("nul", "a\x00b"),
    ("delete", "a\x7fb"),
    ("terminal_escape", "a\x1b[31mb"),
    ("next_line", "a\x85b"),
    ("line_separator", "a b"),
    ("paragraph_separator", "a b"),
    ("byte_order_mark", "﻿a"),
    ("non_bmp", "AUC \U0001f600"),
    ("lone_surrogate", "a\ud800b"),
    ("accented", "Précision@k"),
    ("braces", "{x} {{y}}"),
    ("empty", ""),
    ("long", "m" * 200),
    ("breaks_out_into_two_items", 'a", "b'),
    ("breaks_out_into_an_expression", 'a"+str(1+1)+"b'),
    ("breaks_out_into_a_comment", 'a"  # b'),
]

HOSTILE_IDS = [name for name, _ in HOSTILE_NAMES]
HOSTILE_VALUES = [value for _, value in HOSTILE_NAMES]
