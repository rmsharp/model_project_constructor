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
import sys
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
import sqlalchemy as sa
from model_project_constructor_data_agent.db import (
    DBConnectionError,
    ReadOnlyDB,
    SkippedEntity,
    redact_db_url,
    redact_secrets,
    safe_class_name,
    safe_message,
    sql_dialect_from_url,
)

from tests.hostile_text import (
    CONNECT_CAUSE,
    CONTROLS,
    ESCAPE_NAME,
    ESCAPE_NAME_SCRUBBED,
    ESCAPING_URL,
    EVERY_CONTROL,
    NON_SPACE_CONTROLS,
    NameThatIsAHostileStr,
    NameThatRaises,
    control_ids,
    unsafe,
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


# ---------------------------------------------------------------------------
# Session 262: `redact_secrets` fails open on shapes inside its own claimed
# coverage (BACKLOG.md, filed Session 261). Every case below leaked verbatim
# under the Session 261 implementation -- measured before this session wrote
# any code. Secret-ABSENCE only (learning #268): a `***`-present assertion
# passes on a partial mask, which is exactly how the original regression here
# was missed.
# ---------------------------------------------------------------------------


SPACED_SECRET = "hunter two"  # libpq requires quoting/bracing precisely BECAUSE of
# the space -- a case built around plain SECRET (no space) cannot tell a quote-
# or brace-aware value class from a bare `\S+` one that merely swallows the
# quote/brace characters along with an unspaced secret and passes by accident.


@pytest.mark.parametrize(
    ("text", "secret"),
    [
        (f"DB_PASSWORD={SECRET}", SECRET),
        (f"PGPASSWORD={SECRET}", SECRET),
        (f"db_password={SECRET}", SECRET),
        (f"access_token={SECRET}", SECRET),
        (f"client_secret={SECRET}", SECRET),
        (f"password='{SPACED_SECRET}'", SPACED_SECRET),
        (f'password="{SPACED_SECRET}"', SPACED_SECRET),
        (f"password = {SECRET}", SECRET),
        (f"password: {SECRET}", SECRET),
        (f"{{'password': '{SPACED_SECRET}'}}", SPACED_SECRET),
        (f'{{"password": "{SPACED_SECRET}"}}', SPACED_SECRET),
    ],
    ids=[
        "prefixed-key-upper", "prefixed-key-pg", "prefixed-key-lower", "access_token",
        "client_secret", "single-quoted-with-space", "double-quoted-with-space",
        "spaced-equals", "colon-separator", "single-quoted-json-with-space",
        "double-quoted-json-with-space",
    ],
)
def test_redact_secrets_masks_the_item_leak_table(text: str, secret: str) -> None:
    """`BACKLOG.md`'s leak table, one row per case. The quoted/braced rows use
    `SPACED_SECRET`: a bare, unquoted value class stops at the first
    whitespace, so only a secret containing one actually exercises the quote
    handling the item is about (`password='x'` with no space would pass even
    with quote support ripped out, because bare `\\S+` matches the quotes too)."""
    assert secret not in redact_secrets(text)


@pytest.mark.parametrize(
    ("fn", "text", "secret", "also_gone"),
    [
        # Class 1: a userinfo USERNAME containing '@' (Azure / email-login,
        # which SQLAlchemy accepts unencoded) defeated a pattern that stops at
        # the FIRST '@' rather than the last one before the host.
        (redact_secrets, f"connect to postgresql://svc@myserver:{SECRET}@host/db failed",
         SECRET, None),
        # Class 2: a TAIL leak -- the secret's own unescaped tail past a
        # character the value class stops at. The ODBC case uses a SPACED
        # secret (the item's own example, `PWD={x1 y2};` -> `*** y2};`):
        # without brace support the bare class stops at the space, same as
        # the ampersand case stops at `&`. `secret` is deliberately just the
        # part BEFORE the stop character -- the part a bare, unbraced/
        # unescaped match still catches -- so the test cannot pass merely
        # because the whole string never contained `secret` to begin with;
        # `also_gone` is the tail past the stop character.
        (redact_secrets, f"password={SECRET}&y2", SECRET, "y2"),
        (redact_secrets, f"Driver={{X}};PWD={{{SPACED_SECRET}}};Database=d",
         SPACED_SECRET.split()[0], SPACED_SECRET.split()[-1]),
        # Class 3: percent-encoded inside an `odbc_connect=` payload.
        (redact_db_url,
         "mssql+pyodbc:///?odbc_connect=DRIVER%3D%7BODBC+Driver+17%7D%3BUID%3Dsa%3B"
         f"PWD%3D{SECRET}%3B",
         SECRET, None),
        # Class 4: camel-cased / hyphenated keys outside the original fixed list.
        (redact_secrets, f"AccessToken={SECRET}", SECRET, None),
        (redact_secrets, f"sessionToken={SECRET}", SECRET, None),
        (redact_secrets, f"X-Amz-Signature={SECRET}", SECRET, None),
        (redact_secrets, f"passcode={SECRET}", SECRET, None),
    ],
    ids=["userinfo-at-in-username", "tail-after-ampersand", "tail-inside-odbc-brace",
         "percent-encoded-odbc-connect", "camel-cased-key", "camel-cased-key-session",
         "hyphenated-key", "passcode-key"],
)
def test_redact_secrets_masks_the_four_further_classes(
    fn: object, text: str, secret: str, also_gone: str | None
) -> None:
    """The item's second table: four classes a second reviewer measured, not
    themselves in the leak table. `also_gone`, where given, is the secret's
    own tail -- the shape that a mask stopping at the first stop character
    leaves published."""
    out = fn(text)  # type: ignore[operator]
    assert secret not in out
    if also_gone is not None:
        assert also_gone not in out


@pytest.mark.parametrize(
    "text",
    [
        f"?password={SECRET}&sslmode=require",
        f"host=warehouse password={SECRET} dbname=claims",
    ],
    ids=["stops-before-a-real-kv-pair", "stops-at-whitespace"],
)
def test_redact_secrets_stops_at_the_next_real_field(text: str) -> None:
    """A wider tail match (the fix for the class-2 leak above) must not eat an
    ADJACENT, unrelated field. Without this, a mutant that always consumes to
    end-of-string would pass every test above and still over-mask."""
    out = redact_secrets(text)
    assert SECRET not in out
    assert "sslmode=require" in out or "dbname=claims" in out


def test_redact_secrets_preserves_realistic_diagnostics_with_no_secret() -> None:
    """Widening the key list must not start matching ordinary diagnostic
    prose. Each of these was hand-picked because it is one edit distance from
    a false positive: 'secretary' contains 'secret', 'tokenizer' contains
    'token', 'passcode' is now itself a matched key."""
    for msg in (
        'FATAL:  password authentication failed for user "claims_ro"',
        'connection to server at "warehouse.invalid" (10.0.0.5), port 5432 '
        "failed: Connection refused",
        "(sqlite3.OperationalError) no such table: main.claims",
        "tokenizer=bert max_token_length: 5",
        "password_policy=strict secretary: Jane",
    ):
        assert redact_secrets(msg) == msg


def test_redact_secrets_is_idempotent() -> None:
    once = redact_secrets(f"DB_PASSWORD={SECRET}")
    assert redact_secrets(once) == once


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


# --- get_information_schema: one entity that cannot be reflected is skipped ---

#: What a warehouse built by ``_warehouse`` reflects, in the order it does:
#: tables first, then views, each alphabetical.
GOOD = ["claims", "policies", "v_b_good", "v_y_good"]


def _warehouse(path: Path, *stale: str) -> str:
    """Two tables and two good views, plus one view per ``stale`` name whose base
    table was dropped. SQLite allows that drop (PostgreSQL refuses it), and
    reflecting such a view's columns raises ``OperationalError`` (measured
    Session 265, on SQLAlchemy 2.0.49)."""
    statements = [
        "CREATE TABLE claims (claim_id INTEGER PRIMARY KEY)",
        "CREATE TABLE policies (policy_id INTEGER PRIMARY KEY)",
        "CREATE VIEW v_b_good AS SELECT claim_id FROM claims",
        "CREATE VIEW v_y_good AS SELECT policy_id FROM policies",
    ]
    for name in stale:
        statements += [
            f"CREATE TABLE doomed_{name} (x INTEGER)",
            f"CREATE VIEW {name} AS SELECT x FROM doomed_{name}",
            f"DROP TABLE doomed_{name}",
        ]
    engine = sa.create_engine(f"sqlite:///{path}")
    try:
        with engine.begin() as conn:
            for statement in statements:
                conn.execute(sa.text(statement))
    finally:
        engine.dispose()
    return f"sqlite:///{path}"


@contextmanager
def _connected(url: str) -> Iterator[ReadOnlyDB]:
    db = ReadOnlyDB(url)
    db.connect()
    try:
        yield db
    finally:
        db.close()


def _described(skipped: list[SkippedEntity]) -> list[tuple[str, str, str]]:
    return [(s.namespace, s.name, s.entity_kind) for s in skipped]


def test_without_a_collector_an_unreflectable_view_still_raises(tmp_path: Path) -> None:
    """The default is unchanged. A caller that wants all or nothing — the eval
    corpus, ``tests/eval/eval_corpus.py`` — passes no list and still gets the
    error rather than a silently shorter result."""
    with (
        _connected(_warehouse(tmp_path / "w.db", "v_stale")) as db,
        pytest.raises(sa.exc.OperationalError, match="no such table: main.doomed_v_stale"),
    ):
        db.get_information_schema()


@pytest.mark.parametrize(
    "stale", ["v_a_stale", "v_m_stale", "v_z_stale"], ids=["first", "middle", "last"]
)
def test_an_unreflectable_view_is_collected_and_the_rest_kept(
    tmp_path: Path, stale: str
) -> None:
    """Session 265. The stale view goes first, between and after the good views,
    so a walk that stops at the first skip, or checks only one end, cannot pass."""
    skipped: list[SkippedEntity] = []
    with _connected(_warehouse(tmp_path / "w.db", stale)) as db:
        rows = db.get_information_schema(skipped=skipped)

    assert [r["name"] for r in rows] == GOOD
    assert _described(skipped) == [("main", stale, "view")]
    assert isinstance(skipped[0].error, sa.exc.OperationalError)
    assert f"no such table: main.doomed_{stale}" in str(skipped[0].error)


def test_every_unreflectable_view_is_collected_in_order(tmp_path: Path) -> None:
    """Before Session 265 only the FIRST was ever named: the error stopped the
    walk, so a second stale view stayed invisible until the first was fixed."""
    skipped: list[SkippedEntity] = []
    with _connected(_warehouse(tmp_path / "w.db", "v_a_stale", "v_z_stale")) as db:
        rows = db.get_information_schema(skipped=skipped)

    assert [r["name"] for r in rows] == GOOD
    assert _described(skipped) == [
        ("main", "v_a_stale", "view"),
        ("main", "v_z_stale", "view"),
    ]


@pytest.mark.parametrize("first", [True, False], ids=["ghost-first", "ghost-last"])
def test_a_table_dropped_mid_walk_is_collected_as_a_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, first: bool
) -> None:
    """A table listed and then dropped before its columns are read — concurrent
    DDL on a busy warehouse, and a failure any dialect can have. SQLAlchemy
    reports it as ``NoSuchTableError``, which the walk must skip like any other
    database error."""
    listed = sa.engine.reflection.Inspector.get_table_names

    def _with_ghost(self: Any, schema: str | None = None, **kw: Any) -> list[str]:
        real = listed(self, schema=schema, **kw)
        return ["ghost", *real] if first else [*real, "ghost"]

    monkeypatch.setattr(sa.engine.reflection.Inspector, "get_table_names", _with_ghost)
    skipped: list[SkippedEntity] = []
    with _connected(_warehouse(tmp_path / "w.db")) as db:
        rows = db.get_information_schema(skipped=skipped)

    assert [r["name"] for r in rows] == GOOD
    assert _described(skipped) == [("main", "ghost", "table")]
    assert isinstance(skipped[0].error, sa.exc.NoSuchTableError)


def test_a_non_database_error_is_never_collected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only a database error is skippable. Anything else is a defect in this code
    or in a dialect, and skipping it would hide the defect table by table."""
    reflect = ReadOnlyDB._reflect_entity

    def _broken_for_policies(
        inspector: Any, schema: str, name: str, entity_kind: str
    ) -> dict[str, Any]:
        if name == "policies":
            raise KeyError("referred_table")
        return reflect(inspector, schema, name, entity_kind)

    monkeypatch.setattr(ReadOnlyDB, "_reflect_entity", staticmethod(_broken_for_policies))
    skipped: list[SkippedEntity] = []
    with (
        _connected(_warehouse(tmp_path / "w.db")) as db,
        pytest.raises(KeyError, match="referred_table"),
    ):
        db.get_information_schema(skipped=skipped)
    assert skipped == []


def _outage_at(monkeypatch: pytest.MonkeyPatch, target: str, directory: Path) -> None:
    """Make the database unreachable just before ``target`` is reflected.

    Disposing the pool drops every open connection, and moving the database's
    directory away makes each new one fail with SQLite's "unable to open
    database file" — a real ``OperationalError`` from a real connect, which is
    what a warehouse that goes away mid-walk raises for every entity after it."""
    reflect = ReadOnlyDB._reflect_entity

    def _reflect(inspector: Any, schema: str, name: str, entity_kind: str) -> dict[str, Any]:
        if name == target:
            inspector.bind.dispose()
            directory.rename(directory.with_name(directory.name + "_gone"))
        return reflect(inspector, schema, name, entity_kind)

    monkeypatch.setattr(ReadOnlyDB, "_reflect_entity", staticmethod(_reflect))


@pytest.mark.parametrize(
    ("target", "skipped_before"),
    [("policies", []), ("v_y_good", [("main", "v_a_stale", "view")])],
    ids=["at-a-table", "at-the-last-view"],
)
def test_a_database_lost_mid_walk_raises_rather_than_skipping(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    skipped_before: list[tuple[str, str, str]],
) -> None:
    """Session 265's review measured this on PostgreSQL 17: once the database
    went away, every entity after it was collected as "could not be reflected",
    so ``discover --allow-skipped`` exited 0 over an outage. An entity is
    skipped only while a fresh ``SELECT 1`` still succeeds. The genuine skip
    before the outage stays collected; the outage itself propagates."""
    directory = tmp_path / "warehouse"
    directory.mkdir()
    url = _warehouse(directory / "w.db", "v_a_stale")
    _outage_at(monkeypatch, target, directory)
    skipped: list[SkippedEntity] = []
    with (
        _connected(url) as db,
        pytest.raises(sa.exc.OperationalError, match="unable to open database file"),
    ):
        db.get_information_schema(skipped=skipped)
    assert _described(skipped) == skipped_before


def _disconnect() -> sa.exc.OperationalError:
    return sa.exc.OperationalError(
        statement="SELECT 1",
        params={},
        orig=Exception("server closed the connection unexpectedly"),
        connection_invalidated=True,
    )


@pytest.mark.parametrize("disconnects", [1, 2], ids=["once", "twice"])
def test_a_dropped_connection_is_retried_once_and_never_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, disconnects: int
) -> None:
    """Measured by the review on PostgreSQL 17: killing the probe's backend
    during the walk got a perfectly good table collected as skipped. Only that
    connection was lost, so ``SELECT 1`` alone cannot tell; SQLAlchemy's own
    disconnect flag can. One disconnect is retried and the table is kept; a
    second propagates."""
    reflect = ReadOnlyDB._reflect_entity
    failures = {"left": disconnects}

    def _flaky_policies(
        inspector: Any, schema: str, name: str, entity_kind: str
    ) -> dict[str, Any]:
        if name == "policies" and failures["left"]:
            failures["left"] -= 1
            raise _disconnect()
        return reflect(inspector, schema, name, entity_kind)

    monkeypatch.setattr(ReadOnlyDB, "_reflect_entity", staticmethod(_flaky_policies))
    skipped: list[SkippedEntity] = []
    with _connected(_warehouse(tmp_path / "w.db")) as db:
        if disconnects == 1:
            rows = db.get_information_schema(skipped=skipped)
            assert [r["name"] for r in rows] == GOOD
        else:
            with pytest.raises(sa.exc.OperationalError, match="server closed"):
                db.get_information_schema(skipped=skipped)
    assert skipped == []


def test_a_skipped_entity_repr_hides_the_error() -> None:
    """A driver's message can echo the connection string; a caller that logs
    its ``skipped`` list must not print it."""
    entity = SkippedEntity(
        "main",
        "v_stale",
        "view",
        sa.exc.OperationalError(
            statement="", params={}, orig=Exception(f"postgresql://u:{SECRET}@h/db")
        ),
    )
    assert SECRET not in repr(entity)
    assert "v_stale" in repr(entity)


# --- Session 270: ``safe_message`` is the one place database text is made safe ---
#
# Session 269 wrote this logic as ``discovery._safe_message`` for the schema probe's three
# messages. Its review found seven routes by which database or driver text still reached a
# terminal or a report (``BACKLOG.md``, *Seven more routes ...*); the first three each
# flattened or printed ``str(e)`` themselves. The function moved here, beside
# ``redact_secrets``, so they can call it. These tests hold the function; each call site has
# its own test where it lives, because a site that swaps it for a raw ``str(e)`` leaves every
# other test green.


class TestSafeMessage:
    @pytest.mark.parametrize("ch", CONTROLS, ids=control_ids(CONTROLS))
    def test_each_control_becomes_a_space(self, ch: str) -> None:
        """A space, not nothing: ``a<ESC>b`` must not read ``ab``."""
        assert safe_message(f"a{ch}b") == "a b"

    def test_every_control_at_once(self) -> None:
        assert safe_message(f"boom{EVERY_CONTROL}done") == "boom done"

    @pytest.mark.parametrize("ch", NON_SPACE_CONTROLS, ids=control_ids(NON_SPACE_CONTROLS))
    def test_a_control_inside_a_secret_does_not_cut_the_masking_short(self, ch: str) -> None:
        """Redaction runs BEFORE the scrub. ``redact_secrets`` reads an unquoted value as
        a run of non-whitespace, and these controls are not whitespace to it, so
        ``password=head<ESC>hunter2`` is one value and is masked whole. Scrubbing first
        would turn the control into a space, end the value there and print ``hunter2``
        (measured Session 269)."""
        assert (
            safe_message(f"driver said password=head{ch}{SECRET} tail")
            == "driver said password=*** tail"
        )

    @pytest.mark.parametrize("ch", CONTROLS, ids=control_ids(CONTROLS))
    @pytest.mark.parametrize(
        ("shape", "masked"),
        [
            ("password{ch}={s}", "password =***"),
            ("DB_PASSWORD{ch}: {s}", "DB_PASSWORD : ***"),
            ('token"{ch}={s}', 'token" =***'),
        ],
        ids=["equals", "colon-after-a-prefixed-key", "quoted-key"],
    )
    def test_a_control_between_a_secret_key_and_its_separator_hides_nothing(
        self, ch: str, shape: str, masked: str
    ) -> None:
        """Redaction also runs AFTER the scrub. A control between a key and its separator
        is not whitespace to ``redact_secrets`` (for the 55 that are not), so it hides the
        key and the secret is printed; only the scrub's space lets the masker see
        ``password =hunter2`` (measured Session 269: 55 of 65 leaked with a single pass)."""
        assert (
            safe_message(f"driver said {shape.format(ch=ch, s=SECRET)} tail")
            == f"driver said {masked} tail"
        )

    @pytest.mark.parametrize(
        ("message", "cleaned"),
        [
            ("\x1b[2Jfoo", "[2Jfoo"),
            ("foo\x1b", "foo"),
            ("\x1b", ""),
            ("\x1b\x07\x9b", ""),
            ("x" * 5000 + "\x1b" + "y", "x" * 5000 + " y"),
            ("a\n\x1bb", "a b"),
        ],
        ids=[
            "first",
            "last",
            "only-one",
            "only-controls",
            "after-a-long-prefix",
            "after-a-newline",
        ],
    )
    def test_a_control_is_replaced_wherever_it_sits(self, message: str, cleaned: str) -> None:
        """A scrub keyed to a position or a length (a ``strip``, a cut-off, a
        ``translate`` that misses an edge) survives a control between printable text."""
        assert safe_message(message) == cleaned

    @pytest.mark.parametrize(
        "text",
        [
            "no such table: main.sinistres_é_ÿ_Ā_日本語_🚗",
            "".join(map(chr, range(0xA1, 0xC0))),
            "".join(map(chr, range(0x21, 0x7F))),
            "main.می\u200cخواهم",  # a zero-width non-joiner: Persian needs it (Cf)
            "a\u200eb\ufeffc",  # an LRM and a BOM (Cf): left, on purpose
            "main.e\u0301cole",  # a combining acute accent (Mn)
            "main.\U0001d49c",  # a letter outside the BMP
        ],
        ids=[
            "accents-cjk-emoji",
            "latin1-above-the-c1-block",
            "printable-ascii",
            "zero-width-non-joiner",
            "bidi-mark-and-bom",
            "combining-accent",
            "astral-letter",
        ],
    )
    def test_printable_text_is_left_alone(self, text: str) -> None:
        """Only ``Cc`` is scrubbed: a ``Cf``-wide or ``isprintable``-based scrub would
        split Persian and emoji sequences."""
        assert safe_message(text) == text

    def test_whitespace_is_flattened_to_one_line(self) -> None:
        """SQLAlchemy puts its help URL after a newline on every ``DBAPIError``, and a
        concern or a note is one markdown bullet or one log record."""
        assert safe_message("boom\n[SQL: SELECT 1]\n  (Background: https://x)") == (
            "boom [SQL: SELECT 1] (Background: https://x)"
        )

    def test_a_lone_surrogate_is_replaced_so_the_text_can_be_written(self) -> None:
        """A message built by formatting an ``os.fsdecode``-d path carries one, and a
        report holding one cannot be written as UTF-8 (measured, Session 261)."""
        assert safe_message("a\udcffb") == "a?b"
        safe_message("a\udcffb").encode("utf-8")

    def test_a_string_is_as_good_as_an_exception(self) -> None:
        """``agent.py`` holds the cause as text (``db_error``), not as the exception."""
        assert safe_message(f"x {ESCAPE_NAME} PWD={SECRET};") == (
            f"x {ESCAPE_NAME_SCRUBBED} PWD=***;"
        )
        assert safe_message(RuntimeError("x\x1by")) == "x y"

    @pytest.mark.parametrize(
        "message",
        [
            f"boom{EVERY_CONTROL}done",
            f"password=head\x1b{SECRET} tail",
            f"password\x1b={SECRET}",
            f"postgresql://u:{SECRET}@h/db\n{CONNECT_CAUSE}",
            f"password\x1b=''{SECRET} tail",
            "plain",
            "",
        ],
        ids=[
            "every-control",
            "secret",
            "key-separator",
            "dsn-and-cause",
            "empty-quoted-value",
            "plain",
            "empty",
        ],
    )
    def test_the_output_is_one_line_with_no_control_character_even_when_applied_twice(
        self, message: str
    ) -> None:
        """What holds however often it is applied. It is NOT idempotent: the masker reads a
        quoted value glued to the text after it as the whole value, so ``password=''hunter2``
        becomes ``password=***hunter2`` and a second pass makes it ``password=***``
        (measured, Session 270 review). The docstring says to apply it once, to raw text."""
        once = safe_message(message)
        twice = safe_message(once)
        for out in (once, twice):
            assert unsafe(out) == []
            assert "\n" not in out
            assert out == " ".join(out.split())

    def test_an_unprintable_exception_gives_a_placeholder_and_does_not_raise(self) -> None:
        class Unprintable(Exception):
            def __str__(self) -> str:
                raise RuntimeError("broken __str__")

        assert safe_message(Unprintable()) == "<unprintable>"

    def test_a_str_subclass_message_gives_a_placeholder_and_does_not_raise(self) -> None:
        """``str(e)`` hands a ``str`` SUBCLASS back unchanged, so guarding only the
        ``str(e)`` call leaves that subclass's own methods free to raise."""

        class Hostile(str):
            def encode(self, *a: Any, **k: Any) -> bytes:
                raise RuntimeError("encode boom")

        class StrSubclassError(Exception):
            def __str__(self) -> str:
                return Hostile("x")

        assert safe_message(StrSubclassError()) == "<unprintable>"


class TestConnectError:
    """``ReadOnlyDB.connect`` builds the text of every connect failure, so what the
    exception says is safe to print wherever it is caught (``BACKLOG.md``, route 1)."""

    def _connect_error(self, url: str = ESCAPING_URL) -> DBConnectionError:
        with pytest.raises(DBConnectionError) as excinfo:
            ReadOnlyDB(url).connect()
        return excinfo.value

    def test_the_message_carries_no_control_character_and_is_one_line(self) -> None:
        message = str(self._connect_error())
        assert unsafe(message) == []
        assert "\n" not in message

    def test_the_message_still_names_the_cause(self) -> None:
        """A scrub that also ate the cause would trade this item's bug for a quieter one."""
        message = str(self._connect_error())
        assert message.startswith("cannot connect to 'fakeesc:///claims': ")
        assert f'FATAL: role "{ESCAPE_NAME_SCRUBBED}" does not exist' in message

    def test_a_secret_in_the_driver_text_is_masked(self) -> None:
        message = str(self._connect_error())
        assert SECRET not in message
        assert "PWD=***" in message

    def test_the_url_half_is_repr_quoted(self) -> None:
        """The URL is the operator's own argument and is quoted with ``repr``, which
        escapes every control character; ``%s`` would print a title sequence raw."""
        # A real SQLite path that cannot be opened, so the cause is plain
        # ("unable to open database file") and only the URL half can carry the ESC.
        message = str(self._connect_error(f"sqlite:////nonexistent/{ESCAPE_NAME}/x.db"))
        assert "unable to open database file" in message
        assert unsafe(message) == []
        assert "evil" in message  # the URL is still named. How SQLAlchemy renders the control
        # characters (raw in 2.0, percent-encoded in 2.1) is not this test's business.

    def test_the_raw_driver_exception_stays_on_the_chain_for_a_debugger(self) -> None:
        """The message is cleaned; the cause is not touched, so a library caller who
        wants the original still has it. (Printing it is what a traceback does, which is
        why ``discover`` catches this exception rather than letting it escape.)"""
        error = self._connect_error()
        assert isinstance(error.__cause__, sa.exc.OperationalError)
        assert ESCAPE_NAME in str(error.__cause__)

    def test_a_cause_with_no_text_falls_back_to_its_type(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A bare ``TimeoutError()`` has an empty ``str``, so the message would end in a
        colon and ``discover`` would print an ``error:`` line with nothing after it. A DBAPI
        error reaches here wrapped by SQLAlchemy, whose text names its type; this one does not."""

        def _timeout(*args: object, **kwargs: object) -> object:
            raise TimeoutError()

        monkeypatch.setattr(sa, "create_engine", _timeout)
        message = str(self._connect_error("sqlite:///x.db"))
        assert message == "cannot connect to 'sqlite:///x.db': TimeoutError"

    @pytest.mark.parametrize(
        "url",
        [
            "fakeesc:///x?password=hunter2",
            "fakeesc:///secret",
            "sqlite:////nonexistent_dir/secret",
            "sqlite:////nonexistent_dir/token",
        ],
        ids=["query-password", "path-ends-in-secret", "real-sqlite-secret", "real-sqlite-token"],
    )
    def test_a_message_built_here_is_left_whole_by_the_non_redacting_form(self, url: str) -> None:
        """The sinks (``discover``'s echo, ``agent.py``'s concern) clean this message with
        ``redact=False``. The masker would not leave it whole: it reads ``key``, a separator
        and a run of non-whitespace wherever it finds them, so a URL that ends in ``password=``
        or in a key word loses its closing ``':`` or the exception type (measured, Session 270
        review). Only the control characters are replaced, and there are none to replace here."""
        message = str(self._connect_error(url))
        assert safe_message(message, redact=False) == message


class TestSafeMessageWithoutRedaction:
    """``redact=False``: for text that was redacted where it was built."""

    @pytest.mark.parametrize("ch", CONTROLS, ids=control_ids(CONTROLS))
    def test_each_control_becomes_a_space(self, ch: str) -> None:
        assert safe_message(f"a{ch}b", redact=False) == "a b"

    def test_it_flattens_and_replaces_surrogates_like_the_default(self) -> None:
        assert safe_message("a\n b\udcffc", redact=False) == "a b?c"

    def test_it_does_not_mask(self) -> None:
        """The point of the flag, and its cost: a secret in text nobody redacted stays."""
        assert safe_message(f"x {ESCAPE_NAME} PWD={SECRET}", redact=False) == (
            f"x {ESCAPE_NAME_SCRUBBED} PWD={SECRET}"
        )

    def test_it_never_raises(self) -> None:
        class Unprintable(Exception):
            def __str__(self) -> str:
                raise RuntimeError("broken __str__")

        assert safe_message(Unprintable(), redact=False) == "<unprintable>"


class TestTheSharedHelpers:
    """``tests/hostile_text.py`` is what every Session 270 test is written against, so a
    wrong helper would make them pass or fail for nothing. Held against the Unicode database
    here, once."""

    def test_controls_is_exactly_the_cc_category(self) -> None:
        scanned = [
            chr(cp) for cp in range(sys.maxunicode + 1) if unicodedata.category(chr(cp)) == "Cc"
        ]
        assert scanned == CONTROLS
        assert len(CONTROLS) == 65
        assert [c for c in CONTROLS if not c.isspace()] == NON_SPACE_CONTROLS
        assert len(NON_SPACE_CONTROLS) == 55

    def test_unsafe_names_every_control_but_a_newline_and_nothing_else(self) -> None:
        assert unsafe(EVERY_CONTROL) == [f"U+{ord(c):04X}" for c in CONTROLS if c != "\n"]
        assert unsafe("a\nb") == []
        assert unsafe("é日本語🚗\u200e\u0301") == []
        assert unsafe("x\x1by\x07") == ["U+0007", "U+001B"]

    def test_the_hostile_names_are_what_the_tests_say_they_are(self) -> None:
        assert unsafe(ESCAPE_NAME) == ["U+0007", "U+001B"]
        assert unsafe(ESCAPE_NAME_SCRUBBED) == []
        assert safe_message(ESCAPE_NAME) == ESCAPE_NAME_SCRUBBED


# --- Session 279: ``safe_class_name`` names an LLM client's exception for the data report ---
#
# ``agent.py`` and ``nodes.py`` used to write ``{e}`` into the report for an exception raised by
# the LLM client, which is the gateway's or opencode's text and can hold the API key. Each site
# writes the class name now; this holds the rule, and ``test_data_agent.py`` holds each site.
# The package cannot import ``orchestrator.logging._class_name`` (it is standalone), so the rule
# is stated here and the last test holds the two in step.

_KEY = "sk-ant-NAMETEST0123456789abcdef"


class _CannotBePrinted(Exception):
    def __str__(self) -> str:
        raise AssertionError("the exception's message was read")

    def __repr__(self) -> str:
        raise AssertionError("the exception's repr was read")


_ODD_NAMES = [
    pytest.param("", id="empty"),
    pytest.param("has a space", id="space"),
    pytest.param("bell\x07", id="control-character"),
    pytest.param(f"\x1b[2J{_KEY}", id="escape-sequence-and-key"),
    pytest.param("café", id="non-ascii"),
    pytest.param("1leading_digit", id="not-an-identifier"),
    pytest.param("E" * 101, id="one-hundred-and-one-characters"),
]


def _odd_exceptions() -> list[BaseException]:
    class Odd(Exception, metaclass=NameThatRaises):
        pass

    class OddStr(Exception, metaclass=NameThatIsAHostileStr):
        pass

    return [Odd(_KEY), OddStr(_KEY)]


class TestSafeClassName:
    def test_an_ordinary_class_is_named_by_its_own_name(self) -> None:
        class Local(Exception):
            pass

        assert safe_class_name(RuntimeError("boom")) == "RuntimeError"
        assert safe_class_name(DBConnectionError("boom")) == "DBConnectionError"
        # ``__name__``, not ``__qualname__``: the enclosing function is not part of the name.
        assert safe_class_name(Local()) == "Local"

    def test_it_asks_the_exception_for_nothing(self) -> None:
        assert safe_class_name(_CannotBePrinted(_KEY)) == "_CannotBePrinted"

    @pytest.mark.parametrize("name", _ODD_NAMES)
    def test_a_name_that_is_not_a_short_identifier_is_replaced(self, name: str) -> None:
        """A class built at run time can be named anything: code chooses the name, never the
        host, but a name that is not a plain identifier is replaced rather than carried."""
        assert safe_class_name(type(name, (Exception,), {})(_KEY)) == "<unprintable>"

    def test_the_longest_name_allowed_is_carried(self) -> None:
        assert safe_class_name(type("E" * 100, (Exception,), {})()) == "E" * 100

    def test_a_class_whose_name_cannot_be_read_does_not_raise(self) -> None:
        """It runs inside an ``except`` block that delivers "never raises"."""
        odd, _ = _odd_exceptions()
        assert safe_class_name(odd) == "<unprintable>"

    def test_a_name_that_is_a_str_subclass_is_replaced(self) -> None:
        """A subclass can answer ``isascii``, ``isidentifier`` and ``len`` however it likes."""
        _, odd_str = _odd_exceptions()
        assert safe_class_name(odd_str) == "<unprintable>"

    def test_it_agrees_with_the_orchestrators_copy_of_the_rule(self) -> None:
        """This package cannot import ``orchestrator.logging._class_name``, so the two stay in
        step by a test: the same answer for an ordinary class, a long name, a name that is
        replaced and a class whose name cannot be read."""
        from model_project_constructor.orchestrator.logging import _class_name

        class Local(Exception):
            pass

        # ``Local`` is the class where ``__name__`` ("Local") and ``__qualname__`` (the enclosing
        # function, ``<locals>`` and the name: not an identifier) differ, so a copy that reads
        # the wrong one disagrees here and nowhere else.
        raised = [
            RuntimeError("x"),
            Local(),
            KeyError("x"),
            DBConnectionError("x"),
            _CannotBePrinted(),
            type("E" * 100, (Exception,), {})(),
            *(type(p.values[0], (Exception,), {})() for p in _ODD_NAMES),
            *_odd_exceptions(),
        ]
        assert [safe_class_name(e) for e in raised] == [_class_name(e) for e in raised]
