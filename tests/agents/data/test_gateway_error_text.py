"""A baseline query the gateway rejects does not put the gateway's reply in the report.

Session 279. ``nodes.py``'s baseline collection caught the LLM client's exception and wrote
``f"LLM baseline-query generation failed: {e}"`` into the baseline's ``caveats``: the report's
JSON, and the markdown of a generated project. The Anthropic SDK puts a gateway's reply into the
exception it raises, and a gateway that quotes the request headers puts the API key into that
reply. ``test_data_agent.py`` holds the site with a stand-in client; this holds it with the real
client, the real SDK and a real socket, so a client that wrapped the SDK's exception in text of its
own would not hide a regression. The graph-crash site is driven through the real script in
``tests/scripts/test_run_pipeline_data_error_text.py``.

The gateway answers the other four calls validly (the primary queries, the quality checks, the
summary and the datasheet) and rejects only the baseline call, so the rest of the report is
normal and the failure is the one this site handles.
"""

from __future__ import annotations

import json

import anthropic
import pytest
from model_project_constructor_data_agent.anthropic_client import AnthropicLLMClient

from model_project_constructor.agents.data import DataAgent
from model_project_constructor.agents.data.llm import (
    PrimaryQuerySpec,
    QualityCheckSpec,
    SummaryResult,
)
from model_project_constructor.schemas.v1.data import DataRequest, Datasheet
from tests.agents.website.loopback import echo_the_api_key_in_a_400, message, serving_raw

KEY = "sk-ant-BASELINELEAK0123456789abcdef"


@pytest.fixture
def gateway_reply(
    primary_query_spec_valid: PrimaryQuerySpec,
    qc_specs_valid: list[QualityCheckSpec],
    summary_response: SummaryResult,
    datasheet_response: Datasheet,
):
    """The function ``serving_raw`` calls: which question is being asked decides the answer."""
    primary = [
        {
            "name": primary_query_spec_valid.name,
            "sql": primary_query_spec_valid.sql,
            "purpose": primary_query_spec_valid.purpose,
            "expected_row_count_order": primary_query_spec_valid.expected_row_count_order,
            "inventory_entries_used": [],
        }
    ]
    checks = [
        [
            {"check_name": q.check_name, "check_sql": q.check_sql, "expectation": q.expectation}
            for q in qc_specs_valid
        ]
    ]
    summary = {
        "summary": summary_response.summary,
        "confirmed_expectations": summary_response.confirmed_expectations,
        "unconfirmed_expectations": summary_response.unconfirmed_expectations,
        "data_quality_concerns": summary_response.data_quality_concerns,
    }
    answers = [
        ("Return a JSON array-of-arrays", checks),
        ("Return a JSON array. Each element", primary),
        ('"summary" (2-4 sentences)', summary),
        ('"motivation"', datasheet_response.model_dump()),
    ]

    def reply(request: bytes) -> bytes:
        prompt = json.loads(request.split(b"\r\n\r\n", 1)[1])["messages"][0]["content"]
        if "Baseline metric definition:" in prompt:
            return echo_the_api_key_in_a_400(request)
        for marker, answer in answers:
            if marker in prompt:
                return message(json.dumps(answer))
        raise AssertionError(f"the gateway has no answer for this question: {prompt[-200:]}")

    return reply


def test_the_sdk_puts_the_gateways_reply_into_the_text_of_its_exception() -> None:
    """The premise of the test below: without it, "the key is not in the report" proves nothing."""
    with serving_raw(echo_the_api_key_in_a_400) as gateway:
        client = anthropic.Anthropic(api_key=KEY, base_url=gateway.url, max_retries=0)
        with pytest.raises(anthropic.BadRequestError) as caught:
            client.messages.create(
                model="any", max_tokens=1, messages=[{"role": "user", "content": "hello"}]
            )
    assert KEY in str(caught.value)


def test_a_rejected_baseline_query_names_the_class_and_not_the_gateways_reply(
    sample_request: DataRequest, gateway_reply
) -> None:
    request = sample_request.model_copy(
        update={
            "baseline_metric_name": "subro_recovery_rate",
            "baseline_metric_definition": "Average paid_amount across all claims.",
            "baseline_measurement_window": "trailing 12 months",
        }
    )
    with serving_raw(gateway_reply) as gateway:
        client = anthropic.Anthropic(api_key=KEY, base_url=gateway.url, max_retries=0)
        report = DataAgent(llm=AnthropicLLMClient(client=client), db=None).run(request)

    # The other four calls were answered, so the report is the normal one around the failure.
    assert len(gateway.seen) == 5
    assert gateway.seen[0]["x-api-key"] == KEY
    assert report.status == "COMPLETE"
    assert [q.name for q in report.primary_queries] == ["tx_claims_2024"]
    assert report.baseline_snapshot is not None
    assert report.baseline_snapshot.query_execution_status == "FAILED"
    assert report.baseline_snapshot.caveats == [
        "LLM baseline-query generation failed: BadRequestError"
    ]
    dumped = report.model_dump_json()
    assert KEY not in dumped
    assert "x-api-key" not in dumped
