"""End-to-end CLI tests for the standalone Data Agent.

Uses Typer's CliRunner to invoke the ``model-data-agent run`` command with
the ``--fake-llm`` flag so no real API key is required. The fake client
returns a deterministic primary query + QC pair that exercises the full
flow; the output JSON is parsed as a DataReport and inspected.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import sqlalchemy as sa
from model_project_constructor_data_agent.cli import app
from model_project_constructor_data_agent.llm import TableRanking
from model_project_constructor_data_agent.schemas import (
    DataReport,
    DataSourceEntry,
    DataSourceInventory,
)
from typer.testing import CliRunner

FIXTURE_REQUEST = (
    Path(__file__).resolve().parents[1] / "fixtures" / "sample_request.json"
)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_cli_smoke_fake_llm_no_db(runner: CliRunner, tmp_path: Path) -> None:
    """Fake LLM + no --db-url → COMPLETE report with DB-unreachable concern."""
    out = tmp_path / "report.json"
    result = runner.invoke(
        app,
        [
            "run",
            "--request",
            str(FIXTURE_REQUEST),
            "--output",
            str(out),
            "--fake-llm",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "COMPLETE" in result.output

    report = DataReport.model_validate(json.loads(out.read_text()))
    assert report.status == "COMPLETE"
    assert len(report.primary_queries) == 1
    assert report.primary_queries[0].name == "fake_primary"
    assert any("database unreachable" in c for c in report.data_quality_concerns)
    for qc in report.primary_queries[0].quality_checks:
        assert qc.execution_status == "NOT_EXECUTED"


def test_cli_smoke_fake_llm_with_sqlite(runner: CliRunner, tmp_path: Path) -> None:
    """Fake LLM + live SQLite → QC checks execute against the real DB."""
    import sqlalchemy as sa

    db_path = tmp_path / "smoke.db"
    engine = sa.create_engine(f"sqlite:///{db_path}")
    try:
        with engine.begin() as conn:
            conn.execute(sa.text("CREATE TABLE claims (id INTEGER PRIMARY KEY)"))
            conn.execute(sa.text("INSERT INTO claims (id) VALUES (1), (2), (3)"))
    finally:
        engine.dispose()

    out = tmp_path / "report.json"
    result = runner.invoke(
        app,
        [
            "run",
            "--request",
            str(FIXTURE_REQUEST),
            "--output",
            str(out),
            "--fake-llm",
            "--db-url",
            f"sqlite:///{db_path}",
        ],
    )
    assert result.exit_code == 0, result.output

    report = DataReport.model_validate(json.loads(out.read_text()))
    assert report.status == "COMPLETE"
    assert not any(
        "database unreachable" in c for c in report.data_quality_concerns
    )
    # Fake client asks for SELECT 1 — always passes, one row ⇒ PASSED.
    for qc in report.primary_queries[0].quality_checks:
        assert qc.execution_status == "PASSED"


def test_cli_run_unknown_provider_errors(runner: CliRunner, tmp_path: Path) -> None:
    """``run --provider <unknown>`` (real client path) fails via make_llm_client.

    The factory raises ValueError before constructing any SDK, so the command
    exits non-zero and writes no output.
    """
    out = tmp_path / "report.json"
    result = runner.invoke(
        app,
        [
            "run",
            "--request",
            str(FIXTURE_REQUEST),
            "--output",
            str(out),
            "--provider",
            "openai",
        ],
    )
    assert result.exit_code != 0
    assert isinstance(result.exception, ValueError)
    assert "openai" in str(result.exception)
    assert not out.exists()


def test_cli_run_fake_llm_short_circuits_provider(
    runner: CliRunner, tmp_path: Path
) -> None:
    """``--fake-llm`` wins over ``--provider``: the fake client bypasses the factory."""
    out = tmp_path / "report.json"
    result = runner.invoke(
        app,
        [
            "run",
            "--request",
            str(FIXTURE_REQUEST),
            "--output",
            str(out),
            "--provider",
            "not-a-real-provider",
            "--fake-llm",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "COMPLETE" in result.output


def test_cli_missing_request_file_errors(runner: CliRunner, tmp_path: Path) -> None:
    out = tmp_path / "report.json"
    result = runner.invoke(
        app,
        [
            "run",
            "--request",
            str(tmp_path / "does_not_exist.json"),
            "--output",
            str(out),
            "--fake-llm",
        ],
    )
    assert result.exit_code != 0
    assert not out.exists()


def test_cli_no_args_shows_help(runner: CliRunner) -> None:
    result = runner.invoke(app, [])
    assert "model-data-agent" in result.output.lower() or "usage" in result.output.lower()


def test_python_dash_m_entrypoint_works() -> None:
    """`python -m model_project_constructor_data_agent --help` should not crash."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "model_project_constructor_data_agent", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "run" in result.stdout.lower()
    assert "discover" in result.stdout.lower()


def _seed_discover_db(db_path: Path, *, with_policies: bool = True) -> str:
    engine = sa.create_engine(f"sqlite:///{db_path}")
    try:
        with engine.begin() as conn:
            conn.execute(
                sa.text("CREATE TABLE claims (claim_id INTEGER PRIMARY KEY, amount REAL)")
            )
            if with_policies:
                conn.execute(
                    sa.text(
                        "CREATE TABLE policies (policy_id INTEGER PRIMARY KEY, state TEXT)"
                    )
                )
    finally:
        engine.dispose()
    return f"sqlite:///{db_path}"


def test_cli_discover_smoke(runner: CliRunner, tmp_path: Path) -> None:
    """``discover`` writes a valid DataSourceInventory JSON."""
    db_url = _seed_discover_db(tmp_path / "discover.db")

    out = tmp_path / "inv.json"
    result = runner.invoke(
        app,
        [
            "discover",
            "--db-url",
            db_url,
            "--output",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "2 entries" in result.output

    inv = DataSourceInventory.model_validate(json.loads(out.read_text()))
    fqns = {e.fully_qualified_name for e in inv.entries}
    assert fqns == {"main.claims", "main.policies"}
    assert inv.producers[0].producer_type == "automated"
    assert inv.producers[0].notes is None


def test_cli_discover_rank_with_fake_llm(runner: CliRunner, tmp_path: Path) -> None:
    """``discover --rank-with-llm --fake-llm`` populates relevance_score deterministically."""
    db_url = _seed_discover_db(tmp_path / "discover.db", with_policies=False)

    out = tmp_path / "inv.json"
    result = runner.invoke(
        app,
        [
            "discover",
            "--db-url",
            db_url,
            "--output",
            str(out),
            "--rank-with-llm",
            "--fake-llm",
            "--request-context",
            "subrogation recovery",
        ],
    )
    assert result.exit_code == 0, result.output

    inv = DataSourceInventory.model_validate(json.loads(out.read_text()))
    assert len(inv.entries) == 1
    entry = inv.entries[0]
    assert entry.relevance_score == pytest.approx(0.9)
    assert "fake-llm" in (entry.relevance_reason or "")
    assert inv.producers[0].notes is None


def test_cli_discover_include_schemas_filter(
    runner: CliRunner, tmp_path: Path
) -> None:
    """``--include-schemas`` filters discovery to the named schemas."""
    db_url = _seed_discover_db(tmp_path / "discover.db")

    out_main = tmp_path / "inv_main.json"
    result_main = runner.invoke(
        app,
        [
            "discover",
            "--db-url",
            db_url,
            "--output",
            str(out_main),
            "--include-schemas",
            "main",
        ],
    )
    assert result_main.exit_code == 0, result_main.output
    inv_main = DataSourceInventory.model_validate(json.loads(out_main.read_text()))
    assert len(inv_main.entries) == 2
    assert inv_main.producers[0].notes is None

    out_empty = tmp_path / "inv_empty.json"
    result_empty = runner.invoke(
        app,
        [
            "discover",
            "--db-url",
            db_url,
            "--output",
            str(out_empty),
            "--include-schemas",
            "nonexistent",
        ],
    )
    assert result_empty.exit_code == 0, result_empty.output
    inv_empty = DataSourceInventory.model_validate(json.loads(out_empty.read_text()))
    assert inv_empty.entries == []
    assert len(inv_empty.producers) == 1
    # Without this, "the filter matched nothing" and "the probe blew up" are
    # the same two assertions: a degraded inventory also has entries == [].
    assert inv_empty.producers[0].notes is None


def test_cli_discover_unknown_provider_errors(runner: CliRunner, tmp_path: Path) -> None:
    """``discover --rank-with-llm --provider <unknown>`` surfaces the factory error.

    The DB connects, then make_llm_client raises ValueError for the unknown
    provider before any ranking happens, so the command exits non-zero and
    writes no inventory.
    """
    db_url = _seed_discover_db(tmp_path / "discover.db", with_policies=False)
    out = tmp_path / "inv.json"
    result = runner.invoke(
        app,
        [
            "discover",
            "--db-url",
            db_url,
            "--output",
            str(out),
            "--rank-with-llm",
            "--provider",
            "openai",
            "--request-context",
            "subrogation recovery",
        ],
    )
    assert result.exit_code != 0
    assert isinstance(result.exception, ValueError)
    assert "openai" in str(result.exception)
    assert not out.exists()


def test_cli_discover_unreachable_db_errors(runner: CliRunner, tmp_path: Path) -> None:
    """discover against an unreachable DB exits non-zero (connect failure)."""
    out = tmp_path / "inv.json"
    result = runner.invoke(
        app,
        [
            "discover",
            "--db-url",
            "postgresql://nobody:nobody@127.0.0.1:1/none",
            "--output",
            str(out),
        ],
    )
    assert result.exit_code != 0
    assert not out.exists()


class _FailingRanker:
    """LLM stand-in whose ranking always fails. Records that it was reached."""

    def __init__(self, exc: Exception) -> None:
        self._exc = exc
        self.calls = 0

    def rank_candidate_tables(self, entries: object, request_context: object) -> object:
        self.calls += 1
        raise self._exc


def test_cli_discover_failed_ranking_keeps_the_file_and_exits_nonzero(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Operator ruling, Session 261: ``--rank-with-llm`` was asked for and failed.

    Until Session 261 this was an uncaught traceback and NO file. Now the
    reflection work is saved — the inventory is written, unranked, with a note —
    and the exit status stays non-zero so ``discover ... && next-step`` can still
    tell a ranked inventory from an unranked one.
    """
    import model_project_constructor_data_agent.cli as cli_mod
    from model_project_constructor_data_agent.anthropic_client import LLMParseError
    from model_project_constructor_data_agent.discovery import RANKING_FAILED_NOTE_PREFIX

    ranker = _FailingRanker(LLMParseError("expected JSON array, got dict"))
    monkeypatch.setattr(cli_mod, "make_llm_client", lambda provider, **kw: ranker)

    db_url = _seed_discover_db(tmp_path / "discover.db", with_policies=False)
    out = tmp_path / "inv.json"
    result = runner.invoke(
        app,
        ["discover", "--db-url", db_url, "--output", str(out), "--rank-with-llm"],
    )

    assert ranker.calls == 1  # the failing ranker was really reached
    assert result.exit_code == 1, result.output
    assert isinstance(result.exception, SystemExit)  # a clean exit, not a traceback
    assert "1 entries" in result.stdout
    # The error goes to STDERR, and stdout stays the one "wrote" line. Asserting
    # on ``result.output`` would not pin that: click interleaves both into it.
    assert "UNRANKED" in result.stderr
    assert "UNRANKED" not in result.stdout
    assert "(LLMParseError)" in result.stderr  # the note itself is echoed

    inv = DataSourceInventory.model_validate(json.loads(out.read_text()))
    assert [e.fully_qualified_name for e in inv.entries] == ["main.claims"]
    assert inv.entries[0].relevance_score is None
    assert (inv.producers[0].notes or "").startswith(
        f"{RANKING_FAILED_NOTE_PREFIX} (LLMParseError)"
    )


class _NamesNothingRanker:
    """LLM stand-in that ranks every table under its BARE name, so nothing matches."""

    def __init__(self) -> None:
        self.calls = 0

    def rank_candidate_tables(
        self, entries: list[DataSourceEntry], request_context: object
    ) -> object:
        self.calls += 1
        return [TableRanking(e.name, 0.9, "matches nothing") for e in entries]


def test_cli_discover_ranking_that_names_no_table_exits_nonzero(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Session 264: a ranking that returns normally but names no table is a
    ranking failure, so the Session 261 exit-1 ruling now fires for it. Before,
    nothing raised: every score stayed ``None``, ``notes`` was ``null`` and the
    command exited 0 (measured)."""
    import model_project_constructor_data_agent.cli as cli_mod
    from model_project_constructor_data_agent.discovery import RANKING_FAILED_NOTE_PREFIX

    ranker = _NamesNothingRanker()
    monkeypatch.setattr(cli_mod, "make_llm_client", lambda provider, **kw: ranker)

    db_url = _seed_discover_db(tmp_path / "discover.db", with_policies=False)
    out = tmp_path / "inv.json"
    result = runner.invoke(
        app,
        ["discover", "--db-url", db_url, "--output", str(out), "--rank-with-llm"],
    )

    assert ranker.calls == 1
    assert result.exit_code == 1, result.output
    assert isinstance(result.exception, SystemExit)
    assert "UNRANKED" in result.stderr
    assert "(RankingMatchedNoEntryError)" in result.stderr

    inv = DataSourceInventory.model_validate(json.loads(out.read_text()))
    assert [e.fully_qualified_name for e in inv.entries] == ["main.claims"]
    assert inv.entries[0].relevance_score is None
    assert (inv.producers[0].notes or "").startswith(
        f"{RANKING_FAILED_NOTE_PREFIX} (RankingMatchedNoEntryError)"
    )


def test_cli_discover_missing_credentials_keeps_the_file_and_exits_nonzero(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The ranking failure users will actually hit, through the SHIPPED client.

    With no credentials the Anthropic SDK raises from inside
    ``rank_candidate_tables`` — not from client construction — so it lands in
    the probe's ranking stage (measured Session 261: a ``TypeError`` from the
    SDK's header check, before any send). The dead local port keeps the test
    offline whatever the SDK does first. The exception TYPE is deliberately not
    asserted: it is the SDK's, and a connection error from a future SDK that
    stops checking first is the same outcome for the operator.
    """
    for var in (
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "AWS_BEARER_TOKEN_BEDROCK",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:9")

    db_url = _seed_discover_db(tmp_path / "discover.db", with_policies=False)
    out = tmp_path / "inv.json"
    result = runner.invoke(
        app,
        ["discover", "--db-url", db_url, "--output", str(out), "--rank-with-llm"],
    )

    assert result.exit_code == 1, result.output
    assert isinstance(result.exception, SystemExit)
    inv = DataSourceInventory.model_validate(json.loads(out.read_text()))
    assert [e.fully_qualified_name for e in inv.entries] == ["main.claims"]
    assert inv.entries[0].relevance_score is None
    assert (inv.producers[0].notes or "").startswith("LLM relevance ranking failed")


@pytest.mark.parametrize(
    ("exc", "type_name"),
    [
        (
            sa.exc.OperationalError(
                statement="", params={}, orig=Exception("permission denied")
            ),
            "OperationalError",
        ),
        (KeyError("referred_table"), "KeyError"),
    ],
    ids=["a-type-HEAD-already-caught", "a-type-HEAD-let-escape"],
)
def test_cli_discover_failed_reflection_keeps_the_file_and_exits_nonzero(
    runner: CliRunner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exc: Exception,
    type_name: str,
) -> None:
    """Operator ruling, Session 261: ANY degraded inventory exits 1, file kept.

    Both rows changed, in opposite directions, and the ruling makes them one
    rule. A type the old guard caught (first row) was exit 0 with an empty
    inventory — documented, and silent in any ``discover ... && next-step``. A
    type it let escape (second row) was a traceback, exit 1 and no file.
    """
    import model_project_constructor_data_agent.cli as cli_mod

    def _boom(self: object, schemas: object = None) -> object:
        raise exc

    monkeypatch.setattr(cli_mod.ReadOnlyDB, "get_information_schema", _boom)

    db_url = _seed_discover_db(tmp_path / "discover.db", with_policies=False)
    out = tmp_path / "inv.json"
    result = runner.invoke(app, ["discover", "--db-url", db_url, "--output", str(out)])

    assert result.exit_code == 1, result.output
    assert isinstance(result.exception, SystemExit)
    assert "0 entries" in result.stdout
    assert "EMPTY" in result.stderr
    assert "EMPTY" not in result.stdout
    inv = DataSourceInventory.model_validate(json.loads(out.read_text()))
    assert inv.entries == []
    assert (inv.producers[0].notes or "").startswith(
        f"information_schema probe failed: {type_name}: "
    )


def test_cli_derives_sql_dialect_from_db_url(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``--db-url`` must reach the prompt as a dialect (Session 217).

    The CLI is the seam where the execution target becomes known, so it is where
    the target must be named. Deriving it here — rather than accepting a
    separate flag — is what makes it impossible to point the agent at Postgres
    while telling the model to write SQLite.
    """
    import model_project_constructor_data_agent.cli as cli_mod

    recorded: dict[str, object] = {}

    def _fake_factory(provider: str, **kwargs: object) -> object:
        recorded.update(kwargs)
        return cli_mod._FakeCLIClient()

    monkeypatch.setattr(cli_mod, "make_llm_client", _fake_factory)

    db_path = tmp_path / "smoke.db"
    engine = sa.create_engine(f"sqlite:///{db_path}")
    try:
        with engine.begin() as conn:
            conn.execute(sa.text("CREATE TABLE claims (id INTEGER PRIMARY KEY)"))
    finally:
        engine.dispose()

    result = runner.invoke(
        app,
        [
            "run",
            "--request",
            str(FIXTURE_REQUEST),
            "--output",
            str(tmp_path / "report.json"),
            "--db-url",
            f"sqlite:///{db_path}",
        ],
    )

    assert result.exit_code == 0, result.output
    assert recorded["sql_dialect"] == "sqlite"


def test_cli_survives_a_non_numeric_port_in_db_url(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bad port must not crash the CLI before the DB is ever reached.

    Regression test for the Session 218 defect fixed in Session 223. ``db.dialect``
    is evaluated at ``cli.py:129``, *outside* the ``try`` that begins on the next
    statement, so the bare ``ValueError`` ``make_url`` raises on a non-numeric
    port escaped Typer as a rendered traceback and exited non-zero.

    ⚠ **What this does and does not establish.** Half of the warning that stood
    here was closed in Session 260 and half was not. The report is no longer
    byte-identical to a well-formed-but-unreachable URL's: ``execute_qc`` binds
    the ``DBConnectionError`` and ``agent.py`` appends its cause to the canned
    "database unreachable at QC execution time" concern, so an unexported
    ``$DB_PORT`` reads differently from a warehouse that is down, and
    ``sql_dialect_from_url`` additionally logs a WARNING naming the *parse*
    failure. What is unchanged: the command still exits 0 and ``agent.py``
    still reports ``COMPLETE``, so there is still **no** ``FAILED_AT_DATA``
    off-ramp for either case. That last part is deliberate — it turns runs that
    succeed today into failures, so it needs an operator ruling — and it is
    what remains filed.

    The unit test in ``tests/data_agent_package/test_db.py`` pins the derivation;
    this pins the *seam*, which is the part a user actually meets.
    """
    import model_project_constructor_data_agent.cli as cli_mod

    recorded: dict[str, object] = {}

    def _fake_factory(provider: str, **kwargs: object) -> object:
        recorded.update(kwargs)
        return cli_mod._FakeCLIClient()

    monkeypatch.setattr(cli_mod, "make_llm_client", _fake_factory)

    result = runner.invoke(
        app,
        [
            "run",
            "--request",
            str(FIXTURE_REQUEST),
            "--output",
            str(tmp_path / "report.json"),
            "--db-url",
            "postgresql://user:pw@warehouse.internal:$DB_PORT/claims",
        ],
    )

    # "Survives" has to mean the command actually completed, not merely that it
    # avoided one exception type: without the exit-code assertion this test stays
    # green through any crash that happens after the dialect derivation.
    assert result.exit_code == 0, result.output
    assert result.exception is None, result.output
    # The factory must have been reached at all — under the pre-fix catch the CLI
    # died before `_build_llm`, leaving `recorded` empty. Asserting membership
    # first turns that into a named failure instead of a bare KeyError.
    assert "sql_dialect" in recorded, f"CLI never reached the factory: {result.output}"
    # The dialect is unknowable, so it is left unstated rather than guessed.
    assert recorded["sql_dialect"] is None


def test_cli_leaves_dialect_unset_without_a_db(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No ``--db-url`` ⇒ no execution target ⇒ nothing to name.

    Guessing a dialect here would be worse than silence: the SQL is not executed
    at all on this path (the SKIP_EXECUTION off-ramp), so any named dialect would
    be an unfounded claim about a database the caller never supplied.
    """
    import model_project_constructor_data_agent.cli as cli_mod

    recorded: dict[str, object] = {}

    def _fake_factory(provider: str, **kwargs: object) -> object:
        recorded.update(kwargs)
        return cli_mod._FakeCLIClient()

    monkeypatch.setattr(cli_mod, "make_llm_client", _fake_factory)

    result = runner.invoke(
        app,
        [
            "run",
            "--request",
            str(FIXTURE_REQUEST),
            "--output",
            str(tmp_path / "report.json"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert recorded["sql_dialect"] is None
