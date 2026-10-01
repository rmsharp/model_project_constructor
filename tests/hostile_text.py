"""Hostile database text, shared by the tests that hold it clear of a terminal and a report.

Session 270 (``BACKLOG.md``: the item that was titled *Seven more routes put database or
driver text on a terminal or in a report unscrubbed*, routes 1 to 3; it is now *Seven more
routes can still put database, driver or exception text ...*). Session 269's review of its
own fix found seven routes by which database or driver text still reached a terminal or a
report; Session 270 closed the first three: the connect error ``discover`` let escape as a
traceback, the "database unreachable" concern ``run`` writes into the report, and the driver
exceptions the quality checks and the baseline copy into it. Each is its own call site, so
each has its own test, and they all need the same hostile input: this module is where it
lives.

It serves the tests written for those three routes. ``test_discovery.py`` and ``test_cli.py``
already held their own copies of the control-character helpers (Session 269) and keep them.

Importing it registers the ``fakeesc`` dialect (see :class:`EscapingDialect`). That is a
side effect, on purpose: the URL scheme is unique to these tests and nothing else reads it.
"""

from __future__ import annotations

import sqlite3
import unicodedata
from pathlib import Path

from sqlalchemy.dialects import registry
from sqlalchemy.dialects.sqlite.pysqlite import SQLiteDialect_pysqlite

#: The 65 ``Cc`` characters: the C0 controls, DEL and the C1 controls. A terminal ACTS on
#: these rather than printing them (ESC and BEL open a title or colour sequence; U+009B is
#: a one-character CSI). ``test_db.py`` holds this list, and :func:`unsafe`, against the
#: Unicode database, so neither can drift from it.
CONTROLS = [*map(chr, range(0x00, 0x20)), *map(chr, range(0x7F, 0xA0))]
EVERY_CONTROL = "".join(CONTROLS)
#: The controls ``redact_secrets`` reads as part of an unquoted secret's value. The ten that
#: are whitespace END the value there instead: a documented limit of that masker, which the
#: scrub neither causes nor changes.
NON_SPACE_CONTROLS = [c for c in CONTROLS if not c.isspace()]

#: A terminal-title sequence and a colour code, each opened by ESC, inside an identifier:
#: the shape Session 267 measured (2 ESC and 1 BEL). ``ESCAPE_NAME_SCRUBBED`` is what the
#: scrub leaves of it.
ESCAPE_NAME = "evil\x1b]0;PWNED-TITLE\x07\x1b[31mred"
ESCAPE_NAME_SCRUBBED = "evil ]0;PWNED-TITLE [31mred"

SECRET = "hunter2"
#: A table name shaped like a connection-string fragment. A driver that quotes a name in an
#: error message therefore quotes a secret-shaped string, with no simulation needed.
SECRET_NAME = f"cfg PWD={SECRET};Database=claims"


def control_ids(chars: list[str]) -> list[str]:
    return [f"U+{ord(c):04X}" for c in chars]


def unsafe(text: str) -> list[str]:
    """The characters of ``text`` a terminal would act on, as code points.

    Read from the Unicode database rather than from a range typed here, so these tests and
    the code under test cannot share a typo. A newline is allowed: it is the line break of
    a multi-line capture, and the messages these tests read flatten their own.
    """
    return sorted(
        {f"U+{ord(c):04X}" for c in text if unicodedata.category(c) == "Cc" and c != "\n"}
    )


#: What the simulated driver says when a connect fails: PostgreSQL echoes the role name it
#: was given, and a DSN-shaped detail follows a newline, as SQLAlchemy's own help URL does.
CONNECT_CAUSE = f'FATAL: role "{ESCAPE_NAME}" does not exist\ndetail: PWD={SECRET};Database=claims'


class EscapingDialect(SQLiteDialect_pysqlite):
    """A dialect whose every connect fails with :data:`CONNECT_CAUSE`.

    SIMULATED, not a live PostgreSQL, MySQL, Oracle or SQL Server: the same stand-in the
    Session 269 review used, a SQLite dialect whose DBAPI error carries what a server's
    would. SQLAlchemy wraps it as ``OperationalError`` and appends its help URL after a
    newline, so the message the code under test sees has the shape of a real one.
    """

    name = "fakeesc"
    driver = "fakeesc"
    supports_statement_cache = True

    def create_connect_args(self, url: object) -> tuple[list[object], dict[str, object]]:
        return ([], {})

    def connect(self, *cargs: object, **cparams: object) -> object:
        raise sqlite3.OperationalError(CONNECT_CAUSE)


registry.register("fakeesc", __name__, "EscapingDialect")
#: A URL no server needs to be behind.
ESCAPING_URL = "fakeesc:///claims"


def database_with_a_dangling_view(path: Path, table_name: str) -> str:
    """Build a SQLite file in which ``claims`` is a view over a table that is gone.

    Every statement that names ``claims`` then fails with ``no such table:
    main.<table_name>``: the driver quotes the NAME, which is how a hostile name reaches an
    error message. ``SELECT 1`` still works, so a connect (which runs it) succeeds and a
    quality check or baseline that names ``claims`` fails. A real SQLite file, not a
    simulation, and the same shape Session 269's tests use.

    It replaces a version that overwrote ``sqlite_master`` with text that is not SQL. From
    SQLite 3.50.4 even ``SELECT 1`` fails on such a file (the connect then fails and the
    checks are never run), and SQLite built in defensive mode refuses the overwrite. The
    dangling view behaves the same on every build from 3.39.4 to 3.54.0 (measured by the
    Session 270 review).
    """
    con = sqlite3.connect(path)
    try:
        con.execute(f'CREATE TABLE "{table_name}" (x INTEGER)')
        con.execute(f'CREATE VIEW claims AS SELECT x FROM "{table_name}"')
        con.execute(f'DROP TABLE "{table_name}"')
        con.commit()
    finally:
        con.close()
    return f"sqlite:///{path}"
