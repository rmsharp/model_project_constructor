"""A password typed into a database address stays out of the connect error, report and warning.

Session 271 (``BACKLOG.md``: *A password can still reach the connect error, the report and a
warning*). Two shapes of address defeated the redaction, and measurement found two more routes:

1. **A password containing an unencoded ``@``.** SQLAlchemy ends the password at the FIRST
   ``@`` and hands the rest to the driver as the host, the port or the database, so
   ``bob:P@ssw0rdXYZ@127.0.0.1`` has the password ``P`` and the host ``ssw0rdXYZ@127.0.0.1``.
   The driver echoes that host (psycopg 3: ``failed to resolve host 'ssw0rdXYZ@127.0.0.1'``,
   measured), and ``redact_db_url`` printed ``bob:***@ssw0rdXYZ@127.0.0.1``.
2. **A mistyped scheme separator** (``postgresql//bob:hunter2@h/db``, ``bob:hunter2@h/db``):
   ``make_url`` fails, the fallback pattern needs ``://``, and the address was echoed as typed.
3. **A password with an ``@`` and a ``:``** makes ``make_url`` raise ``ValueError: invalid literal
   for int() with base 10: '123@h:5'``, a password fragment in the cause (measured, 2.0.49).
4. **SQLAlchemy 2.0.40**, which ``sqlalchemy>=2.0,<3`` admits, puts the WHOLE address in its parse
   error (``Could not parse SQLAlchemy URL from string 'postgresql//bob:hunter2@h/db'``). 2.0.41 and
   later do not, and the lock pins 2.0.49, so no run of this suite meets it: it is SIMULATED here.

The oracle is :func:`leaked_run`, not a ``***``-present assertion: a marker passes on a partial leak
(``user:***@ss@host`` shows the marker while printing the tail of ``p@ss``; learning #268).

Evidence labels, as in ``BACKLOG.md``: the ``fakeecho`` dialect is SIMULATED (it echoes every field
SQLAlchemy parsed, the worst case); the parse failures are SQLAlchemy 2.0.49's own and REAL; the
driver echo was measured on a real psycopg 3 and is not reproduced here: no driver is installed.
"""

from __future__ import annotations

import logging
import time
from typing import NoReturn

import pytest
import sqlalchemy as sa
from model_project_constructor_data_agent import db as db_module
from model_project_constructor_data_agent.db import (
    DBConnectionError,
    ReadOnlyDB,
    redact_db_url,
    safe_message,
    sql_dialect_from_url,
)

# Importing registers the ``fakeecho`` dialect (a side effect, on purpose; see its docstring).
from tests.hostile_text import EchoingDialect, leaked_run  # noqa: F401

DB_LOGGER_NAME = "model_project_constructor_data_agent.db"

def test_the_oracle_finds_a_partial_leak_and_ignores_punctuation() -> None:
    """The oracle itself, once: a marker-present check would pass on all three of these."""
    assert leaked_run("P@ssw0rdXYZ", "bob:***@ssw0rdXYZ@host") == "@ssw"
    assert leaked_run("hunter2", "x HUNTER2 y") == "hunt"
    assert leaked_run("a@b", "x a@b y") == "a@b"
    assert leaked_run("@:/?", "postgresql://u:***@h:5/db?x=1") is None
    assert leaked_run("P@ssw0rdXYZ", "bob:***@127.0.0.1:1/claims") is None


#: (id, address, the password the operator MEANT). ``fakeecho`` URLs reach the simulated driver
#: when they parse; the others fail inside SQLAlchemy, which is real.
SHAPES = [
    ("at", "fakeecho://bob:P@ssw0rdXYZ@127.0.0.1:1/claims", "P@ssw0rdXYZ"),
    ("several-at", "fakeecho://bob:a@b@cdefgh@127.0.0.1:1/claims", "a@b@cdefgh"),
    ("at-and-slash", "fakeecho://bob:P@ss/wordXYZ@127.0.0.1:1/claims", "P@ss/wordXYZ"),
    ("at-and-question", "fakeecho://bob:P@ss?wordXYZ@127.0.0.1:1/claims", "P@ss?wordXYZ"),
    ("at-and-colon", "fakeecho://bob:P@ss:123xyz@127.0.0.1:1/claims", "P@ss:123xyz"),
    ("at-and-colon-and-slash", "fakeecho://bob:P@ss:12/xyz@127.0.0.1:1/claims", "P@ss:12/xyz"),
    ("at-in-query-key", "fakeecho://bob:P@s?wordXYZ@127.0.0.1:1/claims", "P@s?wordXYZ"),
    ("at-and-a-bad-port", "fakeecho://bob:P@ssw0rdXYZ@127.0.0.1:$DB_PORT/claims", "P@ssw0rdXYZ"),
    ("scheme-with-two-slashes", "fakeecho//bob:hunter2@127.0.0.1:1/claims", "hunter2"),
    ("scheme-with-one-slash", "fakeecho:/bob:hunter2@127.0.0.1:1/claims", "hunter2"),
    ("no-scheme", "bob:hunter2@127.0.0.1:1/claims", "hunter2"),
    # A ``://`` INSIDE the password, under a mistyped scheme: not the scheme's separator.
    ("a-separator-inside-the-password", "fakeecho//bob:Zq7x://Kw3d@127.0.0.1:1/claims", "Zq7x://Kw3d"),
    # A ``?`` in the user name with an unexpanded port: the old pattern masked this, a guard that
    # refused a ``?`` before the colon printed the password (Session 271 grammar lens).
    (
        "a-question-mark-in-the-user",
        "fakeecho://a?b:Zq7xKw3d@127.0.0.1:$DB_PORT/claims",
        "Zq7xKw3d",
    ),
    # A ``/`` in the user name ends it: the parse puts the rest in the database, with one ``@``.
    ("a-slash-in-the-user", "fakeecho://a/b:Zq7xKw3d@127.0.0.1:1/claims", "Zq7xKw3d"),
    # make_url's own ValueError carries the port field, and ``%r`` doubles a backslash in it.
    (
        "a-backslash-in-the-port-error",
        "fakeecho://bob:a@a:Zq7x\\Kw3d@127.0.0.1/db",
        "a@a:Zq7x\\Kw3d",
    ),
    ("a-tab-in-the-port-error", "fakeecho://bob:a@a:Zq7x\tKw3d@127.0.0.1/db", "a@a:Zq7x\tKw3d"),
    ("no-scheme-and-at", "bob:P@ssw0rdXYZ@127.0.0.1:1/claims", "P@ssw0rdXYZ"),
    ("an-unexpanded-port", "fakeecho://bob:hunter2@127.0.0.1:$DB_PORT/claims", "hunter2"),
    ("an-email-user", "fakeecho://bob@corp.example:hunter2@127.0.0.1:1/claims", "hunter2"),
    # One slash too many PARSES: the user part becomes the database, there is one ``@``, and an
    # address with one ``@`` looks sound. The real CLI printed it (Session 271 sinks lens).
    ("three-slashes", "fakeecho:///bob:Hn4rT8qPz@127.0.0.1:1/claims", "Hn4rT8qPz"),
    # One slash too many, and a ``?`` in the password: the parse finds a database and a query whose
    # value holds the ``@``, and a query's ``@`` is only accounted for after a HOST.
    ("three-slashes-and-a-query-mark", "fakeecho:///bob:Zq7xK9?=@127.0.0.1:1/claims", "Zq7xK9?="),
    # The password whole reaches the cause when every token is short and it ends in a delimiter.
    ("a-short-password-ending-in-a-colon", "fakeecho//bob:aaa7:@127.0.0.1:1/claims", "aaa7:"),
    # An alternation takes the FIRST pattern that matches, so a chain must not outrank the whole.
    (
        "a-password-the-chains-would-cut-short",
        "fakeecho//bob:N_b:P&e@K/*9%uzX,@127.0.0.1/db",
        "N_b:P&e@K/*9%uzX,",
    ),
    # A ``:`` alone before a ``://`` that belongs to the password: no scheme at all.
    (
        "a-colon-before-the-separator-inside-the-password",
        "bob:Zq7x://Kw3d@127.0.0.1:1/claims",
        "Zq7x://Kw3d",
    ),
    # A ``?`` in the password gives a query whose KEY holds the ``@`` (SQLAlchemy keeps it).
    (
        "at-in-a-query-key-with-a-value",
        "fakeecho://bob:Zq7x@s?Kw3d@Vb5n=mWpL@127.0.0.1:1/claims",
        "Zq7x@s?Kw3d@Vb5n=mWpL",
    ),
    # SQLAlchemy's port ValueError prints the last segment: a short token, then punctuation.
    (
        "a-short-last-token-then-punctuation",
        "fakeecho://bob:Hunter@2:Ab1!@127.0.0.1:5432/db",
        "Hunter@2:Ab1!",
    ),
    # Passwords with no ASCII letter: the ValueError prints a segment no exact piece matches.
    (
        "a-cyrillic-password",
        "fakeecho://bob:пароль@секрет:пароль2@127.0.0.1/db",
        "пароль@секрет:пароль2",
    ),
    (
        "a-cjk-password",
        "fakeecho://bob:密码密码@秘密秘密:密码密码@127.0.0.1/db",
        "密码密码@秘密秘密:密码密码",
    ),
    # A passphrase in a SQLite-family address: the password field is not a path.
    ("a-sqlcipher-passphrase", "sqlite+pysqlcipher://:Pass@word1234@/enc.db", "Pass@word1234"),
    ("a-sqlite-address-with-a-user", "sqlite://bob:P@ssw0rdXYZ@127.0.0.1/db", "P@ssw0rdXYZ"),
    # An ``@`` then a ``?`` inside the password: SQLAlchemy sees a query that follows the userinfo
    # with no host or database before it, so the ``@`` in its value is not a legitimate one.
    ("at-then-query", "fakeecho://bob:Zq7xK9@?Vb5nY=mWpL3@127.0.0.1:1/db", "Zq7xK9@?Vb5nY=mWpL3"),
    # The ``@`` that ends the password lands in the database field, with a host before it.
    ("at-and-slash-ends-in-database", "fakeecho://bob:a@bcd/efgh@127.0.0.1:1/claims", "a@bcd/efgh"),
    (
        "an-email-user-and-at",
        "fakeecho://bob@corp.example:P@ssw0rdXYZ@127.0.0.1:1/claims",
        "P@ssw0rdXYZ",
    ),
]
SHAPE_IDS = [shape[0] for shape in SHAPES]


@pytest.mark.parametrize(("_id", "url", "password"), SHAPES, ids=SHAPE_IDS)
def test_the_redacted_address_shows_none_of_the_password(_id: str, url: str, password: str) -> None:
    assert leaked_run(password, redact_db_url(url)) is None


@pytest.mark.parametrize(("_id", "url", "password"), SHAPES, ids=SHAPE_IDS)
def test_the_connect_error_shows_none_of_the_password(_id: str, url: str, password: str) -> None:
    with pytest.raises(DBConnectionError) as excinfo:
        ReadOnlyDB(url).connect()
    assert leaked_run(password, str(excinfo.value)) is None


@pytest.mark.parametrize(("_id", "url", "password"), SHAPES, ids=SHAPE_IDS)
def test_the_dialect_warning_shows_none_of_the_password(
    _id: str, url: str, password: str, caplog: pytest.LogCaptureFixture
) -> None:
    """The warning fires only for an address that does not parse; for the rest this asserts
    that whatever IS logged is clean (``test_db.py`` holds the silence for a parseable one)."""
    with caplog.at_level(logging.WARNING, logger=DB_LOGGER_NAME):
        sql_dialect_from_url(url)
    assert leaked_run(password, caplog.text) is None


@pytest.mark.parametrize(("_id", "url", "password"), SHAPES, ids=SHAPE_IDS)
def test_the_redacted_address_is_a_fixed_point(_id: str, url: str, password: str) -> None:
    """``redact_db_url``'s docstring promises idempotence, so a message built from an address that
    was already redacted is unchanged. It is held for every shape, because the new branch rewrites
    text the structural one never touched."""
    once = redact_db_url(url)
    assert redact_db_url(once) == once


def _parse_error_that_echoes_the_address(*args: object, **kwargs: object) -> NoReturn:
    """What SQLAlchemy 2.0.40 raises for an address it cannot parse (measured; 2.0.41 and later
    say ``from given URL string`` instead). SIMULATED: the lock pins 2.0.49."""
    url = args[0] if args else kwargs.get("url")
    raise sa.exc.ArgumentError(f"Could not parse SQLAlchemy URL from string '{url}'")


UNPARSEABLE_IDS = {
    "scheme-with-two-slashes",
    "scheme-with-one-slash",
    "no-scheme",
    "no-scheme-and-at",
    "an-unexpanded-port",
    "at-and-colon",
    "at-and-colon-and-slash",
    "a-separator-inside-the-password",
    "a-question-mark-in-the-user",
    "a-backslash-in-the-port-error",
    "a-tab-in-the-port-error",
    "a-short-password-ending-in-a-colon",
    "a-password-the-chains-would-cut-short",
    "a-colon-before-the-separator-inside-the-password",
    "a-short-last-token-then-punctuation",
    "a-cyrillic-password",
    "a-cjk-password",
}
UNPARSEABLE = [shape for shape in SHAPES if shape[0] in UNPARSEABLE_IDS]


@pytest.mark.parametrize(("_id", "url", "password"), UNPARSEABLE, ids=[s[0] for s in UNPARSEABLE])
def test_a_parse_error_that_echoes_the_whole_address_shows_none_of_the_password(
    _id: str,
    url: str,
    password: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(sa, "create_engine", _parse_error_that_echoes_the_address)
    monkeypatch.setattr(sa, "make_url", _parse_error_that_echoes_the_address)
    with pytest.raises(DBConnectionError) as excinfo:
        ReadOnlyDB(url).connect()
    assert leaked_run(password, str(excinfo.value)) is None
    with caplog.at_level(logging.WARNING, logger=DB_LOGGER_NAME):
        sql_dialect_from_url(url)
    assert leaked_run(password, caplog.text) is None


# ---------------------------------------------------------------------------
# What must NOT change. A masker that also ate the diagnostic would trade this item's bug for a
# quieter one (``test_db.py::test_connect_error_names_the_cause_without_the_password``), and a
# URL with no password has nothing to mask.
# ---------------------------------------------------------------------------

#: Addresses with no password in them. Each holds an ``@``, or a ``:`` and an ``@``, in a place that
#: is not a password, which is what a looser trigger would mistake for one.
SECRETLESS = [
    "sqlite:////tmp/a@b:c/x@y.db",
    "sqlite:///C:/Users/ann@corp/x@y.db",
    "sqlite:///rel/a@b:c/x@y.db",
    "mssql+pyodbc:///?odbc_connect=DRIVER%3D%7BODBC+Driver+17%7D%3BUID%3Dann%40corp",
    "sqlite+pysqlite:///C:/a@b/x.db",
    "postgresql://bob@db.example:$DB_PORT/claims",
]


@pytest.mark.parametrize("url", SECRETLESS)
def test_an_address_with_no_password_is_shown_as_any_address_is(url: str) -> None:
    """Not masked, and not rewritten beyond what ``render_as_string`` does to every address. That
    differs by SQLAlchemy version (2.1 percent-encodes a ``:`` in a SQLite path), so the expectation
    is the renderer's own output and not the address as typed."""
    try:
        expected = sa.make_url(url).render_as_string(hide_password=True)
    except Exception:  # an unexpanded $DB_PORT does not parse: it is shown as typed
        expected = url
    assert redact_db_url(url) == expected
    assert "***" not in redact_db_url(url)


@pytest.mark.parametrize(
    ("url", "shown"),
    [
        # The structural render percent-encodes an ``@``; that is not a masking.
        ("postgresql://host/db?application_name=etl@nightly", "?application_name=etl%40nightly"),
        ("postgresql://svc@myserver@host/db", "svc%40myserver@host/db"),
    ],
)
def test_an_address_with_no_password_but_an_at_keeps_all_of_it(url: str, shown: str) -> None:
    assert redact_db_url(url).endswith(shown)
    assert "host" in redact_db_url(url)
    assert "***" not in redact_db_url(url)


def test_a_one_slash_typo_with_no_password_masks_the_user_rather_than_echo_a_password() -> None:
    """``postgresql:/bob@h/db`` and ``bob:/s3cret@h/db`` (a password that begins with a slash, no
    scheme) are the same text to a parser. The second is a secret, so both are read as one: the
    user name is masked and the host stays. Session 271 enumeration found the leak, and it is the
    price of ruling for the secret."""
    assert redact_db_url("postgresql:/bob@h/db") == "postgresql:***@h/db"
    assert leaked_run("/s3cret", redact_db_url("bob:/s3cret@127.0.0.1:1/db")) is None


def test_a_correct_url_with_an_at_in_a_query_value_keeps_its_host_and_masks_its_password() -> None:
    """The case a raw count of ``@`` got wrong: it printed ``bob:***@nightly``, a host that was
    never contacted, and ate the real host from the driver's text."""
    url = "postgresql://bob:hunter2@db.example:5432/claims?application_name=etl@nightly"
    assert redact_db_url(url) == (
        "postgresql://bob:***@db.example:5432/claims?application_name=etl%40nightly"
    )


@pytest.mark.parametrize(("_id", "url", "password"), SHAPES, ids=SHAPE_IDS)
def test_the_connect_error_still_names_the_host(_id: str, url: str, password: str) -> None:
    """Both halves matter: no password, and still diagnostic. A shape that names the host
    127.0.0.1 (the SQLite-family ones do not) still names it in the error."""
    with pytest.raises(DBConnectionError) as excinfo:
        ReadOnlyDB(url).connect()
    if "127.0.0.1" in url:
        assert "127.0.0.1" in str(excinfo.value)


def test_an_unparseable_address_still_shows_the_unexpanded_port_and_the_host_it_was_given() -> None:
    url = "fakeecho://bob:P@ssw0rdXYZ@db.example:$DB_PORT/claims"
    with pytest.raises(DBConnectionError) as excinfo:
        ReadOnlyDB(url).connect()
    message = str(excinfo.value)
    assert "$DB_PORT" in message
    assert "db.example" in message
    assert leaked_run("P@ssw0rdXYZ", message) is None


class _Unprintable(Exception):
    def __str__(self) -> str:
        raise RuntimeError("broken __str__")


@pytest.mark.parametrize("url", ["fakeecho://bob:hunter2@h/db", "fakeecho://bob:P@ssw0rdXYZ@h/db"])
def test_a_cause_that_cannot_be_printed_still_gives_a_connect_error(
    url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``connect`` runs inside the ``except`` that delivers "never raises". A scrub that read
    ``str(cause)`` outside ``safe_message``'s guard would let this ``RuntimeError`` escape instead
    (Session 271 regression lens, measured on a port of the design)."""

    def _raise(*args: object, **kwargs: object) -> NoReturn:
        raise _Unprintable()

    monkeypatch.setattr(sa, "create_engine", _raise)
    with pytest.raises(DBConnectionError) as excinfo:
        ReadOnlyDB(url).connect()
    assert str(excinfo.value).endswith(": <unprintable>")


# ---------------------------------------------------------------------------
# What a REAL driver prints. Each text below was captured by Session 271's drivers lens from the
# named driver and version against a refused or unresolvable target, for the typed password shown
# (``driver_matrix/out_sa2.0.49_*.json``, field ``raw``), and is pasted here verbatim or cut short
# at the end; none is paraphrased. No driver is installed in this project. A driver re-escapes,
# brackets, strips, splits, truncates or lower-cases what it echoes, so the scrub matches the
# ALPHANUMERIC TOKENS of the password and never the text a driver might have rewritten around them.
# ---------------------------------------------------------------------------

REAL_ECHOES = [
    # (id, driver, typed address, text the driver put in its error)
    (
        "psycopg3-comma",
        "psycopg 3.3.6",
        "postgresql+psycopg://bob:Zq7xK9@mWpL3,Vb5nY@127.0.0.1:1/db",
        "(psycopg.OperationalError) failed to resolve host 'Vb5nY@127.0.0.1': [Errno 8] nodename",
    ),
    (
        "psycopg2-comma",
        "psycopg2 2.9",
        "postgresql+psycopg2://bob:Zq7xK9@mWpL3,Vb5nY@127.0.0.1:1/db",
        'could not translate host name "mWpL3" to address: nodename nor servname provided, or not '
        'known\ncould not translate host name "Vb5nY@127.0.0.1" to address: nodename nor servname',
    ),
    (
        "psycopg3-backslash",
        "psycopg 3.3.6",
        "postgresql+psycopg://bob:Zq7xK9@mWpL3\\Vb5nY@127.0.0.1:1/db",
        "(psycopg.OperationalError) failed to resolve host 'mWpL3\\\\Vb5nY@127.0.0.1': [Errno 8]",
    ),
    (
        "pymysql-quote",
        "PyMySQL",
        "mysql+pymysql://bob:Zq7xK9@mWpL3'Vb5nY@127.0.0.1:1/db",
        (
            "(pymysql.err.OperationalError) (2003, 'Can\\'t connect to MySQL server "
            'on "mWpL3\\\'Vb5nY@127.0.0.1" ([Errno 8] nodename nor servname provided,'
            " or not known)')\n(Background on this error at: https://sqlalche.me/e/2"
            '0/e3q8)'
        ),
    ),
    (
        "pymssql-bytes-repr",
        "pymssql",
        "mssql+pymssql://bob:Zq7xK9@mWpL\u00e93\u00fc@127.0.0.1:1/db",
        (
            "(pymssql.exceptions.OperationalError) (20009, b'DB-Lib error message 2"
            '0009, severity 9:\\nUnable to connect: TDS server is unavailable or doe'
            "s not exist (mWpL\\xc3\\xa93\\xc3\\xbc@127.0.0.1)\\n')\n(Background on this "
            'error at: https://sqlalche.me/e/20/e3q8)'
        ),
    ),
    (
        "mysql-connector-stripped",
        "mysql-connector-python",
        "mysql+mysqlconnector://bob:Zq7xK9@ mWpL3Vb5nY@127.0.0.1:1/db",
        "2005 (HY000): Unknown MySQL server host 'mWpL3Vb5nY@127.0.0.1' (8)",
    ),
    (
        "psycopg3-bracket-host",
        "psycopg 3.3.6",
        "postgresql+psycopg://bob:Zq7xK9@[mWpL3]Vb5nY@127.0.0.1:1/db",
        "(psycopg.OperationalError) failed to resolve host 'mWpL3': [Errno 8] nodename nor",
    ),
    (
        "clickhouse-lowercased-and-cut-at-hash",
        "clickhouse-driver",
        "clickhouse+native://bob:Zq7xK9@mWpL3#Vb5nY@127.0.0.1:1/db",
        'Orig exception: Code: 210. nodename nor servname provided, or not known (mwpl3:9000)',
    ),
]
REAL_ECHO_IDS = [echo[0] for echo in REAL_ECHOES]


def _typed_password(url: str) -> str:
    """The password as typed: between the first ``:`` after ``://`` and the host's ``@``."""
    start = url.index("://") + 3
    return url[url.index(":", start) + 1 : url.index("@127.0.0.1")]


@pytest.mark.parametrize(("_id", "driver", "url", "text"), REAL_ECHOES, ids=REAL_ECHO_IDS)
def test_a_real_drivers_echo_shows_none_of_the_password(
    _id: str, driver: str, url: str, text: str
) -> None:
    password = _typed_password(url)
    assert leaked_run(password, text), f"the fixture must show the password to start with: {driver}"
    assert leaked_run(password, safe_message(text, url=url)) is None


@pytest.mark.parametrize("control", ["\t", "\n", "\x00", "\x1b", "\x7f"])
def test_the_password_is_removed_before_the_text_is_flattened(control: str) -> None:
    """A driver prints a control character raw, and ``safe_message`` turns it into a space and
    collapses whitespace. The exact pieces match the password as typed, so removing it AFTER that
    leaves what no chain covers: ``ab<control>c`` is a tail of three alphanumeric characters. The
    leak is two characters (``'ab ***@'``), which is why the exact output is the assertion: the
    first version of this test used a password the chains cover in either order and could not
    fail, and the review's swap mutant showed it."""
    url = f"postgresql://bob:Zq7xK9@ab{control}c@127.0.0.1:1/db"
    text = f"failed to resolve host 'ab{control}c@127.0.0.1'"
    assert safe_message(text, url=url) == "failed to resolve host '***@127.0.0.1'"


@pytest.mark.parametrize("control", ["\t", "\n", "\x00"])
def test_a_control_character_inside_a_long_password_does_not_stop_the_removal(control: str) -> None:
    """The case the chains cover: a gap of one flattened space is inside their six."""
    url = f"postgresql+psycopg2://bob:Zq7xK9@mWpL3{control}Vb5nY@127.0.0.1:1/db"
    text = f'could not translate host name "mWpL3{control}Vb5nY@127.0.0.1" to address'
    cleaned = safe_message(text, url=url)
    assert leaked_run("Zq7xK9@mWpL3 Vb5nY", cleaned) is None
    assert "127.0.0.1" in cleaned


def test_the_longest_exact_piece_wins() -> None:
    """The password whole and its tail after an ``@`` start at the same place when the tail is a
    prefix of the password: shortest first would mask the tail and leave the rest."""
    url = "postgresql//bob:Zq7xK9mW@Zq7x@127.0.0.1:1/db"
    text = f"Could not parse SQLAlchemy URL from string '{url}'"
    cleaned = safe_message(text, url=url)
    assert "K9mW" not in cleaned
    assert leaked_run("Zq7xK9mW@Zq7x", cleaned) is None


def test_a_percent_encoded_password_is_removed_in_its_decoded_form_too() -> None:
    """SQLAlchemy hands the driver the DECODED password, so that is what a driver can echo."""
    url = "postgresql://bob:Zq7%40mK9xRt@x@127.0.0.1:1/db"
    text = "could not authenticate with credential 'Zq7@mK9xRt'"
    assert leaked_run("Zq7@mK9xRt", safe_message(text, url=url)) is None


def test_a_short_piece_is_removed_only_beside_the_at_that_follows_it() -> None:
    """A piece under four characters would erase itself from every word if removed anywhere, so
    it goes only where an ``@`` follows it: the shape a mis-assigned host takes. A left boundary
    keeps it from taking the last letter off ``user@host``."""
    url = "postgresql://bob:Zq7xK9mWpL3@s@127.0.0.1:1/db"
    assert safe_message("host 's@127.0.0.1' and user postgres@db", url=url) == (
        "host '***@127.0.0.1' and user postgres@db"
    )


def test_a_mask_made_of_stars_is_not_matched_again() -> None:
    url = "postgresql://bob:p@*@w0rd1@127.0.0.1:1/db"
    text = "could not translate host name \"*@w0rd1@127.0.0.1\" to address"
    cleaned = safe_message(text, url=url)
    assert "w0rd1" not in cleaned
    assert "*****" not in cleaned


def test_the_scrub_is_linear_in_the_password() -> None:
    """The first design enumerated every run of segments between delimiters: cubic, 4 s at 160
    delimiters and a hang at 100,000 (Session 271 over-masking lens). It runs inside the
    ``except`` block that must not raise."""
    password = "@".join(["ab:cdefgh"] * 3000)
    url = f"postgresql://bob:{password}@h/db"
    start = time.perf_counter()
    safe_message("x " * 5000, url=url)
    assert time.perf_counter() - start < 10.0


def test_a_scrub_that_cannot_finish_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """The scrub runs inside the ``except`` blocks that deliver "never raises", and a scrub that
    stopped part-way has not removed the password: say so, and show nothing."""

    def _boom(password: str) -> NoReturn:
        raise RuntimeError("boom")

    monkeypatch.setattr(db_module, "_password_patterns", _boom)
    url = "postgresql://bob:P@ssw0rdXYZ@127.0.0.1:1/db"
    assert safe_message("failed to resolve host 'ssw0rdXYZ@127.0.0.1'", url=url) == "<unprintable>"


# ---------------------------------------------------------------------------
# The decisions inside the redaction that a mutation pass and a review found unheld (Session 271).
# Each case below fails when the decision it names is removed; a decision not named here may not be.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "text"),
    [
        # An ``@`` in the user name: the parse accounts for it, so the address is trusted.
        ("postgresql://bob@corp.example:hunter2xyz@h/db", "rejected hunter2xyz for the role"),
        # A percent-encoded ``@`` in the password: SQLAlchemy decodes it, so it is trusted too.
        ("postgresql://bob:hunter2%40wxyzq@h/db", "rejected wxyzq for the role"),
        ("postgresql://bob:hunter2xyz@h/db?application_name=etl@nightly", "rejected hunter2xyz"),
    ],
    ids=["an-at-in-the-user", "an-encoded-at-in-the-password", "an-at-in-a-query-value"],
)
def test_a_trusted_parse_leaves_the_driver_text_alone(url: str, text: str) -> None:
    """The scrub removes a password BY VALUE, which costs the words it shares with the message.
    It is paid only where SQLAlchemy cannot be trusted, and a correctly parsed address is trusted:
    no measured driver echoes a password that parsed, and ``_mask_kv`` still handles ``key=``."""
    assert safe_message(text, url=url) == text


def test_a_sqlalchemy_url_object_is_a_valid_address() -> None:
    """``ReadOnlyDB`` has always accepted whatever ``make_url`` does."""
    url = sa.make_url("postgresql://bob:hunter2@h/db")
    assert redact_db_url(url) == "postgresql://bob:***@h/db"
    assert safe_message("x hunter2", url=url) == "x hunter2"


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("postgresql://bob:pw@h/db", ("postgresql://bob:", "pw", "@h/db")),
        ("postgresql://bob:p@ss@h/db", ("postgresql://bob:", "p@ss", "@h/db")),
        ("bob:pw@h/db", ("bob:", "pw", "@h/db")),
        ("postgresql//bob:pw@h/db", ("postgresql//bob:", "pw", "@h/db")),
        # A ``://`` after a ``:``, ``/`` or ``@`` belongs to the password, not to the scheme.
        ("postgresql//bob:a://b@h/db", ("postgresql//bob:", "a://b", "@h/db")),
        # Not a scheme separator, so the first colon in the address is the user's: the one in it.
        ("u@x://p:q@h/db", ("u@x:", "//p:q", "@h/db")),
        ("a/b://p:q@h/db", ("a/b:", "//p:q", "@h/db")),
        ("postgresql://host/db", None),
        ("postgresql://bob@h/db", None),
    ],
)
def test_the_userinfo_is_split_the_way_an_operator_means_it(
    url: str, expected: tuple[str, str, str] | None
) -> None:
    assert db_module._split_userinfo(url) == expected


@pytest.mark.parametrize("gap", ["", ":", "\\\\", "[\\\\]", "\\\\'.", "\\\\ \\\\ "])
def test_a_driver_that_puts_up_to_six_characters_between_tokens_still_loses_the_password(
    gap: str,
) -> None:
    """Every token is short, so only a CHAIN can remove them: a driver that doubles a backslash,
    brackets a host or strips a space leaves the tokens and rewrites what is between them."""
    url = "postgresql://bob:Zq@qx:zv@h/db"
    assert safe_message(f"no route to qx{gap}zv now", url=url) == "no route to *** now"


def test_the_longest_chain_wins() -> None:
    """Four short tokens joined by anything are one chain, not two: an alternation takes the first
    pattern that matches, so the chains are tried most tokens first."""
    url = "postgresql://bob:ab@cd@ef@gh@h/db"
    assert safe_message("x ab:cd:ef:gh y", url=url) == "x *** y"


def test_a_gap_of_seven_characters_is_the_limit_of_a_chain() -> None:
    url = "postgresql://bob:Zq@qx:zv@h/db"
    assert "qx" in safe_message("no route to qx.......zv now", url=url)


def test_a_short_token_is_removed_only_beside_the_at_that_follows_it() -> None:
    """The word ``abc`` is not removed from a message because a password contains it."""
    url = "postgresql://bob:abc@xyz@h/db"
    assert safe_message("the abc table", url=url) == "the abc table"
    assert safe_message("host 'abc@h'", url=url) == "host '***@h'"


def test_a_short_token_beside_an_at_is_removed_whatever_its_case() -> None:
    """A resolver lower-cases a host name before it echoes it (clickhouse, hdbcli: measured)."""
    url = "postgresql://bob:Zq7xK9mWpL3@Ab@127.0.0.1:1/db"
    assert safe_message("failed to resolve host 'ab@127.0.0.1'", url=url) == (
        "failed to resolve host '***@127.0.0.1'"
    )


def test_the_tail_after_the_first_at_is_removed_even_when_every_token_is_short() -> None:
    """``aaa#`` holds three alphanumeric characters, so no token or chain of it qualifies. The tail
    does: it is what SQLAlchemy hands the driver as a host."""
    url = "postgresql://bob:@aaa#@127.0.0.1:1/db"
    assert safe_message("failed to resolve host 'aaa#@127.0.0.1'", url=url) == (
        "failed to resolve host '***@127.0.0.1'"
    )


def test_the_pieces_are_bounded_however_long_the_password_is() -> None:
    """The scrub runs inside an ``except`` block that must not stall. Distinct tokens defeat the
    de-duplication that kept the repeated-token test above fast."""
    password = "@".join(f"t{i:05d}x" for i in range(3000))
    patterns, short = db_module._password_patterns(password)
    assert len(patterns) <= db_module._MAX_PATTERNS
    assert short == []
    start = time.perf_counter()
    safe_message("x " * 5000, url=f"postgresql://bob:{password}@h/db")
    assert time.perf_counter() - start < 10.0


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("bob:Zq7x://Kw3d@h/db", ("bob:", "Zq7x://Kw3d", "@h/db")),
        ("postgresql://bob@db.example:$DB_PORT/claims", None),
        ("postgresql//bob@h:5432/db", None),
        ("bob@h:5432/db", None),
    ],
)
def test_the_split_finds_no_password_where_there_is_none(
    url: str, expected: tuple[str, str, str] | None
) -> None:
    """A colon AFTER the ``@`` is the host's port, not a user's: the search stops at the ``@``."""
    assert db_module._split_userinfo(url) == expected


def test_a_proper_scheme_is_found_before_a_separator_inside_the_password() -> None:
    url = "postgresql://bob:Zq7x://Kw3d@h:$DB_PORT/db"
    assert redact_db_url(url) == "postgresql://bob:***@h:$DB_PORT/db"


def test_a_repeated_query_key_with_an_at_in_it_is_a_legitimate_query() -> None:
    url = "postgresql://bob:hunter2@db.example:5432/claims?a=b&a=c@d"
    assert redact_db_url(url) == "postgresql://bob:***@db.example:5432/claims?a=b&a=c%40d"


def test_a_chain_does_not_bridge_alphanumerics() -> None:
    """The gap is characters that are NOT alphanumeric; ``.{0,6}`` would remove a phrase."""
    url = "postgresql://bob:Zq@qx:zv@h/db"
    assert safe_message("no route to qx and zv now", url=url) == "no route to qx and zv now"


def test_an_address_that_is_only_a_query_keeps_an_at_in_its_value() -> None:
    """A raw ``odbc_connect`` payload holds ``Uid=ann@srv``: no userinfo, no host, no database."""
    url = (
        "mssql+pyodbc:///?odbc_connect=Driver={ODBC Driver 18 for SQL Server};"
        "Server=tcp:srv.database.windows.net,1433;Database=claims;Uid=ann@srv;"
        "Pwd=Sup3rSecretValue;Encrypt=yes"
    )
    shown = redact_db_url(url)
    assert "srv.database.windows.net" in shown
    assert "Sup3rSecretValue" not in shown
    text = "Login failed for srv.database.windows.net claims"
    assert safe_message(text, url=url) == text


@pytest.mark.parametrize(
    "url",
    [
        "sqlite+pysqlcipher://:Pass@word1234@/enc.db",
        "sqlite://bob:P@ssw0rdXYZ@127.0.0.1/db",
    ],
)
def test_a_sqlite_family_address_with_a_password_is_not_exempt(url: str) -> None:
    """``sqlite+pysqlcipher`` keeps a passphrase in the password field: the backend name alone is
    not a reason to trust the parse (the review's red-team lens, measured on the real console)."""
    shown = redact_db_url(url)
    assert "word1234" not in shown
    assert "ssw0rdXYZ" not in shown


def test_a_sqlalchemy_url_made_from_an_ambiguous_string_is_read_as_typed() -> None:
    """``make_url`` has already split ``P@ssw0rdXYZ@h`` into a password ``P`` and a host
    ``ssw0rdXYZ@h``; rendering the object restores the ``@`` the trigger looks for."""
    url = sa.make_url("postgresql://bob:P@ssw0rdXYZ@127.0.0.1:1/db")
    assert leaked_run("P@ssw0rdXYZ", redact_db_url(url)) is None
    cleaned = safe_message("could not translate host name 'ssw0rdXYZ@127.0.0.1'", url=url)
    assert leaked_run("P@ssw0rdXYZ", cleaned) is None


def test_a_lone_surrogate_in_the_address_does_not_raise() -> None:
    """``render_as_string`` raises on one, and the masked address is rendered again."""
    assert "ssw0rd" not in redact_db_url("postgresql://bob:p@ssw0rd@h/db\udcff")


def test_a_non_latin_password_is_removed_in_its_bytes_repr_too() -> None:
    """pymssql prints a bytes repr of the host (captured: ``mWpL\\xc3\\xa93\\xc3\\xbc``)."""
    password = "Zq7xK9@\u5bc6\u7801\u5f88\u957f"
    url = f"mssql+pymssql://bob:{password}@127.0.0.1:1/db"
    escaped = "".join(f"\\x{b:02x}" for b in "\u5bc6\u7801\u5f88\u957f".encode())
    text = f"Unable to connect: TDS server is unavailable ({escaped}@127.0.0.1)"
    cleaned = safe_message(text, url=url)
    assert "\\xe5" not in cleaned
    assert "127.0.0.1" in cleaned


def test_a_long_password_keeps_every_token_a_driver_echoes_of_one_field() -> None:
    """Past ``_MAX_PATTERNS`` the cap must drop the chains of MOST tokens, not the single tokens a
    driver echoes (the review's red-team lens: 50 tokens leaked the first)."""
    password = "tok00000@" + "/".join(f"t{i:05d}x" for i in range(1, 60))
    url = f"postgresql://bob:{password}@127.0.0.1:1/db"
    for token in ("t00001x", "t00030x", "t00059x"):
        cleaned = safe_message(f"could not translate host name \"{token}\" to address", url=url)
        assert token not in cleaned


def test_a_100_kilobyte_address_does_not_stall_the_scrub() -> None:
    """The bounds on exact pieces and tokens are performance bounds: without them an address of
    100,000 ``@`` took 8.6 s (measured by the review; 0.001 s with them). Mutating the code cannot
    show that, only a size can."""
    url = "postgresql://bob:" + "@" * 100_000 + "h/db"
    start = time.perf_counter()
    safe_message("x y z", url=url)
    redact_db_url(url)
    assert time.perf_counter() - start < 5.0


def test_a_url_of_a_type_nobody_expected_is_tolerated() -> None:
    """``safe_message`` runs inside the ``except`` blocks that deliver "never raises": an address
    that is neither a string nor a URL is not a reason to raise, or to withhold the text."""
    assert safe_message("x y", url=12345) == "x y"  # type: ignore[arg-type]


def test_a_lone_surrogate_in_a_query_value_does_not_raise() -> None:
    """``render_as_string`` percent-encodes the query and raises on a lone surrogate, and the
    masked address is rendered once more."""
    shown = redact_db_url("postgresql://bob:p@ssw0rdXYZ@h/db?x=\udcff")
    assert "ssw0rdXYZ" not in shown


def test_the_tail_after_the_first_at_goes_whole_when_no_token_or_chain_can() -> None:
    """``ab:c`` has three alphanumeric characters: no token and no chain reaches four, and the
    short token ``c`` alone would leave ``ab:``. The tail is four characters, so it is a piece."""
    url = "postgresql://bob:Zq7xK9@ab:c@127.0.0.1:1/db"
    assert safe_message("failed to resolve host 'ab:c@127.0.0.1'", url=url) == (
        "failed to resolve host '***@127.0.0.1'"
    )


def test_a_chain_of_short_non_latin_tokens_bridges_what_a_driver_puts_between_them() -> None:
    """Two letters each, so only a chain of the Unicode tokens can remove them, with the Unicode
    gap: a bracket and a backslash are not letters in either alphabet."""
    url = "postgresql://bob:Zq@\u5bc6\u7801:\u79d8\u5bc6@127.0.0.1:1/db"
    cleaned = safe_message("no route to \u5bc6\u7801[\\\u79d8\u5bc6] now", url=url)
    assert "\u5bc6" not in cleaned
    assert "\u79d8" not in cleaned


def test_a_password_of_many_short_tokens_does_not_stall_the_scrub() -> None:
    """A chain is built from every token and every length up to six: unbounded, a password of
    200,000 tokens costs seconds and megabytes in an ``except`` block. Only a size can show it."""
    url = "postgresql://bob:" + "".join(f"t{i}@" for i in range(60_000)) + "h/db"
    start = time.perf_counter()
    safe_message("x y z", url=url)
    assert time.perf_counter() - start < 5.0
