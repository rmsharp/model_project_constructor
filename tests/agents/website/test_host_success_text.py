"""A hostile repository host cannot put a control code in the values its SUCCESS replies carry.

``test_host_failure_text.py`` holds what a host's failure leaves behind; this file holds what its
2xx replies do (``BACKLOG.md`` route 8, found by Session 274's scouting): the project address, the
project id, the default branch and the commit id. They are the host's words, they become
``RepoProjectResult`` fields, the website command and the pipeline script print them, and two of
them (the id and the branch) go back to the host inside a request path, where a control character
makes ``httpx`` raise ``InvalidURL`` out of the adapter.

Three levels, each against a real socket. The adapters are called directly, which is where the
scrub lives; the agent is run over each adapter, which is what an operator sees; and a registry-wide
test goes red for a registered host whose adapter does not leave through ``scrubbed_values``.
``test_host_success_end_to_end.py`` holds the website command and the pipeline script.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from model_project_constructor.agents.website._host_text import REDACTED, scrub_host_text
from model_project_constructor.agents.website.agent import WebsiteAgent
from model_project_constructor.agents.website.graph import build_website_graph
from model_project_constructor.agents.website.protocol import (
    CommitInfo,
    ProjectInfo,
    RepoClient,
)
from model_project_constructor.orchestrator.config import REPO_PLATFORMS
from model_project_constructor.schemas.v1.data import DataReport
from model_project_constructor.schemas.v1.intake import IntakeReport
from model_project_constructor.schemas.v1.repo import RepoProjectResult, RepoTarget
from tests.agents.website.loopback import serving_raw
from tests.agents.website.success_hosts import (
    HOSTILE,
    SHIPPED,
    TOKEN,
    Shipped,
    is_clean,
    serve,
)

FILES = {"README.md": "# r\n", "analysis/01 plan.qmd": "q\n"}
URL = "https://h.example/g/p"

#: Not route 8, and open: GitHub's ``commit_files`` sends the host's own commit sha back in the body
#: of its next request, and ``httpx`` cannot encode a lone surrogate there, so the run raises
#: ``UnicodeEncodeError`` (not a ``RepoClientError``) BEFORE the scrub, which is on what the method
#: returns, can see the value. ``strict``: the day that is fixed these go red and the marks go.
GITHUB_REUSES_THE_SHA = pytest.mark.xfail(
    strict=True,
    raises=UnicodeEncodeError,
    reason="BACKLOG.md: an adapter puts a host's value into its next request unscrubbed "
    "(GitHub's commit sha in a PATCH body, parent_sha in a path)",
)


def _commit_cases() -> list[object]:
    return [
        pytest.param(
            shipped,
            kind,
            id=f"{shipped.name}-{kind}",
            marks=[GITHUB_REUSES_THE_SHA]
            if shipped.host == "github" and kind == "lone-surrogate"
            else [],
        )
        for shipped in SHIPPED
        for kind in sorted(HOSTILE)
    ]


def _assert_result_is_clean(result: RepoProjectResult) -> None:
    for name in ("project_url", "project_id", "initial_commit_sha"):
        value = getattr(result, name)
        assert is_clean(value), (name, value)


# ---------------------------------------------------------------------------------------------
# The adapters, called directly.
# ---------------------------------------------------------------------------------------------


def _create(shipped: Shipped, project: dict[str, object]) -> ProjectInfo:
    with serving_raw(serve(shipped.router(project, "abc"))) as server:
        return shipped.make(server.url).create_project(
            namespace=shipped.namespace, name="n", visibility="private"
        )


def _commit(shipped: Shipped, commit_id: object) -> CommitInfo:
    project = shipped.project_reply(id_text="", url=URL, branch="main")
    with serving_raw(serve(shipped.router(project, commit_id))) as server:
        adapter = shipped.make(server.url)
        info = adapter.create_project(namespace=shipped.namespace, name="n", visibility="private")
        return adapter.commit_files(
            project_id=info.id, branch=info.default_branch, files=FILES, message="m"
        )


@pytest.mark.parametrize("kind", sorted(HOSTILE))
@pytest.mark.parametrize("shipped", SHIPPED, ids=lambda s: s.name)
def test_create_project_returns_every_field_scrubbed(shipped: Shipped, kind: str) -> None:
    text = HOSTILE[kind]
    raw = (shipped.raw_id(text), f"https://h.example/g/p{text}tail", f"main{text}")
    info = _create(shipped, shipped.project_reply(id_text=raw[0], url=raw[1], branch=raw[2]))
    assert info == ProjectInfo(*(scrub_host_text(value) for value in raw))
    assert is_clean(info.id) and is_clean(info.url) and is_clean(info.default_branch)


@pytest.mark.parametrize(("shipped", "kind"), _commit_cases())
def test_commit_files_returns_the_sha_scrubbed_and_the_paths_as_they_are(
    shipped: Shipped, kind: str
) -> None:
    commit = _commit(shipped, f"abc{HOSTILE[kind]}def")
    assert commit.sha == scrub_host_text(f"abc{HOSTILE[kind]}def")
    assert is_clean(commit.sha)
    # The paths are the caller's own: a path with a space in it must not be collapsed.
    assert commit.files_committed == sorted(FILES)
    assert "analysis/01 plan.qmd" in commit.files_committed


@pytest.mark.parametrize("shipped", SHIPPED, ids=lambda s: s.name)
def test_a_reply_with_nothing_to_remove_comes_back_exactly_as_the_host_wrote_it(
    shipped: Shipped,
) -> None:
    """The scrub changes text only when there is something to remove: an address with a port, a
    query, a fragment and non-ASCII letters, a GitHub ``owner/name``, a branch with a slash, a dot,
    an underscore and a hyphen, and a full sha."""
    url = "https://gitlab.exämple.org:8443/g/sub/p-1?x=1&y=2#frag"
    sha = "0123456789abcdef0123456789abcdef01234567"
    project = shipped.project_reply(id_text="", url=url, branch="release/1.0_rc-2")
    info = _create(shipped, project)
    assert info == ProjectInfo(
        id="42" if shipped.host == "gitlab" else "g/n", url=url, default_branch="release/1.0_rc-2"
    )
    assert _commit(shipped, sha).sha == sha


@pytest.mark.parametrize("shipped", SHIPPED, ids=lambda s: s.name)
def test_a_host_that_echoes_the_token_in_a_success_reply_does_not_get_it_into_the_values(
    shipped: Shipped,
) -> None:
    """The party that echoes the request headers can put the token in a ``2xx`` as it can in an
    error page, and the result is saved. (``test_run_pipeline_website_crash_resume.py`` had a host
    do this with the project id.)"""
    project = shipped.project_reply(
        id_text=shipped.raw_id(f"-{TOKEN}"),
        url=f"https://h.example/{TOKEN}/p",
        branch=f"main-{TOKEN}",
    )
    info = _create(shipped, project)
    assert TOKEN not in repr(info)
    assert REDACTED in info.id and REDACTED in info.url and REDACTED in info.default_branch
    assert TOKEN not in repr(_commit(shipped, f"sha-{TOKEN}"))
    assert REDACTED in _commit(shipped, f"sha-{TOKEN}").sha


# ---------------------------------------------------------------------------------------------
# The agent over each adapter: what an operator sees.
# ---------------------------------------------------------------------------------------------


def _run(
    client: RepoClient,
    intake: IntakeReport,
    data: DataReport,
    target: RepoTarget,
    *,
    ci_platform: str,
) -> RepoProjectResult:
    agent = WebsiteAgent(client, ci_platform=ci_platform)  # type: ignore[arg-type]
    # A failed commit is retried with a 1 s, 2 s, 4 s backoff; nothing here waits for it.
    agent.graph = build_website_graph(client, sleep=lambda _seconds: None)
    return agent.run(intake, data, target)


def _run_against(
    shipped: Shipped,
    project: dict[str, object],
    commit_id: object,
    intake: IntakeReport,
    data: DataReport,
) -> RepoProjectResult:
    target = RepoTarget(
        host_url="https://unused.example",
        namespace=shipped.namespace,
        project_name_hint="Route 8",
        visibility="private",
    )
    with serving_raw(serve(shipped.router(project, commit_id))) as server:
        return _run(shipped.make(server.url), intake, data, target, ci_platform=shipped.host)


@pytest.mark.parametrize(("shipped", "kind"), _commit_cases())
def test_the_result_of_a_run_holds_no_control_code_from_an_address_or_a_commit_id(
    shipped: Shipped,
    kind: str,
    intake_report: IntakeReport,
    data_report: DataReport,
) -> None:
    text = HOSTILE[kind]
    url = f"https://h.example/g/p{text}tail"
    project = shipped.project_reply(id_text="", url=url, branch="main")
    result = _run_against(shipped, project, f"abc{text}def", intake_report, data_report)
    assert result.status == "COMPLETE", result.failure_reason
    _assert_result_is_clean(result)
    assert result.project_url == scrub_host_text(url)
    assert result.initial_commit_sha == scrub_host_text(f"abc{text}def")


@pytest.mark.parametrize("kind", sorted(HOSTILE))
@pytest.mark.parametrize("shipped", SHIPPED, ids=lambda s: s.name)
def test_a_project_id_with_a_control_code_is_a_result_not_a_crash(
    shipped: Shipped,
    kind: str,
    intake_report: IntakeReport,
    data_report: DataReport,
) -> None:
    """The id goes back to the host in a request path. ``httpx`` refuses a path with a control
    character, and the refusal (``InvalidURL``) is not a ``RepoClientError``, so it left the agent
    as a crash after the host had already made the project. Cleaned, the id either still names the
    project (a control code at the end just disappears: ``42 + BEL`` is ``42``) or names nothing, in
    which case the host answers 404 and the commit fails as any other failed commit does."""
    raw_id = shipped.raw_id(HOSTILE[kind])
    project = shipped.project_reply(id_text=raw_id, url=URL, branch="main")
    result = _run_against(shipped, project, "abc", intake_report, data_report)
    names_the_project = scrub_host_text(raw_id) == shipped.raw_id("")
    assert result.status == ("COMPLETE" if names_the_project else "FAILED"), result.failure_reason
    _assert_result_is_clean(result)
    if not names_the_project:
        assert result.failure_reason is not None
        assert is_clean(result.failure_reason)
        assert "repo_error_retry_exhausted" in result.failure_reason


@pytest.mark.parametrize("kind", sorted(HOSTILE))
@pytest.mark.parametrize("shipped", SHIPPED[1:], ids=lambda s: s.name)
def test_a_default_branch_with_a_control_code_is_a_result_not_a_crash(
    shipped: Shipped,
    kind: str,
    intake_report: IntakeReport,
    data_report: DataReport,
) -> None:
    """GitHub puts the branch in a request path as well (GitLab sends it in a JSON body, where it
    cannot be refused by the client, so it is held by the direct tests above)."""
    branch = f"main{HOSTILE[kind]}"
    project = shipped.project_reply(id_text="", url=URL, branch=branch)
    result = _run_against(shipped, project, "abc", intake_report, data_report)
    names_the_branch = scrub_host_text(branch) == "main"
    assert result.status == ("COMPLETE" if names_the_branch else "FAILED"), result.failure_reason
    if not names_the_branch:
        assert result.failure_reason is not None
        assert is_clean(result.failure_reason)


def test_a_client_that_is_not_an_adapter_is_not_touched(
    intake_report: IntakeReport,
    data_report: DataReport,
    repo_target: RepoTarget,
) -> None:
    """The limit, stated by a test so it cannot be forgotten: the scrub is the two adapters', and
    ``scrubbed_errors`` has the same one. A ``RepoClient`` of someone else's owns its own values."""

    @dataclass
    class Stub:
        def create_project(self, *, namespace: str, name: str, visibility: str) -> ProjectInfo:
            return ProjectInfo(id="42", url="https://h/p\x1b[2J", default_branch="main")

        def commit_files(
            self, *, project_id: str, branch: str, files: dict[str, str], message: str
        ) -> CommitInfo:
            return CommitInfo(sha="abc", files_committed=sorted(files))

    result = _run(Stub(), intake_report, data_report, repo_target, ci_platform="gitlab")
    assert result.project_url == "https://h/p\x1b[2J"


# ---------------------------------------------------------------------------------------------
# The registry.
# ---------------------------------------------------------------------------------------------

PROTOCOL_METHODS = sorted(
    name
    for name, member in vars(RepoClient).items()
    if not name.startswith("_") and callable(member)
)


@pytest.mark.parametrize("host", sorted(REPO_PLATFORMS))
def test_every_registered_host_scrubs_every_value_of_the_protocol(host: str) -> None:
    """The pipeline script builds its adapter from this registry. A host added to it, or a method
    added to ``RepoClient``, whose adapter does not return through ``scrubbed_values`` would reopen
    the leak without any test above noticing, because they name the two adapters and the two
    methods: this goes red instead. The marker is set by ``scrubbed_values`` alone."""
    adapter = REPO_PLATFORMS[host].adapter_factory(
        host_url="http://127.0.0.1:9", private_token=TOKEN
    )
    assert PROTOCOL_METHODS
    for name in PROTOCOL_METHODS:
        method = getattr(type(adapter), name)
        assert getattr(method, "__scrubs_host_values__", False) is True, (host, name)
