"""A crash in the website stage does not let ``--resume`` create a second project.

``BACKLOG.md``, *"A website stage that raises something other than a ``RepoClientError`` saves no
result"*, measured by Session 274's review and reproduced here before the fix: the host answers
``POST /projects`` with a ``201`` and then something the adapter cannot read, run 1 dies with a
traceback and saves nothing, and ``--resume`` prints ``RESUMED from: website`` and creates the
project again. Every test drives the real script as a subprocess at a real socket and counts the
``POST /api/v4/projects`` the host received; ``tests/orchestrator/test_pipeline_website_failure.py``
holds the same behaviour for every exception kind without the socket.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
from collections.abc import Callable, Iterator
from contextlib import ExitStack
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from tests.agents.website.loopback import serving_raw

TOKEN = "glpat-CRASHRESUME0123456789"
REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "run_pipeline.py"
RUN_ID = "crashed"

#: ``python -c`` runs the script with ``SIGINT`` set to Python's own handler, whatever the test
#: runner's parent left it as: a job started in the background inherits ``SIG_IGN``, and then
#: Ctrl-C would never raise ``KeyboardInterrupt`` and the test would prove nothing.
BOOT = (
    "import runpy, signal, sys; "
    "signal.signal(signal.SIGINT, signal.default_int_handler); "
    "sys.argv = sys.argv[1:]; "
    "runpy.run_path(sys.argv[0], run_name='__main__')"
)


def _deep_json_raises_recursion_error() -> bool:
    """CPython 3.11 to 3.13 raise ``RecursionError`` for 100,000 open brackets; 3.14 parses them
    and raises ``JSONDecodeError``, which the adapter handles as an ordinary error reply."""
    try:
        json.loads(b"[" * 100_000)
    except RecursionError:
        return True
    except ValueError:
        return False
    return False


def _http(status: int, reason: str, body: bytes, content_type: str = "application/json") -> bytes:
    head = (
        f"HTTP/1.1 {status} {reason}\r\nContent-Type: {content_type}\r\n"
        f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n"
    )
    return head.encode() + body


@dataclass
class Host:
    """A GitLab-shaped host: every call is honest except the one named by ``fails_at``.

    ``fails_at`` is ``"project"`` (the reply to ``POST /projects``), ``"commit"`` (the reply to the
    commit) or ``""`` (all honest). ``how`` says what the failing reply is.
    """

    fails_at: str
    how: str
    base: str = ""
    requests: list[tuple[str, str]] = field(default_factory=list)
    commit_seen: threading.Event = field(default_factory=threading.Event)
    release: threading.Event = field(default_factory=threading.Event)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _next_id: int = 1001

    def posts_to_projects(self) -> int:
        return sum(1 for m, p in self.requests if (m, p) == ("POST", "/api/v4/projects"))

    def _failing(self) -> bytes:
        if self.how == "no-id":
            return _http(201, "Created", b"{}")
        if self.how == "deep-json":
            return _http(400, "Bad Request", b"[" * 100_000)
        if self.how == "echoed-id":
            # A host that echoes the token it was sent as the project's id. The next request puts
            # the id in a URL, ``httpx`` refuses the control code and quotes the URL in its message:
            # an exception whose MESSAGE carries the token, which no other case here does.
            created = {
                "id": f"{TOKEN}\x07 x",
                "web_url": f"{self.base}/p/x",
                "default_branch": "main",
            }
            return _http(201, "Created", json.dumps(created).encode())
        # ``hold``: the commit never gets an answer until the test lets go of it.
        self.commit_seen.set()
        self.release.wait(60)
        return _http(500, "Internal Server Error", b"released", "text/plain")

    def reply(self, request: bytes) -> bytes:
        method, path, _ = request.split(b"\r\n", 1)[0].decode().split(" ", 2)
        with self._lock:
            self.requests.append((method, path))
        if method == "GET" and path.startswith("/api/v4/groups/"):
            return _http(200, "OK", b'{"id": 7}')
        if (method, path) == ("POST", "/api/v4/projects"):
            if self.fails_at == "project":
                return self._failing()
            with self._lock:
                project_id = self._next_id
                self._next_id += 1
            created = {
                "id": project_id,
                "web_url": f"{self.base}/p/{project_id}",
                "default_branch": "main",
            }
            return _http(201, "Created", json.dumps(created).encode())
        if method == "GET" and path.startswith("/api/v4/projects/"):
            return _http(200, "OK", b'{"id": 1}')
        if method == "POST" and path.endswith("/repository/commits"):
            if self.fails_at == "commit":
                return self._failing()
            return _http(201, "Created", b'{"id": "0123456789abcdef0123456789abcdef01234567"}')
        return _http(404, "Not Found", b"{}")


@pytest.fixture
def serve() -> Iterator[Callable[[Host], Host]]:
    """Start the socket for the ``Host`` a test builds; stop it, and release a held reply, after."""
    hosts: list[Host] = []
    with ExitStack() as stack:

        def start(host: Host) -> Host:
            host.base = stack.enter_context(serving_raw(host.reply)).url
            hosts.append(host)
            return host

        try:
            yield start
        finally:
            for host in hosts:
                host.release.set()


def _env(host: Host) -> dict[str, str]:
    # ``serving_raw`` has already set the proxy variables aside in this process's environment.
    env = {k: v for k, v in os.environ.items() if not k.startswith("MPC_")}
    env.update(MPC_HOST="gitlab", MPC_HOST_URL=host.base, GITLAB_TOKEN=TOKEN, GITHUB_TOKEN=TOKEN)
    return env


def _argv(checkpoints: Path, *extra: str) -> list[str]:
    return ["--live", "--host", "gitlab", "--checkpoint-dir", str(checkpoints), *extra]


def _run(host: Host, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        env=_env(host),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        stdin=subprocess.DEVNULL,
        timeout=180,
    )


def _saved(checkpoints: Path) -> dict[str, object]:
    return json.loads((checkpoints / RUN_ID / "RepoProjectResult.result.json").read_text())


def _everything(directory: Path) -> str:
    return "".join(
        path.read_text(errors="replace") for path in sorted(directory.rglob("*")) if path.is_file()
    )


def _assert_resume_refuses(host: Host, checkpoints: Path, *, posts_before: int) -> None:
    resumed = _run(host, _argv(checkpoints, "--resume", RUN_ID))
    shown = resumed.stdout + resumed.stderr
    assert resumed.returncode == 2, shown
    assert "RESUMED from" not in shown
    assert "to retry the website stage" in resumed.stderr
    assert str(checkpoints / RUN_ID / "RepoProjectResult.result.json") in resumed.stderr
    assert host.posts_to_projects() == posts_before, host.requests


@pytest.mark.parametrize(
    ("fails_at", "how", "error_class"),
    [
        pytest.param("commit", "no-id", "KeyError", id="commit-reply-without-an-id"),
        pytest.param("project", "no-id", "KeyError", id="project-created-but-reply-without-an-id"),
        pytest.param(
            "project",
            "deep-json",
            "RecursionError",
            id="error-body-100000-deep",
            marks=pytest.mark.skipif(
                not _deep_json_raises_recursion_error(),
                reason="this Python parses 100,000 nested brackets; unit tests raise it directly",
            ),
        ),
        pytest.param("project", "echoed-id", "InvalidURL", id="project-id-echoing-the-token"),
    ],
)
def test_a_crash_is_saved_and_resume_makes_no_second_project(
    serve: Callable[[Host], Host], tmp_path: Path, fails_at: str, how: str, error_class: str
) -> None:
    host = serve(Host(fails_at, how))
    checkpoints = tmp_path / "checkpoints"

    crashed = _run(host, _argv(checkpoints, "--run-id", RUN_ID))

    shown = crashed.stdout + crashed.stderr
    assert crashed.returncode == 1, shown
    assert "Traceback" not in shown
    assert "Status:  FAILED_AT_WEBSITE" in crashed.stdout
    saved = _saved(checkpoints)
    assert saved["status"] == "FAILED"
    reason = saved["failure_reason"]
    assert isinstance(reason, str)
    assert reason.startswith(f"unexpected_error: {error_class} (")
    assert "may already have created a project" in reason
    printed = [line for line in crashed.stdout.splitlines() if line.strip().startswith("Failure:")]
    assert [line.split("Failure:", 1)[1].strip() for line in printed] == [reason]
    assert TOKEN not in shown + _everything(checkpoints)
    assert "\x07" not in shown + _everything(checkpoints)
    assert host.posts_to_projects() == 1

    _assert_resume_refuses(host, checkpoints, posts_before=1)


def test_an_interrupt_during_the_commit_is_saved_and_resume_makes_no_second_project(
    serve: Callable[[Host], Host], tmp_path: Path
) -> None:
    """Ctrl-C while the host is holding the commit reply open: the run still stops, and the
    project the host already made is not made again by ``--resume`` against an honest host."""
    host = serve(Host("commit", "hold"))
    checkpoints = tmp_path / "checkpoints"
    process = subprocess.Popen(
        [sys.executable, "-c", BOOT, str(SCRIPT), *_argv(checkpoints, "--run-id", RUN_ID)],
        cwd=REPO_ROOT,
        env=_env(host),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        for _ in range(600):  # 120 s
            if host.commit_seen.wait(0.2):
                break
            if process.poll() is not None:
                out, err = process.communicate()
                pytest.fail(f"the script exited ({process.returncode}) first:\n{out}\n{err}")
        else:
            pytest.fail("the script never reached the commit")
        process.send_signal(signal.SIGINT)
        out, err = process.communicate(timeout=120)
    finally:
        host.release.set()
        if process.poll() is None:
            process.kill()
            process.communicate()

    assert process.returncode != 0, out + err
    assert "KeyboardInterrupt" in err
    saved = _saved(checkpoints)
    assert saved["status"] == "FAILED"
    assert str(saved["failure_reason"]).startswith("interrupted: KeyboardInterrupt (")
    assert TOKEN not in out + err + _everything(checkpoints)
    assert host.posts_to_projects() == 1

    host.fails_at = ""  # the host recovered: an honest resume would have built a second project
    _assert_resume_refuses(host, checkpoints, posts_before=1)
