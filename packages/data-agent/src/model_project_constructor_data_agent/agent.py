"""Data Agent public entry point.

Per §4.2 and §12 of the architecture plan, :meth:`DataAgent.run` must not
raise for expected failures. Every internal error path returns a
:class:`DataReport` whose ``status`` field tells the orchestrator what
happened. Exceptions are reserved for unexpected programming errors; even
those are caught at the outer boundary and surfaced as
``status="EXECUTION_FAILED"`` so a buggy node cannot take down the pipeline.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from model_project_constructor_data_agent.db import ReadOnlyDB, safe_class_name, safe_message
from model_project_constructor_data_agent.graph import build_graph
from model_project_constructor_data_agent.llm import (
    LLMClient,
    PrimaryQuerySpec,
    SummaryResult,
)
from model_project_constructor_data_agent.schemas import (
    BaselineSnapshot,
    DataReport,
    DataRequest,
    Datasheet,
    PrimaryQuery,
    QualityCheck,
)


class DataAgent:
    """Single public entry point for the Data Agent pipeline."""

    def __init__(self, llm: LLMClient, db: ReadOnlyDB | None = None) -> None:
        self._llm = llm
        self._db = db
        self._app = build_graph(llm, db)

    def run(self, request: DataRequest) -> DataReport:
        missing = _missing_semantics(request)
        if missing:
            return _incomplete_report(request, missing)

        initial_state: dict[str, Any] = {
            "request": request,
            "sql_retry_count": 0,
            "db_executed": False,
        }
        try:
            final_state = self._app.invoke(initial_state)
        except Exception as e:
            # The class, never the text: it is the LLM client's exception, whose text is a
            # gateway's reply or an upstream error event and can hold the API key. The
            # report is saved and written into a committed project.
            return _execution_failed_report(request, f"graph crashed: {safe_class_name(e)}")

        status = final_state.get("status", "EXECUTION_FAILED")
        if status == "EXECUTION_FAILED":
            return _execution_failed_report(
                request,
                final_state.get("failure_reason", "unknown failure"),
            )
        try:
            return _assemble_complete_report(request, final_state)
        except Exception as e:
            # The report is built from the model's replies, so a value outside the
            # vocabulary (``PrimaryQuery``'s ``Literal``), fewer quality-check groups than
            # queries (``zip(strict=True)``) or a field of the wrong type (``DataReport``)
            # raises here, after the graph has finished. Same rule as above: the class and
            # never the text, because pydantic's message quotes the reply it refused.
            return _execution_failed_report(
                request, f"report assembly failed: {safe_class_name(e)}"
            )


def _missing_semantics(request: DataRequest) -> list[str]:
    """Catch vacuous-but-schema-valid requests.

    Pydantic already rejects absent required fields; this layer catches
    empty strings and empty lists, which the schema accepts but which leave
    the LLM nothing to work from. Returning a non-empty list triggers the
    INCOMPLETE_REQUEST path described in §4.2.
    """
    missing: list[str] = []
    if not request.target_description.strip():
        missing.append("target_description")
    if not request.required_features:
        missing.append("required_features")
    if not request.population_filter.strip():
        missing.append("population_filter")
    if not request.time_range.strip():
        missing.append("time_range")
    return missing


def _incomplete_report(request: DataRequest, missing: list[str]) -> DataReport:
    return DataReport(
        status="INCOMPLETE_REQUEST",
        request=request,
        primary_queries=[],
        summary=(
            "DataRequest is missing or vacuous in required fields: "
            + ", ".join(missing)
        ),
        confirmed_expectations=[],
        unconfirmed_expectations=[],
        data_quality_concerns=[f"missing_field:{m}" for m in missing],
        created_at=datetime.now(UTC),
    )


def _execution_failed_report(request: DataRequest, reason: str) -> DataReport:
    return DataReport(
        status="EXECUTION_FAILED",
        request=request,
        primary_queries=[],
        summary=f"Data Agent run failed: {reason}",
        confirmed_expectations=[],
        unconfirmed_expectations=[],
        data_quality_concerns=[reason],
        created_at=datetime.now(UTC),
    )


def _assemble_complete_report(
    request: DataRequest, final_state: dict[str, Any]
) -> DataReport:
    specs: list[PrimaryQuerySpec] = final_state["primary_query_specs"]
    checks_per_primary: list[list[QualityCheck]] = final_state["quality_checks"]
    datasheets: list[Datasheet] = final_state["datasheets"]
    summary: SummaryResult = final_state["summary_result"]

    primary_queries = [
        PrimaryQuery(
            name=spec.name,
            sql=spec.sql,
            purpose=spec.purpose,
            expected_row_count_order=spec.expected_row_count_order,  # type: ignore[arg-type]
            quality_checks=checks,
            datasheet=sheet,
            inventory_entries_used=list(spec.inventory_entries_used),
        )
        for spec, checks, sheet in zip(
            specs, checks_per_primary, datasheets, strict=True
        )
    ]

    data_quality_concerns = list(summary.data_quality_concerns)
    if not final_state.get("db_executed", False):
        concern = (
            "database unreachable at QC execution time; "
            "quality checks not executed"
        )
        db_error = final_state.get("db_error")
        if db_error:
            # Driver text. SQLAlchemy appends a help URL after a newline on every
            # DBAPIError and a concern is rendered as one markdown bullet, and the
            # report is written into a committed project, so a terminal control code
            # in it would be live wherever it is printed: one line, controls replaced.
            # ``redact=False``, because ``ReadOnlyDB.connect`` redacted the text where
            # it built it and the masker is not safe to run over the composed message
            # again (``safe_message``'s docstring says how it mangles one).
            concern = f"{concern}: {safe_message(db_error, redact=False)}"
        data_quality_concerns.append(concern)

    baseline_snapshot: BaselineSnapshot | None = final_state.get("baseline_snapshot")

    return DataReport(
        status="COMPLETE",
        request=request,
        primary_queries=primary_queries,
        summary=summary.summary,
        confirmed_expectations=list(summary.confirmed_expectations),
        unconfirmed_expectations=list(summary.unconfirmed_expectations),
        data_quality_concerns=data_quality_concerns,
        created_at=datetime.now(UTC),
        baseline_snapshot=baseline_snapshot,
    )
