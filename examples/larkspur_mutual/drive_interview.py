"""Play the stakeholder in the intake web UI, over real HTTP, and save the report.

Starts the keyless app from ``serve_intake.py`` on a free local port, opens a
session, answers each question with the matching ``qa_pairs`` answer from
``intake_fixture.yaml``, accepts the draft, and writes the finished
``IntakeReport`` to ``out/intake_report.json``. Run from the repository root::

    uv run python examples/larkspur_mutual/drive_interview.py

The web UI never writes the report to disk (it serves it at
``/sessions/{id}/report.json``), which is why this script does.
"""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path

import httpx
import uvicorn
from serve_intake import FIXTURE, OUT, build_app

from model_project_constructor.agents.intake.fixture import answers_from_fixture, load_fixture
from model_project_constructor.schemas.v1.intake import IntakeReport

MAX_STEPS = 60  # a guard: 20 questions and 4 reviews are the app's own ceilings


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _short(text: str, width: int = 96) -> str:
    one_line = " ".join(text.split())
    return one_line if len(one_line) <= width else one_line[: width - 1] + "…"


def run(out_dir: Path = OUT) -> Path:
    """Interview to completion and return the path of the saved ``IntakeReport``."""
    out_dir.mkdir(exist_ok=True)
    db = out_dir / "larkspur_interview.db"
    for suffix in ("", "-shm", "-wal"):  # a fresh database: a finished session cannot be redone
        (out_dir / f"{db.name}{suffix}").unlink(missing_ok=True)

    fixture = load_fixture(FIXTURE)
    answers = answers_from_fixture(fixture)
    sid = fixture["session_id"]

    app = build_app(db)
    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    try:
        deadline = time.monotonic() + 15
        while True:
            try:
                if httpx.get(f"{base}/healthz", timeout=1.0).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            if time.monotonic() > deadline:
                raise RuntimeError("the intake app did not come up within 15 s")
            time.sleep(0.1)

        with httpx.Client(base_url=base, timeout=30.0) as client:
            started = client.post(
                "/sessions",
                data={
                    "stakeholder_id": fixture["stakeholder_id"],
                    "session_id": sid,
                    "domain": fixture["domain"],
                    "initial_problem": " ".join(fixture["initial_problem"].split()),
                },
            )
            if started.status_code != 303:
                raise RuntimeError(f"POST /sessions answered {started.status_code}, not 303")
            print(f"  session {sid} opened at {base}/sessions/{sid}")

            posted = 0
            for _ in range(MAX_STEPS):
                state = client.get(f"/sessions/{sid}/state.json").json()
                phase = state["phase"]
                if phase == "question":
                    if posted >= len(answers):
                        raise RuntimeError("the app asked more questions than the fixture holds")
                    print(f"  Q{posted + 1}: {_short(state['question'])}")
                    print(f"      A: {_short(answers[posted])}")
                    reply = client.post(f"/sessions/{sid}/answer", data={"answer": answers[posted]})
                    reply.raise_for_status()
                    posted += 1
                elif phase == "review":
                    print("  review: accept")
                    reply = client.post(f"/sessions/{sid}/review", data={"review": "accept"})
                    reply.raise_for_status()
                elif phase == "complete":
                    break
                else:
                    raise RuntimeError(f"unexpected phase {phase!r}: {state}")
            else:
                raise RuntimeError(f"no completed report after {MAX_STEPS} steps")

            body = client.get(f"/sessions/{sid}/report.json")
            body.raise_for_status()
            report = IntakeReport.model_validate_json(body.text)
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        app.state.store.close()

    target = out_dir / "intake_report.json"
    target.write_text(report.model_dump_json(indent=2) + "\n")
    print(
        f"  report: status={report.status} questions_asked={report.questions_asked} "
        f"revision_cycles={report.revision_cycles} -> {target}"
    )
    return target


if __name__ == "__main__":
    print("Interview (the intake web UI, keyless, over HTTP):")
    run()
