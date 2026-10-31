"""Which host a live run uses, and so which token it sends (Larkspur point 3).

``scripts/run_pipeline.py`` used to take its token from ``OrchestratorSettings`` (which follows
``MPC_HOST``, default ``gitlab``) and build its adapter from ``--host`` (default ``gitlab``). The
two were never compared, so:

* ``--host github --live`` with ``MPC_HOST`` unset and ``GITLAB_TOKEN`` set sent the GitLab token
  to ``api.github.com``;
* ``MPC_HOST=github --live`` with no ``--host`` sent the GitHub token to ``gitlab.com``;
* ``--host github --live`` with only ``GITHUB_TOKEN`` set failed with "``GITLAB_TOKEN`` is
  required", a sentence about the wrong host.

Every earlier test set ``MPC_HOST`` to the same host it passed, so none could see any of it. These
tests give the two tokens different values and disagree on purpose.

The rule, ruled by the operator: ``build_website_runner`` reads the token for the host it is
given, whatever the environment says; ``resolve_host`` (the command line's policy) uses whichever
of ``--host`` and ``MPC_HOST`` is given, and a LIVE run refuses the two when they differ.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

from model_project_constructor.orchestrator.config import ConfigError

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_pipeline.py"

GITLAB_SECRET = "glpat-SECRETgitlab9f3kQ7"
GITHUB_SECRET = "ghp_SECRETgithub4m8xZ2"


@pytest.fixture(scope="module")
def run_pipeline_module():
    spec = importlib.util.spec_from_file_location("_host_run_pipeline_under_test", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def _clean_host_environment(monkeypatch):
    """A developer's exported ``MPC_HOST`` or token must not decide these tests."""
    for var in ("MPC_HOST", "MPC_HOST_URL", "MPC_NAMESPACE", "GITLAB_TOKEN", "GITHUB_TOKEN"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def adapters(monkeypatch, run_pipeline_module):
    """Replace both adapter classes and ``WebsiteAgent`` with stubs that record their arguments.

    Returns ``{"github": [kwargs, ...], "gitlab": [kwargs, ...]}``, one entry per construction, so a
    test can say that an adapter was never built as well as what the built one received.
    """
    built: dict[str, list[dict]] = {"github": [], "gitlab": []}

    class _GitHub:
        def __init__(self, **kwargs):
            built["github"].append(dict(kwargs))

    class _GitLab:
        def __init__(self, **kwargs):
            built["gitlab"].append(dict(kwargs))

    class _Agent:
        def __init__(self, *_args, **_kwargs):
            pass

        def run(self, *_args, **_kwargs):
            return None

    import model_project_constructor.agents.website.github_adapter as gh_mod
    import model_project_constructor.agents.website.gitlab_adapter as gl_mod

    monkeypatch.setattr(gh_mod, "GitHubAdapter", _GitHub)
    monkeypatch.setattr(gl_mod, "GitLabAdapter", _GitLab)
    monkeypatch.setattr(run_pipeline_module, "WebsiteAgent", _Agent)
    return built


# ---------------------------------------------------------------------------
# build_website_runner: the token follows the host it is given
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mpc_host", [None, "gitlab", "github"])
def test_a_live_github_run_sends_the_github_token_whatever_mpc_host_says(
    run_pipeline_module, adapters, monkeypatch, mpc_host
):
    """Both tokens are set, so a token picked by ``MPC_HOST`` is wrong in two cases of three."""
    monkeypatch.setenv("GITLAB_TOKEN", GITLAB_SECRET)
    monkeypatch.setenv("GITHUB_TOKEN", GITHUB_SECRET)
    if mpc_host is not None:
        monkeypatch.setenv("MPC_HOST", mpc_host)

    run_pipeline_module.build_website_runner(host="github", live=True)

    assert adapters["gitlab"] == []
    assert adapters["github"] == [
        {"private_token": GITHUB_SECRET, "host_url": "https://api.github.com"}
    ]


@pytest.mark.parametrize("mpc_host", [None, "github", "gitlab"])
def test_a_live_gitlab_run_sends_the_gitlab_token_whatever_mpc_host_says(
    run_pipeline_module, adapters, monkeypatch, mpc_host
):
    monkeypatch.setenv("GITLAB_TOKEN", GITLAB_SECRET)
    monkeypatch.setenv("GITHUB_TOKEN", GITHUB_SECRET)
    if mpc_host is not None:
        monkeypatch.setenv("MPC_HOST", mpc_host)

    run_pipeline_module.build_website_runner(host="gitlab", live=True)

    assert adapters["github"] == []
    assert adapters["gitlab"] == [
        {"private_token": GITLAB_SECRET, "host_url": "https://gitlab.com"}
    ]


@pytest.mark.parametrize(
    ("host", "other_token_var", "other_secret", "needed_var"),
    [
        ("github", "GITLAB_TOKEN", GITLAB_SECRET, "GITHUB_TOKEN"),
        ("gitlab", "GITHUB_TOKEN", GITHUB_SECRET, "GITLAB_TOKEN"),
    ],
)
@pytest.mark.parametrize("mpc_host", [None, "gitlab", "github"])
def test_a_live_run_with_only_the_other_hosts_token_names_the_token_it_needs(
    run_pipeline_module,
    adapters,
    monkeypatch,
    host,
    other_token_var,
    other_secret,
    needed_var,
    mpc_host,
):
    """The token that IS set belongs to the other host: no adapter may be built with it, and the
    sentence must name the host the run is for, not the one ``MPC_HOST`` happens to say."""
    monkeypatch.setenv(other_token_var, other_secret)
    if mpc_host is not None:
        monkeypatch.setenv("MPC_HOST", mpc_host)

    with pytest.raises(ConfigError) as caught:
        run_pipeline_module.build_website_runner(host=host, live=True)

    assert adapters == {"github": [], "gitlab": []}
    assert f"{needed_var} is required for host={host!r}" in str(caught.value)
    assert other_secret not in str(caught.value)


# ---------------------------------------------------------------------------
# resolve_host: the command line's policy
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("flag", "mpc_host", "live", "expected"),
    [
        # Nothing says anything: the long-standing default.
        (None, None, True, "gitlab"),
        (None, None, False, "gitlab"),
        # One of the two is given: that one is used (the second row is the mirror case).
        ("github", None, True, "github"),
        (None, "github", True, "github"),
        (None, "github", False, "github"),
        ("gitlab", None, True, "gitlab"),
        # Both given and equal.
        ("github", "github", True, "github"),
        ("gitlab", "gitlab", True, "gitlab"),
        # The environment variable is normalised exactly as ``OrchestratorSettings`` does.
        ("github", "  GitHub ", True, "github"),
        (None, "GITHUB", True, "github"),
        # A dry run reads no token, so the flag is the whole answer there.
        ("github", "gitlab", False, "github"),
        ("gitlab", "github", False, "gitlab"),
        ("github", "not-a-host", False, "github"),
    ],
)
def test_resolve_host_uses_whichever_is_given(run_pipeline_module, flag, mpc_host, live, expected):
    env = {} if mpc_host is None else {"MPC_HOST": mpc_host}
    assert run_pipeline_module.resolve_host(flag, live=live, env=env) == expected


@pytest.mark.parametrize(("flag", "mpc_host"), [("github", "gitlab"), ("gitlab", "github")])
def test_resolve_host_refuses_a_live_run_whose_flag_and_variable_disagree(
    run_pipeline_module, flag, mpc_host
):
    with pytest.raises(ConfigError) as caught:
        run_pipeline_module.resolve_host(flag, live=True, env={"MPC_HOST": mpc_host})
    assert f"--host {flag}" in str(caught.value)
    assert f"MPC_HOST={mpc_host}" in str(caught.value)


@pytest.mark.parametrize("flag", [None, "github"])
def test_resolve_host_names_an_invalid_variable_in_the_words_settings_uses(
    run_pipeline_module, flag
):
    """A live run with a misspelt ``MPC_HOST`` is refused whether or not ``--host`` is given; a
    dry run is refused only when it has to read the variable (no flag)."""
    with pytest.raises(ConfigError, match=r"MPC_HOST must be one of \['github', 'gitlab'\]"):
        run_pipeline_module.resolve_host(flag, live=True, env={"MPC_HOST": "gitlb"})


def test_resolve_host_reads_the_process_environment_by_default(run_pipeline_module, monkeypatch):
    monkeypatch.setenv("MPC_HOST", "github")
    assert run_pipeline_module.resolve_host(None, live=True) == "github"
    with pytest.raises(ConfigError):
        run_pipeline_module.resolve_host("gitlab", live=True)


# ---------------------------------------------------------------------------
# main(): the policy reaches the command line
# ---------------------------------------------------------------------------


class _Stop(Exception):
    """Raised by a stub to end ``main()`` as soon as the runner is being built."""


@pytest.fixture
def runner_calls(monkeypatch, run_pipeline_module, tmp_path):
    """Stop ``main()`` at ``build_website_runner`` and record how it was called."""
    calls: list[dict] = []

    def _stop(**kwargs):
        calls.append(kwargs)
        raise _Stop

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(run_pipeline_module, "build_website_runner", _stop)
    return calls


def _argv(monkeypatch, *args):
    monkeypatch.setattr("sys.argv", ["run_pipeline.py", *args])


def test_main_refuses_a_live_mismatch_before_anything_is_built(
    run_pipeline_module, runner_calls, monkeypatch, capsys
):
    monkeypatch.setenv("MPC_HOST", "gitlab")
    monkeypatch.setenv("GITLAB_TOKEN", GITLAB_SECRET)
    monkeypatch.setenv("GITHUB_TOKEN", GITHUB_SECRET)
    _argv(monkeypatch, "--live", "--host", "github")

    with pytest.raises(SystemExit) as excinfo:
        run_pipeline_module.main()

    assert excinfo.value.code == 2
    shown = capsys.readouterr()
    assert "--host github" in shown.err and "MPC_HOST=gitlab" in shown.err
    assert runner_calls == []
    assert GITLAB_SECRET not in shown.out + shown.err
    assert GITHUB_SECRET not in shown.out + shown.err


def test_main_follows_mpc_host_when_no_host_flag_is_given(
    run_pipeline_module, runner_calls, monkeypatch, capsys
):
    """The mirror case: ``MPC_HOST=github --live`` used to build a GitLab client around the GitHub
    token."""
    monkeypatch.setenv("MPC_HOST", "github")
    monkeypatch.setenv("GITHUB_TOKEN", GITHUB_SECRET)
    _argv(monkeypatch, "--live")

    with pytest.raises(_Stop):
        run_pipeline_module.main()

    assert runner_calls == [{"host": "github", "live": True}]
    assert "Host: github" in capsys.readouterr().out


def test_main_follows_the_flag_when_mpc_host_is_unset(
    run_pipeline_module, runner_calls, monkeypatch, capsys
):
    monkeypatch.setenv("GITHUB_TOKEN", GITHUB_SECRET)
    _argv(monkeypatch, "--live", "--host", "github")

    with pytest.raises(_Stop):
        run_pipeline_module.main()

    assert runner_calls == [{"host": "github", "live": True}]
    assert "Host: github" in capsys.readouterr().out


def test_main_defaults_to_gitlab_when_neither_is_given(
    run_pipeline_module, runner_calls, monkeypatch, capsys
):
    _argv(monkeypatch)

    with pytest.raises(_Stop):
        run_pipeline_module.main()

    assert runner_calls == [{"host": "gitlab", "live": False}]
    assert "Host: gitlab" in capsys.readouterr().out


def test_main_lets_a_dry_run_name_a_host_the_variable_does_not(
    run_pipeline_module, runner_calls, monkeypatch
):
    """Nothing is sent in a dry run, so the flag wins and the stale variable is not an error."""
    monkeypatch.setenv("MPC_HOST", "gitlab")
    _argv(monkeypatch, "--host", "github")

    with pytest.raises(_Stop):
        run_pipeline_module.main()

    assert runner_calls == [{"host": "github", "live": False}]


def test_main_reports_a_misspelt_mpc_host_as_a_usage_error_not_a_traceback(
    run_pipeline_module, runner_calls, monkeypatch, capsys
):
    monkeypatch.setenv("MPC_HOST", "gitlb")
    _argv(monkeypatch, "--live")

    with pytest.raises(SystemExit) as excinfo:
        run_pipeline_module.main()

    assert excinfo.value.code == 2
    assert "MPC_HOST must be one of" in capsys.readouterr().err
    assert runner_calls == []


# ---------------------------------------------------------------------------
# The real script, in a child process
# ---------------------------------------------------------------------------


def test_the_script_refuses_a_live_mismatch_and_prints_neither_token(tmp_path):
    """Argument parsing, the exit status and the output of the real script; the refusal happens
    before any request could be made, so no server is needed.

    ``MPC_HOST_URL`` points at a loopback port nothing listens on: on the unfixed script this
    test reached the real ``api.github.com`` with an invented token (measured, a 401), and a
    regression must fail here without going to the internet to do it."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("MPC_")}
    env.update(
        MPC_HOST="gitlab",
        MPC_HOST_URL="http://127.0.0.1:9",
        GITLAB_TOKEN=GITLAB_SECRET,
        GITHUB_TOKEN=GITHUB_SECRET,
    )

    done = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--live",
            "--host",
            "github",
            "--checkpoint-dir",
            str(tmp_path / "checkpoints"),
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        stdin=subprocess.DEVNULL,
        timeout=180,
    )

    shown = done.stdout + done.stderr
    assert done.returncode == 2, shown
    assert "--host github" in shown and "MPC_HOST=gitlab" in shown
    assert "Traceback" not in shown
    assert GITLAB_SECRET not in shown and GITHUB_SECRET not in shown
    assert not (tmp_path / "checkpoints").exists()
