"""Unit tests for the information_schema reference producer (Phase 2).

Covers ``probe_information_schema`` in
``packages/data-agent/src/model_project_constructor_data_agent/discovery.py``
per plan §9 Phase 2. Fake-DB coverage only — live-DB testing deferred.

Tests seed a transient SQLite database with known tables / views / FKs and
assert the probe's output against the data-source-inventory contract from
Phase 1.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pytest
import sqlalchemy as sa
from anthropic.types import TextBlock
from model_project_constructor_data_agent import (
    DataSourceInventory,
    ReadOnlyDB,
    TableRanking,
    probe_information_schema,
)
from model_project_constructor_data_agent.anthropic_client import (
    AnthropicLLMClient,
    LLMParseError,
)
from model_project_constructor_data_agent.discovery import (
    PRODUCER_ID,
    PRODUCER_VERSION,
    RANKING_FAILED_NOTE_PREFIX,
)
from model_project_constructor_data_agent.schemas import DataSourceEntry


@pytest.fixture
def seeded_sqlite(tmp_path: Path) -> str:
    """SQLite DB with 3 tables + 1 view + 1 FK for discovery tests."""
    db_path = tmp_path / "discover.db"
    engine = sa.create_engine(f"sqlite:///{db_path}")
    try:
        with engine.begin() as conn:
            conn.execute(
                sa.text(
                    "CREATE TABLE claims "
                    "(claim_id INTEGER PRIMARY KEY, loss_amount REAL NOT NULL)"
                )
            )
            conn.execute(
                sa.text(
                    "CREATE TABLE policies "
                    "(policy_id INTEGER PRIMARY KEY, state TEXT)"
                )
            )
            conn.execute(
                sa.text(
                    "CREATE TABLE outcomes ("
                    "claim_id INTEGER PRIMARY KEY, "
                    "recovered_amount REAL, "
                    "FOREIGN KEY (claim_id) REFERENCES claims(claim_id))"
                )
            )
            conn.execute(
                sa.text(
                    "CREATE VIEW v_claim_summary AS SELECT claim_id FROM claims"
                )
            )
    finally:
        engine.dispose()
    return f"sqlite:///{db_path}"


def _probe(url: str, **kwargs: Any) -> DataSourceInventory:
    """Helper: connect, probe, close — for HEALTHY-path tests only.

    ⚠ The ``notes is None`` assertion is load-bearing, not tidiness. Since
    Session 261 the probe absorbs every ``Exception`` from reflection, entry
    building and ranking into a labelled inventory, so a healthy-path test that
    asserts only on ``entries`` would pass with reflection completely broken.
    Measured Session 261, with ``get_information_schema`` raising on every call:
    about half the healthy-path tests here still passed without this line, and
    none do with it. (No count on purpose — two reviewers measured two different
    figures, because it depends on which breakage and which revision of this
    file.) A test that WANTS a degraded inventory calls
    ``probe_information_schema`` directly.
    """
    db = ReadOnlyDB(url)
    db.connect()
    try:
        inv = probe_information_schema(db, **kwargs)
    finally:
        db.close()
    assert inv.producers[0].notes is None, inv.producers[0].notes
    return inv


DISCOVERY_LOGGER = "model_project_constructor_data_agent.discovery"
SECRET = "hunter2"

GOOD_ROW: dict[str, Any] = {
    "namespace": "main",
    "name": "claims",
    "entity_kind": "table",
    "columns": [{"name": "id", "data_type": "INTEGER"}],
    "primary_key_columns": ["id"],
}


def _three_rows() -> list[dict[str, Any]]:
    return [{**GOOD_ROW, "name": n} for n in ("claims", "outcomes", "policies")]


def _discovery_warnings(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [
        r
        for r in caplog.records
        if r.name == DISCOVERY_LOGGER and r.levelno == logging.WARNING
    ]


class _RowsDB:
    """Duck-typed DB whose reflection returns whatever it was given."""

    def __init__(self, rows: Any) -> None:
        self._rows = rows

    def get_information_schema(self, schemas: list[str] | None = None) -> Any:
        return self._rows


class _RaisingDB:
    def __init__(self, exc: BaseException) -> None:
        self._exc = exc

    def get_information_schema(self, schemas: list[str] | None = None) -> Any:
        raise self._exc


class _Ranker:
    """Ranker whose behaviour is a callable; records every call.

    ⚠ Never signal "should not be called" from a fake on the probe's path by
    raising an ``Exception`` subclass — the probe absorbs it. Record the call
    and assert on ``calls`` outside the probe.
    """

    def __init__(self, behaviour: Any) -> None:
        self._behaviour = behaviour
        self.calls: list[str | None] = []

    def rank_candidate_tables(
        self, entries: list[DataSourceEntry], request_context: str | None
    ) -> Any:
        self.calls.append(request_context)
        return self._behaviour(entries)


def _raise(exc: BaseException) -> Any:
    def _behaviour(entries: list[DataSourceEntry]) -> Any:
        raise exc

    return _behaviour


class TestProbeHappyPath:
    def test_returns_inventory(self, seeded_sqlite: str) -> None:
        inv = _probe(seeded_sqlite)
        assert isinstance(inv, DataSourceInventory)

    def test_discovers_tables_and_view(self, seeded_sqlite: str) -> None:
        inv = _probe(seeded_sqlite)
        assert len(inv.entries) == 4
        fqns = {e.fully_qualified_name for e in inv.entries}
        assert fqns == {
            "main.claims",
            "main.outcomes",
            "main.policies",
            "main.v_claim_summary",
        }

    def test_producer_metadata(self, seeded_sqlite: str) -> None:
        inv = _probe(seeded_sqlite)
        assert len(inv.producers) == 1
        producer = inv.producers[0]
        assert producer.producer_id == PRODUCER_ID
        assert producer.producer_type == "automated"
        assert producer.producer_version == PRODUCER_VERSION
        assert producer.notes is None

    def test_entity_kind_table_vs_view(self, seeded_sqlite: str) -> None:
        inv = _probe(seeded_sqlite)
        by_fqn = {e.fully_qualified_name: e for e in inv.entries}
        assert by_fqn["main.claims"].entity_kind == "table"
        assert by_fqn["main.v_claim_summary"].entity_kind == "view"

    def test_primary_key_columns_detected(self, seeded_sqlite: str) -> None:
        inv = _probe(seeded_sqlite)
        by_fqn = {e.fully_qualified_name: e for e in inv.entries}
        claims = by_fqn["main.claims"]
        assert claims.primary_key_columns == ["claim_id"]
        pk_flag_cols = {c.name for c in claims.columns if c.is_primary_key}
        assert pk_flag_cols == {"claim_id"}

    def test_foreign_key_target_populated(self, seeded_sqlite: str) -> None:
        inv = _probe(seeded_sqlite)
        by_fqn = {e.fully_qualified_name: e for e in inv.entries}
        outcomes = by_fqn["main.outcomes"]
        fk_cols = [c for c in outcomes.columns if c.is_foreign_key]
        assert len(fk_cols) == 1
        assert fk_cols[0].name == "claim_id"
        assert fk_cols[0].foreign_key_target == "main.claims.claim_id"

    def test_every_entry_resolves_producer(self, seeded_sqlite: str) -> None:
        """Cross-field validator guarantees FK integrity at construction."""
        inv = _probe(seeded_sqlite)
        known = {p.producer_id for p in inv.producers}
        for entry in inv.entries:
            assert entry.producer_id in known

    def test_request_context_preserved(self, seeded_sqlite: str) -> None:
        inv = _probe(seeded_sqlite, request_context="subrogation recovery")
        assert inv.request_context == "subrogation recovery"

    def test_created_at_populated(self, seeded_sqlite: str) -> None:
        inv = _probe(seeded_sqlite)
        assert inv.created_at is not None
        assert inv.producers[0].produced_at == inv.created_at

    def test_columns_captured_with_types(self, seeded_sqlite: str) -> None:
        inv = _probe(seeded_sqlite)
        by_fqn = {e.fully_qualified_name: e for e in inv.entries}
        claims_cols = {c.name: c for c in by_fqn["main.claims"].columns}
        assert claims_cols["claim_id"].data_type == "INTEGER"
        assert claims_cols["loss_amount"].data_type == "REAL"
        assert claims_cols["loss_amount"].nullable is False


class TestProbeIncludeSchemas:
    def test_filter_matching_schema_returns_entries(self, seeded_sqlite: str) -> None:
        inv = _probe(seeded_sqlite, include_schemas=["main"])
        assert len(inv.entries) == 4

    def test_filter_matching_nothing_returns_empty_entries(
        self, seeded_sqlite: str
    ) -> None:
        inv = _probe(seeded_sqlite, include_schemas=["nonexistent"])
        assert inv.entries == []
        assert len(inv.producers) == 1


class TestProbeDegradation:
    def test_empty_database_returns_empty_inventory(self, tmp_path: Path) -> None:
        db_path = tmp_path / "empty.db"
        engine = sa.create_engine(f"sqlite:///{db_path}")
        try:
            with engine.connect():
                pass
        finally:
            engine.dispose()
        inv = _probe(f"sqlite:///{db_path}")
        assert inv.entries == []
        assert len(inv.producers) == 1
        assert inv.producers[0].notes is None

    def test_probe_before_connect_surfaces_as_empty_with_note(
        self, tmp_path: Path
    ) -> None:
        """RuntimeError from a not-connected DB is caught; inventory has notes."""
        db = ReadOnlyDB(f"sqlite:///{tmp_path / 'x.db'}")
        inv = probe_information_schema(db)
        assert inv.entries == []
        notes = inv.producers[0].notes or ""
        assert notes.startswith("information_schema probe failed: RuntimeError: ")
        assert "before connect" in notes

    def test_sqlalchemy_error_caught(self) -> None:
        """A fake ReadOnlyDB that raises SQLAlchemyError becomes empty-with-note."""

        class FailingDB:
            def get_information_schema(
                self, schemas: list[str] | None = None
            ) -> list[dict[str, Any]]:
                raise sa.exc.OperationalError(
                    statement="", params={}, orig=Exception("permission denied")
                )

        inv = probe_information_schema(FailingDB())  # type: ignore[arg-type]
        assert inv.entries == []
        assert len(inv.producers) == 1
        notes = inv.producers[0].notes or ""
        assert notes.startswith("information_schema probe failed: OperationalError: ")
        assert "permission denied" in notes

    def test_not_implemented_error_caught(self) -> None:
        class UnsupportedDB:
            def get_information_schema(
                self, schemas: list[str] | None = None
            ) -> list[dict[str, Any]]:
                raise NotImplementedError("dialect 'fake_dialect' not supported")

        inv = probe_information_schema(UnsupportedDB())  # type: ignore[arg-type]
        assert inv.entries == []
        notes = inv.producers[0].notes or ""
        assert notes.startswith("information_schema probe failed: NotImplementedError: ")
        assert "fake_dialect" in notes


class TestProbeRoundTrip:
    def test_serializes_and_reloads_as_equal_inventory(
        self, seeded_sqlite: str
    ) -> None:
        original = _probe(seeded_sqlite, request_context="claims-domain")
        blob = original.model_dump_json()
        restored = DataSourceInventory.model_validate_json(blob)
        assert restored == original


class TestProbeWithLLMRanking:
    def test_llm_without_ranking_method_is_ignored(self, seeded_sqlite: str) -> None:
        """LLM object lacking rank_candidate_tables: relevance fields stay None."""

        class NoRankingLLM:
            pass

        inv = _probe(seeded_sqlite, llm=NoRankingLLM(), request_context="claims")
        for entry in inv.entries:
            assert entry.relevance_score is None
            assert entry.relevance_reason is None

    def test_llm_ranking_populates_relevance(self, seeded_sqlite: str) -> None:
        class AllSameRankingLLM:
            # A recorder, not an in-ranker ``assert``: the probe absorbs any
            # Exception a ranker raises, AssertionError included.
            contexts: list[str | None] = []

            def rank_candidate_tables(
                self,
                entries: list[DataSourceEntry],
                request_context: str | None,
            ) -> list[TableRanking]:
                self.contexts.append(request_context)
                return [
                    TableRanking(
                        fully_qualified_name=e.fully_qualified_name,
                        relevance_score=0.5,
                        relevance_reason=f"fake rank for {e.name}",
                    )
                    for e in entries
                ]

        inv = _probe(
            seeded_sqlite, llm=AllSameRankingLLM(), request_context="claims domain"
        )
        assert AllSameRankingLLM.contexts == ["claims domain"]
        assert len(inv.entries) == 4
        for entry in inv.entries:
            assert entry.relevance_score == pytest.approx(0.5)
            assert entry.relevance_reason is not None
            assert "fake rank" in entry.relevance_reason

    def test_partial_ranking_leaves_unranked_entries_none(
        self, seeded_sqlite: str
    ) -> None:
        """Entries the LLM does not return stay at relevance_score=None."""

        class PartialRankingLLM:
            def rank_candidate_tables(
                self,
                entries: list[DataSourceEntry],
                request_context: str | None,
            ) -> list[TableRanking]:
                return [
                    TableRanking(
                        fully_qualified_name=entries[0].fully_qualified_name,
                        relevance_score=0.95,
                        relevance_reason="top pick",
                    )
                ]

        inv = _probe(
            seeded_sqlite, llm=PartialRankingLLM(), request_context="claims"
        )
        scored = [e for e in inv.entries if e.relevance_score is not None]
        unscored = [e for e in inv.entries if e.relevance_score is None]
        assert len(scored) == 1
        assert scored[0].relevance_score == pytest.approx(0.95)
        assert len(unscored) == len(inv.entries) - 1

    def test_llm_ignored_when_entries_empty(self, tmp_path: Path) -> None:
        """LLM ranking is skipped when there are no entries. That saves an LLM
        call, and since Session 264 it is also what keeps an empty database from
        reading as a ranking that named no entry — a failure, and exit 1."""
        db_path = tmp_path / "empty.db"
        engine = sa.create_engine(f"sqlite:///{db_path}")
        try:
            with engine.connect():
                pass
        finally:
            engine.dispose()

        # A recorder, not a tripwire that raises: since Session 261 the probe
        # absorbs any Exception a ranker raises, so ``raise AssertionError``
        # here would be swallowed into a note and this test could never fail.
        llm = _Ranker(lambda entries: [])
        inv = _probe(f"sqlite:///{db_path}", llm=llm, request_context="anything")
        assert llm.calls == []
        assert inv.entries == []


class TestProbeNeverRaises:
    """Stage 1 — reflection and entry building. Filed Session 223, closed 261.

    Message strings in these fakes deliberately do NOT contain their own
    exception's type name, or the type-name assertions would pass with
    ``type(e).__name__`` deleted from the note.
    """

    @pytest.mark.parametrize(
        "exc",
        [KeyError("referred_table"), TypeError("boom"), AttributeError("boom")],
        ids=lambda e: type(e).__name__,
    )
    def test_unlisted_reflection_error_degrades_and_names_its_type(
        self, exc: Exception
    ) -> None:
        """The old guard was a three-type tuple; none of these was in it."""
        inv = probe_information_schema(_RaisingDB(exc))  # type: ignore[arg-type]
        assert inv.entries == []
        notes = inv.producers[0].notes or ""
        # str(KeyError("referred_table")) is just "'referred_table'" — the type
        # name is the only informative part of that note.
        assert notes.startswith(
            f"information_schema probe failed: {type(exc).__name__}: "
        )

    @pytest.mark.parametrize(
        ("rows", "type_name"),
        [
            ([{"namespace": "main"}], "KeyError"),
            ([{**GOOD_ROW, "entity_kind": "procedure"}], "ValidationError"),
            (None, "TypeError"),
        ],
        ids=["missing-name", "bad-entity-kind", "rows-none"],
    )
    def test_entry_build_failure_degrades(self, rows: Any, type_name: str) -> None:
        """Entry building sat outside the ``try`` entirely until Session 261."""
        inv = probe_information_schema(_RowsDB(rows))  # type: ignore[arg-type]
        assert inv.entries == []
        assert (inv.producers[0].notes or "").startswith(
            f"information_schema probe failed: {type_name}: "
        )

    @pytest.mark.parametrize(
        ("row", "fqn"),
        [
            ({**GOOD_ROW, "name": "bad\udc80name"}, "main.bad\udc80name"),
            ({**GOOD_ROW, "namespace": "sch\udcffema"}, "sch\udcffema.claims"),
            (
                {**GOOD_ROW, "columns": [{"name": "c\ud83d", "data_type": "INTEGER"}]},
                "main.claims",
            ),
            (
                {**GOOD_ROW, "columns": [{"name": "c", "data_type": "INT\udc80"}]},
                "main.claims",
            ),
        ],
        ids=["table-name", "namespace", "column-name", "column-type"],
    )
    @pytest.mark.parametrize("first", [True, False], ids=["bad-row-first", "bad-row-last"])
    @pytest.mark.parametrize("with_llm", [True, False], ids=["ranking-on", "ranking-off"])
    def test_reflected_text_that_cannot_be_written_fails_the_probe(
        self, row: dict[str, Any], fqn: str, first: bool, with_llm: bool
    ) -> None:
        """A lone surrogate validates as a ``str`` but cannot be written as UTF-8,
        so until Session 264 the inventory built, the file was written with exit
        0, and ``model_validate_json`` then refused to load it (measured). It is
        now a probe failure — blamed on reflection, where it came from, and
        never on ranking, which a later stage would otherwise report. Plain
        ``discover`` passes no LLM, hence ``ranking-off``; the bad row goes first
        and last, so a check of only one end of the list cannot pass."""
        llm = _Ranker(lambda entries: []) if with_llm else None
        rows = [row, GOOD_ROW] if first else [GOOD_ROW, row]
        inv = probe_information_schema(_RowsDB(rows), llm=llm)  # type: ignore[arg-type]
        assert inv.entries == []
        # The note names the table: pydantic's own error gives only a position.
        assert (inv.producers[0].notes or "").startswith(
            "information_schema probe failed: UnwritableEntryError: "
            f"entry {fqn!r} cannot be written as UTF-8 JSON: PydanticSerializationError: "
        )
        if llm is not None:
            assert llm.calls == []  # stage 1 failed, so stage 2 never ran
        assert DataSourceInventory.model_validate_json(inv.model_dump_json()) == inv

    def test_one_bad_table_fails_the_whole_probe(self) -> None:
        """No per-table skipping: a partial inventory is never returned unlabelled."""
        inv = probe_information_schema(
            _RowsDB([GOOD_ROW, {"namespace": "main"}])  # type: ignore[arg-type]
        )
        assert inv.entries == []

    def test_probe_failure_logs_exactly_one_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING, logger=DISCOVERY_LOGGER):
            probe_information_schema(_RaisingDB(KeyError("k")))  # type: ignore[arg-type]
        warnings = _discovery_warnings(caplog)
        assert len(warnings) == 1
        assert "KeyError" in warnings[0].getMessage()

    def test_note_and_log_mask_a_driver_echoed_password_on_one_line(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Assert the SECRET's absence, never a marker's presence (learning #268)."""
        exc = sa.exc.OperationalError(
            statement="",
            params={},
            orig=Exception(
                f"could not connect: postgresql://user:{SECRET}@host/db\nDETAIL: x"
            ),
        )
        with caplog.at_level(logging.WARNING, logger=DISCOVERY_LOGGER):
            inv = probe_information_schema(_RaisingDB(exc))  # type: ignore[arg-type]
        notes = inv.producers[0].notes or ""
        assert SECRET not in notes
        assert "\n" not in notes
        assert "could not connect" in notes  # redaction must not eat the cause
        assert ["\n" in r.getMessage() for r in _discovery_warnings(caplog)] == [False]
        # caplog.text is the FORMATTED record, traceback included; getMessage()
        # is not, so it would pass with ``exc_info=True`` leaking the raw text.
        assert SECRET not in caplog.text

    def test_unprintable_exception_still_degrades(self) -> None:
        class Unprintable(Exception):
            def __str__(self) -> str:
                raise RuntimeError("broken __str__")

        inv = probe_information_schema(_RaisingDB(Unprintable()))  # type: ignore[arg-type]
        assert inv.entries == []
        assert "Unprintable" in (inv.producers[0].notes or "")

    def test_str_subclass_message_still_degrades(self) -> None:
        """``str(e)`` hands a ``str`` SUBCLASS back unchanged, so guarding only the
        ``str(e)`` call leaves that subclass's own methods free to raise."""

        class Hostile(str):
            def encode(self, *a: Any, **k: Any) -> bytes:
                raise RuntimeError("encode boom")

        class StrSubclassError(Exception):
            def __str__(self) -> str:
                return Hostile("x")

        inv = probe_information_schema(_RaisingDB(StrSubclassError()))  # type: ignore[arg-type]
        assert inv.entries == []
        assert "StrSubclassError: <unprintable>" in (inv.producers[0].notes or "")

    def test_lone_surrogate_in_the_cause_still_serializes(self) -> None:
        """A message built by formatting an ``os.fsdecode``-d path carries its lone
        surrogate. (An OS-RAISED OSError repr-escapes its filename and does not —
        measured — which is why this one is hand-built.)"""
        inv = probe_information_schema(
            _RaisingDB(OSError("cannot open /data/\udcff.db"))  # type: ignore[arg-type]
        )
        assert DataSourceInventory.model_validate_json(inv.model_dump_json()) == inv

    @pytest.mark.parametrize("exc_type", [KeyboardInterrupt, SystemExit])
    def test_base_exception_from_reflection_propagates(
        self, exc_type: type[BaseException]
    ) -> None:
        with pytest.raises(exc_type):
            probe_information_schema(_RaisingDB(exc_type()))  # type: ignore[arg-type]


class TestRankingFailureKeepsEntries:
    """Stage 2 — ranking is an optional enrichment; its failure keeps the tables."""

    @pytest.mark.parametrize(
        ("behaviour", "type_name"),
        [
            (_raise(LLMParseError("expected JSON array, got dict")), "LLMParseError"),
            (_raise(KeyError("fully_qualified_name")), "KeyError"),
            (lambda entries: None, "TypeError"),
            (lambda entries: [{"fully_qualified_name": "main.claims"}], "AttributeError"),
            (lambda entries: ["main.claims"], "AttributeError"),
        ],
        ids=["parse-error", "wrong-keys", "rankings-none", "rankings-dicts", "rankings-strings"],
    )
    def test_ranking_failure_keeps_every_entry_unranked(
        self, behaviour: Any, type_name: str
    ) -> None:
        inv = probe_information_schema(
            _RowsDB(_three_rows()),  # type: ignore[arg-type]
            llm=_Ranker(behaviour),
            request_context="claims",
        )
        assert [e.fully_qualified_name for e in inv.entries] == [
            "main.claims",
            "main.outcomes",
            "main.policies",
        ]
        assert [e.relevance_score for e in inv.entries] == [None, None, None]
        assert [e.relevance_reason for e in inv.entries] == [None, None, None]
        notes = inv.producers[0].notes or ""
        assert notes.startswith(
            f"{RANKING_FAILED_NOTE_PREFIX} ({type_name}); all 3 entries are unranked."
        )
        # The two degradations must stay distinguishable by text.
        assert "probe failed" not in notes

    @pytest.mark.parametrize(
        ("llm", "expected_note_start"),
        [
            (
                type("LazyProperty", (), {
                    "rank_candidate_tables": property(
                        lambda self: (_ for _ in ()).throw(RuntimeError("lazy init failed"))
                    )
                })(),
                f"{RANKING_FAILED_NOTE_PREFIX} (RuntimeError)",
            ),
            # ``None`` reads as "this client does not rank" — same as no attribute.
            (type("NotCallable", (), {"rank_candidate_tables": None})(), None),
            (
                type("NotCallable", (), {"rank_candidate_tables": 42})(),
                f"{RANKING_FAILED_NOTE_PREFIX} (TypeError)",
            ),
        ],
        ids=["attribute-lookup-raises", "attribute-is-none", "attribute-not-callable"],
    )
    def test_odd_ranker_attributes_never_escape(
        self, llm: Any, expected_note_start: str | None
    ) -> None:
        """``hasattr`` swallows only AttributeError, so the lookup is inside the try
        — and a failure there is LABELLED, not swallowed into a healthy-looking
        inventory."""
        inv = probe_information_schema(_RowsDB(_three_rows()), llm=llm)  # type: ignore[arg-type]
        assert len(inv.entries) == 3
        notes = inv.producers[0].notes
        if expected_note_start is None:
            assert notes is None
        else:
            assert (notes or "").startswith(expected_note_start)

    def test_ranking_failure_logs_exactly_one_warning_carrying_the_cause(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING, logger=DISCOVERY_LOGGER):
            probe_information_schema(
                _RowsDB(_three_rows()),  # type: ignore[arg-type]
                llm=_Ranker(_raise(LLMParseError("prose reply, not an array"))),
            )
        warnings = _discovery_warnings(caplog)
        assert len(warnings) == 1
        message = warnings[0].getMessage()
        assert "returning 3 entries UNRANKED" in message
        assert "LLMParseError" in message
        assert "prose reply, not an array" in message

    @pytest.mark.parametrize(
        "leak",
        [
            f"401 {{'received_headers': {{'x-api-key': '{SECRET}'}}}}",
            f"Authorization: Bearer {SECRET}",
            f"opencode exited 1: ANTHROPIC_API_KEY={SECRET}",
        ],
        ids=["gateway-body", "bearer", "env-echo"],
    )
    def test_ranking_note_never_persists_the_message(self, leak: str) -> None:
        """The note is PUBLISHED with the inventory, so it carries the
        exception's TYPE only, unconditionally, and the message goes to the
        WARNING instead -- by design, not because ``redact_secrets`` happens
        to miss these shapes. It still does: Session 262 widened the key list
        enough that ``redact_secrets`` now masks two of the three ("gateway-
        body" and "env-echo" both contain a `key=`/`key:` form under a key the
        wider list matches), leaving only "bearer" -- a header with no `key=`/
        `key:` form at all -- genuinely blind (measured). None of that changes
        this test: the note is type-only regardless of what the redactor can
        see, which is the point of the design."""
        inv = probe_information_schema(
            _RowsDB(_three_rows()),  # type: ignore[arg-type]
            llm=_Ranker(_raise(RuntimeError(leak))),
        )
        assert SECRET not in inv.model_dump_json()
        assert "RuntimeError" in (inv.producers[0].notes or "")

    def test_ranking_warning_is_masked_and_single_line(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Stage 2 has its OWN ``_safe_message`` call site; stage 1's tests do not
        reach it. Swapping it for a raw ``str(e)`` survived every other test here
        (measured Session 261)."""
        exc = RuntimeError(f"gateway refused postgresql://user:{SECRET}@host/db\nretry later")
        with caplog.at_level(logging.WARNING, logger=DISCOVERY_LOGGER):
            probe_information_schema(
                _RowsDB(_three_rows()), llm=_Ranker(_raise(exc))  # type: ignore[arg-type]
            )
        assert SECRET not in caplog.text
        messages = [r.getMessage() for r in _discovery_warnings(caplog)]
        assert len(messages) == 1
        assert "gateway refused" in messages[0]  # redaction must not eat the cause
        assert "\n" not in messages[0]

    def test_unprintable_ranker_exception_still_keeps_the_entries(self) -> None:
        class Unprintable(Exception):
            def __str__(self) -> str:
                raise RuntimeError("broken __str__")

        inv = probe_information_schema(
            _RowsDB(_three_rows()), llm=_Ranker(_raise(Unprintable()))  # type: ignore[arg-type]
        )
        assert len(inv.entries) == 3
        assert (inv.producers[0].notes or "").startswith(
            f"{RANKING_FAILED_NOTE_PREFIX} (Unprintable)"
        )

    def test_failure_after_a_good_ranking_applies_nothing(self) -> None:
        """The bad element comes AFTER a good one, so a streaming apply would show.

        ⚠ Measured Session 261: against THIS implementation, which builds the
        whole ranking map before touching an entry, an apply-in-place mutant
        survives this test — the failure lands in the map. The test that kills
        that mutant is the invalid-score one below. This one guards the other
        design (apply as the rankings stream in), where bad-element-FIRST would
        fail before applying anything and pass."""

        def _behaviour(entries: list[DataSourceEntry]) -> Any:
            return [
                TableRanking(entries[0].fully_qualified_name, 0.9, "ok"),
                "not a ranking",
            ]

        inv = probe_information_schema(
            _RowsDB(_three_rows()), llm=_Ranker(_behaviour)  # type: ignore[arg-type]
        )
        assert [e.relevance_score for e in inv.entries] == [None, None, None]
        assert [e.relevance_reason for e in inv.entries] == [None, None, None]

    def test_ranker_mutating_its_input_then_failing_changes_nothing(self) -> None:
        """The ranker gets deep copies, so "entries are unranked" stays true."""

        def _behaviour(entries: list[DataSourceEntry]) -> Any:
            entries[0].relevance_score = 0.99
            # The NESTED mutation is what separates a deep copy from a shallow
            # ``model_copy()``, which shares the column objects (measured).
            entries[0].columns[0].name = "mutated"
            entries.clear()
            raise RuntimeError("failed after mutating in place")

        inv = probe_information_schema(
            _RowsDB(_three_rows()), llm=_Ranker(_behaviour)  # type: ignore[arg-type]
        )
        assert [e.relevance_score for e in inv.entries] == [None, None, None]
        assert [c.name for c in inv.entries[0].columns] == ["id"]

    def test_invalid_score_is_a_ranking_failure_not_an_invalid_inventory(self) -> None:
        """The bad score is on the LAST entry so a partial apply would show.

        ``model_copy(update=...)`` skips validation, and so does
        ``model_validate(<instance>)`` — validation must start from a dict."""

        def _behaviour(entries: list[DataSourceEntry]) -> Any:
            return [
                TableRanking(entries[0].fully_qualified_name, 0.9, "ok"),
                TableRanking(entries[-1].fully_qualified_name, "high", "bad"),  # type: ignore[arg-type]
            ]

        inv = probe_information_schema(
            _RowsDB(_three_rows()), llm=_Ranker(_behaviour)  # type: ignore[arg-type]
        )
        assert [e.relevance_score for e in inv.entries] == [None, None, None]
        assert (inv.producers[0].notes or "").startswith(
            f"{RANKING_FAILED_NOTE_PREFIX} (ValidationError)"
        )
        assert DataSourceInventory.model_validate_json(inv.model_dump_json()) == inv

    @pytest.mark.parametrize("exc_type", [KeyboardInterrupt, SystemExit])
    def test_base_exception_from_ranker_propagates(
        self, exc_type: type[BaseException]
    ) -> None:
        with pytest.raises(exc_type):
            probe_information_schema(
                _RowsDB(_three_rows()),  # type: ignore[arg-type]
                llm=_Ranker(_raise(exc_type())),
            )

    def test_successful_ranking_leaves_no_note_and_no_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        def _behaviour(entries: list[DataSourceEntry]) -> Any:
            return [TableRanking(e.fully_qualified_name, 0.5, "r") for e in entries]

        with caplog.at_level(logging.WARNING, logger=DISCOVERY_LOGGER):
            inv = probe_information_schema(
                _RowsDB(_three_rows()), llm=_Ranker(_behaviour)  # type: ignore[arg-type]
            )
        assert [e.relevance_score for e in inv.entries] == [0.5, 0.5, 0.5]
        assert inv.producers[0].notes is None
        assert _discovery_warnings(caplog) == []


AT = pytest.mark.parametrize("at", [0, 1, 2], ids=["bad-first", "bad-middle", "bad-last"])


def _one_scored(score: Any, *, at: int, reason: str = "r") -> Any:
    """A ranking of every entry in which only the entry at index ``at`` carries
    ``score`` (and ``reason``); the rest are good. The tests put the bad value
    in every position: last catches a ranking applied one entry at a time,
    first catches a check that runs once, after the loop, on the last entry
    only — a one-level dedent, which survived every test while the bad value
    was always last (measured Session 264)."""

    def _behaviour(entries: list[DataSourceEntry]) -> Any:
        return [
            TableRanking(e.fully_qualified_name, score, reason)
            if i == at
            else TableRanking(e.fully_qualified_name, 0.5, "ok")
            for i, e in enumerate(entries)
        ]

    return _behaviour


def _assert_unranked_with(inv: DataSourceInventory, type_name: str) -> None:
    assert [e.fully_qualified_name for e in inv.entries] == [
        "main.claims",
        "main.outcomes",
        "main.policies",
    ]
    assert [e.relevance_score for e in inv.entries] == [None, None, None]
    assert [e.relevance_reason for e in inv.entries] == [None, None, None]
    assert (inv.producers[0].notes or "").startswith(
        f"{RANKING_FAILED_NOTE_PREFIX} ({type_name}); all 3 entries are unranked."
    )


def _warning_of(caplog: pytest.LogCaptureFixture, behaviour: Any) -> str:
    with caplog.at_level(logging.WARNING, logger=DISCOVERY_LOGGER):
        probe_information_schema(
            _RowsDB(_three_rows()), llm=_Ranker(behaviour)  # type: ignore[arg-type]
        )
    messages = [r.getMessage() for r in _discovery_warnings(caplog)]
    assert len(messages) == 1
    return messages[0]


class TestRankingThatCannotBeApplied:
    """Stage 2 — a ranker that RETURNS, but with a ranking that cannot be applied.

    Filed Session 261, closed Session 264. Each failure case here raised nothing
    before Session 264, so the probe wrote ``notes=None`` and ``discover`` exited
    0 (measured). Each is now an ordinary ranking failure: all-or-nothing, the
    entries kept unranked, the note naming a type that says what went wrong.
    The tests named ``..._legal`` or ``..._never_checked`` pin what must NOT have
    changed with it.
    """

    @pytest.mark.parametrize(
        "behaviour",
        [
            lambda entries: [],
            lambda entries: iter(()),
            lambda entries: [TableRanking(e.name, 0.9, "r") for e in entries],
            lambda entries: [
                TableRanking(e.fully_qualified_name.upper(), 0.9, "r") for e in entries
            ],
            lambda entries: [TableRanking("main.invented", 0.9, "r")],
        ],
        ids=["empty-list", "empty-iterator", "bare-names", "case-differs", "invented-only"],
    )
    def test_a_ranking_that_names_no_entry_is_a_failure(self, behaviour: Any) -> None:
        """``anthropic_client.py`` sends the prompt only the top 20 entries by
        score, so above 20 tables an unranked inventory can drop the relevant
        one — and nothing said the ranking had not been applied."""
        inv = probe_information_schema(
            _RowsDB(_three_rows()), llm=_Ranker(behaviour)  # type: ignore[arg-type]
        )
        _assert_unranked_with(inv, "RankingMatchedNoEntryError")

    def test_the_no_match_warning_shows_what_was_returned_and_what_was_expected(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The note carries the type only; the WARNING is where the operator sees
        that ``claims`` came back for ``main.claims``."""
        message = _warning_of(
            caplog, lambda entries: [TableRanking(e.name, 0.9, "r") for e in entries]
        )
        assert "'claims'" in message
        assert "'main.claims'" in message

    def test_the_no_match_warning_is_bounded_however_long_the_reply(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The quoted names come from the model and the WARNING is logged whole,
        so both how many names and how long each one is are capped."""
        invented = [f"main.invented_{i}_" + "x" * 5_000 for i in range(50)]
        message = _warning_of(
            caplog, lambda entries: [TableRanking(n, 0.9, "r") for n in invented]
        )
        assert "50 distinct name(s) returned" in message
        assert "invented_2_" in message
        assert "invented_3_" not in message
        assert len(message) < 1_000

    def test_a_partial_ranking_with_invented_names_is_still_legal(self) -> None:
        """Partial rankings stay legal: matching ONE entry is enough, and a name
        that matches nothing is ignored, as it always was."""

        def _behaviour(entries: list[DataSourceEntry]) -> Any:
            return [
                TableRanking("main.invented", 0.9, "not a real table"),
                TableRanking(entries[1].fully_qualified_name, 0.7, "real"),
            ]

        inv = probe_information_schema(
            _RowsDB(_three_rows()), llm=_Ranker(_behaviour)  # type: ignore[arg-type]
        )
        assert inv.producers[0].notes is None
        assert [e.relevance_score for e in inv.entries] == [None, 0.7, None]

    @AT
    @pytest.mark.parametrize(
        "score",
        [
            float("nan"),
            float("inf"),
            float("-inf"),
            7.5,
            -1.0,
            1.0000001,
            -0.0000001,
            None,
            "nan",
        ],
        ids=[
            "nan",
            "inf",
            "minus-inf",
            "wrong-scale",
            "negative",
            "just-above-one",
            "just-below-zero",
            "none",
            "nan-as-text",
        ],
    )
    def test_a_score_that_is_not_a_finite_number_in_0_1_is_a_failure(
        self, score: Any, at: int
    ) -> None:
        """Operator ruling, Session 264: reject, never clamp. A reply on the wrong
        scale (0-10) would clamp to all 1.0 and lose the order ranking exists
        for. ``NaN`` also defeated the prompt's sort outright — five entries
        scored ``[0.1, nan, 0.9, 0.5, 0.2]`` came back in input order (measured).
        The shipped client hands over a float, so its ``NaN`` is the ``nan``
        case (see the end-to-end test below); ``nan-as-text`` is a duck-typed
        ranker's string, which pydantic's lax float coercion turns into ``nan``
        — checking the VALIDATED score is what catches it."""
        inv = probe_information_schema(
            _RowsDB(_three_rows()), llm=_Ranker(_one_scored(score, at=at))  # type: ignore[arg-type]
        )
        _assert_unranked_with(inv, "InvalidRelevanceScoreError")

    def test_the_bad_score_warning_names_the_value_and_the_table(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The note carries the type only, so this WARNING is the operator's one
        record of which table was given which score."""
        message = _warning_of(caplog, _one_scored(7.5, at=1))
        assert "relevance_score 7.5 for 'main.outcomes'" in message

    @pytest.mark.parametrize("score", [0.0, 1.0], ids=["zero", "one"])
    def test_the_bounds_themselves_are_legal(self, score: float) -> None:
        inv = probe_information_schema(
            _RowsDB(_three_rows()), llm=_Ranker(_one_scored(score, at=2))  # type: ignore[arg-type]
        )
        assert inv.producers[0].notes is None
        assert [e.relevance_score for e in inv.entries] == [0.5, 0.5, score]

    def test_a_bad_score_on_an_invented_name_is_never_applied_so_never_checked(
        self,
    ) -> None:
        """The check is on APPLIED scores: a ranking for a table that does not
        exist is ignored whole, exactly as the partial-ranking rule ignores it."""

        def _behaviour(entries: list[DataSourceEntry]) -> Any:
            return [TableRanking(e.fully_qualified_name, 0.5, "r") for e in entries] + [
                TableRanking("main.invented", float("nan"), "r")
            ]

        inv = probe_information_schema(
            _RowsDB(_three_rows()), llm=_Ranker(_behaviour)  # type: ignore[arg-type]
        )
        assert inv.producers[0].notes is None
        assert [e.relevance_score for e in inv.entries] == [0.5, 0.5, 0.5]

    @AT
    def test_a_reason_that_cannot_be_written_is_a_failure_and_the_file_reloads(
        self, at: int
    ) -> None:
        """A reply cut inside an escaped emoji pair (``"…\\ud83d"``) passes
        ``_extract_json`` and schema validation. Until Session 264 the file was
        written with exit 0 and then refused to reload (measured)."""
        inv = probe_information_schema(
            _RowsDB(_three_rows()),  # type: ignore[arg-type]
            llm=_Ranker(_one_scored(0.5, at=at, reason="cut mid-emoji \ud83d")),
        )
        _assert_unranked_with(inv, "UnwritableEntryError")
        assert DataSourceInventory.model_validate_json(inv.model_dump_json()) == inv

    def test_the_unwritable_reason_warning_names_the_table(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        message = _warning_of(caplog, _one_scored(0.5, at=1, reason="cut \ud83d"))
        assert "UnwritableEntryError: entry 'main.outcomes' cannot be written" in message


class _CannedAnthropic:
    """The Anthropic SDK's ``messages.create``, answering with one canned text."""

    def __init__(self, text: str) -> None:
        self.messages = self
        self._text = text

    def create(self, **kwargs: Any) -> Any:
        return type("R", (), {"content": [TextBlock(text=self._text, type="text")]})()


@pytest.mark.parametrize(
    ("reply", "type_name"),
    [
        ('[{"fully_qualified_name": "main.claims", "relevance_score": NaN, '
         '"relevance_reason": "r"}]', "InvalidRelevanceScoreError"),
        ('[{"fully_qualified_name": "main.claims", "relevance_score": "Infinity", '
         '"relevance_reason": "r"}]', "InvalidRelevanceScoreError"),
        ('[{"fully_qualified_name": "main.claims", "relevance_score": 9, '
         '"relevance_reason": "r"}]', "InvalidRelevanceScoreError"),
        ('[{"fully_qualified_name": "claims", "relevance_score": 0.9, '
         '"relevance_reason": "r"}]', "RankingMatchedNoEntryError"),
        ('[{"fully_qualified_name": "main.claims", "relevance_score": 0.9, '
         '"relevance_reason": "cut \\ud83d"}]', "UnwritableEntryError"),
    ],
    ids=["bare-NaN", "Infinity-as-text", "wrong-scale", "bare-name", "escaped-surrogate"],
)
def test_the_shipped_client_reply_reaches_the_same_failures(
    reply: str, type_name: str
) -> None:
    """End to end through ``AnthropicLLMClient.rank_candidate_tables``: every
    reply above is one the shipped client accepts — ``_extract_json`` parses a
    bare ``NaN`` and ``float()`` parses ``"Infinity"`` — so the checks in
    ``_ranked`` are what stand between it and the file."""
    llm = AnthropicLLMClient(client=_CannedAnthropic(reply), model="fake-model")  # type: ignore[arg-type]
    inv = probe_information_schema(_RowsDB([GOOD_ROW]), llm=llm)  # type: ignore[arg-type]
    assert [e.relevance_score for e in inv.entries] == [None]
    assert (inv.producers[0].notes or "").startswith(
        f"{RANKING_FAILED_NOTE_PREFIX} ({type_name}); all 1 entries are unranked."
    )
