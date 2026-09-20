"""Unit tests for the Data Agent's DB helpers — specifically dialect derivation.

``sql_dialect_from_url`` is what stops the generated SQL from being written for
the wrong database. Session 216 measured every SQL-execution failure on *every*
provider as an unsupported-function error (``DATEDIFF``,
``PERCENTILE_CONT … WITHIN GROUP``, ``MEDIAN``) against a SQLite target: the
model was writing warehouse SQL because nothing told it otherwise. These tests
pin the parse-only derivation that feeds the prompt.

No database is created and no driver is installed for the non-SQLite URLs —
that is the point: ``make_url`` parses the string, so the dialect is knowable
before connecting and without the DBAPI package being present.

Session 223 measured the *failure* surface the same way, against SQLAlchemy
2.0.49: ``make_url`` reports a structurally unparseable URL as
``sa.exc.ArgumentError``, but coerces the port segment with a bare ``int()``,
so a non-numeric port escapes as the raw ``ValueError`` — and ``ArgumentError``
is **not** a ``ValueError`` subclass. Five inputs take that second path (an
unexpanded environment variable, an alphabetic port, an empty port, a float
port, and an IPv6 host with a bad port); the derivation had been catching only
the first type since it was written, which made its own "degrades rather than
raising" promise false for all five. The tests below pin both arms of that
catch, and its upper bound.
"""

from __future__ import annotations

import logging

import pytest
from model_project_constructor_data_agent.db import (
    DBConnectionError,
    ReadOnlyDB,
    redact_db_url,
    redact_secrets,
    sql_dialect_from_url,
)

DB_LOGGER_NAME = "model_project_constructor_data_agent.db"


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("sqlite:///:memory:", "sqlite"),
        ("sqlite:////tmp/pc_eval.db", "sqlite"),
        ("postgresql://user:pw@host:5432/claims", "postgresql"),
        # ``get_backend_name`` strips the ``+driver`` suffix, so a prompt built
        # from this says "postgresql", not "postgresql+psycopg".
        ("postgresql+psycopg://user:pw@host/claims", "postgresql"),
        ("mysql+pymysql://user:pw@host/claims", "mysql"),
        ("mssql+pyodbc://user:pw@host/claims", "mssql"),
        # Dialects with no driver installed here still parse — derivation is
        # string-only, so an enterprise warehouse URL works without the package.
        ("snowflake://user:pw@account/claims/public", "snowflake"),
        ("duckdb:///warehouse.duckdb", "duckdb"),
    ],
)
def test_dialect_derived_from_url_without_connecting(url: str, expected: str) -> None:
    assert sql_dialect_from_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not a url at all",
        "://missing-scheme",
    ],
)
def test_unparseable_url_degrades_to_none(url: str) -> None:
    """A malformed URL must not raise here.

    The dialect is an optional prompt enrichment; the URL's real failure belongs
    to ``connect()``, which callers already handle. Raising during prompt
    construction would turn a bad ``--db-url`` into a crash before the agent
    ever reports why.
    """
    assert sql_dialect_from_url(url) is None


@pytest.mark.parametrize(
    "url",
    [
        # The case that bites in practice: a ``--db-url`` templated from a shell
        # environment where the port variable was never exported.
        "postgresql://user:pw@host:$DB_PORT/claims",
        "postgresql://user:pw@host:${DB_PORT}/claims",
        "postgresql://user:pw@host:abc/claims",
        # An empty port — the same shell template with the variable set to "".
        "postgresql://user:pw@host:/claims",
        "postgresql://user:pw@host:54.32/claims",
        # IPv6 literal plus a bad port: the host bracket parses, the port does not.
        "postgresql://user:pw@[::1]:$DB_PORT/claims",
        "mysql+pymysql://user:pw@host:$MYSQL_PORT/claims",
    ],
)
def test_non_numeric_port_degrades_to_none(url: str) -> None:
    """A non-numeric port must degrade like any other unparseable URL.

    Regression test for the contract violation filed in Session 218 and fixed in
    Session 223. ``make_url`` coerces the port with a bare ``int()``, so this
    class escaped as a raw ``ValueError`` — and ``sa.exc.ArgumentError`` is
    **not** a ``ValueError`` subclass (it derives from ``SQLAlchemyError``), so
    the original single-type catch could never have caught it.

    This is not a hypothetical input. Both production seams that derive a
    dialect — ``scripts/run_pipeline.py`` and the data agent's CLI — take the
    URL straight from the user, and the derivation runs *before* the DB is
    connected. So an unexpanded ``$DB_PORT`` produced a raw traceback that
    pre-empted the very error path (``ReadOnlyDB.connect`` raising
    ``DBConnectionError``) that was designed to report it.

    This test also pins the **width** of the catch: narrowing it back to
    ``except sa.exc.ArgumentError`` alone makes every case here raise.
    """
    assert sql_dialect_from_url(url) is None


def test_out_of_range_port_still_parses() -> None:
    """Dialect derivation is not URL validation — do not "fix" this into one.

    ``int()`` accepts a negative or absurdly large port, so these parse and
    yield a dialect. That is deliberate: this function's only job is to tell the
    prompt which SQL dialect to write, and judging whether the URL describes a
    reachable database belongs to ``connect()``. Tightening this into range
    validation would reintroduce the raise-at-prompt-construction bug from the
    other direction.
    """
    assert sql_dialect_from_url("postgresql://user:pw@host:-1/claims") == "postgresql"
    assert sql_dialect_from_url("postgresql://user:pw@host:99999999999/claims") == "postgresql"


def test_unexpected_error_propagates_rather_than_degrading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The catch has an upper bound too: only *parse* failures degrade.

    Pins the other side of the Session 223 widening. ``except Exception`` would
    make every test above pass while silently converting a genuine defect in
    this function — a typo, a bad SQLAlchemy upgrade, an import-time breakage —
    into a ``None`` that reads as "the operator typed a bad URL". The dialect
    would then go quietly missing from the prompt and the generated SQL would be
    written for the wrong database, which is precisely the failure this module
    exists to prevent (see the module docstring).

    Verified by mutation: without this test, widening the catch to
    ``except Exception`` leaves the whole file green.
    """
    import sqlalchemy as sa

    def _boom(_url: str) -> object:
        raise RuntimeError("SQLAlchemy internals changed shape")

    monkeypatch.setattr(sa, "make_url", _boom)
    with pytest.raises(RuntimeError, match="SQLAlchemy internals changed shape"):
        sql_dialect_from_url("postgresql://user:pw@host:5432/claims")


def test_readonly_db_dialect_degrades_on_non_numeric_port() -> None:
    """The property delegates, so it inherits the fix — pinned, not assumed."""
    db = ReadOnlyDB("postgresql://user:pw@host:$DB_PORT/claims")
    assert db.dialect is None


def test_readonly_db_exposes_dialect_before_connect() -> None:
    """The accessor must work pre-``connect()``.

    ``generate_queries`` is the first node in the graph and the DB is not
    connected until ``execute_qc``, so a dialect that required a live connection
    would arrive too late to reach the prompt.
    """
    db = ReadOnlyDB("sqlite:///:memory:")
    assert db._engine is None  # not connected
    assert db.dialect == "sqlite"


def test_readonly_db_dialect_matches_module_function() -> None:
    db = ReadOnlyDB("postgresql://user:pw@host/claims")
    assert db.dialect == sql_dialect_from_url(db.url)


# ---------------------------------------------------------------------------
# Session 260 — the connect error's cause is reported, and carries no secret.
#
# ``execute_qc`` now binds the ``DBConnectionError`` and the text reaches
# ``DataReport.data_quality_concerns``, which is serialized to the ``--output``
# report, the checkpoint envelope and the generated project's
# ``reports/data_report.{json,md}``. That makes the message's contents a
# publication decision, not just a diagnostic one: before this session
# ``connect`` composed it from ``self.url`` raw, so a password went with it.
#
# The shapes below are the ones that defeated earlier drafts of the redaction,
# kept as tests precisely because a hand-picked example list did not find them:
# a password containing ``@`` (masking stops at the FIRST one, leaving a tail),
# one containing ``/`` or a space (a character class excluding them masks
# NOTHING), and ``?password=`` in the query string — a second, fully functional
# credential channel SQLAlchemy passes to the DBAPI.
# ---------------------------------------------------------------------------

SECRET = "hunter2"


@pytest.mark.parametrize(
    ("url", "secret"),
    [
        ("postgresql://user:hunter2@host:5432/claims", SECRET),
        # The case this project actually hits: a --db-url templated from a
        # shell environment where the port variable was never exported. It does
        # not parse, so the structural path cannot run and the fallback must.
        ("postgresql://user:hunter2@host:$DB_PORT/claims", SECRET),
        ("postgresql+psycopg://user:hunter2@host/claims", SECRET),
        # Unencoded metacharacters in the password. RFC 3986 says percent-encode
        # them; an operator pasting a generated password does not.
        ("postgresql://user:p@ss@host:$DB_PORT/claims", "p@ss"),
        ("postgresql://user:p/ss@host:$DB_PORT/claims", "p/ss"),
        ("postgresql://user:my pass@host:$DB_PORT/claims", "my pass"),
        # The query string is a credential channel of its own.
        ("postgresql://host:5432/claims?password=hunter2", SECRET),
        ("postgresql://user:hunter2@host/claims?sslpassword=hunter2", SECRET),
    ],
)
def test_redact_db_url_masks_every_secret_shape(url: str, secret: str) -> None:
    """Assert the SECRET is gone, never that a ``***`` marker is present.

    A marker assertion passes on a partial leak: an earlier draft turned
    ``user:p@ss@host`` into ``user:***@ss@host``, which shows the marker while
    publishing the tail of the password.
    """
    assert secret not in redact_db_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://host:5432/claims",  # no credential at all
        "postgresql://user@host/claims",  # user, no password
        "sqlite:///:memory:",
        "sqlite:////nonexistent/path/does/not/exist.db",
        "not-a-url",
    ],
)
def test_redact_db_url_leaves_a_secretless_url_alone(url: str) -> None:
    """Over-masking is safe but destroys the diagnostic; don't do it."""
    assert redact_db_url(url) == url


def test_redact_db_url_is_idempotent() -> None:
    once = redact_db_url("postgresql://user:hunter2@host:5432/claims")
    assert redact_db_url(once) == once


def test_redact_secrets_masks_a_driver_echoed_dsn() -> None:
    """A driver may echo a libpq ``key=value`` DSN rather than a URL."""
    assert SECRET not in redact_secrets(
        "connection failed: password=hunter2 host=warehouse"
    )


def test_redact_secrets_preserves_a_message_with_no_secret() -> None:
    msg = "invalid literal for int() with base 10: '$DB_PORT'"
    assert redact_secrets(msg) == msg


def test_connect_error_names_the_cause_without_the_password() -> None:
    """Both halves matter: no secret, and still diagnostic.

    A redaction that also ate the cause would trade this item's bug for a
    quieter version of the same one.
    """
    db = ReadOnlyDB(f"postgresql://user:{SECRET}@warehouse.invalid:$DB_PORT/claims")
    with pytest.raises(DBConnectionError) as excinfo:
        db.connect()

    message = str(excinfo.value)
    assert SECRET not in message
    assert "warehouse.invalid" in message
    assert "$DB_PORT" in message


def test_connect_error_masks_a_query_string_password() -> None:
    db = ReadOnlyDB(f"postgresql://warehouse.invalid:5432/claims?password={SECRET}")
    with pytest.raises(DBConnectionError) as excinfo:
        db.connect()

    assert SECRET not in str(excinfo.value)


# --- option (b): a PARSE failure is distinguishable from a CONNECT failure ---


def test_unparseable_url_warns_and_names_the_cause(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger=DB_LOGGER_NAME):
        assert sql_dialect_from_url(f"postgresql://user:{SECRET}@host:$DB_PORT/db") is None

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    message = warnings[0].getMessage()
    assert "invalid literal for int() with base 10" in message
    assert "PARSE" in message
    assert SECRET not in message


def test_a_parseable_url_warns_about_nothing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Load-bearing negative.

    Without it, a later change making the warning unconditional would fire on
    every healthy run and nothing would notice.
    """
    with caplog.at_level(logging.WARNING, logger=DB_LOGGER_NAME):
        assert sql_dialect_from_url("sqlite:///:memory:") == "sqlite"

    assert [r for r in caplog.records if r.levelno == logging.WARNING] == []


def test_readonly_db_dialect_seam_warns(caplog: pytest.LogCaptureFixture) -> None:
    """``cli.py`` evaluates ``ReadOnlyDB.dialect``, not the module function."""
    with caplog.at_level(logging.WARNING, logger=DB_LOGGER_NAME):
        assert ReadOnlyDB("postgresql://user:pw@host:$DB_PORT/claims").dialect is None

    assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 1
