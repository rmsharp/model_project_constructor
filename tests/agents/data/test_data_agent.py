"""End-to-end tests for the Data Agent flow.

The FakeLLMClient is deterministic: ``primary_queries_sequence`` is a
list of responses returned in order on consecutive calls. Providing more
than one entry exercises the RETRY_ONCE branch (first call invalid,
second valid); providing two invalid entries exercises the
EXECUTION_FAILED branch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest
from model_project_constructor_data_agent.llm import BaselineQuerySpec

from model_project_constructor.agents.data import DataAgent, LLMClient
from model_project_constructor.agents.data.db import DBConnectionError, ReadOnlyDB
from model_project_constructor.agents.data.llm import (
    PrimaryQuerySpec,
    QualityCheckSpec,
    SummaryResult,
)
from model_project_constructor.schemas.v1.data import (
    DataReport,
    DataRequest,
    Datasheet,
    DataSourceInventory,
    QualityCheck,
)
from tests.hostile_text import (
    CONNECT_CAUSE,
    ESCAPE_NAME,
    ESCAPE_NAME_SCRUBBED,
    ESCAPING_URL,
    EVERY_CONTROL,
    SECRET,
    SECRET_NAME,
    NameThatIsAHostileStr,
    NameThatRaises,
    database_with_a_dangling_view,
    leaked_run,
    unsafe,
)


@dataclass
class FakeLLMClient:
    """Deterministic stand-in for a real LLM integration."""

    primary_queries_sequence: list[list[PrimaryQuerySpec]]
    qc_response: list[list[QualityCheckSpec]]
    summary_response: SummaryResult
    datasheet_response: Datasheet
    generate_primary_calls: int = field(default=0, init=False)
    summarize_calls: int = field(default=0, init=False)
    last_summarize_db_executed: bool | None = field(default=None, init=False)

    def generate_primary_queries(
        self,
        request: DataRequest,
        previous_error: str | None = None,
        *,
        data_source_inventory: DataSourceInventory | None = None,
    ) -> list[PrimaryQuerySpec]:
        idx = min(
            self.generate_primary_calls,
            len(self.primary_queries_sequence) - 1,
        )
        self.generate_primary_calls += 1
        return self.primary_queries_sequence[idx]

    def generate_quality_checks(
        self,
        request: DataRequest,
        primary_queries: list[PrimaryQuerySpec],
    ) -> list[list[QualityCheckSpec]]:
        if not self.qc_response:
            return [[] for _ in primary_queries]
        if len(self.qc_response) == len(primary_queries):
            return self.qc_response
        return [self.qc_response[0] for _ in primary_queries]

    def summarize(
        self,
        request: DataRequest,
        primary_queries: list[PrimaryQuerySpec],
        quality_checks: list[list[QualityCheck]],
        db_executed: bool,
    ) -> SummaryResult:
        self.summarize_calls += 1
        self.last_summarize_db_executed = db_executed
        return self.summary_response

    def generate_datasheet(
        self, request: DataRequest, primary_query: PrimaryQuerySpec
    ) -> Datasheet:
        return self.datasheet_response

    def generate_baseline_query(
        self,
        request: DataRequest,
        metric_name: str,
        metric_definition: str,
        measurement_window: str,
    ) -> BaselineQuerySpec:
        return BaselineQuerySpec(
            metric_name=metric_name,
            sql=f"SELECT AVG(paid_amount) AS {metric_name} FROM claims",
            measurement_unit="USD",
        )


def test_fake_llm_client_implements_protocol(
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    fake = FakeLLMClient(
        primary_queries_sequence=[[primary_query_spec_valid]],
        qc_response=[qc_specs_valid],
        summary_response=summary_response,
        datasheet_response=datasheet_response,
    )
    assert isinstance(fake, LLMClient)


def test_happy_path_against_seeded_sqlite(
    seeded_db: ReadOnlyDB,
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    fake = FakeLLMClient(
        primary_queries_sequence=[[primary_query_spec_valid]],
        qc_response=[qc_specs_valid],
        summary_response=summary_response,
        datasheet_response=datasheet_response,
    )
    agent = DataAgent(llm=fake, db=seeded_db)

    report = agent.run(sample_request)

    assert report.status == "COMPLETE"
    assert report.request == sample_request
    assert len(report.primary_queries) == 1

    pq = report.primary_queries[0]
    assert pq.name == "tx_claims_2024"
    assert len(pq.quality_checks) == 2
    # row_count_nonempty should have returned one row with the count ⇒ PASSED
    row_count_check = next(
        c for c in pq.quality_checks if c.check_name == "row_count_nonempty"
    )
    assert row_count_check.execution_status == "PASSED"
    assert row_count_check.raw_result is not None
    assert row_count_check.raw_result["row_count"] == 1
    # no_negative_paid_amount returns zero rows ⇒ FAILED in our Phase 2A proxy
    neg_check = next(
        c for c in pq.quality_checks if c.check_name == "no_negative_paid_amount"
    )
    assert neg_check.execution_status == "FAILED"
    assert neg_check.raw_result is not None
    assert neg_check.raw_result["row_count"] == 0

    assert pq.datasheet == datasheet_response
    assert fake.summarize_calls == 1
    assert fake.last_summarize_db_executed is True
    assert "database unreachable" not in " ".join(report.data_quality_concerns)


def test_retry_once_then_success(
    seeded_db: ReadOnlyDB,
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    bad = PrimaryQuerySpec(
        name="bad_first_attempt",
        sql="   ",
        purpose="intentionally invalid to exercise RETRY_ONCE",
        expected_row_count_order="thousands",
    )
    fake = FakeLLMClient(
        primary_queries_sequence=[[bad], [primary_query_spec_valid]],
        qc_response=[qc_specs_valid],
        summary_response=summary_response,
        datasheet_response=datasheet_response,
    )
    agent = DataAgent(llm=fake, db=seeded_db)

    report = agent.run(sample_request)

    assert report.status == "COMPLETE"
    assert fake.generate_primary_calls == 2
    assert report.primary_queries[0].name == "tx_claims_2024"


def test_fail_after_retry_exhausted(
    seeded_db: ReadOnlyDB,
    sample_request: DataRequest,
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    bad_a = PrimaryQuerySpec(
        name="still_bad_a",
        sql="",
        purpose="empty",
        expected_row_count_order="tens",
    )
    bad_b = PrimaryQuerySpec(
        name="still_bad_b",
        sql="   \n\t",
        purpose="whitespace-only",
        expected_row_count_order="tens",
    )
    fake = FakeLLMClient(
        primary_queries_sequence=[[bad_a], [bad_b]],
        qc_response=[],
        summary_response=summary_response,
        datasheet_response=datasheet_response,
    )
    agent = DataAgent(llm=fake, db=seeded_db)

    report = agent.run(sample_request)

    assert report.status == "EXECUTION_FAILED"
    assert report.primary_queries == []
    assert "invalid SQL" in report.summary
    assert fake.generate_primary_calls == 2  # original + one retry


def test_db_unreachable_sets_qc_not_executed(
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    unreachable = ReadOnlyDB("sqlite:////nonexistent/path/does/not/exist.db")

    fake = FakeLLMClient(
        primary_queries_sequence=[[primary_query_spec_valid]],
        qc_response=[qc_specs_valid],
        summary_response=summary_response,
        datasheet_response=datasheet_response,
    )
    agent = DataAgent(llm=fake, db=unreachable)

    report = agent.run(sample_request)

    assert report.status == "COMPLETE"
    assert fake.last_summarize_db_executed is False
    assert any(
        "database unreachable" in c for c in report.data_quality_concerns
    )
    # Every QC should still be in NOT_EXECUTED state
    for qc in report.primary_queries[0].quality_checks:
        assert qc.execution_status == "NOT_EXECUTED"


def test_db_unreachable_when_db_is_none(
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    fake = FakeLLMClient(
        primary_queries_sequence=[[primary_query_spec_valid]],
        qc_response=[qc_specs_valid],
        summary_response=summary_response,
        datasheet_response=datasheet_response,
    )
    agent = DataAgent(llm=fake, db=None)

    report = agent.run(sample_request)

    assert report.status == "COMPLETE"
    for qc in report.primary_queries[0].quality_checks:
        assert qc.execution_status == "NOT_EXECUTED"


def test_per_qc_error_is_isolated(
    seeded_db: ReadOnlyDB,
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    ok_check = QualityCheckSpec(
        check_name="ok_check",
        check_sql="SELECT COUNT(*) FROM claims",
        expectation="claims table has rows",
    )
    broken_check = QualityCheckSpec(
        check_name="broken_check",
        check_sql="SELECT * FROM no_such_table_at_all",
        expectation="will raise because table does not exist",
    )
    fake = FakeLLMClient(
        primary_queries_sequence=[[primary_query_spec_valid]],
        qc_response=[[ok_check, broken_check]],
        summary_response=summary_response,
        datasheet_response=datasheet_response,
    )
    agent = DataAgent(llm=fake, db=seeded_db)

    report = agent.run(sample_request)

    assert report.status == "COMPLETE"
    qcs = report.primary_queries[0].quality_checks
    ok = next(c for c in qcs if c.check_name == "ok_check")
    broken = next(c for c in qcs if c.check_name == "broken_check")
    assert ok.execution_status == "PASSED"
    assert broken.execution_status == "ERROR"
    assert "no_such_table_at_all" in broken.result_summary


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    [
        ("target_description", ""),
        ("required_features", []),
        ("population_filter", "   "),
        ("time_range", ""),
    ],
)
def test_incomplete_request_short_circuits(
    field_name: str,
    replacement: object,
    sample_request: DataRequest,
    seeded_db: ReadOnlyDB,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    bad_request = sample_request.model_copy(update={field_name: replacement})
    fake = FakeLLMClient(
        primary_queries_sequence=[[primary_query_spec_valid]],
        qc_response=[qc_specs_valid],
        summary_response=summary_response,
        datasheet_response=datasheet_response,
    )
    agent = DataAgent(llm=fake, db=seeded_db)

    report = agent.run(bad_request)

    assert report.status == "INCOMPLETE_REQUEST"
    assert report.primary_queries == []
    assert any(
        field_name in concern for concern in report.data_quality_concerns
    )
    # Short-circuit: LLM must never be invoked.
    assert fake.generate_primary_calls == 0


def test_unexpected_exception_surfaces_as_execution_failed(
    seeded_db: ReadOnlyDB,
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    class ExplodingLLM(FakeLLMClient):
        def generate_primary_queries(
            self,
            request: DataRequest,
            previous_error: str | None = None,
            *,
            data_source_inventory: DataSourceInventory | None = None,
        ) -> list[PrimaryQuerySpec]:
            raise RuntimeError("simulated internal crash")

    fake = ExplodingLLM(
        primary_queries_sequence=[[primary_query_spec_valid]],
        qc_response=[qc_specs_valid],
        summary_response=summary_response,
        datasheet_response=datasheet_response,
    )
    agent = DataAgent(llm=fake, db=seeded_db)

    report = agent.run(sample_request)

    # The class and not the message: see "Session 279" at the end of this file.
    assert report.status == "EXECUTION_FAILED"
    assert report.summary == "Data Agent run failed: graph crashed: RuntimeError"
    assert report.data_quality_concerns == ["graph crashed: RuntimeError"]
    assert "simulated internal crash" not in report.model_dump_json()


def test_inventory_entries_used_plumbed_end_to_end(
    seeded_db: ReadOnlyDB,
    sample_request: DataRequest,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    """End-to-end Phase 3 plumbing: inventory → prompt → report provenance.

    An inventory-aware FakeLLMClient seeds ``inventory_entries_used`` on the
    PrimaryQuerySpec it returns; the Data Agent assembles the final report
    with the list carried through to :class:`PrimaryQuery`. Pins the
    consumer-integration invariant in plan §11 without requiring a live LLM.
    """
    from datetime import UTC, datetime

    from model_project_constructor.schemas.v1.data import (
        DataSourceEntry,
        DataSourceInventory,
        ProducerMetadata,
    )

    produced_at = datetime.now(UTC)
    inventory = DataSourceInventory(
        entries=[
            DataSourceEntry(
                name="claims",
                namespace="public",
                fully_qualified_name="public.claims",
                entity_kind="table",
                producer_id="test_producer_v1",
            )
        ],
        producers=[
            ProducerMetadata(
                producer_id="test_producer_v1",
                producer_type="curated",
                produced_at=produced_at,
            )
        ],
        created_at=produced_at,
    )
    request_with_inventory = sample_request.model_copy(
        update={"data_source_inventory": inventory}
    )
    inventory_aware_spec = PrimaryQuerySpec(
        name="tx_claims_2024",
        sql=(
            "SELECT claim_id, paid_amount, subro_recovered FROM claims "
            "WHERE state = 'TX'"
        ),
        purpose="Training set for TX subrogation recovery classifier",
        expected_row_count_order="thousands",
        inventory_entries_used=["public.claims"],
    )

    captured: dict[str, DataSourceInventory | None] = {"inv": None}

    class InventoryAwareFake(FakeLLMClient):
        def generate_primary_queries(
            self,
            request: DataRequest,
            previous_error: str | None = None,
            *,
            data_source_inventory: DataSourceInventory | None = None,
        ) -> list[PrimaryQuerySpec]:
            captured["inv"] = data_source_inventory
            self.generate_primary_calls += 1
            return [inventory_aware_spec]

    fake = InventoryAwareFake(
        primary_queries_sequence=[[inventory_aware_spec]],
        qc_response=[qc_specs_valid],
        summary_response=summary_response,
        datasheet_response=datasheet_response,
    )
    agent = DataAgent(llm=fake, db=seeded_db)

    report = agent.run(request_with_inventory)

    assert report.status == "COMPLETE"
    assert captured["inv"] is inventory
    assert report.primary_queries[0].inventory_entries_used == ["public.claims"]
    assert report.request.data_source_inventory is inventory


def test_inventory_entries_used_defaults_empty_when_inventory_absent(
    seeded_db: ReadOnlyDB,
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    """Pre-Phase-3 callers that never set inventory see ``[]`` on the output.

    Backward-compat: the baseline ``primary_query_spec_valid`` fixture does
    not set ``inventory_entries_used``; the field must default to ``[]`` on
    the assembled :class:`PrimaryQuery` without any caller-side opt-in.
    """
    fake = FakeLLMClient(
        primary_queries_sequence=[[primary_query_spec_valid]],
        qc_response=[qc_specs_valid],
        summary_response=summary_response,
        datasheet_response=datasheet_response,
    )
    agent = DataAgent(llm=fake, db=seeded_db)

    report = agent.run(sample_request)

    assert report.status == "COMPLETE"
    assert report.primary_queries[0].inventory_entries_used == []
    assert report.request.data_source_inventory is None


# ---------------------------------------------------------------------------
# Phase 3 — baseline collection (business-value-capture-plan.md §5 Phase 3)
# ---------------------------------------------------------------------------


def _request_with_baseline(sample_request: DataRequest) -> DataRequest:
    return sample_request.model_copy(
        update={
            "baseline_metric_name": "subro_recovery_rate",
            "baseline_metric_definition": (
                "Average paid_amount across all claims in the population."
            ),
            "baseline_measurement_window": "trailing 12 months",
        }
    )


def test_baseline_collection_executed_when_plan_and_db_present(
    seeded_db: ReadOnlyDB,
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    """Plan present + DB reachable → snapshot has EXECUTED status + numeric value."""
    fake = FakeLLMClient(
        primary_queries_sequence=[[primary_query_spec_valid]],
        qc_response=[qc_specs_valid],
        summary_response=summary_response,
        datasheet_response=datasheet_response,
    )
    agent = DataAgent(llm=fake, db=seeded_db)

    report = agent.run(_request_with_baseline(sample_request))

    assert report.status == "COMPLETE"
    assert report.baseline_snapshot is not None
    assert report.baseline_snapshot.metric_name == "subro_recovery_rate"
    assert report.baseline_snapshot.query_execution_status == "EXECUTED"
    assert report.baseline_snapshot.value is not None
    # Seeded fixture has 5 rows with paid_amount {5000, 8000, 2500, 15000, 6200};
    # avg = 7340.0
    assert report.baseline_snapshot.value == 7340.0
    assert report.baseline_snapshot.measurement_unit == "USD"
    assert report.baseline_snapshot.caveats == []


def test_baseline_collection_skipped_when_no_plan(
    seeded_db: ReadOnlyDB,
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    """No baseline_metric_definition on the request → baseline_snapshot is None."""
    fake = FakeLLMClient(
        primary_queries_sequence=[[primary_query_spec_valid]],
        qc_response=[qc_specs_valid],
        summary_response=summary_response,
        datasheet_response=datasheet_response,
    )
    agent = DataAgent(llm=fake, db=seeded_db)

    report = agent.run(sample_request)

    assert report.status == "COMPLETE"
    assert report.baseline_snapshot is None


def test_baseline_collection_not_executed_when_db_unreachable(
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    """Plan present but DB unreachable → snapshot status NOT_EXECUTED, SQL preserved."""
    unreachable = ReadOnlyDB("sqlite:////nonexistent/path/baseline.db")
    fake = FakeLLMClient(
        primary_queries_sequence=[[primary_query_spec_valid]],
        qc_response=[qc_specs_valid],
        summary_response=summary_response,
        datasheet_response=datasheet_response,
    )
    agent = DataAgent(llm=fake, db=unreachable)

    report = agent.run(_request_with_baseline(sample_request))

    assert report.status == "COMPLETE"
    assert report.baseline_snapshot is not None
    assert report.baseline_snapshot.query_execution_status == "NOT_EXECUTED"
    assert report.baseline_snapshot.value is None
    assert "subro_recovery_rate" in report.baseline_snapshot.query_sql
    assert any(
        "database not reachable" in c for c in report.baseline_snapshot.caveats
    )


def test_baseline_collection_failed_on_sql_error(
    seeded_db: ReadOnlyDB,
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    """LLM returns SQL against a missing table → fail-the-snapshot, not the graph."""

    class BadBaselineSQLClient(FakeLLMClient):
        def generate_baseline_query(
            self,
            request: DataRequest,
            metric_name: str,
            metric_definition: str,
            measurement_window: str,
        ) -> BaselineQuerySpec:
            return BaselineQuerySpec(
                metric_name=metric_name,
                sql="SELECT AVG(x) FROM table_that_does_not_exist",
                measurement_unit="USD",
            )

    fake = BadBaselineSQLClient(
        primary_queries_sequence=[[primary_query_spec_valid]],
        qc_response=[qc_specs_valid],
        summary_response=summary_response,
        datasheet_response=datasheet_response,
    )
    agent = DataAgent(llm=fake, db=seeded_db)

    report = agent.run(_request_with_baseline(sample_request))

    # Fail-the-snapshot, not fail-the-graph (Session 88 Phase 1A resolution).
    assert report.status == "COMPLETE"
    assert report.baseline_snapshot is not None
    assert report.baseline_snapshot.query_execution_status == "FAILED"
    assert report.baseline_snapshot.value is None
    assert any(
        "table_that_does_not_exist" in c for c in report.baseline_snapshot.caveats
    )


def test_baseline_collection_failed_on_llm_error(
    seeded_db: ReadOnlyDB,
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    """LLM raises during baseline-query generation → fail-the-snapshot."""

    class ExplodingBaselineClient(FakeLLMClient):
        def generate_baseline_query(
            self,
            request: DataRequest,
            metric_name: str,
            metric_definition: str,
            measurement_window: str,
        ) -> BaselineQuerySpec:
            raise RuntimeError("simulated baseline LLM crash")

    fake = ExplodingBaselineClient(
        primary_queries_sequence=[[primary_query_spec_valid]],
        qc_response=[qc_specs_valid],
        summary_response=summary_response,
        datasheet_response=datasheet_response,
    )
    agent = DataAgent(llm=fake, db=seeded_db)

    report = agent.run(_request_with_baseline(sample_request))

    assert report.status == "COMPLETE"
    assert report.baseline_snapshot is not None
    assert report.baseline_snapshot.query_execution_status == "FAILED"
    assert report.baseline_snapshot.value is None
    assert report.baseline_snapshot.query_sql == ""
    # The class and not the message: see "Session 279" at the end of this file.
    assert report.baseline_snapshot.caveats == [
        "LLM baseline-query generation failed: RuntimeError"
    ]
    assert "simulated baseline LLM crash" not in report.model_dump_json()


# ---------------------------------------------------------------------------
# Session 260 — the report tells the operator WHICH failure happened.
#
# Before this session the concern was a fixed string, so a typo'd port, an
# unexported shell variable and a genuine warehouse outage produced reports
# that were byte-identical modulo ``created_at``. These are the tests that make
# option (a) mean something rather than merely run.
# ---------------------------------------------------------------------------


def _run_with_db(
    db: ReadOnlyDB | None,
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> object:
    fake = FakeLLMClient(
        primary_queries_sequence=[[primary_query_spec_valid]],
        qc_response=[qc_specs_valid],
        summary_response=summary_response,
        datasheet_response=datasheet_response,
    )
    return DataAgent(llm=fake, db=db).run(sample_request)


def test_two_different_db_failures_produce_different_concerns(
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    """The discriminator. This is the whole point of the item.

    It is also the only guard on ``db_error`` being declared in
    ``DataAgentState``: langgraph silently DROPS a node return key that the
    schema does not declare, so removing that declaration makes both concerns
    collapse back to the canned string and only this test notices.
    """
    args = (
        sample_request,
        primary_query_spec_valid,
        qc_specs_valid,
        summary_response,
        datasheet_response,
    )
    bad_port = _run_with_db(
        ReadOnlyDB("postgresql://user:pw@warehouse.internal:$DB_PORT/claims"), *args
    )
    unreachable = _run_with_db(
        ReadOnlyDB("sqlite:////nonexistent/path/does/not/exist.db"), *args
    )

    assert bad_port.data_quality_concerns != unreachable.data_quality_concerns
    assert any(
        "invalid literal for int()" in c for c in bad_port.data_quality_concerns
    )
    assert any(
        "unable to open database file" in c
        for c in unreachable.data_quality_concerns
    )
    # The canned prefix is kept, not replaced — every existing assertion on it
    # stays meaningful, and so does docs/tutorial.md's description.
    for report in (bad_port, unreachable):
        assert any(
            "database unreachable at QC execution time" in c
            for c in report.data_quality_concerns
        )


def test_the_concern_stays_one_line(
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    """SQLAlchemy appends a help URL after a newline on every ``DBAPIError``.

    A concern renders as a single markdown bullet in the generated project's
    ``reports/data_report.md``, so an unflattened one produces a bare
    continuation line there.
    """
    report = _run_with_db(
        ReadOnlyDB("sqlite:////nonexistent/path/does/not/exist.db"),
        sample_request,
        primary_query_spec_valid,
        qc_specs_valid,
        summary_response,
        datasheet_response,
    )

    assert all("\n" not in c for c in report.data_quality_concerns)


def test_the_report_never_carries_the_db_password(
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    """Asserted over the WHOLE serialized report, not just the concerns list.

    ``data_quality_concerns`` is rendered into ``reports/data_report.json`` and
    ``.md`` in the generated project, written to the ``--output`` path and put
    in the checkpoint envelope — so this string is published, not just logged.
    """
    import json

    secret = "hunter2"
    for url in (
        f"postgresql://user:{secret}@warehouse.internal:$DB_PORT/claims",
        f"postgresql://warehouse.internal:5432/claims?password={secret}",
    ):
        report = _run_with_db(
            ReadOnlyDB(url),
            sample_request,
            primary_query_spec_valid,
            qc_specs_valid,
            summary_response,
            datasheet_response,
        )
        assert secret not in json.dumps(report.model_dump(mode="json"))


def test_no_db_url_keeps_the_canned_concern_alone(
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    """``db is None`` raises nothing, so there is no cause to append.

    The mechanical detector for the design trap: if a later change makes
    ``db_error`` unconditional, this path would start claiming a connection
    failure that never happened.
    """
    report = _run_with_db(
        None,
        sample_request,
        primary_query_spec_valid,
        qc_specs_valid,
        summary_response,
        datasheet_response,
    )

    assert (
        "database unreachable at QC execution time; quality checks not executed"
        in report.data_quality_concerns
    )


# ---------------------------------------------------------------------------
# Session 270 — database and driver text never reaches the report raw.
#
# ``BACKLOG.md``, *Seven more routes ...*, routes 2 and 3. Everything below lands in
# ``data_quality_concerns``, a quality check's ``result_summary`` or a baseline's
# ``caveats``, which ``templates.py`` writes into the generated project's committed
# markdown and the report JSON, and which the summarise prompt also reads. Each of the
# three sites is its own call, so each has its own test: a site that goes back to a raw
# ``f"{e}"`` leaves the others green.
# ---------------------------------------------------------------------------


class _RawConnectErrorDB(ReadOnlyDB):
    """A database whose connect fails with text this package did not build, as a
    subclass, a wrapper or a later change could raise ``DBConnectionError``."""

    def connect(self) -> None:
        raise DBConnectionError(f"cannot connect: {CONNECT_CAUSE} {EVERY_CONTROL} end")


class _RawExecuteErrorDB(ReadOnlyDB):
    """A database that connects and then fails every statement with raw driver text."""

    def __init__(self, message: str) -> None:
        super().__init__("sqlite:///unused.db")
        self._message = message

    def connect(self) -> None:
        return None

    def execute(self, sql: str) -> list[dict[str, object]]:
        raise RuntimeError(self._message)


def _run_with(
    db: ReadOnlyDB,
    request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> object:
    fake = FakeLLMClient(
        primary_queries_sequence=[[primary_query_spec_valid]],
        qc_response=[qc_specs_valid],
        summary_response=summary_response,
        datasheet_response=datasheet_response,
    )
    return DataAgent(llm=fake, db=db).run(request)


def test_the_unreachable_database_concern_carries_no_control_character(
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    """Route 2, through the real connect error. ``agent.py`` flattened it with
    ``' '.join(str(db_error).split())``, which removes whitespace only, so the ESC and
    BEL of a driver's quoted role name reached the report (2 ESC and 1 BEL measured)."""
    report = _run_with(
        ReadOnlyDB(ESCAPING_URL),
        sample_request,
        primary_query_spec_valid,
        qc_specs_valid,
        summary_response,
        datasheet_response,
    )

    (concern,) = [c for c in report.data_quality_concerns if "database unreachable" in c]
    assert unsafe(concern) == []
    assert "\n" not in concern
    assert f'FATAL: role "{ESCAPE_NAME_SCRUBBED}" does not exist' in concern
    assert SECRET not in concern


def test_the_unreachable_database_concern_cleans_text_it_was_handed_raw(
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    """The report is where the text is written, so its control characters are replaced
    there too, not only where ``ReadOnlyDB.connect`` builds it: swapping ``agent.py``'s
    call for the old flatten survives the test above, because the connect error is
    already clean. It does not mask secrets again (``redact=False``): ``connect`` did,
    and the masker mangles a message composed from text it already cleaned."""
    report = _run_with(
        _RawConnectErrorDB("sqlite:///unused.db"),
        sample_request,
        primary_query_spec_valid,
        qc_specs_valid,
        summary_response,
        datasheet_response,
    )

    (concern,) = [c for c in report.data_quality_concerns if "database unreachable" in c]
    assert unsafe(concern) == []
    assert concern.startswith(
        "database unreachable at QC execution time; quality checks not executed: "
        "cannot connect: FATAL: role "
    )
    assert concern.endswith(" end")


@pytest.mark.parametrize(
    ("url", "kept"),
    [
        ("fakeesc:///x?password=hunter2", "password=***': (sqlite3.OperationalError) FATAL:"),
        (
            "sqlite:////nonexistent_dir/secret",
            "secret': (sqlite3.OperationalError) unable to open database file",
        ),
    ],
    ids=["url-ends-in-a-password-parameter", "path-ends-in-a-key-word"],
)
def test_the_unreachable_database_concern_keeps_the_diagnostic_whole(
    url: str,
    kept: str,
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    """Session 270 review: running the full ``safe_message`` over the composed connect
    message made the masker eat the ``':`` after a URL ending in ``password=***`` and the
    exception type after a path ending in a key word, where the old plain flatten kept the
    text intact. ``agent.py`` replaces control characters and flattens, and leaves the
    redaction to ``connect``."""
    report = _run_with(
        ReadOnlyDB(url),
        sample_request,
        primary_query_spec_valid,
        qc_specs_valid,
        summary_response,
        datasheet_response,
    )

    (concern,) = [c for c in report.data_quality_concerns if "database unreachable" in c]
    assert kept in concern
    assert SECRET not in concern


def test_a_quality_check_error_carries_no_control_character_or_secret(
    tmp_path: Path,
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    """Route 3, ``nodes.py``'s ``execute_qc``: ``f"execution error: {e}"`` was the whole
    driver exception, neither redacted nor flattened nor scrubbed. A real SQLite file in
    which ``claims`` is a view over a dropped table quotes that table's NAME in the error,
    so a hostile name reaches ``result_summary`` (2 ESC and 1 BEL measured, and a
    newline)."""
    for n, (name, scrubbed) in enumerate(
        [
            (ESCAPE_NAME, ESCAPE_NAME_SCRUBBED),
            (SECRET_NAME, "cfg PWD=***;Database=claims"),
        ]
    ):
        url = database_with_a_dangling_view(tmp_path / f"{n}.db", name)
        report = _run_with(
            ReadOnlyDB(url),
            sample_request,
            primary_query_spec_valid,
            qc_specs_valid,
            summary_response,
            datasheet_response,
        )
        checks = report.primary_queries[0].quality_checks
        assert [qc.execution_status for qc in checks] == ["ERROR", "ERROR"]
        assert len(checks) == 2
        for qc in checks:
            assert unsafe(qc.result_summary) == []
            assert "\n" not in qc.result_summary
            assert SECRET not in qc.result_summary
            assert qc.result_summary.startswith("execution error: ")
            assert f"no such table: main.{scrubbed}" in qc.result_summary


def test_a_quality_check_error_is_cleaned_in_full(
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    """Every control, a secret and a newline, through a driver that raises raw text."""
    report = _run_with(
        _RawExecuteErrorDB(f"boom{EVERY_CONTROL}done\npassword={SECRET}"),
        sample_request,
        primary_query_spec_valid,
        qc_specs_valid,
        summary_response,
        datasheet_response,
    )

    checks = report.primary_queries[0].quality_checks
    assert len(checks) == 2  # a loop over nothing passes
    for qc in checks:
        assert qc.execution_status == "ERROR"
        assert qc.result_summary == "execution error: boom done password=***"


def test_a_baseline_error_carries_no_control_character_or_secret(
    tmp_path: Path,
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    """Route 3, ``nodes.py``'s baseline collection: ``caveats=[f"baseline SQL execution
    error: {e}"]`` reaches ``analysis/06_implementation_plan.qmd``. Its own call site, so
    its own test."""
    for n, (name, scrubbed) in enumerate(
        [
            (ESCAPE_NAME, ESCAPE_NAME_SCRUBBED),
            (SECRET_NAME, "cfg PWD=***;Database=claims"),
        ]
    ):
        url = database_with_a_dangling_view(tmp_path / f"{n}.db", name)
        report = _run_with(
            ReadOnlyDB(url),
            _request_with_baseline(sample_request),
            primary_query_spec_valid,
            qc_specs_valid,
            summary_response,
            datasheet_response,
        )
        snapshot = report.baseline_snapshot
        assert snapshot is not None
        assert snapshot.query_execution_status == "FAILED"
        (caveat,) = snapshot.caveats
        assert unsafe(caveat) == []
        assert "\n" not in caveat
        assert SECRET not in caveat
        assert caveat.startswith("baseline SQL execution error: ")
        assert f"no such table: main.{scrubbed}" in caveat


def test_a_baseline_error_is_cleaned_in_full(
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    report = _run_with(
        _RawExecuteErrorDB(f"boom{EVERY_CONTROL}done\npassword={SECRET}"),
        _request_with_baseline(sample_request),
        primary_query_spec_valid,
        qc_specs_valid,
        summary_response,
        datasheet_response,
    )

    snapshot = report.baseline_snapshot
    assert snapshot is not None
    assert snapshot.caveats == ["baseline SQL execution error: boom done password=***"]


def test_the_whole_serialized_report_holds_no_control_character_or_secret(
    tmp_path: Path,
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    """Asserted over the WHOLE report as the website reads it, once decoded, so a place
    these tests did not think of would also fail. JSON escapes a control as ``\\u001b``,
    which is why the check is on the decoded values, not on the serialized text."""
    import json

    name = f"{ESCAPE_NAME} {SECRET_NAME}"
    url = database_with_a_dangling_view(tmp_path / "whole.db", name)
    report = _run_with(
        ReadOnlyDB(url),
        _request_with_baseline(sample_request),
        primary_query_spec_valid,
        qc_specs_valid,
        summary_response,
        datasheet_response,
    )

    decoded = json.loads(json.dumps(report.model_dump(mode="json")))
    strings: list[str] = []

    def _collect(value: object) -> None:
        if isinstance(value, str):
            strings.append(value)
        elif isinstance(value, dict):
            for item in value.values():
                _collect(item)
        elif isinstance(value, list):
            for item in value:
                _collect(item)

    _collect(decoded)
    # The execution routes ran: a quality check and the baseline failed on the dangling view,
    # and a connect that failed instead would make the report hold none of them.
    assert [qc.execution_status for qc in report.primary_queries[0].quality_checks] == [
        "ERROR",
        "ERROR",
    ]
    assert report.baseline_snapshot is not None
    assert report.baseline_snapshot.query_execution_status == "FAILED"
    assert any("no such table" in s for s in strings)
    assert [s for s in strings if unsafe(s.replace("\n", " "))] == []
    assert [s for s in strings if SECRET in s] == []


@pytest.mark.parametrize(
    ("url", "password"),
    [
        ("fakeecho://bob:P@ssw0rdXYZ@127.0.0.1:1/claims", "P@ssw0rdXYZ"),
        ("fakeecho//bob:hunter2@127.0.0.1:1/claims", "hunter2"),
        ("fakeecho:///bob:Hn4rT8qPz@127.0.0.1:1/claims", "Hn4rT8qPz"),
    ],
    ids=["unencoded-at", "mistyped-separator", "three-slashes"],
)
def test_the_unreachable_database_concern_carries_no_part_of_a_password_in_the_address(
    url: str,
    password: str,
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    """Session 271: the concern is written into the report, the checkpoint and a committed
    project's markdown, so a password that reached it was published. ``agent.py`` cleans the
    text it is handed and leaves the redaction to ``connect``, so this is held where the text is
    built, through the whole agent. The host stays: the operator needs it."""
    report = _run_with(
        ReadOnlyDB(url),
        sample_request,
        primary_query_spec_valid,
        qc_specs_valid,
        summary_response,
        datasheet_response,
    )

    (concern,) = [c for c in report.data_quality_concerns if "database unreachable" in c]
    assert "127.0.0.1" in concern
    assert leaked_run(password, concern) is None
    assert leaked_run(password, report.model_dump_json()) is None


# ---------------------------------------------------------------------------
# Session 279 — a crash's text never reaches the report; its class does.
#
# ``BACKLOG.md``, *Exception text that is not the database's*: ``agent.py`` wrote
# ``f"graph crashed: {e}"`` into ``summary`` and ``data_quality_concerns``, and ``nodes.py``
# wrote ``f"LLM baseline-query generation failed: {e}"`` into the baseline's ``caveats``.
# Both are the text of whatever the LLM client raised: an SDK ``APIError`` carries the
# gateway's reply, which a proxy that echoes request headers fills with the API key, and
# opencode's error events carry upstream text. The report is written to ``DataReport.json``
# and into a committed project's markdown, so the key was published. ``safe_message`` masks
# the ``x-api-key: <key>`` shape and leaves a bare ``sk-ant-`` token, so the fix is the class
# name, as the scripted intake runner's was in Session 278 (``db.safe_class_name``).
#
# Each site is its own call, so each has its own tests: a site that goes back to ``{e}`` (or to
# a bare ``type(e).__name__``) leaves the other site's tests green.
# ---------------------------------------------------------------------------

GATEWAY_KEY = "sk-ant-DATALEAK0123456789abcdef"


def _hostile_text() -> str:
    """What a gateway or a driver can put in an exception: the key twice (as a header echo and
    bare), a password, every control character, a newline and a markdown fence."""
    return (
        f"Error code: 400 - rejected the request (x-api-key: {GATEWAY_KEY}) "
        f"bare {GATEWAY_KEY} password={SECRET}{EVERY_CONTROL}\nline two ```"
    )


class _CannotBePrinted(Exception):
    """An exception that fails when anything asks it for its text."""

    def __str__(self) -> str:
        raise AssertionError("the agent read the exception's message")

    def __repr__(self) -> str:
        raise AssertionError("the agent read the exception's repr")


@dataclass
class _RaisesWhileGeneratingQueries(FakeLLMClient):
    error: BaseException = field(default_factory=lambda: RuntimeError("unset"))

    def generate_primary_queries(
        self,
        request: DataRequest,
        previous_error: str | None = None,
        *,
        data_source_inventory: DataSourceInventory | None = None,
    ) -> list[PrimaryQuerySpec]:
        raise self.error


@dataclass
class _RaisesWhileGeneratingTheBaseline(FakeLLMClient):
    error: BaseException = field(default_factory=lambda: RuntimeError("unset"))

    def generate_baseline_query(
        self,
        request: DataRequest,
        metric_name: str,
        metric_definition: str,
        measurement_window: str,
    ) -> BaselineQuerySpec:
        raise self.error


def _crash_report(
    site: str,
    error: BaseException,
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> DataReport:
    """The report of an agent whose LLM raises ``error`` at ``site`` ("graph" or "baseline")."""
    common = {
        "primary_queries_sequence": [[primary_query_spec_valid]],
        "qc_response": [qc_specs_valid],
        "summary_response": summary_response,
        "datasheet_response": datasheet_response,
    }
    try:
        if site == "graph":
            return DataAgent(
                llm=_RaisesWhileGeneratingQueries(**common, error=error), db=None
            ).run(sample_request)
        return DataAgent(
            llm=_RaisesWhileGeneratingTheBaseline(**common, error=error), db=None
        ).run(_request_with_baseline(sample_request))
    except Exception:
        pass
    # Outside the handler on purpose. Raised inside it, the failure would carry the exception
    # being handled as its context, and pytest reads that class's name to print it: for a class
    # whose name cannot be read that is an INTERNALERROR, which ends the whole session
    # instead of failing this test (measured, with ``safe_class_name`` replaced by an inline,
    # unguarded read at the ``agent.py`` site).
    pytest.fail("DataAgent.run raised instead of returning a report", pytrace=False)


def _every_string(report: DataReport) -> list[str]:
    """Every string the report holds, once decoded (JSON escapes a control as ``\\u001b``)."""
    import json

    strings: list[str] = []

    def _collect(value: object) -> None:
        if isinstance(value, str):
            strings.append(value)
        elif isinstance(value, dict):
            for item in value.values():
                _collect(item)
        elif isinstance(value, list):
            for item in value:
                _collect(item)

    _collect(json.loads(report.model_dump_json()))
    return strings


def _own_text(site: str, report: DataReport) -> str:
    """The text this site wrote: the failure's reason, or the baseline's caveat."""
    if site == "graph":
        assert report.status == "EXECUTION_FAILED"
        (concern,) = report.data_quality_concerns
        assert report.summary == f"Data Agent run failed: {concern}"
        return concern
    assert report.status == "COMPLETE"
    assert report.baseline_snapshot is not None
    assert report.baseline_snapshot.query_execution_status == "FAILED"
    (caveat,) = report.baseline_snapshot.caveats
    return caveat


SITES = pytest.mark.parametrize(
    ("site", "prefix"),
    [
        pytest.param("graph", "graph crashed: ", id="agent.py-graph-crashed"),
        pytest.param(
            "baseline", "LLM baseline-query generation failed: ", id="nodes.py-baseline"
        ),
    ],
)


@SITES
def test_a_crash_names_its_class_and_none_of_what_it_said(
    site: str,
    prefix: str,
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    class GatewayRejected(Exception):
        pass

    report = _crash_report(
        site,
        GatewayRejected(_hostile_text()),
        sample_request,
        primary_query_spec_valid,
        qc_specs_valid,
        summary_response,
        datasheet_response,
    )

    assert _own_text(site, report) == f"{prefix}GatewayRejected"
    everything = "\n".join(_every_string(report))
    assert GATEWAY_KEY not in everything
    assert "x-api-key" not in everything
    assert SECRET not in everything
    assert "line two" not in everything
    assert [s for s in _every_string(report) if unsafe(s.replace("\n", " "))] == []
    # The file the pipeline saves is this same dump.
    assert GATEWAY_KEY not in report.model_dump_json()


@SITES
def test_a_crash_that_cannot_be_printed_still_returns_a_report(
    site: str,
    prefix: str,
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    """``DataAgent.run`` is documented never to raise. Formatting ``{e}`` inside the ``except``
    block was a raise site: an exception whose ``__str__`` raises replaced the report with a
    crash. Reading the class name asks the exception for nothing."""
    report = _crash_report(
        site,
        _CannotBePrinted(GATEWAY_KEY),
        sample_request,
        primary_query_spec_valid,
        qc_specs_valid,
        summary_response,
        datasheet_response,
    )

    assert _own_text(site, report) == f"{prefix}_CannotBePrinted"


@SITES
@pytest.mark.parametrize(
    "name",
    [
        pytest.param("has a space", id="space"),
        pytest.param(f"\x1b[2J{GATEWAY_KEY}", id="escape-sequence-and-key"),
        pytest.param("café", id="non-ascii"),
        pytest.param("E" * 101, id="one-hundred-and-one-characters"),
    ],
)
def test_a_crash_whose_class_name_is_not_a_short_identifier_is_not_carried(
    site: str,
    prefix: str,
    name: str,
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    """A class built at run time can be named anything. Each site goes through
    ``safe_class_name``, not a bare ``type(e).__name__``."""
    report = _crash_report(
        site,
        type(name, (Exception,), {})(GATEWAY_KEY),
        sample_request,
        primary_query_spec_valid,
        qc_specs_valid,
        summary_response,
        datasheet_response,
    )

    assert _own_text(site, report) == f"{prefix}<unprintable>"
    assert GATEWAY_KEY not in report.model_dump_json()


@SITES
@pytest.mark.parametrize(
    "metaclass",
    [
        pytest.param(NameThatRaises, id="name-cannot-be-read"),
        pytest.param(NameThatIsAHostileStr, id="name-is-a-str-subclass"),
    ],
)
def test_a_crash_whose_class_name_the_helper_must_guard_still_returns_a_report(
    site: str,
    prefix: str,
    metaclass: type,
    sample_request: DataRequest,
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
) -> None:
    """The names ``type(name, ...)`` cannot build. A site that read the name inline, without the
    guard, would raise from inside its ``except`` block (the first) or carry the name (the second):
    the odd-name test above passes for such a site, because every name it builds is a plain
    ``str`` that can be read."""

    class Odd(Exception, metaclass=metaclass):  # type: ignore[call-arg]
        pass

    report = _crash_report(
        site,
        Odd(GATEWAY_KEY),
        sample_request,
        primary_query_spec_valid,
        qc_specs_valid,
        summary_response,
        datasheet_response,
    )

    assert _own_text(site, report) == f"{prefix}<unprintable>"
    assert GATEWAY_KEY not in report.model_dump_json()
