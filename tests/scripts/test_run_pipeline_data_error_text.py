"""A scripted data stage that fails does not write what the exception said into its report.

Session 279, closing point 5 of the ``BACKLOG.md`` item that Session 270's review filed as
*"Exception text that is not the database's, written to the same sinks raw"* (``agent.py``'s
``graph crashed: {e}``; ``nodes.py``'s baseline caveat is held in
``tests/agents/data/test_gateway_error_text.py``). Session 278's review measured the leak this
test drives: the Anthropic SDK puts a gateway's reply into the exception it raises, a gateway that
quotes the request headers puts the API key into that reply, and the data agent wrote the
exception's text into ``DataReport.json``'s ``summary`` and ``data_quality_concerns``, which the
pipeline saves and ``templates.py`` writes into a committed project. It was on disk and not on the
screen, which is why the intake runner's test, which looks at the screen first, would not have
seen it.

The test drives the real script as a subprocess with the SDK pointed at a loopback gateway, and
looks for the key on the screen and in every file the run wrote, wherever it wrote them (the
subprocess runs in an empty directory and the checkpoint directory is inside it).
``tests/agents/data/test_data_agent.py`` holds the agent's own contract without the socket, and
``test_run_pipeline_intake_error_text.py`` pins that the SDK quotes the reply in its exception,
which is the premise of this one.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from tests.agents.website.loopback import echo_the_api_key_in_a_400, serving_raw

KEY = "sk-ant-DATASTAGELEAK0123456789abcdef"
REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "run_pipeline.py"
RUN_ID = "data-leak"


def _everything(directory: Path) -> str:
    return "".join(
        path.read_text(errors="replace") for path in sorted(directory.rglob("*")) if path.is_file()
    )


def test_a_gateway_that_echoes_the_key_does_not_put_it_in_the_data_report(tmp_path: Path) -> None:
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
    # The scenario is real: the key reached the gateway, so an echo of it was possible.
    assert gateway.seen
    assert gateway.seen[0].get("x-api-key") == KEY
    assert run.returncode == 1, shown
    assert "Traceback" not in shown
    assert "Status:  FAILED_AT_DATA" in run.stdout

    envelope = json.loads((checkpoints / RUN_ID / "DataReport.json").read_text())
    saved = envelope["payload"]
    assert saved["status"] == "EXECUTION_FAILED"
    assert saved["summary"] == "Data Agent run failed: graph crashed: BadRequestError"
    assert saved["data_quality_concerns"] == ["graph crashed: BadRequestError"]

    everything = shown + _everything(tmp_path)
    assert KEY not in everything
    assert "x-api-key" not in everything
