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

Every invisible character is written here as an escape, never raw: a raw U+2028 or U+FEFF looks
like a space or nothing in a diff, and an editor that rewrites line terminators or strips a byte
order mark would change the value without a word. The decomposed accent, the Angstrom sign and
the ligature are the names a normalising writer would change (NFC and NFKC each alter one).
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
    ("line_separator", "a\u2028b"),
    ("paragraph_separator", "a\u2029b"),
    ("byte_order_mark", "\ufeffa"),
    ("vertical_tab", "a\x0bb"),
    ("form_feed", "a\x0cb"),
    ("group_separator", "a\x1db"),
    ("no_break_space", "a\xa0b"),
    ("ideographic_space", "a\u3000b"),
    ("zero_width_space", "a\u200bb"),
    ("zero_width_joiner", "a\u200db"),
    ("right_to_left_override", "a\u202eb"),
    ("private_use", "a\ue000b"),
    ("noncharacter", "a\uffffb"),
    ("unassigned", "a\u0378b"),
    ("tag_character", "a\U000e0001b"),
    ("non_bmp", "AUC \U0001f600"),
    ("lone_surrogate", "a\ud800b"),
    ("accented", "Précision@k"),
    ("decomposed_accent", "e\u0301"),
    ("angstrom_sign", "\u212b"),
    ("fi_ligature", "\ufb01"),
    ("surrounding_spaces", " a "),
    ("only_whitespace", " \t "),
    ("braces", "{x} {{y}}"),
    ("empty", ""),
    ("long", "m" * 200),
    ("breaks_out_into_two_items", 'a", "b'),
    ("breaks_out_into_an_expression", 'a"+str(1+1)+"b'),
    ("breaks_out_into_a_comment", 'a"  # b'),
]

HOSTILE_IDS = [name for name, _ in HOSTILE_NAMES]
HOSTILE_VALUES = [value for _, value in HOSTILE_NAMES]

# Names that steer a path (Session 296, BACKLOG (7)(a)). The set above holds the values a Python
# string literal must survive and none of them has a ``/`` or a ``..`` in it, so it never
# exercised a name used as a file name. Each of these did something to the generated project
# before ``_file_stems``: wrote outside ``queries/primary/``, replaced another file, made a file
# name Windows or git refuses, or made the generated governance check crash. Anything that is not
# plain ASCII is built with ``chr``: the Write tool turns an escape into the raw character
# (learning #397), and a raw look-alike of a slash would read as a slash in a diff.
_FULLWIDTH_SOLIDUS = chr(0xFF0F)
_LONE_SURROGATE = chr(0xD800)

PATH_NAMES: list[tuple[str, str]] = [
    ("traversal_to_the_model_card", "x/../../governance/model_card"),
    ("parent_directory", "../escape"),
    ("two_parents", "../../outside"),
    ("nested", "a/b"),
    ("backslash", "a\\b"),
    ("absolute", "/etc/passwd"),
    ("empty", ""),
    ("dot", "."),
    ("dot_dot", ".."),
    ("three_dots", "..."),
    ("windows_device", "CON"),
    ("windows_device_nul", "NUL"),
    ("newline", "a\nb"),
    ("nul_character", "a" + chr(0) + "b"),
    ("over_255_bytes", "a" * 300),
    ("trailing_dot", "a."),
    ("trailing_space", "a "),
    ("leading_dash", "-rf"),
    ("git_directory", ".git"),
    ("git_short_name", "GIT~1"),
    ("traversal_with_a_slash_inside", "x/../y"),
    ("percent_encoded_slash", "a%2fb"),
    ("fullwidth_solidus", _FULLWIDTH_SOLIDUS),
    ("fullwidth_solidus_inside", "a" + _FULLWIDTH_SOLIDUS + "b"),
    ("names_another_directory", "queries/primary/x"),
    ("looks_like_a_datasheet", "datasheet_x"),
    ("quality_directory", "../quality/x"),
    ("lone_surrogate", "a" + _LONE_SURROGATE + "b"),
]

PATH_IDS = [name for name, _ in PATH_NAMES]
PATH_VALUES = [value for _, value in PATH_NAMES]
# The lone surrogate cannot travel through the agent (the checkpointer refuses it first, part
# (7)(d)); the renderers are plain functions and are tested with it, the agent is not.
PATH_NAMES_FOR_THE_AGENT = [(i, v) for i, v in PATH_NAMES if i != "lone_surrogate"]
