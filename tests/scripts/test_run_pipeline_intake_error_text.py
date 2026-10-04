"""A scripted intake that fails does not print or save what the exception said.

Session 278, closing the intake-runner half of the ``BACKLOG.md`` item that Session 276's review
filed as *"Two more places put a model's or a gateway's error text where a token could be"* (the
other half, the data agent's discovery log, is still open under its new title; see
``CHANGELOG.md``). The script turns an exception raised by the scripted intake runner into a
``DRAFT_INCOMPLETE`` report; that report's ``missing_fields`` carried ``str(exc)``, the pipeline
copies ``missing_fields`` into the run's ``failure_reason``, the script prints it as
``Failure: ...`` and the report is saved as ``IntakeReport.json``. A gateway that answers an error
with the request headers in the body puts the API key into all three. The test drives the real
script as a subprocess, with the Anthropic SDK pointed at a loopback gateway that does exactly
that, and looks for the key on the screen and in every file the run wrote, wherever it wrote them
(the subprocess runs in an empty directory, and the checkpoint directory is inside it);
``test_run_pipeline_adapter.py`` holds the adapter's own contract without the socket.

The end-to-end test would pass trivially if the SDK stopped quoting a reply's body in its exception,
so the premise is pinned on its own, as ``test_logging_error_text.py`` pins pydantic's and httpx's.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from tests.agents.website.loopback import echo_the_api_key_in_a_400, serving_raw

KEY = "sk-ant-INTAKELEAK0123456789abcdef"
REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "run_pipeline.py"
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "_b2_failmode.yaml"
RUN_ID = "intake-leak"


def _everything(directory: Path) -> str:
    return "".join(
        path.read_text(errors="replace") for path in sorted(directory.rglob("*")) if path.is_file()
    )


def test_the_sdk_puts_the_gateways_reply_into_the_text_of_its_exception() -> None:
    """The premise of the test below: without it, "the key is not in the output" proves nothing."""
    import anthropic

    with serving_raw(echo_the_api_key_in_a_400) as gateway:
        client = anthropic.Anthropic(api_key=KEY, base_url=gateway.url, max_retries=0)
        try:
            client.messages.create(
                model="any", max_tokens=1, messages=[{"role": "user", "content": "hello"}]
            )
        except anthropic.BadRequestError as error:
            assert KEY in str(error)
        else:
            raise AssertionError("the gateway's 400 did not raise")


def test_a_gateway_that_echoes_the_key_does_not_put_it_on_the_screen_or_on_disk(
    tmp_path: Path,
) -> None:
    workdir = tmp_path / "cwd"
    workdir.mkdir()
    checkpoints = tmp_path / "checkpoints"
    with serving_raw(echo_the_api_key_in_a_400) as gateway:
        # ``serving_raw`` has already set the proxy variables aside in this process's environment.
        env = {k: v for k, v in os.environ.items() if not k.startswith(("MPC_", "ANTHROPIC_"))}
        env.update(ANTHROPIC_API_KEY=KEY, ANTHROPIC_BASE_URL=gateway.url)
        run = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--llm",
                "both",
                "--intake-fixture",
                str(FIXTURE),
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
    # The scenario is real: the key reached the gateway, so an echo of it was possible.
    assert gateway.seen
    assert gateway.seen[0].get("x-api-key") == KEY
    assert run.returncode == 1, shown
    assert "Traceback" not in shown
    assert "Status:  FAILED_AT_INTAKE" in run.stdout

    envelope = json.loads((checkpoints / RUN_ID / "IntakeReport.json").read_text())
    saved = envelope["payload"]
    assert saved["status"] == "DRAFT_INCOMPLETE"
    assert saved["missing_fields"] == ["interview_aborted: BadRequestError"]
    printed = [line for line in run.stdout.splitlines() if line.strip().startswith("Failure:")]
    assert len(printed) == 1
    assert "BadRequestError" in printed[0]

    everything = shown + _everything(tmp_path)
    assert KEY not in everything
    assert "x-api-key" not in everything
