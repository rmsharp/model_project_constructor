"""A hostile repository host cannot put a terminal control code on a screen or in a result file.

``test_host_success_text.py`` holds the agent and the adapters; this file holds the three places the
values go after them (``BACKLOG.md`` route 8): the website command's ``Project:`` and ``Commit:``
lines, the pipeline script's ``Project:`` line, and the ``RepoProjectResult.result.json`` the script
saves and a later ``--resume`` prints from. Every test drives the real command, or the real script,
as a subprocess at a socket that answers the whole request sequence correctly with text in the
project address and the commit id; nothing between the socket and the screen is stubbed.

A reply of the kind that matters here is a VALID one: a ``2xx`` the host chose the words of. The
website command's ``echo`` strips an ANSI CSI sequence when stdout is not a terminal, so the text
below also holds an OSC window-title sequence and ``ESC c``, which it does not.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from model_project_constructor.agents.website._host_text import REDACTED, scrub_host_text
from tests.agents.website.loopback import serving_raw
from tests.agents.website.success_hosts import (
    EVERYTHING,
    SHIPPED,
    TOKEN,
    Shipped,
    is_clean,
    recording,
    serve,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
# The address also carries a lone surrogate: nothing reuses it in a request, and unscrubbed it makes
# the graph's checkpointer raise before anything is printed.
URL = f"https://h.example/g/p{EVERYTHING}\ud800tail"
SHA = f"abc{EVERYTHING}def"
HOSTS = {"gitlab": SHIPPED[0], "github": SHIPPED[1]}


def _command(
    shipped: Shipped, host_url: str, intake: Path, data: Path, out: Path
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "model_project_constructor.agents.website",
            "--intake",
            str(intake),
            "--data",
            str(data),
            "--host",
            shipped.host,
            "--host-url",
            host_url,
            "--namespace",
            shipped.namespace,
            "--private-token",
            TOKEN,
            "-o",
            str(out),
        ],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        stdin=subprocess.DEVNULL,
        timeout=120,
    )


def _script(
    shipped: Shipped, host_url: str, checkpoints: Path, *extra: str
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.update(
        MPC_HOST=shipped.host,
        MPC_HOST_URL=host_url,
        MPC_NAMESPACE=shipped.namespace,
        GITLAB_TOKEN=TOKEN,
        GITHUB_TOKEN=TOKEN,
    )
    return subprocess.run(
        [
            sys.executable,
            "scripts/run_pipeline.py",
            "--live",
            "--host",
            shipped.host,
            "--run-id",
            "route8",
            "--checkpoint-dir",
            str(checkpoints),
            *extra,
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        stdin=subprocess.DEVNULL,
        timeout=300,
    )


def _everything(directory: Path) -> str:
    """The text of every file under ``directory``: what a checkpoint directory holds."""
    return "".join(
        path.read_text(errors="replace") for path in sorted(directory.rglob("*")) if path.is_file()
    )


def _line(text: str, label: str) -> str:
    lines = [line for line in text.splitlines() if line.strip().startswith(label)]
    assert len(lines) == 1, (label, lines)
    return lines[0].strip()


@pytest.mark.parametrize("name", sorted(HOSTS))
def test_the_real_command_prints_and_writes_nothing_a_terminal_acts_on(
    name: str, intake_report_path: Path, data_report_path: Path, tmp_path: Path
) -> None:
    shipped = HOSTS[name]
    hostile = shipped.project_reply(id_text="", url=URL, branch="main")
    clean = shipped.project_reply(id_text="", url="https://h.example/g/p", branch="main")
    outputs = []
    for project, sha in ((hostile, SHA), (clean, "abc")):
        out = tmp_path / f"{len(outputs)}.json"
        with serving_raw(serve(shipped.router(project, sha))) as server:
            done = _command(shipped, server.url, intake_report_path, data_report_path, out)
        assert done.returncode == 0, done.stderr
        outputs.append((done, out))
    (hostile_run, hostile_out), (clean_run, _) = outputs

    # Nothing on either stream is a control code, and the host's line break did not make a line.
    # (Line breaks are the streams' own: a warning on stderr is not a finding.)
    assert is_clean(hostile_run.stderr.replace("\n", ""))
    assert is_clean(hostile_run.stdout.replace("\n", ""))
    assert len(hostile_run.stdout.splitlines()) == len(clean_run.stdout.splitlines())
    assert _line(hostile_run.stdout, "Project:") == f"Project: {scrub_host_text(URL)}"
    assert _line(hostile_run.stdout, "Commit:") == f"Commit:  {scrub_host_text(SHA)}"
    assert _line(hostile_run.stdout, "Status:") == "Status:  COMPLETE"

    # The file holds the same scrubbed text, and none of its three fields has a control code.
    saved = json.loads(hostile_out.read_text())
    assert saved["project_url"] == scrub_host_text(URL)
    assert saved["initial_commit_sha"] == scrub_host_text(SHA)
    for key in ("project_url", "project_id", "initial_commit_sha"):
        assert is_clean(saved[key]), key


@pytest.mark.parametrize("name", sorted(HOSTS))
def test_the_pipeline_script_prints_and_saves_nothing_a_terminal_acts_on(
    name: str, tmp_path: Path
) -> None:
    shipped = HOSTS[name]
    hostile = shipped.project_reply(id_text="", url=URL, branch="main")
    clean = shipped.project_reply(id_text="", url="https://h.example/g/p", branch="main")
    runs = []
    for project, sha in ((hostile, SHA), (clean, "abc")):
        checkpoints = tmp_path / f"ckpt{len(runs)}"
        with serving_raw(serve(shipped.router(project, sha))) as server:
            done = _script(shipped, server.url, checkpoints)
        assert done.returncode == 0, done.stdout + done.stderr
        runs.append((done, checkpoints))
    (hostile_run, hostile_ckpt), (clean_run, _) = runs

    shown = hostile_run.stdout + hostile_run.stderr
    assert is_clean(shown.replace("\n", "")), repr(shown)
    # A host that sends a line break must not get a second printed line out of it: the hostile run
    # prints exactly as many lines as a run against a host that sent nothing odd.
    assert len(hostile_run.stdout.splitlines()) == len(clean_run.stdout.splitlines())
    assert _line(hostile_run.stdout, "Project:") == f"Project: {scrub_host_text(URL)}"

    saved = json.loads((hostile_ckpt / "route8" / "RepoProjectResult.result.json").read_text())
    assert saved["project_url"] == scrub_host_text(URL)
    assert saved["initial_commit_sha"] == scrub_host_text(SHA)

    # The run is complete, so resuming it prints the saved address; it must be the clean one. (The
    # adapter already scrubbed what was saved, so this leg holds the round trip; the resume print's
    # own scrub, for a file saved before the adapters scrubbed, is held by
    # ``tests/scripts/test_run_pipeline_resume.py``.)
    with serving_raw(serve(shipped.router(hostile, SHA))) as server:
        resumed = _script(shipped, server.url, hostile_ckpt, "--resume", "route8")
    assert resumed.returncode == 0, resumed.stdout + resumed.stderr
    assert is_clean((resumed.stdout + resumed.stderr).replace("\n", ""))
    assert f"Result: {scrub_host_text(URL)}" in resumed.stdout


def test_a_project_id_with_a_control_code_is_a_failed_result_through_the_real_command(
    intake_report_path: Path, data_report_path: Path, tmp_path: Path
) -> None:
    """Before the fix this was a traceback ending in ``InvalidURL`` and exit 1, with the project
    already made on the host. Now it is a ``FAILED`` result like any failed commit; the command
    retries a failed commit three times with a 1 s and a 2 s wait, so this one test takes three."""
    shipped = HOSTS["gitlab"]
    project = shipped.project_reply(
        id_text=shipped.raw_id("\x1b]0;PWNED-TITLE\x07"), url="https://h.example/g/p", branch="main"
    )
    out = tmp_path / "result.json"
    with serving_raw(serve(shipped.router(project, "abc"))) as server:
        done = _command(shipped, server.url, intake_report_path, data_report_path, out)
    assert "Traceback" not in done.stderr and "InvalidURL" not in done.stderr, done.stderr
    assert is_clean(done.stderr) and is_clean(done.stdout.replace("\n", ""))
    saved = json.loads(out.read_text())
    assert saved["status"] == "FAILED"
    assert is_clean(saved["failure_reason"])


def test_a_host_that_echoes_the_token_as_the_project_id_leaves_it_out_of_everything(
    tmp_path: Path,
) -> None:
    """Session 275's fixture, with the outcome it has now. The id was ``<token> BEL x``: ``httpx``
    refused the BEL in the next request's path and the run crashed before the id was saved. Now the
    id is scrubbed, the token goes with it, and the host (which has no such project) answers 404,
    so the run is a failed commit like any other and neither the screen nor a file holds the
    token. The token is also gone from what the result SAVES as the project id."""
    shipped = HOSTS["gitlab"]
    project = shipped.project_reply(
        id_text=f"{TOKEN}\x07 x", url="https://h.example/g/p", branch="main"
    )
    checkpoints = tmp_path / "checkpoints"
    with serving_raw(serve(shipped.router(project, "abc"))) as server:
        done = _script(shipped, server.url, checkpoints)
    shown = done.stdout + done.stderr
    assert done.returncode == 1, shown
    assert "Traceback" not in shown
    assert "Status:  FAILED_AT_WEBSITE" in done.stdout
    kept = _everything(checkpoints)
    assert TOKEN not in shown + kept
    # The checkpoint is JSON, where a bell would be the six characters ``\u0007``.
    assert "\x07" not in shown and "\\u0007" not in kept
    saved = json.loads((checkpoints / "route8" / "RepoProjectResult.result.json").read_text())
    assert saved["project_id"] == f"{REDACTED} x"


def test_a_parent_sha_with_a_control_code_is_a_failed_result_through_the_real_command(
    intake_report_path: Path, data_report_path: Path, tmp_path: Path
) -> None:
    """GitHub's reference reply names a parent commit whose sha holds an escape sequence, and the
    adapter writes that sha into the path of its next request, which ``httpx`` refuses to build.
    Before ``RepoHttpClient.build_request`` converted the refusal this was a traceback ending in
    ``InvalidURL`` and exit 1, with the repository already made on the host. Now it is a ``FAILED``
    result like any failed commit, and the request the host never saw is absent from what it did."""
    shipped = HOSTS["github"]
    project = shipped.project_reply(id_text="", url="https://h.example/g/p", branch="main")
    parent = "abc\x1b]0;PWNED-TITLE\x07def"
    router, seen = recording(shipped.router(project, "abc", shas={"parent_sha": parent}))
    out = tmp_path / "result.json"
    with serving_raw(serve(router)) as server:
        done = _command(shipped, server.url, intake_report_path, data_report_path, out)
    shown = done.stdout + done.stderr
    assert "Traceback" not in shown and "InvalidURL" not in shown, shown
    assert "PWNED-TITLE" not in shown
    assert is_clean(done.stderr) and is_clean(done.stdout.replace("\n", ""))
    saved = json.loads(out.read_text())
    assert saved["status"] == "FAILED"
    assert "could not be built" in saved["failure_reason"], saved["failure_reason"]
    assert is_clean(saved["failure_reason"])
    assert not any(p.startswith("/repos/g/n/git/commits/") for _, p in seen), seen


def test_a_parent_sha_with_a_control_code_is_a_failed_stage_through_the_real_script(
    tmp_path: Path,
) -> None:
    """The same host through ``scripts/run_pipeline.py``: the pipeline's own account of it is the
    ``FAILED_AT_WEBSITE`` status line and a saved ``FAILED`` result, not Session 275's net for an
    exception nobody expected (``unexpected_error``)."""
    shipped = HOSTS["github"]
    project = shipped.project_reply(id_text="", url="https://h.example/g/p", branch="main")
    router, seen = recording(
        shipped.router(project, "abc", shas={"parent_sha": "abc\x1b]0;PWNED-TITLE\x07def"})
    )
    checkpoints = tmp_path / "checkpoints"
    with serving_raw(serve(router)) as server:
        done = _script(shipped, server.url, checkpoints)
    shown = done.stdout + done.stderr
    assert done.returncode == 1, shown
    assert "Traceback" not in shown and "InvalidURL" not in shown, shown
    assert "Status:  FAILED_AT_WEBSITE" in done.stdout
    kept = _everything(checkpoints)
    assert "PWNED-TITLE" not in shown + kept
    saved = json.loads((checkpoints / "route8" / "RepoProjectResult.result.json").read_text())
    assert saved["status"] == "FAILED"
    assert "unexpected_error" not in saved["failure_reason"], saved["failure_reason"]
    assert "could not be built" in saved["failure_reason"], saved["failure_reason"]
    assert not any(p.startswith("/repos/g/n/git/commits/") for _, p in seen), seen
