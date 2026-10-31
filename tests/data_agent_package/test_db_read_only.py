"""``ReadOnlyDB`` is read-only: the gate in ``execute`` and the connection ``connect`` makes.

Before Session 288 ``execute`` ran whatever it was given. Measured then, on a SQLite file:
``DROP TABLE``, ``CREATE TABLE``, ``ALTER``, ``PRAGMA user_version = 7``, ``VACUUM``, ``ATTACH``,
``VACUUM INTO``, ``SELECT * FROM pragma_optimize`` and a ``WITH ... DELETE`` all persisted (a plain
``INSERT``, ``UPDATE`` or ``DELETE`` only failed to, because the pysqlite driver opens a transaction
before those and SQLAlchemy rolls back on exit). Of those, ``VACUUM`` changes the file's bytes but
not its schema, rows or ``user_version``, and ``pragma_optimize`` writes ``sqlite_stat1`` only on a
table big enough to need statistics, so on this suite's three-row fixture neither shows in
``_state``; they are pinned by the rule that refuses them. A write that returned no rows then raised
``ResourceClosedError`` after it had run, so a failed quality check did not mean no effect.

What is REAL here: SQLite, through the real engine, the real gate and the real pool, with the
database file checked afterwards by a separate ``sqlite3`` connection. Two tests in that part
inject a fault on purpose and say so (a spy in place of the engine, a hook that refuses). What is
SIMULATED, and labelled so: PostgreSQL, MySQL and the dialects with no hook. No server or driver
for them is installed in this environment. The tests below call the hook functions on a recording
stand-in for the DBAPI connection and check the statements sent, in order; the tests of the
registration by name and of the ``create_engine`` options use stubs. The tests in
``test_db_read_only_dialects.py`` go further: SQLAlchemy's real PostgreSQL and MySQL dialects run on
a stand-in driver module. None of it shows what a server does with the statements; that was measured
in throwaway containers in Session 288 (PostgreSQL 17 and MySQL 8.4): see the docstrings in
``db.py`` and ``read_only_gate.py``.
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import sqlalchemy as sa
from model_project_constructor_data_agent import db as db_module
from model_project_constructor_data_agent.db import DBConnectionError, ReadOnlyDB
from model_project_constructor_data_agent.read_only_gate import ReadOnlyViolation

# Statements the gate must refuse. The ``{dir}`` ones would create a file if they ran.
WRITES = [
    "DROP TABLE claims",
    "CREATE TABLE z (a INTEGER)",
    "DELETE FROM claims",
    "INSERT INTO claims VALUES (99, 1.0)",
    "UPDATE claims SET paid = 0",
    "WITH x AS (SELECT 1) DELETE FROM claims",
    "WITH x AS (SELECT 98 AS a, 1.0 AS b) INSERT INTO claims SELECT a, b FROM x",
    "PRAGMA user_version = 7",
    "ATTACH DATABASE '{dir}/attached.db' AS x",
    "VACUUM INTO '{dir}/copy.db'",
    "SELECT * FROM pragma_optimize",
    'SELECT * FROM "pragma_optimize"',
    "SELECT * FROM [pragma_optimize]",
    "SELECT 1; DROP TABLE claims",
]


@pytest.fixture
def claims_db(tmp_path: Path) -> Path:
    path = tmp_path / "claims.db"
    connection = sqlite3.connect(path)
    try:
        connection.execute("CREATE TABLE claims (claim_id INTEGER PRIMARY KEY, paid REAL)")
        connection.executemany(
            "INSERT INTO claims VALUES (?, ?)", [(1, 10.0), (2, 20.0), (3, 30.0)]
        )
        connection.commit()
    finally:
        connection.close()
    return path


def _state(path: Path) -> dict[str, Any]:
    """What a separate connection sees: schema, rows, ``user_version`` and the files beside it."""
    connection = sqlite3.connect(path)
    try:
        return {
            "schema": connection.execute(
                "SELECT type, name FROM sqlite_master ORDER BY name"
            ).fetchall(),
            "rows": connection.execute("SELECT * FROM claims").fetchall(),
            "user_version": connection.execute("PRAGMA user_version").fetchone(),
            "files": sorted(p.name for p in path.parent.iterdir()),
        }
    finally:
        connection.close()


@contextmanager
def _connected(url: str) -> Iterator[ReadOnlyDB]:
    db = ReadOnlyDB(url)
    db.connect()
    try:
        yield db
    finally:
        db.close()


def _engine(db: ReadOnlyDB) -> sa.Engine:
    assert db._engine is not None
    return db._engine


# --------------------------------------------------------------------------------------------
# REAL: SQLite, the gate and the connection together
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("sql", WRITES)
def test_a_statement_that_writes_is_refused_and_changes_nothing(claims_db: Path, sql: str) -> None:
    before = _state(claims_db)
    with _connected(f"sqlite:///{claims_db}") as db, pytest.raises(ReadOnlyViolation):
        db.execute(sql.format(dir=claims_db.parent))
    assert _state(claims_db) == before


def test_a_query_still_runs(claims_db: Path) -> None:
    with _connected(f"sqlite:///{claims_db}") as db:
        assert db.execute("SELECT claim_id, paid FROM claims ORDER BY claim_id;") == [
            {"claim_id": 1, "paid": 10.0},
            {"claim_id": 2, "paid": 20.0},
            {"claim_id": 3, "paid": 30.0},
        ]
        assert db.execute("WITH t AS (SELECT SUM(paid) AS s FROM claims) SELECT s FROM t") == [
            {"s": 60.0}
        ]
        assert db.execute("VALUES (1), (2)") == [{"column1": 1}, {"column1": 2}]


def test_the_dialect_the_gate_reads_is_the_connected_engines(claims_db: Path) -> None:
    db = ReadOnlyDB(f"sqlite:///{claims_db}")
    assert db._dialect_name is None
    db.connect()
    assert db._dialect_name == "sqlite"
    # SQLite quotes an identifier in brackets; an unknown dialect would refuse the ``[``.
    assert len(db.execute("SELECT [claim_id] FROM claims")) == 3
    db.close()
    assert db._dialect_name is None


def test_a_refusal_comes_before_any_connection_is_borrowed(claims_db: Path) -> None:
    """Fault injection: a spy in place of the engine fails the test if the pool is asked."""

    def boom() -> None:
        raise AssertionError("the pool was asked for a connection")

    with _connected(f"sqlite:///{claims_db}") as db:
        real = db._engine
        db._engine = SimpleNamespace(connect=boom)  # type: ignore[assignment]
        try:
            with pytest.raises(ReadOnlyViolation):
                db.execute("DROP TABLE claims")
        finally:
            db._engine = real


def test_execute_before_connect_is_still_a_runtime_error() -> None:
    with pytest.raises(RuntimeError, match="before connect"):
        ReadOnlyDB("sqlite:///:memory:").execute("DROP TABLE claims")


def test_reflection_still_works_under_the_read_only_connection(claims_db: Path) -> None:
    with _connected(f"sqlite:///{claims_db}") as db:
        assert [e["name"] for e in db.get_information_schema()] == ["claims"]


# --------------------------------------------------------------------------------------------
# REAL: the connection on its own, with the gate bypassed by going straight to the engine
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE claims",
        "CREATE TABLE z (a INTEGER)",
        "CREATE TEMP TABLE z (a INTEGER)",
        "DELETE FROM claims",
        "INSERT INTO claims VALUES (99, 1.0)",
        "UPDATE claims SET paid = 0",
    ],
)
def test_the_connection_refuses_writes_even_with_the_gate_bypassed(
    claims_db: Path, sql: str
) -> None:
    before = _state(claims_db)
    with (
        _connected(f"sqlite:///{claims_db}") as db,
        _engine(db).connect() as conn,
        pytest.raises(sa.exc.OperationalError, match="readonly"),
    ):
        conn.exec_driver_sql(sql)
    assert _state(claims_db) == before


def test_pragma_off_sent_through_the_pool_does_not_reach_the_next_borrower(
    claims_db: Path,
) -> None:
    """The reason the SQLite hook is on ``checkout`` as well as ``connect``.

    Measured Session 288, with a ``connect``-only hook: after ``PRAGMA query_only = OFF`` the next
    ``DROP TABLE`` on the same pooled connection succeeded and the table was gone.
    """
    before = _state(claims_db)
    with _connected(f"sqlite:///{claims_db}") as db:
        engine = _engine(db)
        with engine.connect() as first:
            pooled = first.connection.dbapi_connection
            first.exec_driver_sql("PRAGMA query_only = OFF")
        with engine.connect() as second:
            assert second.connection.dbapi_connection is pooled  # the same connection, reused
            with pytest.raises(sa.exc.OperationalError, match="readonly"):
                second.exec_driver_sql("DROP TABLE claims")
    assert _state(claims_db) == before


def test_an_in_memory_database_is_read_only_too() -> None:
    with (
        _connected("sqlite:///:memory:") as db,
        _engine(db).connect() as conn,
        pytest.raises(sa.exc.OperationalError, match="readonly"),
    ):
        conn.exec_driver_sql("CREATE TABLE z (a INTEGER)")


def test_connect_fails_when_read_only_cannot_be_enforced(
    claims_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fault injection: a hook that refuses. Checks the conversion and that the connection closes.

    The real hook's refusal, on a driver that ignores the pragma, is in the next test.
    """
    seen: list[sqlite3.Connection] = []

    def refuse(dbapi_connection: sqlite3.Connection, *_args: Any) -> None:
        seen.append(dbapi_connection)
        raise db_module._ReadOnlyNotEnforced("the stub refused")

    monkeypatch.setattr(db_module, "_enforce_sqlite_read_only", refuse)
    db = ReadOnlyDB(f"sqlite:///{claims_db}")
    with pytest.raises(DBConnectionError, match="the stub refused"):
        db.connect()
    assert db._engine is None
    assert db._dialect_name is None
    # SQLAlchemy drops the half-made pool entry without closing it; the wrapper does.
    assert len(seen) == 1
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        seen[0].execute("SELECT 1")


def test_connect_fails_when_the_sqlite_driver_ignores_the_pragma(
    claims_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The REAL SQLite hook against a driver that silently ignores ``PRAGMA query_only = ON``."""

    class _IgnoringCursor:
        def __init__(self, inner: Any) -> None:
            self._inner = inner

        def execute(self, sql: str, *args: Any) -> Any:
            if sql.startswith("PRAGMA query_only ="):
                return self  # what SQLite does with a pragma it does not know
            return self._inner.execute(sql, *args)

        def __getattr__(self, name: str) -> Any:
            return getattr(self._inner, name)

    class _IgnoringConnection:
        def __init__(self, inner: sqlite3.Connection) -> None:
            self.inner = inner

        def cursor(self, *args: Any, **kwargs: Any) -> _IgnoringCursor:
            return _IgnoringCursor(self.inner.cursor(*args, **kwargs))

        def __getattr__(self, name: str) -> Any:
            return getattr(self.inner, name)

    made: list[_IgnoringConnection] = []

    def creator() -> _IgnoringConnection:
        made.append(_IgnoringConnection(sqlite3.connect(claims_db)))
        return made[-1]

    real = sa.create_engine
    monkeypatch.setattr(sa, "create_engine", lambda url, **kw: real(url, creator=creator, **kw))
    db = ReadOnlyDB(f"sqlite:///{claims_db}")
    with pytest.raises(DBConnectionError, match="SQLite did not turn PRAGMA query_only on"):
        db.connect()
    assert db._engine is None
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        made[0].inner.execute("SELECT 1")


# --------------------------------------------------------------------------------------------
# SIMULATED: a recording stand-in for the DBAPI connection
# --------------------------------------------------------------------------------------------


class _Cursor:
    def __init__(self, log: list[str], answer: tuple[Any, ...] | None) -> None:
        self._log = log
        self._answer = answer

    def execute(self, sql: str) -> None:
        self._log.append(sql)

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._answer

    def close(self) -> None:
        self._log.append("<close>")


class _Dbapi:
    def __init__(self, answer: tuple[Any, ...] | None = None) -> None:
        self.log: list[str] = []
        self._answer = answer

    def cursor(self) -> _Cursor:
        return _Cursor(self.log, self._answer)

    def commit(self) -> None:
        self.log.append("<commit>")


def test_sqlite_hook_turns_the_pragma_on_and_reads_it_back() -> None:
    dbapi = _Dbapi((1,))
    db_module._enforce_sqlite_read_only(dbapi, object())
    assert dbapi.log == ["PRAGMA query_only = ON", "PRAGMA query_only", "<close>"]


@pytest.mark.parametrize("answer", [(0,), None])
def test_sqlite_hook_refuses_a_pragma_that_did_not_take(answer: tuple[int] | None) -> None:
    with pytest.raises(db_module._ReadOnlyNotEnforced):
        db_module._enforce_sqlite_read_only(_Dbapi(answer))


def test_postgresql_hook_sets_the_session_default_reads_it_back_and_commits() -> None:
    dbapi = _Dbapi(("on",))
    db_module._enforce_postgresql_read_only(dbapi, object())
    # The commit comes last: the SET opened a transaction, and psycopg2 refuses to set the
    # per-transaction characteristic inside one (see test_db_read_only_dialects.py).
    assert dbapi.log == [
        "SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY",
        "SHOW default_transaction_read_only",
        "<close>",
        "<commit>",
    ]


@pytest.mark.parametrize("answer", [("off",), None])
def test_postgresql_hook_refuses_a_session_that_is_not_read_only(
    answer: tuple[str] | None,
) -> None:
    with pytest.raises(db_module._ReadOnlyNotEnforced):
        db_module._enforce_postgresql_read_only(_Dbapi(answer))


def test_mysql_hook_makes_the_session_read_only() -> None:
    dbapi = _Dbapi()
    db_module._enforce_mysql_read_only(dbapi, object())
    assert dbapi.log == ["SET SESSION TRANSACTION READ ONLY", "<close>"]


def test_mysql_hook_lets_the_servers_refusal_through() -> None:
    """There is no read-back on MySQL, so the exception is the only signal that it did not take."""

    class _Refusing(_Dbapi):
        def cursor(self) -> _Cursor:
            class _Raises(_Cursor):
                def execute(self, sql: str) -> None:
                    raise RuntimeError("you have an error in your SQL syntax")

            return _Raises(self.log, None)

    with pytest.raises(RuntimeError, match="syntax"):
        db_module._enforce_mysql_read_only(_Refusing(), object())


@pytest.mark.parametrize(
    ("dialect", "expected"),
    [
        ("sqlite", [("connect", "sqlite"), ("checkout", "sqlite")]),
        ("postgresql", [("connect", "postgresql")]),
        ("mysql", [("connect", "mysql"), ("checkout", "mysql")]),
        ("mariadb", [("connect", "mysql"), ("checkout", "mysql")]),
        ("mssql", []),
        ("oracle", []),
        ("snowflake", []),
    ],
)
def test_each_dialect_gets_the_hooks_it_has(
    monkeypatch: pytest.MonkeyPatch, dialect: str, expected: list[tuple[str, str]]
) -> None:
    """Pins WHICH function is registered for each event, not only the event's name."""
    hooks = {
        "sqlite": db_module._enforce_sqlite_read_only,
        "postgresql": db_module._enforce_postgresql_read_only,
        "mysql": db_module._enforce_mysql_read_only,
    }
    registered: list[tuple[str, Any]] = []
    monkeypatch.setattr(sa.event, "listen", lambda target, name, fn: registered.append((name, fn)))
    engine = SimpleNamespace(dialect=SimpleNamespace(name=dialect))
    unhooked = db_module._install_read_only(engine)  # type: ignore[arg-type]
    # A ``connect`` hook is wrapped so that a refusal closes the raw connection; ``__wrapped__``
    # is the hook itself. A ``checkout`` hook is registered bare (the pool invalidates on a raise).
    assert [(name, getattr(fn, "__wrapped__", fn)) for name, fn in registered] == [
        (name, hooks[kind]) for name, kind in expected
    ]
    assert [name for name, fn in registered if hasattr(fn, "__wrapped__")] == [
        name for name, _kind in expected if name == "connect"
    ]
    assert unhooked == (None if expected else dialect)


def test_a_connect_hook_that_raises_closes_the_connection_and_lets_the_error_through() -> None:
    class _Closable:
        closed = False

        def close(self) -> None:
            self.closed = True

    def refuse(dbapi_connection: Any, *_unused: Any) -> None:
        raise db_module._ReadOnlyNotEnforced("no")

    connection = _Closable()
    with pytest.raises(db_module._ReadOnlyNotEnforced):
        db_module._close_when_it_raises(refuse)(connection, object())
    assert connection.closed


def test_a_connect_hook_that_works_leaves_the_connection_open() -> None:
    class _Closable:
        closed = False

        def close(self) -> None:
            self.closed = True

    connection = _Closable()
    db_module._close_when_it_raises(lambda *_a: None)(connection, object())
    assert not connection.closed


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://u:pw@h/db",
        "postgresql+psycopg2://u:pw@h/db",
        "postgresql+psycopg://u:pw@h/db",
        "postgresql+pg8000://u:pw@h/db",
    ],
)
def test_a_postgresql_url_asks_for_read_only_transactions(
    monkeypatch: pytest.MonkeyPatch, url: str
) -> None:
    """The driver-qualified forms are the real-world ones; the backend name is what is read."""
    seen: dict[str, Any] = {}

    def fake_create_engine(url: str, **kwargs: Any) -> None:
        seen[url] = kwargs
        raise TimeoutError

    monkeypatch.setattr(sa, "create_engine", fake_create_engine)
    with pytest.raises(DBConnectionError):
        ReadOnlyDB(url).connect()
    assert seen == {url: {"execution_options": {"postgresql_readonly": True}}}


@pytest.mark.parametrize(
    "url",
    [
        "mysql://u:pw@h/db",
        "mysql+pymysql://u:pw@h/db",
        "mariadb+pymysql://u:pw@h/db",
        "sqlite:///:memory:",
        "sqlite+pysqlite:///:memory:",
        "mssql+pyodbc://u:pw@h/db",
    ],
)
def test_no_other_url_asks_for_read_only_transactions_through_the_engine(
    monkeypatch: pytest.MonkeyPatch, url: str
) -> None:
    seen: dict[str, Any] = {}

    def fake_create_engine(url: str, **kwargs: Any) -> None:
        seen[url] = kwargs
        raise TimeoutError

    monkeypatch.setattr(sa, "create_engine", fake_create_engine)
    with pytest.raises(DBConnectionError):
        ReadOnlyDB(url).connect()
    assert seen == {url: {}}


def test_a_dialect_with_no_hook_logs_a_warning_that_names_the_dialect_and_nothing_else(
    claims_db: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(db_module, "_install_read_only", lambda engine: "snowflake")
    with (
        caplog.at_level(logging.WARNING, logger=db_module.__name__),
        _connected(f"sqlite:///{claims_db}"),
    ):
        pass
    records = [r for r in caplog.records if r.name == db_module.__name__]
    assert [r.levelno for r in records] == [logging.WARNING]
    messages = [r.getMessage() for r in records]
    assert len(messages) == 1
    assert "'snowflake'" in messages[0]
    assert "statement gate" in messages[0]
    assert "unable to write" in messages[0]
    assert claims_db.name not in caplog.text and str(claims_db.parent) not in caplog.text


def test_a_dialect_with_hooks_logs_no_warning(
    claims_db: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with (
        caplog.at_level(logging.WARNING, logger=db_module.__name__),
        _connected(f"sqlite:///{claims_db}"),
    ):
        pass
    assert [r for r in caplog.records if r.name == db_module.__name__] == []
