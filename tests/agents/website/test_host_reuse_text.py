"""A value a repository host sent, which an adapter writes into its next request, fails cleanly.

Session 281's review filed *An adapter puts a value the host sent into its next request*; Session
282 closed it, and ``BACKLOG.md`` keeps the two points that were never part of the fix under the
title *The id and the branch go into request paths unquoted, and one wiki sentence is now
imprecise*. Route 8 scrubs what ``create_project`` and ``commit_files`` RETURN; it cannot reach a
value an adapter reads from one reply and writes into the next request: GitHub's ``parent_sha`` (in
a path), its base-tree, blob, tree and commit shas (in JSON bodies) and GitLab's group id (in a JSON
body). ``httpx`` refuses to build some of those requests: ``InvalidURL`` for a C0 control or DEL in
a path, and ``ValueError`` for a lone surrogate (``UnicodeEncodeError``) in a path or, from 0.28, in
a body, and from 0.28 for a ``NaN`` or an infinity in a body. None is an ``httpx.HTTPError``, so no
``except`` in an adapter caught any, none is a ``RepoClientError``, and the website command ended in
a traceback and the pipeline in ``unexpected_error``, possibly after the host had made the project.

``RepoHttpClient.build_request`` now turns them into the error the adapters already catch. Three
levels, each against a real socket that RECORDS what reached it, because a refused request must be
absent from that list: a request sent with something cleaned out of it would also have "failed
cleanly", and only the list tells the two apart. ``test_repo_http_client.py`` holds the client.
"""

from __future__ import annotations

import pytest

from model_project_constructor.agents.website._http import UNBUILDABLE_REQUEST_TEXT
from model_project_constructor.agents.website.agent import WebsiteAgent
from model_project_constructor.agents.website.graph import build_website_graph
from model_project_constructor.agents.website.protocol import CommitInfo, RepoClientError
from model_project_constructor.schemas.v1.data import DataReport
from model_project_constructor.schemas.v1.intake import IntakeReport
from model_project_constructor.schemas.v1.repo import RepoProjectResult, RepoTarget
from tests.agents.website.loopback import serving_raw
from tests.agents.website.success_hosts import (
    HOSTILE,
    HTTPX_WRITES_JSON_AS_UTF8,
    SHIPPED,
    Shipped,
    is_clean,
    recording,
    serve,
)

FILES = {"README.md": "# r\n", "analysis/01  plan.qmd": "q\n"}
URL = "https://h.example/g/p"
GITHUB = SHIPPED[1]
GITLAB = SHIPPED[0]

#: The one request that can never be built for each value, as (method, path prefix): where the
#: adapter writes the value, and so what must be missing from what reached the host.
REFUSED_AT = {
    "parent_sha": ("GET", "/repos/g/n/git/commits/"),
    "base_tree_sha": ("POST", "/repos/g/n/git/trees"),
    "blob_sha": ("POST", "/repos/g/n/git/trees"),
    "tree_sha": ("POST", "/repos/g/n/git/commits"),
    "commit_sha": ("PATCH", "/repos/g/n/git/refs/heads/main"),
}
#: The values GitHub's git-data calls hand back, which go into a JSON body next.
BODY_SHAS = ["base_tree_sha", "blob_sha", "tree_sha", "commit_sha"]
#: What ``httpx`` 0.28 cannot write into a JSON body: a lone surrogate, ``NaN``, an infinity (a
#: reply of ``{"sha": NaN}`` parses to a float; the routers write one with ``json.dumps``).
UNENCODABLE = {
    "lone-surrogate": f"abc{HOSTILE['lone-surrogate']}def",
    "nan": float("nan"),
    "infinity": float("inf"),
}
#: Every kind of text but the C1 control, which ``httpx`` percent-encodes in a path instead of
#: refusing (``test_repo_http_client.py`` holds that), so the request is sent and the host answers.
REFUSED_IN_A_PATH = sorted(kind for kind in HOSTILE if kind != "c1-csi")
skip_before_0_28 = pytest.mark.skipif(
    not HTTPX_WRITES_JSON_AS_UTF8,
    reason="httpx < 0.28 escapes a lone surrogate in a JSON body and sends a NaN or an infinity",
)


def _reached(seen: list[tuple[str, str]], where: tuple[str, str]) -> bool:
    method, prefix = where
    return any(m == method and p.startswith(prefix) for m, p in seen)


def _commit_files(
    shas: dict[str, object], commit_sha: object = "c1"
) -> tuple[CommitInfo | Exception, list[tuple[str, str]]]:
    """GitHub's ``commit_files`` against a host that answers with ``shas``; what happened (the
    result, or the exception, whatever its class) and what reached the host."""
    router, seen = recording(GITHUB.router({}, commit_sha, shas=shas))
    with serving_raw(serve(router)) as server:
        adapter = GITHUB.make(server.url)
        try:
            outcome: CommitInfo | Exception = adapter.commit_files(
                project_id="g/n", branch="main", files=FILES, message="m"
            )
        except Exception as error:
            outcome = error
    return outcome, seen


def _create_project(group_id: object) -> tuple[object, list[tuple[str, str]]]:
    router, seen = recording(GITLAB.router({"id": 42, "web_url": URL}, "abc", group_id=group_id))
    with serving_raw(serve(router)) as server:
        adapter = GITLAB.make(server.url)
        try:
            outcome: object = adapter.create_project(
                namespace=GITLAB.namespace, name="n", visibility="private"
            )
        except Exception as error:
            outcome = error
    return outcome, seen


def _assert_refused_cleanly(outcome: object, *, said: str | None = None) -> None:
    assert isinstance(outcome, RepoClientError), repr(outcome)
    assert UNBUILDABLE_REQUEST_TEXT in str(outcome)
    assert is_clean(str(outcome)), str(outcome)
    assert "PWNED-TITLE" not in str(outcome) and "Status:  COMPLETE" not in str(outcome)
    # ``scrubbed_errors`` raises a new error after its handler: nothing is chained behind it, so
    # ``httpx``'s own message (which repeats part of what it refused) is not reachable from it.
    assert outcome.__cause__ is None and outcome.__context__ is None
    for httpx_words in (
        "non-printable",
        "surrogates not allowed",
        "codec can't encode",
        "not JSON compliant",
    ):
        assert httpx_words not in str(outcome)
    if said is not None:
        assert said in str(outcome)


# ---------------------------------------------------------------------------------------------
# The controls: the routers answer the whole sequence, so a refusal below is the refusal.
# ---------------------------------------------------------------------------------------------


def test_github_commit_with_ordinary_shas_completes_and_reaches_every_request() -> None:
    outcome, seen = _commit_files({})
    assert outcome == CommitInfo(sha="c1", files_committed=sorted(FILES))
    for where in REFUSED_AT.values():
        assert _reached(seen, where), where


def test_gitlab_create_project_with_an_ordinary_group_id_completes() -> None:
    outcome, seen = _create_project(7)
    assert getattr(outcome, "id", None) == "42", repr(outcome)
    assert ("POST", "/api/v4/projects") in seen


# ---------------------------------------------------------------------------------------------
# The adapters, called directly.
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("kind", REFUSED_IN_A_PATH)
def test_a_parent_sha_httpx_cannot_put_in_a_path_is_a_clean_error_and_is_never_sent(
    kind: str,
) -> None:
    """``InvalidURL`` for a control code, ``UnicodeEncodeError`` for a lone surrogate. Both from
    every ``httpx`` this project admits."""
    outcome, seen = _commit_files({"parent_sha": f"abc{HOSTILE[kind]}def"})
    _assert_refused_cleanly(outcome, said="commit_files failed (project='g/n', branch='main')")
    assert not _reached(seen, REFUSED_AT["parent_sha"]), seen
    # The first requests were made: the host was told what the adapter had to say before this.
    assert ("GET", "/repos/g/n/git/ref/heads/main") in seen


def test_a_parent_sha_httpx_can_encode_still_names_the_parent_and_the_commit_completes() -> None:
    """The limit of the refusal is ``httpx``'s: a C1 control is percent-encoded and sent, the host
    reads it as the same sha, and nothing is refused that could have been built."""
    outcome, seen = _commit_files({"parent_sha": f"abc{HOSTILE['c1-csi']}def"})
    assert outcome == CommitInfo(sha="c1", files_committed=sorted(FILES)), repr(outcome)
    assert _reached(seen, REFUSED_AT["parent_sha"])


@skip_before_0_28
@pytest.mark.parametrize("kind", sorted(UNENCODABLE))
@pytest.mark.parametrize("site", BODY_SHAS)
def test_a_sha_httpx_cannot_encode_in_a_body_is_a_clean_error_and_is_never_sent(
    site: str, kind: str
) -> None:
    """The commit sha comes back from the host's ``POST``, and the others from the ``GET`` and
    ``POST`` before it; each is written into a later body."""
    value = UNENCODABLE[kind]
    if site == "commit_sha":
        outcome, seen = _commit_files({}, commit_sha=value)
    else:
        outcome, seen = _commit_files({site: value})
    _assert_refused_cleanly(outcome, said="commit_files failed (project='g/n', branch='main')")
    assert not _reached(seen, REFUSED_AT[site]), seen


@pytest.mark.parametrize("kind", sorted(set(HOSTILE) - {"lone-surrogate"}))
@pytest.mark.parametrize("site", BODY_SHAS)
def test_a_control_code_in_a_body_sha_is_escaped_by_json_and_the_commit_completes(
    site: str, kind: str
) -> None:
    """Not refused, because nothing is wrong with the request: JSON writes a C0 control as
    ``\\u001b`` and ``httpx`` 0.28 writes DEL and a C1 control as they are. Held so the fix is not
    widened to refuse what ``httpx`` builds."""
    value = f"abc{HOSTILE[kind]}def"
    outcome, _ = (
        _commit_files({}, commit_sha=value)
        if site == "commit_sha"
        else _commit_files({site: value})
    )
    assert isinstance(outcome, CommitInfo), repr(outcome)


@skip_before_0_28
@pytest.mark.parametrize("kind", sorted(UNENCODABLE))
def test_a_group_id_httpx_cannot_encode_is_a_clean_error_and_the_project_is_never_asked_for(
    kind: str,
) -> None:
    """GitLab's group id goes into the create-project body as ``namespace_id``."""
    outcome, seen = _create_project(UNENCODABLE[kind])
    _assert_refused_cleanly(outcome, said="create_project failed for 'n'")
    assert ("POST", "/api/v4/projects") not in seen, seen
    assert any(p.startswith("/api/v4/groups/") for _, p in seen)


# ---------------------------------------------------------------------------------------------
# The agent over each adapter: what an operator sees.
# ---------------------------------------------------------------------------------------------


def _run(
    shipped: Shipped, router: object, intake: IntakeReport, data: DataReport
) -> tuple[RepoProjectResult, list[tuple[str, str]]]:
    target = RepoTarget(
        host_url="https://unused.example",
        namespace=shipped.namespace,
        project_name_hint="Reuse",
        visibility="private",
    )
    recorded, seen = recording(router)  # type: ignore[arg-type]
    with serving_raw(serve(recorded)) as server:
        client = shipped.make(server.url)
        agent = WebsiteAgent(client, ci_platform=shipped.host)  # type: ignore[arg-type]
        # A failed commit is attempted three times with a 1 s and a 2 s wait; nothing waits here.
        agent.graph = build_website_graph(client, sleep=lambda _seconds: None)
        return agent.run(intake, data, target), seen


def _assert_a_failed_result(result: RepoProjectResult, *, reason: str) -> None:
    assert result.status == "FAILED", result
    assert result.failure_reason is not None
    assert is_clean(result.failure_reason), result.failure_reason
    assert reason in result.failure_reason, result.failure_reason
    assert UNBUILDABLE_REQUEST_TEXT in result.failure_reason, result.failure_reason
    assert "PWNED-TITLE" not in result.failure_reason


@pytest.mark.parametrize(
    "shipped", [s for s in SHIPPED if s.host == "github"], ids=lambda s: s.name
)
@pytest.mark.parametrize("kind", ["osc-title", "del", "lone-surrogate"])
def test_a_run_whose_host_sent_an_unsendable_parent_sha_is_a_failed_result_not_a_crash(
    shipped: Shipped, kind: str, intake_report: IntakeReport, data_report: DataReport
) -> None:
    project = shipped.project_reply(id_text="", url=URL, branch="main")
    router = shipped.router(project, "abc", shas={"parent_sha": f"abc{HOSTILE[kind]}def"})
    result, seen = _run(shipped, router, intake_report, data_report)
    _assert_a_failed_result(result, reason="repo_error_retry_exhausted")
    assert not _reached(seen, REFUSED_AT["parent_sha"]), seen
    # Retried, as any failed commit is: the same first request is made more than once.
    assert sum(1 for m, p in seen if m == "GET" and p == "/repos/g/n/git/ref/heads/main") > 1


@skip_before_0_28
@pytest.mark.parametrize("kind", sorted(UNENCODABLE))
@pytest.mark.parametrize(
    "shipped", [s for s in SHIPPED if s.host == "github"], ids=lambda s: s.name
)
def test_a_run_whose_host_sent_an_unencodable_commit_sha_is_a_failed_result_not_a_crash(
    shipped: Shipped, kind: str, intake_report: IntakeReport, data_report: DataReport
) -> None:
    """The lone-surrogate case is the one ``GITHUB_REUSES_THE_SHA`` held as a strict expected
    failure. The commit is attempted three times: the project and the blobs are made each time."""
    project = shipped.project_reply(id_text="", url=URL, branch="main")
    router = shipped.router(project, UNENCODABLE[kind])
    result, seen = _run(shipped, router, intake_report, data_report)
    _assert_a_failed_result(result, reason="repo_error_retry_exhausted")
    assert not _reached(seen, REFUSED_AT["commit_sha"]), seen


@skip_before_0_28
@pytest.mark.parametrize("kind", sorted(UNENCODABLE))
def test_a_run_whose_host_sent_an_unencodable_group_id_is_a_failed_result_not_a_crash(
    kind: str, intake_report: IntakeReport, data_report: DataReport
) -> None:
    """This fails at ``create_project``, before the host has made anything, and is not retried:
    only a failed COMMIT is. What the host saw is the one group lookup."""
    project = GITLAB.project_reply(id_text="", url=URL, branch="main")
    router = GITLAB.router(project, "abc", group_id=UNENCODABLE[kind])
    result, seen = _run(GITLAB, router, intake_report, data_report)
    assert result.status == "FAILED", result
    assert result.failure_reason is not None
    assert is_clean(result.failure_reason)
    assert result.failure_reason.startswith("repo_error: create_project failed"), result
    assert "repo_error_retry_exhausted" not in result.failure_reason
    assert UNBUILDABLE_REQUEST_TEXT in result.failure_reason, result.failure_reason
    assert [method for method, _ in seen] == ["GET"], seen
