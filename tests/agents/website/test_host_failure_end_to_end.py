"""A hostile repository host cannot put the token or a control code on a screen or on disk.

``test_host_failure_text.py`` holds the adapters; this file holds the three places the text goes
after them (``BACKLOG.md`` Route 7, measured by Session 274's scouting): the website command's
JSON on stdout or in ``-o``, the pipeline script's ``Failure:`` line, and the pipeline's
``RepoProjectResult.result.json`` checkpoint. Every test drives the real command, or the real
script as a subprocess, at a socket that answers the first request with a valid ``500`` that
echoes the request headers; nothing between the socket and the file is stubbed.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from model_project_constructor.agents.website.cli import app
from tests.agents.website.loopback import PROXY_VARIABLES, Loopback, serving_raw

TOKEN = "glpat-SECRET9f3kQ7xZ2mW"
REPO_ROOT = Path(__file__).resolve().parents[3]
RUNNER = CliRunner()


def _http500(body: bytes) -> bytes:
    return (
        b"HTTP/1.1 500 Internal Server Error\r\nContent-Type: text/plain\r\n"
        b"Content-Length: " + str(len(body)).encode() + b"\r\nConnection: close\r\n\r\n" + body
    )


def _head(request: bytes) -> bytes:
    return request.split(b"\r\n\r\n", 1)[0]


def _echo(request: bytes) -> bytes:
    return _http500(_head(request))


def _echo_with_controls(request: bytes) -> bytes:
    return _http500(b"\x1b[2J\x07\x00" + _head(request) + b"\r\n" + b"x" * 5000)


REPLIES: dict[str, Callable[[bytes], bytes]] = {"echo": _echo, "controls": _echo_with_controls}


@pytest.fixture
def hostile(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> Iterator[Loopback]:
    """A socket whose every reply is the parametrised hostile one, with proxies set aside."""
    for name in PROXY_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    with serving_raw(REPLIES[request.param]) as server:
        yield server


def _everything(directory: Path) -> str:
    """The text of every file under ``directory``: what a checkpoint directory holds."""
    return "".join(
        path.read_text(errors="replace") for path in sorted(directory.rglob("*")) if path.is_file()
    )


def _assert_clean(failure_reason: str) -> None:
    assert TOKEN not in failure_reason
    assert "***" in failure_reason
    assert not any(ord(c) < 0x20 or 0x7F <= ord(c) <= 0x9F for c in failure_reason)
    assert len(failure_reason) < 1100


@pytest.mark.parametrize("hostile", sorted(REPLIES), indirect=True)
@pytest.mark.parametrize("host", ["gitlab", "github"])
def test_the_website_command_prints_and_writes_none_of_it(
    intake_report_path: Path,
    data_report_path: Path,
    hostile: Loopback,
    tmp_path: Path,
    host: str,
) -> None:
    out = tmp_path / "result.json"
    argv = [
        "--intake",
        str(intake_report_path),
        "--data",
        str(data_report_path),
        "--host",
        host,
        "--host-url",
        hostile.url,
        # GitHub has one owner level: the CLI's GitLab-shaped default would be refused before any
        # request was sent.
        "--namespace",
        "my-org",
        "--private-token",
        TOKEN,
    ]
    to_stdout = RUNNER.invoke(app, argv)
    to_file = RUNNER.invoke(app, [*argv, "-o", str(out)])
    shown = to_stdout.stdout + to_stdout.stderr + to_file.stdout + to_file.stderr + out.read_text()
    assert TOKEN not in shown
    # The raw control codes would appear in JSON as ``\u001b``: they are not in the message at all.
    assert "\\u001b" not in shown
    assert "\\u0007" not in shown
    for text in (to_stdout.stdout, out.read_text()):
        payload = json.loads(text[text.index("{") :].split("\nWrote ")[0])
        assert payload["status"] == "FAILED"
        _assert_clean(payload["failure_reason"])


@pytest.mark.parametrize("hostile", sorted(REPLIES), indirect=True)
def test_the_real_command_is_clean_too(
    intake_report_path: Path, data_report_path: Path, hostile: Loopback, tmp_path: Path
) -> None:
    out = tmp_path / "result.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "model_project_constructor.agents.website",
            "--intake",
            str(intake_report_path),
            "--data",
            str(data_report_path),
            "--host-url",
            hostile.url,
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
    shown = completed.stdout + completed.stderr + out.read_text()
    assert TOKEN not in shown
    assert "\x1b" not in shown and "\x07" not in shown
    _assert_clean(json.loads(out.read_text())["failure_reason"])


@pytest.mark.parametrize("hostile", sorted(REPLIES), indirect=True)
@pytest.mark.parametrize("host", ["gitlab", "github"])
def test_the_pipeline_script_prints_and_saves_none_of_it(
    hostile: Loopback, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, host: str
) -> None:
    """The second route to the same sink: the token comes from the environment, the failure is
    printed on the ``Failure:`` line and saved in the run's ``RepoProjectResult`` checkpoint."""
    env = dict(os.environ)
    env.update(
        MPC_HOST=host,
        MPC_HOST_URL=hostile.url,
        GITLAB_TOKEN=TOKEN,
        GITHUB_TOKEN=TOKEN,
    )
    checkpoints = tmp_path / "checkpoints"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_pipeline.py",
            "--live",
            "--host",
            host,
            "--run-id",
            "hostile",
            "--checkpoint-dir",
            str(checkpoints),
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
    shown = completed.stdout + completed.stderr
    assert completed.returncode == 1, shown
    assert TOKEN not in shown + _everything(checkpoints)
    assert "\x1b" not in shown and "\x07" not in shown
    saved = json.loads((checkpoints / "hostile" / "RepoProjectResult.result.json").read_text())
    assert saved["status"] == "FAILED"
    _assert_clean(saved["failure_reason"])
    # The terminal shows the same one line, not a continuation of it.
    printed = [
        line for line in completed.stdout.splitlines() if line.strip().startswith("Failure:")
    ]
    assert len(printed) == 1
    assert printed[0].split("Failure:", 1)[1].strip() == saved["failure_reason"]
