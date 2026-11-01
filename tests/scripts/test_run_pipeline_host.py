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
import re
import subprocess
import sys
from pathlib import Path

import pytest

from model_project_constructor.agents.website.governance_templates import CIHostConfig
from model_project_constructor.orchestrator.config import REPO_PLATFORMS, ConfigError

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
    """A developer's exported ``MPC_*`` setting or host token must not decide these tests.

    Every ``MPC_*`` variable goes, not a hand-picked list: ``build_website_runner`` hands the whole
    environment to ``OrchestratorSettings.from_env``, which validates ``MPC_LOG_LEVEL`` and others.
    """
    for var in [v for v in os.environ if v.startswith("MPC_")] + ["GITLAB_TOKEN", "GITHUB_TOKEN"]:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def agent_calls(monkeypatch, run_pipeline_module):
    """Replace ``WebsiteAgent`` with a stub; returns the keyword arguments of each construction."""
    calls: list[dict] = []

    class _Agent:
        def __init__(self, *_args, **kwargs):
            calls.append(dict(kwargs))

        def run(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(run_pipeline_module, "WebsiteAgent", _Agent)
    return calls


@pytest.fixture
def adapters(monkeypatch, agent_calls):
    """Replace both adapter classes with stubs that record their arguments.

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

    import model_project_constructor.agents.website.github_adapter as gh_mod
    import model_project_constructor.agents.website.gitlab_adapter as gl_mod

    monkeypatch.setattr(gh_mod, "GitHubAdapter", _GitHub)
    monkeypatch.setattr(gl_mod, "GitLabAdapter", _GitLab)
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


@pytest.mark.parametrize("live", [True, False])
@pytest.mark.parametrize("host", ["github", "gitlab"])
def test_the_ci_manifest_follows_the_host_it_is_given_not_the_environment(
    run_pipeline_module, adapters, agent_calls, monkeypatch, host, live
):
    """``ci_platform`` decides which CI file the generated project gets; the environment names the
    other host here, and both tokens are set so a live run builds."""
    other = "gitlab" if host == "github" else "github"
    monkeypatch.setenv("MPC_HOST", other)
    monkeypatch.setenv("GITLAB_TOKEN", GITLAB_SECRET)
    monkeypatch.setenv("GITHUB_TOKEN", GITHUB_SECRET)

    run_pipeline_module.build_website_runner(host=host, live=live)

    assert agent_calls == [{"ci_platform": host, "ci_host_config": CIHostConfig()}]


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
    # The way out is part of the message: an operator who only sees the refusal needs it.
    assert "unset MPC_HOST to follow --host" in str(caught.value)


@pytest.mark.parametrize("bad", ["gitlb", "", "   "])
@pytest.mark.parametrize(("flag", "live"), [(None, True), (None, False), ("github", True)])
def test_resolve_host_names_an_invalid_variable_in_the_words_settings_uses(
    run_pipeline_module, flag, live, bad
):
    """Whenever the variable has to be read it must be a host name: a live run reads it with or
    without ``--host``, and a dry run reads it when there is no flag. A blank value is not "unset"
    (``OrchestratorSettings`` has never accepted one), and that is a change for a dry run, which
    never read the variable before Session 292. A dry run WITH a flag never reads it: the table
    above pins that."""
    message = re.escape(f"MPC_HOST must be one of {sorted(REPO_PLATFORMS)}")
    with pytest.raises(ConfigError, match=message):
        run_pipeline_module.resolve_host(flag, live=live, env={"MPC_HOST": bad})


def test_resolve_host_reads_the_process_environment_by_default(run_pipeline_module, monkeypatch):
    monkeypatch.setenv("MPC_HOST", "github")
    assert run_pipeline_module.resolve_host(None, live=True) == "github"
    with pytest.raises(ConfigError):
        run_pipeline_module.resolve_host("gitlab", live=True)


def test_resolve_host_given_an_environment_does_not_fall_back_to_the_process_one(
    run_pipeline_module, monkeypatch
):
    """An empty mapping is an environment, not "none given"."""
    monkeypatch.setenv("MPC_HOST", "github")
    assert run_pipeline_module.resolve_host(None, live=True, env={}) == "gitlab"


def test_resolve_host_reads_only_mpc_host_not_the_rest_of_the_settings(run_pipeline_module):
    """The other ``MPC_*`` settings are ``build_website_runner``'s business (a live run); a bad one
    must not stop the choice of host."""
    env = {
        "MPC_HOST": "github",
        "MPC_LOG_LEVEL": "bogus",
        "MPC_HOST_URL": "",
        "MPC_NAMESPACE": "https://x",
    }
    assert run_pipeline_module.resolve_host(None, live=True, env=env) == "github"


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
    out = capsys.readouterr().out
    assert "Host: github" in out
    # The repository target is built from the same host, not from the flag alone.
    assert "Target: my-org on https://api.github.com" in out


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
    out = capsys.readouterr().out
    assert "Host: gitlab" in out
    assert "Target: data-science/model-drafts on https://gitlab.com" in out


def test_main_lets_a_dry_run_name_a_host_the_variable_does_not(
    run_pipeline_module, runner_calls, monkeypatch, capsys
):
    """Nothing is sent in a dry run, so the flag wins and the stale variable is not an error."""
    monkeypatch.setenv("MPC_HOST", "gitlab")
    _argv(monkeypatch, "--host", "github")

    with pytest.raises(_Stop):
        run_pipeline_module.main()

    assert runner_calls == [{"host": "github", "live": False}]
    assert "Target: my-org on https://api.github.com" in capsys.readouterr().out


@pytest.mark.parametrize("bad", ["gitlb", ""])
@pytest.mark.parametrize("mode", [["--live"], []])
def test_main_reports_a_bad_mpc_host_as_a_usage_error_not_a_traceback(
    run_pipeline_module, runner_calls, monkeypatch, capsys, bad, mode
):
    """Also a DRY run with no ``--host``: before Session 292 it never read the variable and ran to
    ``COMPLETE`` whatever it held; it now has to, to know which host to preview."""
    monkeypatch.setenv("MPC_HOST", bad)
    _argv(monkeypatch, *mode)

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

    ``MPC_HOST_URL`` points at a loopback port nothing listens on. The first version of this
    test had no such line, and on the unfixed script it reached the real ``api.github.com`` with
    an invented token (measured, a 401); with the line, a regression fails here by connection
    refused, and the proxy variables are set aside so that it cannot be routed elsewhere."""
    proxies = {"http_proxy", "https_proxy", "all_proxy"}
    env = {
        k: v for k, v in os.environ.items() if not k.startswith("MPC_") and k.lower() not in proxies
    }
    env["NO_PROXY"] = "127.0.0.1"
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
    assert "usage:" in done.stderr  # a usage error, not a bare message
    assert "Traceback" not in shown
    assert GITLAB_SECRET not in shown and GITHUB_SECRET not in shown
    assert not (tmp_path / "checkpoints").exists()
