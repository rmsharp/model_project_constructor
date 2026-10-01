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
from typing import NoReturn

import pytest
import sqlalchemy as sa
from model_project_constructor_data_agent import db as db_module
from model_project_constructor_data_agent.db import (
    DBConnectionError,
    ReadOnlyDB,
    redact_db_url,
    redact_secrets,
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
#: is not a password, which is what a looser trigger would mistake for one (Session 271 regression
#: lens: counting every ``@`` rewrote the first of these to ``bob:***@nightly``).
SECRETLESS = [
    "sqlite:////tmp/a@b:c/x@y.db",
    "sqlite:///C:/Users/ann@corp/x@y.db",
    "sqlite:///rel/a@b:c/x@y.db",
    "mssql+pyodbc:///?odbc_connect=DRIVER%3D%7BODBC+Driver+17%7D%3BUID%3Dann%40corp",
]


@pytest.mark.parametrize("url", SECRETLESS)
def test_an_address_with_no_password_is_echoed_unchanged(url: str) -> None:
    assert redact_db_url(url) == url


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
    """Both halves matter: no password, and still diagnostic. Every shape's host is 127.0.0.1."""
    with pytest.raises(DBConnectionError) as excinfo:
        ReadOnlyDB(url).connect()
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
# named driver and version against a refused or unresolvable target, for the typed password shown,
# and then hand-copied here: no driver is installed in this project. A driver re-escapes, brackets,
# strips, splits, truncates or lower-cases what it echoes, so the scrub matches the ALPHANUMERIC
# TOKENS of the password and never the text a driver might have rewritten around them.
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
        '(2003, "Can\'t connect to MySQL server on \'mWpL3\\\'Vb5nY@127.0.0.1\'")',
    ),
    (
        "pymssql-bytes-repr",
        "pymssql",
        "mssql+pymssql://bob:Zq7xK9@mWpL\u00e93\u00fc@127.0.0.1:1/db",
        "Unable to connect: TDS server is unavailable (mWpL\\xc3\\xa93\\xc3\\xbc@127.0.0.1)",
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
        "Code: 210. Connection refused (mwpl3:9000)",
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
    collapses whitespace. Removing the password AFTER that leaks it: the typed password has the
    control in it, and the flattened text no longer does (measured on psycopg2, pg8000 and
    mysql-connector with a tab, a newline or a NUL after the ``@``)."""
    url = f"postgresql+psycopg2://bob:Zq7xK9@mWpL3{control}Vb5nY@127.0.0.1:1/db"
    text = f'could not translate host name "mWpL3{control}Vb5nY@127.0.0.1" to address'
    cleaned = safe_message(text, url=url)
    assert leaked_run("Zq7xK9@mWpL3 Vb5nY", cleaned) is None
    assert "127.0.0.1" in cleaned


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
    import time

    password = "@".join(["ab:cdefgh"] * 3000)
    url = f"postgresql://bob:{password}@h/db"
    start = time.perf_counter()
    safe_message("x " * 5000, url=url)
    assert time.perf_counter() - start < 2.0


def test_redact_secrets_takes_the_address_too() -> None:
    """The dialect warning calls ``redact_secrets`` on the parse error, not ``safe_message``."""
    url = "postgresql://bob:Zq7xK9@mWpL3:Vb5nY@127.0.0.1:1/db"
    text = "invalid literal for int() with base 10: 'Vb5nY@127.0.0.1:1'"
    assert leaked_run("Vb5nY", redact_secrets(text, url=url)) is None
    assert redact_secrets(text) == text  # no address: unchanged, as before


def test_a_scrub_that_cannot_finish_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """The scrub runs inside the ``except`` blocks that deliver "never raises", and a scrub that
    stopped part-way has not removed the password: say so, and show nothing."""

    def _boom(password: str) -> NoReturn:
        raise RuntimeError("boom")

    monkeypatch.setattr(db_module, "_password_patterns", _boom)
    url = "postgresql://bob:P@ssw0rdXYZ@127.0.0.1:1/db"
    assert safe_message("failed to resolve host 'ssw0rdXYZ@127.0.0.1'", url=url) == "<unprintable>"
    assert redact_secrets("ssw0rdXYZ", url=url) == "<unprintable>"
