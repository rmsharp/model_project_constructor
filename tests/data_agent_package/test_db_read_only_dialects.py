"""``ReadOnlyDB`` on PostgreSQL, MySQL and MariaDB, through SQLAlchemy's REAL dialects.

Nothing here needs a server or a driver package. ``sys.modules`` gets a stand-in ``psycopg2`` or
``pymysql`` and SQLAlchemy builds its own dialect on it, so ``dialect.name``, the event dispatch,
``postgresql_readonly`` and the ``make_url`` backend detection are all REAL; only the wire is fake.
So is what a server would do with a statement: the stand-in answers ``SHOW`` as it is told and
refuses a statement when told to. The server behaviour the hooks rely on was measured in throwaway
containers in Session 288 (PostgreSQL 17, MySQL 8.4) and is not re-checked by any CI job.

The stand-in names what SQLAlchemy 2.x imports from each driver, so a SQLAlchemy release that
imports more can break these tests without any change here: a failure that names a missing
attribute of ``psycopg2`` or ``pymysql`` is the stand-in, not the code under test.
"""

from __future__ import annotations

import sys
import types
from typing import Any

import pytest
import sqlalchemy as sa
from model_project_constructor_data_agent.db import DBConnectionError, ReadOnlyDB
from model_project_constructor_data_agent.read_only_gate import ReadOnlyViolation


class _Cur:
    def __init__(self, conn: _Conn) -> None:
        self.conn = self.connection = conn
        self._rows: list[tuple[Any, ...]] = []
        self.description: Any = None
        self.rowcount = -1
        self.lastrowid = None

    def execute(self, sql: str, params: Any = None) -> int:
        self.conn.log.append(sql)
        if _Conn.refuse is not None and sql == _Conn.refuse:
            raise RuntimeError("syntax error")
        self.conn.in_txn = self.conn.flavour == "pg"
        s = sql.strip().lower()
        rows: list[tuple[Any, ...]] = []
        if s.startswith("show default_transaction_read_only"):
            rows = [(_Conn.show_answer,)]
        elif "version()" in s:
            rows = [(self.conn.version,)]
        elif "current_schema" in s:
            rows = [("public",)]
        elif "transaction isolation" in s:
            rows = [("read committed",)]
        elif "standard_conforming_strings" in s:
            rows = [("on",)]
        elif "database()" in s:
            rows = [("db",)]
        elif "@@lower_case_table_names" in s:
            rows = [(0,)]
        elif "@@sql_mode" in s:
            rows = [("STRICT_TRANS_TABLES",)]
        elif "isolation" in s:
            rows = [("REPEATABLE-READ",)]
        elif s.startswith("select 1"):
            rows = [(1,)]
        elif s.startswith("select 5"):
            rows = [(2,)]
        self._rows = rows
        self.description = [("x", 25, None, None, None, None, None)] if rows else None
        return 0

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list[tuple[Any, ...]]:
        return list(self._rows)

    def close(self) -> None:
        pass


class _Conn:
    server_version = 170000
    notices: list[str] = []
    isolation_level = 1

    refuse: str | None = None  # a statement the fake server rejects, as an old server would
    show_answer: str = "on"  # what the fake server says default_transaction_read_only is

    def __init__(self, flavour: str, version: str) -> None:
        self.flavour, self.version = flavour, version
        self.log: list[str] = []
        self.in_txn = False
        self.closed = False
        self._ro: bool | None = None

    @property
    def readonly(self) -> bool | None:
        return self._ro

    @readonly.setter
    def readonly(self, value: bool) -> None:
        # psycopg2: set_session (and so ``readonly=``) is refused inside a transaction.
        self.log.append(f"<readonly={value} in_txn={self.in_txn}>")
        if self.in_txn:
            raise RuntimeError("set_session cannot be used inside a transaction")
        self._ro = value

    def cursor(self, *_a: Any, **_k: Any) -> _Cur:
        return _Cur(self)

    def commit(self) -> None:
        self.in_txn = False
        self.log.append("<commit>")

    def rollback(self) -> None:
        self.in_txn = False
        self.log.append("<rollback>")

    def close(self) -> None:
        self.closed = True

    def ping(self, *_a: Any, **_k: Any) -> None:
        pass

    def character_set_name(self) -> str:
        return "utf8mb4"

    def autocommit(self, _v: Any = None) -> None:
        pass


def _install(monkeypatch: pytest.MonkeyPatch, name: str, flavour: str, version: str) -> list[_Conn]:
    made: list[_Conn] = []
    monkeypatch.setattr(_Conn, "refuse", None)
    monkeypatch.setattr(_Conn, "show_answer", "on")

    def connect(*_a: Any, **_k: Any) -> _Conn:
        conn = _Conn(flavour, version)
        made.append(conn)
        return conn

    mod = types.ModuleType(name)
    mod.paramstyle = "pyformat"  # type: ignore[attr-defined]
    mod.connect = connect  # type: ignore[attr-defined]
    mod.apilevel, mod.threadsafety = "2.0", 2  # type: ignore[attr-defined]
    for exc in [
        "Warning",
        "Error",
        "InterfaceError",
        "DatabaseError",
        "DataError",
        "OperationalError",
        "IntegrityError",
        "InternalError",
        "ProgrammingError",
        "NotSupportedError",
    ]:
        setattr(mod, exc, type(exc, (Exception,), {}))
    subs: dict[str, types.ModuleType] = {name: mod}
    if name == "psycopg2":
        mod.__version__ = "2.9.9 (dt dec pq3 ext lo64)"  # type: ignore[attr-defined]
        ext = types.ModuleType("psycopg2.extensions")
        for attr in [
            "ISOLATION_LEVEL_AUTOCOMMIT",
            "ISOLATION_LEVEL_READ_COMMITTED",
            "ISOLATION_LEVEL_REPEATABLE_READ",
            "ISOLATION_LEVEL_SERIALIZABLE",
            "ISOLATION_LEVEL_READ_UNCOMMITTED",
        ]:
            setattr(ext, attr, 0)
        ext.register_type = lambda *a, **k: None  # type: ignore[attr-defined]
        ext.UNICODE = ext.UNICODEARRAY = object()  # type: ignore[attr-defined]
        extras = types.ModuleType("psycopg2.extras")
        extras.register_uuid = extras.register_hstore = lambda *a, **k: None  # type: ignore[attr-defined]
        extras.HstoreAdapter = type(
            "HstoreAdapter", (), {"get_oids": staticmethod(lambda *a, **k: None)}
        )  # type: ignore[attr-defined]
        extras.execute_values = extras.execute_batch = lambda *a, **k: None  # type: ignore[attr-defined]
        mod.extensions, mod.extras = ext, extras  # type: ignore[attr-defined]
        subs.update({"psycopg2.extensions": ext, "psycopg2.extras": extras})
    else:
        mod.__version__, mod.version_info = "1.1.0", (1, 1, 0, "final", 0)  # type: ignore[attr-defined]
        const = types.ModuleType("pymysql.constants")
        const.CLIENT = types.SimpleNamespace(MULTI_STATEMENTS=1 << 16, FOUND_ROWS=2)  # type: ignore[attr-defined]
        conv = types.ModuleType("pymysql.converters")
        mod.constants, mod.converters = const, conv  # type: ignore[attr-defined]
        subs.update({"pymysql.constants": const, "pymysql.converters": conv})
    for key, value in subs.items():
        monkeypatch.setitem(sys.modules, key, value)
    return made


@pytest.mark.parametrize("url", ["postgresql://u:pw@h/db", "postgresql+psycopg2://u:pw@h/db"])
def test_a_real_postgresql_dialect_is_read_only_before_the_first_statement(
    monkeypatch: pytest.MonkeyPatch, url: str
) -> None:
    made = _install(monkeypatch, "psycopg2", "pg", "PostgreSQL 17.0")
    db = ReadOnlyDB(url)
    db.connect()
    assert db._dialect_name == "postgresql"
    log = made[0].log
    probe = log.index("SELECT 1")
    # The session default is set, read back and committed, then SQLAlchemy asks the driver for
    # read-only transactions (outside any transaction), and only then does the first statement run.
    assert log[probe - 4 : probe] == [
        "SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY",
        "SHOW default_transaction_read_only",
        "<commit>",
        "<readonly=True in_txn=False>",
    ]
    # The gate is told the connected engine's dialect: ``#`` is an operator only on PostgreSQL.
    assert db.execute("SELECT 5 # 3") == [{"x": 2}]
    db.close()


@pytest.mark.parametrize(
    ("url", "version"),
    [
        ("mysql+pymysql://u:pw@h/db", "8.4.0"),
        ("mariadb+pymysql://u:pw@h/db", "10.11.5-MariaDB"),
    ],
)
def test_a_real_mysql_dialect_is_read_only_on_every_borrowed_connection(
    monkeypatch: pytest.MonkeyPatch, url: str, version: str
) -> None:
    made = _install(monkeypatch, "pymysql", "my", version)
    db = ReadOnlyDB(url)
    db.connect()
    engine = db._engine
    assert engine is not None
    with engine.connect() as a, engine.connect() as b:
        a.execute(sa.text("SELECT 1"))
        b.execute(sa.text("SELECT 1"))
    assert len(made) == 2
    for conn in made:
        assert "SET SESSION TRANSACTION READ ONLY" in conn.log[: conn.log.index("SELECT 1")]
        # and none of another dialect's read-only statements
        assert not [s for s in conn.log if s.startswith(("SET SESSION CHARACTERISTICS", "PRAGMA"))]
    # The connection taken from the pool again is made read-only again (checkout).
    before = [c.log.count("SET SESSION TRANSACTION READ ONLY") for c in made]
    with engine.connect() as again:
        again.execute(sa.text("SELECT 1"))
    after = [c.log.count("SET SESSION TRANSACTION READ ONLY") for c in made]
    assert sum(after) == sum(before) + 1
    db.close()


def test_mysql_connect_fails_closed_when_the_server_refuses_the_statement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The MySQL hook has no read-back; a refusal by the server is the only signal it has."""
    made = _install(monkeypatch, "pymysql", "my", "8.4.0")
    monkeypatch.setattr(_Conn, "refuse", "SET SESSION TRANSACTION READ ONLY")
    db = ReadOnlyDB("mysql+pymysql://u:pw@h/db")
    with pytest.raises(DBConnectionError):
        db.connect()
    assert db._engine is None
    assert [conn.closed for conn in made] == [True]


def test_mysql_dialect_is_what_the_gate_reads(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, "pymysql", "my", "8.4.0")
    db = ReadOnlyDB("mysql+pymysql://u:pw@h/db")
    db.connect()
    assert db._dialect_name == "mysql"
    with pytest.raises(ReadOnlyViolation) as refused:
        db.execute("SELECT 5 # 3")  # ``#`` starts a comment on MySQL
    assert refused.value.code == "HASH_COMMENT"
    db.close()


def test_postgresql_connect_fails_when_the_session_is_not_read_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    made = _install(monkeypatch, "psycopg2", "pg", "PostgreSQL 17.0")
    monkeypatch.setattr(_Conn, "show_answer", "off")
    db = ReadOnlyDB("postgresql+psycopg2://u:pw@h/db")
    with pytest.raises(DBConnectionError, match="PostgreSQL did not make the session read-only"):
        db.connect()
    assert db._engine is None
    assert [conn.closed for conn in made] == [True]
