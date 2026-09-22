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
from model_project_constructor_data_agent import (
    DataSourceInventory,
    ReadOnlyDB,
    TableRanking,
    probe_information_schema,
)
from model_project_constructor_data_agent.anthropic_client import LLMParseError
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
        """LLM ranking is skipped when there are no entries (saves an LLM call)."""
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
