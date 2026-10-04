"""A model reply the data agent cannot assemble ends the run as ``FAILED_AT_DATA``, not as a crash.

Session 280, route 9 of ``BACKLOG.md``'s *Seven more routes* item. ``DataAgent.run`` guarded only
the graph, so a reply whose ``expected_row_count_order`` is outside ``PrimaryQuery``'s vocabulary
(every other call answered validly, so the graph ran to its end) made the report's assembly raise
out of ``run``, against its documented contract. Pydantic's message quotes the value it refused,
which is the model's own text, so whatever printed or saved the exception published it.

The test drives the real script as a subprocess, with the real client and SDK pointed at a
loopback gateway that answers each question validly except for that one field, and looks for the
model's text on the screen and in every file the run wrote (``test_run_pipeline_data_error_text.py``
does the same for a gateway that refuses the first call).
``tests/agents/data/test_data_agent.py`` holds the agent's contract without the socket.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from model_project_constructor_data_agent.schemas import PrimaryQuery
from pydantic import ValidationError

from tests.agents.website.loopback import message, serving_raw

KEY = "sk-ant-BADREPLY0123456789abcdef"
# What a model can write in a field that is meant to be one of four words: prose, a terminal
# control code, and a phrase this test can search for.
THE_MODELS_TEXT = "about forty million\x1b[2J MODELSAIDTHIS"
REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "run_pipeline.py"
RUN_ID = "bad-reply"

_PRIMARY = [
    {
        "name": "tx_claims_2024",
        "sql": "SELECT claim_id, paid_amount FROM claims WHERE state = 'TX'",
        "purpose": "Training set for TX subrogation recovery classifier",
        "expected_row_count_order": THE_MODELS_TEXT,
        "inventory_entries_used": [],
    }
]
_CHECKS = [
    [
        {
            "check_name": "row_count_nonempty",
            "check_sql": "SELECT COUNT(*) AS n FROM claims",
            "expectation": "The claim set holds at least one row",
        }
    ]
]
_SUMMARY = {
    "summary": "The claim set could not be summarised.",
    "confirmed_expectations": [],
    "unconfirmed_expectations": [],
    "data_quality_concerns": [],
}
_DATASHEET = {
    "motivation": "m",
    "composition": "c",
    "collection_process": "p",
    "preprocessing": "n",
    "uses": "u",
    "known_biases": [],
    "maintenance": "t",
}
_BASELINE = {"metric_name": "m", "sql": "SELECT 1", "measurement_unit": "count"}

# The question being asked decides the answer: a marker from each prompt in ``anthropic_client``.
_ANSWERS = [
    ("Return a JSON array-of-arrays", _CHECKS),
    ("Return a JSON array. Each element", _PRIMARY),
    ('"summary" (2-4 sentences)', _SUMMARY),
    ('"motivation"', _DATASHEET),
    ("Baseline metric definition:", _BASELINE),
]


def _gateway_reply(request: bytes) -> bytes:
    prompt = json.loads(request.split(b"\r\n\r\n", 1)[1])["messages"][0]["content"]
    for marker, answer in _ANSWERS:
        if marker in prompt:
            return message(json.dumps(answer))
    raise AssertionError(f"the gateway has no answer for this question: {prompt[-200:]}")


def _everything(directory: Path) -> str:
    return "".join(
        path.read_text(errors="replace") for path in sorted(directory.rglob("*")) if path.is_file()
    )


def test_the_premise_pydantic_quotes_the_value_it_refuses() -> None:
    """Without this, "the model's text is not in the report" would prove nothing: it must be
    that the exception the assembly raises carries it."""
    with pytest.raises(ValidationError) as caught:
        PrimaryQuery.model_validate(
            {
                **_PRIMARY[0],
                "quality_checks": [],
                "datasheet": _DATASHEET,
            }
        )
    assert "MODELSAIDTHIS" in str(caught.value)


def test_an_unassemblable_reply_is_a_failed_data_stage_and_none_of_it_is_quoted(
    tmp_path: Path,
) -> None:
    workdir = tmp_path / "cwd"
    workdir.mkdir()
    checkpoints = tmp_path / "checkpoints"
    with serving_raw(_gateway_reply) as gateway:
        # ``serving_raw`` has already set the proxy variables aside in this process's environment.
        env = {k: v for k, v in os.environ.items() if not k.startswith(("MPC_", "ANTHROPIC_"))}
        env.update(ANTHROPIC_API_KEY=KEY, ANTHROPIC_BASE_URL=gateway.url)
        run = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--llm",
                "data",
                "--checkpoint-dir",
                str(checkpoints),
                "--run-id",
                RUN_ID,
            ],
            cwd=workdir,
            env=env,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            stdin=subprocess.DEVNULL,
            timeout=180,
        )

    shown = run.stdout + run.stderr
    # The scenario is real: the graph ran to its end, so the failure is the assembly's.
    assert len(gateway.seen) >= 4, shown
    assert run.returncode == 1, shown
    assert "Traceback" not in shown
    assert "Status:  FAILED_AT_DATA" in run.stdout

    envelope = json.loads((checkpoints / RUN_ID / "DataReport.json").read_text())
    saved = envelope["payload"]
    assert saved["status"] == "EXECUTION_FAILED"
    assert saved["summary"] == "Data Agent run failed: report assembly failed: ValidationError"
    assert saved["data_quality_concerns"] == ["report assembly failed: ValidationError"]
    assert saved["primary_queries"] == []

    everything = shown + _everything(tmp_path)
    assert "MODELSAIDTHIS" not in everything
    assert "input_value" not in everything
    assert "\x1b" not in everything
