"""Statement gate for :meth:`ReadOnlyDB.execute`: one query, and nothing that writes.

``ReadOnlyDB`` runs SQL a language model wrote, so "read-only" has to be a property of the
statement and of the connection, not a hope about the model. This module is the statement half.
:func:`check_read_only_sql` either returns or raises :class:`ReadOnlyViolation`; it never
touches a database.

**What passes.** Exactly one statement (one trailing ``;`` is fine) that starts, after any
opening parentheses, with ``SELECT``, ``WITH`` or ``VALUES``, and that contains no write keyword,
``INTO``, row lock, assignment or side-effecting function name outside string literals,
quoted identifiers and comments.

**Why a scanner and not ``sqlparse``.** The property needed is "refuse whenever two dialects
could read this text differently", which a forgiving tokenizer cannot give. Measured against
``sqlparse`` 0.5.5 (Session 288): ``get_type()`` calls a data-modifying CTE
(``WITH x AS (DELETE ... RETURNING *) SELECT ...``), ``SELECT ... INTO`` and ``SELECT ... FOR
UPDATE`` plain ``SELECT``s; it splits a nested ``/* /* */ */`` comment as non-nesting; and it
returns one ``SELECT`` for an unterminated string. The same text is read differently by the
engines: ``SELECT 1--1`` is ``1`` on PostgreSQL and ``2`` on MySQL, ``/*!50000 + 1 */`` runs on
MySQL only, a backslash before a quote closes a literal on PostgreSQL and SQLite but not on
MySQL, and ``#`` is a comment on MySQL but an operator on PostgreSQL. So a comment or a
literal is recognised only where every dialect agrees on where it ends, and everything else is
refused.

**What it deliberately over-refuses** (a refused query is reported as a failed check, never a
crash): ``TABLE t``, ``SHOW``, ``EXPLAIN``, ``PRAGMA``; a column or table literally named
``set``, ``do``, ``use``, ``load``, ``call`` or ``into`` unless quoted; ``t.delete`` (a keyword
after a dot); ``INSERT(...)`` as a MySQL function; ``--`` with no space after it; ``#`` outside
PostgreSQL; ``ESCAPE '\\'``; ``pg_*`` functions; any character outside printable ASCII in code
(it is still allowed inside a literal, a quoted identifier or a comment).

**What it cannot stop.** A function with a side effect that is not on the name list below, a
``SELECT`` that is merely expensive (no row cap, unbounded recursion), and anything a read-only
account is meant to prevent: ``dblink``, ``pg_read_file`` and ``COPY ... TO PROGRAM`` on
PostgreSQL, ``LOAD_FILE`` on MySQL, ``OPENROWSET`` and ``xp_cmdshell`` on SQL Server. T-SQL needs
no ``;`` between statements, so on SQL Server this keyword list is the only thing separating two
statements. The account must be unable to write whatever this module does.

The refusal carries a short constant reason code. It never quotes the SQL: the report already
stores the SQL separately, and the message reaches the report through ``safe_message``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import NamedTuple

__all__ = ["ReadOnlyViolation", "check_read_only_sql"]

# One short sentence per code. A code is a rule, so a test can pin which rule refused.
_REASONS: dict[str, str] = {
    "NOT_TEXT": "the statement is not a string",
    "NUL": "the statement contains a NUL byte",
    "NOT_UTF8": "the statement cannot be encoded as UTF-8",
    "EMPTY": "the statement has no code in it",
    "CODE_CHARACTER": "a control, invisible or non-ASCII character outside a literal or comment",
    "LINE_COMMENT_FORM": "a -- comment with no space after it, or ended by a lone carriage return",
    "EXECUTABLE_COMMENT": "a /*! or /*M! comment, which MySQL and MariaDB execute",
    "NESTED_COMMENT": "a block comment containing /*, which dialects disagree about",
    "UNTERMINATED": "an unterminated string, identifier, comment or dollar quote",
    "BACKSLASH_QUOTE": "a backslash before a quote, which dialects disagree about",
    "HASH_COMMENT": "a # outside PostgreSQL, a comment on some dialects and code on others",
    "BRACKET": "a [ in a dialect whose use of brackets is not known",
    "DOLLAR": "a $ form in a dialect whose use of dollar quoting is not known",
    "PREFIXED_STRING": "a q'...' or U&'...' string, whose extent depends on the dialect",
    "ASSIGNMENT": "a := variable assignment",
    "NOT_A_QUERY": "the statement does not start with SELECT, WITH or VALUES",
    "MULTIPLE_STATEMENTS": "more than one statement, or a ; that is not the last token",
    "WRITE_KEYWORD": "a keyword that writes, changes the session, or runs a program",
    "ROW_LOCK": "a row-locking clause (FOR UPDATE, FOR SHARE, LOCK IN SHARE MODE)",
    "PRAGMA_FUNCTION": "a pragma_* table function, one of which writes",
    "SIDE_EFFECT_FUNCTION": "a function with a side effect",
}


class ReadOnlyViolation(ValueError):
    """The statement is not one the read-only gate lets through.

    ``code`` names the rule that refused it. The message holds the code and a fixed sentence, never
    the SQL, so it is safe to put in a report.
    """

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"refused by the read-only gate ({code}): {_REASONS[code]}")


@dataclass(frozen=True)
class _Profile:
    """The lexical facts that differ by dialect and that the scanner has to know."""

    bracket_quotes: bool = False  # ``[ident]`` is a quoted identifier: SQLite, SQL Server
    bracket_doubles: bool = False  # ``]]`` inside it is a literal ``]``: SQL Server
    hash_operator: bool = False  # ``#`` is an operator, not a comment: PostgreSQL
    dollar_quotes: bool = False  # ``$tag$ ... $tag$`` is a string: PostgreSQL
    unknown: bool = False  # a dialect with no facts here: refuse anything that depends on them


_PROFILES: dict[str, _Profile] = {
    "sqlite": _Profile(bracket_quotes=True),
    "postgresql": _Profile(hash_operator=True, dollar_quotes=True),
    "mysql": _Profile(),
    "mariadb": _Profile(),
    "mssql": _Profile(bracket_quotes=True, bracket_doubles=True),
    "oracle": _Profile(),
}
_UNKNOWN_DIALECT = _Profile(unknown=True)

_FIRST_WORDS = frozenset({"SELECT", "WITH", "VALUES"})

# Refused wherever they appear as a word in code. ``INTO`` covers SELECT ... INTO (PostgreSQL and
# SQL Server create a table; MySQL writes a file or a session variable) and INSERT INTO.
_WRITE_WORDS = frozenset(
    {
        "INSERT", "UPDATE", "DELETE", "MERGE", "UPSERT", "DROP", "CREATE", "ALTER", "RENAME",
        "ATTACH", "DETACH", "PRAGMA", "VACUUM", "REINDEX", "COPY", "CALL", "DO", "EXEC",
        "EXECUTE", "GRANT", "REVOKE", "DENY", "SET", "DECLARE", "USE", "LOAD", "HANDLER",
        "PREPARE", "DEALLOCATE", "LISTEN", "NOTIFY", "UNLISTEN", "DISCARD", "CLUSTER", "REFRESH",
        "BACKUP", "RESTORE", "SHUTDOWN", "KILL", "DBCC", "BULK", "OPENROWSET", "OPENQUERY",
        "OPENDATASOURCE", "OPENXML", "WAITFOR", "INTO",
    }
)  # fmt: skip
# Statements in one dialect and ordinary functions in another: refused unless a ``(`` follows.
_WRITE_WORDS_UNLESS_CALLED = frozenset({"REPLACE", "TRUNCATE"})
_SIDE_EFFECT_FUNCTIONS = frozenset(
    {
        "nextval", "setval", "set_config", "sleep", "benchmark", "get_lock", "release_lock",
        "release_all_locks", "load_file", "load_extension", "writefile", "readfile", "optimize",
        "fts3_tokenizer", "edit",
    }
)  # fmt: skip
_SIDE_EFFECT_PREFIXES = ("pg_", "lo_", "dblink", "xp_", "sp_", "utl_", "dbms_")

_WHITESPACE = " \t\n\r\f"
_WORD_START = re.compile(r"[A-Za-z_]")
_WORD_CONTINUE = re.compile(r"[A-Za-z0-9_$]")
_DOLLAR_TAG = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)?\$")
_DOLLAR_PARAMETER = re.compile(r"\$[0-9]+")
_NUMBER = re.compile(r"[0-9][0-9A-Za-z_.]*")


class _Token(NamedTuple):
    kind: str  # "word", "quoted" (identifier), "string", "punct", "semicolon", "number"
    text: str


def check_read_only_sql(sql: str, dialect: str | None = None) -> None:
    """Return if ``sql`` is one read-only query, else raise :class:`ReadOnlyViolation`.

    ``dialect`` is SQLAlchemy's backend name (``"postgresql"``, ``"mysql"``, ``"sqlite"``...); a
    name this module has no facts for, or ``None``, gets the strictest reading.
    """
    profile = _PROFILES.get((dialect or "").lower(), _UNKNOWN_DIALECT)
    tokens = _tokenize(sql, profile)

    first = 0
    while first < len(tokens) and tokens[first] == _Token("punct", "("):
        first += 1
    if first == len(tokens):
        raise ReadOnlyViolation("EMPTY" if not tokens else "NOT_A_QUERY")
    if tokens[first].kind != "word" or tokens[first].text.upper() not in _FIRST_WORDS:
        raise ReadOnlyViolation("NOT_A_QUERY")

    semicolons = [i for i, token in enumerate(tokens) if token.kind == "semicolon"]
    if semicolons:
        if semicolons[0] != len(tokens) - 1:
            raise ReadOnlyViolation("MULTIPLE_STATEMENTS")
        tokens = tokens[:-1]

    for i, token in enumerate(tokens):
        following = tokens[i + 1] if i + 1 < len(tokens) else _Token("end", "")
        if token == _Token("punct", ":="):
            raise ReadOnlyViolation("ASSIGNMENT")
        if token.kind == "word":
            _check_word(token.text.upper(), following)
        if token.kind in ("word", "quoted") and following == _Token("punct", "("):
            name = token.text.lower()
            if name in _SIDE_EFFECT_FUNCTIONS or name.startswith(_SIDE_EFFECT_PREFIXES):
                raise ReadOnlyViolation("SIDE_EFFECT_FUNCTION")


def _check_word(word: str, following: _Token) -> None:
    if word in _WRITE_WORDS_UNLESS_CALLED:
        if following != _Token("punct", "("):
            raise ReadOnlyViolation("WRITE_KEYWORD")
    elif word in _WRITE_WORDS:
        raise ReadOnlyViolation("WRITE_KEYWORD")
    elif word == "FOR" and following.kind == "word":
        if following.text.upper() in ("UPDATE", "SHARE", "NO", "KEY"):
            raise ReadOnlyViolation("ROW_LOCK")
    elif word == "LOCK" and following.kind == "word" and following.text.upper() == "IN":
        raise ReadOnlyViolation("ROW_LOCK")
    elif word.startswith("PRAGMA_"):
        raise ReadOnlyViolation("PRAGMA_FUNCTION")


def _tokenize(sql: str, profile: _Profile) -> list[_Token]:
    """Split ``sql`` into tokens, dropping whitespace and comments; refuse what is ambiguous."""
    if not isinstance(sql, str):
        raise ReadOnlyViolation("NOT_TEXT")
    if "\x00" in sql:
        raise ReadOnlyViolation("NUL")
    try:
        sql.encode("utf-8")
    except UnicodeEncodeError:
        raise ReadOnlyViolation("NOT_UTF8") from None

    n = len(sql)
    i = 0
    tokens: list[_Token] = []
    while i < n:
        c = sql[i]
        if c in _WHITESPACE:
            i += 1
            continue
        if not 0x20 <= ord(c) < 0x7F:
            raise ReadOnlyViolation("CODE_CHARACTER")
        two = sql[i : i + 2]
        if two == "--":
            i = _skip_line_comment(sql, i)
        elif two == "/*":
            i = _skip_block_comment(sql, i)
        elif c == "#":
            if not profile.hash_operator:
                raise ReadOnlyViolation("HASH_COMMENT")
            tokens.append(_Token("punct", c))
            i += 1
        elif c == "'":
            end = _scan_quoted(sql, i, "'")
            tokens.append(_Token("string", sql[i:end]))
            i = end
        elif c == '"':
            end = _scan_quoted(sql, i, '"')
            tokens.append(_Token("quoted", sql[i + 1 : end - 1].replace('""', '"')))
            i = end
        elif c == "`":
            end = _scan_backtick(sql, i)
            tokens.append(_Token("quoted", sql[i + 1 : end - 1].replace("``", "`")))
            i = end
        elif c == "[":
            i = _scan_bracket(sql, i, profile, tokens)
        elif c == "$" and (profile.dollar_quotes or profile.unknown):
            i = _scan_dollar(sql, i, profile, tokens)
        elif c == ";":
            tokens.append(_Token("semicolon", c))
            i += 1
        elif c in "0123456789":
            match = _NUMBER.match(sql, i)
            assert match is not None
            text = match.group(0)
            i += len(text)
            # ``1DELETE`` is a number to some lexers and a keyword to others: expose the word.
            word = re.sub(r"^[0-9._]+", "", text)
            tokens.append(_Token("word", word) if word else _Token("number", text))
        elif _WORD_START.match(c) or c == "$":
            end = i + 1
            while end < n and _WORD_CONTINUE.match(sql[end]):
                end += 1
            word = sql[i:end]
            if word.lower() in ("q", "nq") and sql[end : end + 1] == "'":
                raise ReadOnlyViolation("PREFIXED_STRING")
            if word.lower() == "u" and sql[end : end + 2] in ('&"', "&'"):
                raise ReadOnlyViolation("PREFIXED_STRING")
            tokens.append(_Token("word", word))
            i = end
        elif two == ":=":
            tokens.append(_Token("punct", ":="))
            i += 2
        else:
            tokens.append(_Token("punct", c))
            i += 1
    return tokens


def _skip_line_comment(sql: str, start: int) -> int:
    """Return the index where the ``--`` comment at ``start`` ends (the newline, or the end)."""
    after = sql[start + 2 : start + 3]
    if after and ord(after) > 0x20:
        raise ReadOnlyViolation("LINE_COMMENT_FORM")  # MySQL reads ``1--1`` as ``1 - -1``
    newline = sql.find("\n", start)
    end = len(sql) if newline < 0 else newline
    carriage = sql.find("\r", start, end)
    # A CR ends a PostgreSQL comment but not a MySQL one, unless it is the CR of a CRLF.
    if carriage >= 0 and not (carriage == end - 1 and end < len(sql)):
        raise ReadOnlyViolation("LINE_COMMENT_FORM")
    return end


def _skip_block_comment(sql: str, start: int) -> int:
    """Return the index just past the ``/* */`` comment at ``start``."""
    if sql.startswith(("/*!", "/*M!", "/*m!"), start):
        raise ReadOnlyViolation("EXECUTABLE_COMMENT")
    close = sql.find("*/", start + 2)
    if close < 0:
        raise ReadOnlyViolation("UNTERMINATED")
    # PostgreSQL and SQL Server nest block comments, MySQL and SQLite do not. The search runs one
    # character into the closer so a ``/*`` that overlaps it (``/* a /*/``) counts as nested.
    if sql.find("/*", start + 2, close + 1) >= 0:
        raise ReadOnlyViolation("NESTED_COMMENT")
    return close + 2


def _scan_quoted(sql: str, start: int, quote: str) -> int:
    """Return the index just past the ``quote``-delimited run at ``start``."""
    n = len(sql)
    j = start + 1
    while j < n:
        c = sql[j]
        if c == "\\":
            if j + 1 >= n:
                raise ReadOnlyViolation("UNTERMINATED")
            if sql[j + 1] == quote:
                raise ReadOnlyViolation("BACKSLASH_QUOTE")
            j += 2
        elif c == quote:
            if sql[j + 1 : j + 2] == quote:
                j += 2
            else:
                return j + 1
        else:
            j += 1
    raise ReadOnlyViolation("UNTERMINATED")


def _scan_backtick(sql: str, start: int) -> int:
    j = start + 1
    while True:
        close = sql.find("`", j)
        if close < 0:
            raise ReadOnlyViolation("UNTERMINATED")
        if sql[close + 1 : close + 2] == "`":
            j = close + 2
            continue
        return close + 1


def _scan_bracket(sql: str, start: int, profile: _Profile, tokens: list[_Token]) -> int:
    if not profile.bracket_quotes:
        if profile.unknown:
            raise ReadOnlyViolation("BRACKET")
        tokens.append(_Token("punct", "["))  # an array subscript
        return start + 1
    j = start + 1
    while True:
        close = sql.find("]", j)
        if close < 0:
            raise ReadOnlyViolation("UNTERMINATED")
        if profile.bracket_doubles and sql[close + 1 : close + 2] == "]":
            j = close + 2
            continue
        tokens.append(_Token("quoted", sql[start + 1 : close]))
        return close + 1


def _scan_dollar(sql: str, start: int, profile: _Profile, tokens: list[_Token]) -> int:
    tag = _DOLLAR_TAG.match(sql, start)
    if tag is not None:
        if not profile.dollar_quotes:
            raise ReadOnlyViolation("DOLLAR")
        delimiter = tag.group(0)
        close = sql.find(delimiter, start + len(delimiter))
        if close < 0:
            raise ReadOnlyViolation("UNTERMINATED")
        tokens.append(_Token("string", delimiter))
        return close + len(delimiter)
    parameter = _DOLLAR_PARAMETER.match(sql, start)
    if parameter is not None:
        tokens.append(_Token("punct", parameter.group(0)))
        return parameter.end()
    if profile.unknown:
        raise ReadOnlyViolation("DOLLAR")
    tokens.append(_Token("punct", "$"))
    return start + 1
