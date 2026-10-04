"""A reply nested more deeply than any host sends fails as a ``RepoClientError``.

Session 282 filed and Session 283 closed three crashes in which a value a host (or the caller) chose
left an adapter as something that is not a ``RepoClientError``; this is the second. The adapters
read a reply with ``response.json()`` and catch ``ValueError``. ``json`` raises ``RecursionError``,
which is not one, for a body nested deeply enough, and every supported CPython has such a depth
(measured by bisection: 995 levels on 3.11.15, 9,998 on 3.12.13, 9,999 on 3.13.5, 116,211 on
3.14.6). So the website command ended in a traceback and the pipeline saved ``unexpected_error:
RecursionError``, possibly after the host had made the project. The same read sits in each
adapter's name-conflict check, which runs on a 4xx body.

A body that does parse is not safe either: a value nested a little under the parser's limit goes
back to the host inside the next request (GitHub's shas, GitLab's group id), and ``httpx`` writes a
body with ``json.dumps``, which gives up a little sooner (994, 9,997, 9,998 and about 104,600), so
the request could not be built (``RecursionError`` out of ``build_request``). That window is one
level wide on 3.11 and about 12,000 on 3.14, so the repair is not a catch at either end:
``reply_json`` refuses a reply nested past ``MAX_REPLY_NESTING``, which is far above anything a
host sends and far below the lowest depth at which any supported CPython fails. It also refuses a
reply whose deep part nothing reads, which an unlimited read accepted below those depths, and that
is a choice (``BACKLOG.md``). ``test_host_reuse_text.py`` holds the other requests an adapter
cannot build.

Three levels, as for the neighbouring failure: the helper, each place an adapter reads a reply (a
real socket that RECORDS what reached it, so a value that was refused is shown never to have been
sent on), and the whole run in ``tests/scripts/test_run_pipeline_website_crash_resume.py``.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx
import pytest

from model_project_constructor.agents.website._host_text import MAX_REPLY_NESTING, reply_json
from model_project_constructor.agents.website._http import RepoHttpClient
from model_project_constructor.agents.website.protocol import (
    RepoClientError,
    RepoNameConflictError,
)
from tests.agents.website.loopback import serving_raw
from tests.agents.website.success_hosts import SHIPPED, Shipped, is_clean, serve

URL = "https://h.example/g/p"
FILES = {"README.md": "# r\n"}
GITLAB = SHIPPED[0]
GITHUB = SHIPPED[1]

#: Deep enough to raise ``RecursionError`` out of ``json`` on 3.11 to 3.13 and nested far past the
#: limit on 3.14, whose own failing depth (116,211) this stays under: there it parses and the limit
#: refuses it. So this does not run the ``RecursionError`` handler on every interpreter; the stub
#: below does.
DEEP = 100_000


def nest(depth: int) -> bytes:
    """Valid JSON: ``depth`` arrays, one inside the next."""
    return b"[" * depth + b"]" * depth


def nest_objects(depth: int) -> bytes:
    return b'{"a":' * depth + b"1" + b"}" * depth


def _reply(body: bytes, status: int = 200) -> httpx.Response:
    return httpx.Response(status, content=body, headers={"content-type": "application/json"})


# ---------------------------------------------------------------------------------------------
# The helper
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        b'{"id": 7, "web_url": "https://h.example/g/p"}',
        b'{"object": {"sha": "abc"}}',
        b"[1, 2, 3]",
        b"null",
        b'"text"',
        b"[" + b",".join(b'{"k": [1, {"j": 2}]}' for _ in range(5_000)) + b"]",
        nest(MAX_REPLY_NESTING),
        nest_objects(MAX_REPLY_NESTING),
    ],
    ids=[
        "project",
        "ref",
        "array",
        "null",
        "string",
        "wide",
        "arrays-at-limit",
        "objects-at-limit",
    ],
)
def test_a_reply_within_the_limit_is_what_the_library_returns(body: bytes) -> None:
    assert reply_json(_reply(body)) == json.loads(body)


@pytest.mark.parametrize("depth", [MAX_REPLY_NESTING + 1, 1_000, DEEP])
@pytest.mark.parametrize("shape", [nest, nest_objects], ids=["arrays", "objects"])
def test_a_reply_nested_past_the_limit_is_a_value_error(
    depth: int, shape: Callable[[int], bytes]
) -> None:
    """``ValueError`` is what both adapters already catch for a body that is not JSON. Whether the
    library itself fails on it (``RecursionError`` from ``json``, from 995 levels on 3.11 and a
    higher depth on each later version) or parses it (the first case everywhere, the second on
    3.12 and later, the third on 3.14) makes no difference."""
    with pytest.raises(ValueError, match="nests more than") as caught:
        reply_json(_reply(shape(depth)))
    # Raised after the handler that swallowed the ``RecursionError``: its traceback, which holds
    # thousands of frames, is not kept reachable behind this one.
    assert caught.value.__cause__ is None and caught.value.__context__ is None
    assert str(caught.value) == f"the reply nests more than {MAX_REPLY_NESTING} levels deep"


class _ParserRunsOutOfStack(httpx.Response):
    """A reply whose ``json()`` raises what ``json`` raises for a body nested past its depth."""

    def json(self, **kwargs: object) -> object:
        raise RecursionError("maximum recursion depth exceeded while decoding a JSON array")


def test_a_recursion_error_from_the_parser_is_a_value_error_on_every_interpreter() -> None:
    """The handler itself, which no input runs on every CPython: ``DEEP`` stays under the depth at
    which 3.14's parser fails. Deleting the handler is invisible there without this."""
    with pytest.raises(ValueError, match="nests more than") as caught:
        reply_json(_ParserRunsOutOfStack(200))
    assert caught.value.__cause__ is None and caught.value.__context__ is None


def test_the_message_holds_none_of_the_hosts_words() -> None:
    """Its text is this module's own: a deep reply that carries text of a host's choosing in
    shallow places (a forged status line, a window-title escape) is not quoted back."""
    forged = "\x1b]0;PWNED\x07 Status:  COMPLETE"
    body = b'{"message": "' + json.dumps(forged)[1:-1].encode() + b'", "deep": ' + nest(DEEP) + b"}"
    with pytest.raises(ValueError) as caught:
        reply_json(_reply(body))
    assert str(caught.value) == f"the reply nests more than {MAX_REPLY_NESTING} levels deep"


def test_a_reply_whose_deep_part_nothing_reads_is_refused_too() -> None:
    """The cost of a limit over a catch, stated and held: the whole reply is measured, not only the
    values the adapters read, so ``{"id": 7, "unused": <100 levels>}`` is refused although an
    unlimited read accepted it (100 levels parse on every supported CPython)."""
    body = b'{"id": 7, "web_url": "https://h.example/g/p", "unused": ' + nest(100) + b"}"
    with pytest.raises(ValueError, match="nests more than"):
        reply_json(_reply(body))


def test_the_limit_counts_levels_of_either_kind_together() -> None:
    """``[{"a": [{"a": ...}]}]`` nests by the sum of its arrays and objects."""

    def mixed(pairs: int) -> bytes:
        return b'[{"a":' * pairs + b"1" + b"}]" * pairs

    at_limit = mixed(MAX_REPLY_NESTING // 2)
    past_limit = mixed(MAX_REPLY_NESTING // 2 + 1)
    assert reply_json(_reply(at_limit)) == json.loads(at_limit)
    with pytest.raises(ValueError, match="nests more than"):
        reply_json(_reply(past_limit))


def test_a_body_that_is_not_json_keeps_the_librarys_own_error() -> None:
    with pytest.raises(json.JSONDecodeError):
        reply_json(_reply(b'{"id": '))


def test_what_it_returns_can_always_be_written_into_the_next_request() -> None:
    """The reason there is a limit and not a catch: a value ``reply_json`` lets through, at its
    deepest, goes into a request body, a path and a message on this interpreter without
    ``RecursionError``. Nest it where GitHub's tree call puts a sha (three levels down)."""
    value = reply_json(_reply(nest(MAX_REPLY_NESTING)))
    client = RepoHttpClient()
    tree = [{"path": "a", "mode": "100644", "type": "blob", "sha": value}]
    in_a_body = client.build_request(
        "POST", "https://h.example/x", json={"base_tree": value, "tree": tree}
    )
    in_a_path = client.build_request("GET", f"https://h.example/repos/g/n/git/commits/{value}")
    assert in_a_body.content and in_a_path.url.path.startswith("/repos/g/n/git/commits/")
    assert str(value)


# ---------------------------------------------------------------------------------------------
# Each place an adapter reads a reply
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Site:
    """One reply an adapter parses: the request it answers and what the adapter writes next."""

    name: str
    shipped: Shipped
    call: str
    method: str
    prefix: str
    status: int
    #: A body that parses, with ``{N}`` where the nested value goes: the shape the adapter reads
    #: the value from. Empty for a reply whose value is not written into a later request.
    shaped: str
    #: The request that would carry the value, which must then never reach the host.
    carries: tuple[str, str] | None

    @property
    def wrappers(self) -> int:
        """How many arrays or objects ``shaped`` puts around the value; they count toward the
        reply's nesting like any other."""
        return self.shaped.count("{") - 1

    def with_value_nested(self, reply_depth: int) -> bytes:
        """``shaped``, with the value as deep as makes the whole reply ``reply_depth`` levels."""
        value = nest(reply_depth - self.wrappers).decode()
        return self.shaped.replace("{N}", value).encode()


SITES = [
    Site(
        "gitlab-group-lookup", GITLAB, "create_project", "GET", "/api/v4/groups/", 200,
        '{"id": {N}}', ("POST", "/api/v4/projects"),
    ),
    Site(
        "gitlab-create", GITLAB, "create_project", "POST", "/api/v4/projects", 201,
        "", None,
    ),
    Site(
        "gitlab-commit", GITLAB, "commit_files", "POST", "/api/v4/projects/42/repository/commits",
        201, "", None,
    ),
    Site(
        "github-create", GITHUB, "create_project", "POST", "/orgs/g/repos", 201,
        "", None,
    ),
    Site(
        "github-parent", GITHUB, "commit_files", "GET", "/repos/g/n/git/ref/heads/main", 200,
        '{"object": {"sha": {N}}}', ("GET", "/repos/g/n/git/commits/"),
    ),
    Site(
        "github-base-tree", GITHUB, "commit_files", "GET", "/repos/g/n/git/commits/", 200,
        '{"tree": {"sha": {N}}}', ("POST", "/repos/g/n/git/trees"),
    ),
    Site(
        "github-blob", GITHUB, "commit_files", "POST", "/repos/g/n/git/blobs", 201,
        '{"sha": {N}}', ("POST", "/repos/g/n/git/trees"),
    ),
    Site(
        "github-tree", GITHUB, "commit_files", "POST", "/repos/g/n/git/trees", 201,
        '{"sha": {N}}', ("POST", "/repos/g/n/git/commits"),
    ),
    Site(
        "github-commit", GITHUB, "commit_files", "POST", "/repos/g/n/git/commits", 201,
        '{"sha": {N}}', ("PATCH", "/repos/g/n/git/refs/heads/main"),
    ),
]

#: The same two create calls answered with the status each host uses for "that name is taken". The
#: adapters read the body of such a reply to decide whether it IS a name conflict, and they read it
#: with the same ``response.json()``.
CONFLICT_SITES = [
    Site(
        "gitlab-conflict", GITLAB, "create_project", "POST", "/api/v4/projects", 409,
        "", None,
    ),
    Site(
        "github-conflict", GITHUB, "create_project", "POST", "/orgs/g/repos", 422,
        "", None,
    ),
]


def _raw(status: int, body: bytes) -> bytes:
    reason = {200: "OK", 201: "Created", 409: "Conflict", 422: "Unprocessable Entity"}[status]
    head = (
        f"HTTP/1.1 {status} {reason}\r\nContent-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n"
    )
    return head.encode() + body


def _run(site: Site, hostile: bytes) -> tuple[object, list[tuple[str, str]]]:
    """The adapter's call against a host that answers the whole sequence honestly except for the one
    request ``site`` names, which it answers with ``hostile``; what happened (the result, or the
    exception, whatever its class) and what reached the host."""
    shipped = site.shipped
    project = shipped.project_reply(id_text="", url=URL, branch="main")
    honest = serve(shipped.router(project, "c1"))
    seen: list[tuple[str, str]] = []

    def reply(request: bytes) -> bytes:
        method, target, _ = request.split(b"\r\n", 1)[0].decode("latin-1").split(" ", 2)
        path = urlsplit(target).path
        seen.append((method, path))
        if method == site.method and path.startswith(site.prefix):
            return _raw(site.status, hostile)
        return honest(request)

    with serving_raw(reply) as server:
        adapter = shipped.make(server.url)
        try:
            if site.call == "create_project":
                outcome: object = adapter.create_project(
                    namespace=shipped.namespace, name="n", visibility="private"
                )
            else:
                outcome = adapter.commit_files(
                    project_id="42" if shipped.host == "gitlab" else "g/n",
                    branch="main",
                    files=FILES,
                    message="m",
                )
        except Exception as error:
            outcome = error
    return outcome, seen


def _assert_a_repo_error(outcome: object) -> RepoClientError:
    assert isinstance(outcome, RepoClientError), repr(outcome)
    assert not isinstance(outcome, RepoNameConflictError)
    assert is_clean(str(outcome)), str(outcome)
    # A message is bounded: the host's body is not copied into it whole.
    assert len(str(outcome)) < 2_000
    return outcome


@pytest.mark.parametrize("site", [*SITES, *CONFLICT_SITES], ids=lambda s: s.name)
def test_a_reply_nested_past_any_limit_fails_as_a_repo_client_error(site: Site) -> None:
    outcome, _ = _run(site, nest(DEEP))
    error = _assert_a_repo_error(outcome)
    if site.status in (409, 422):
        # Not a name conflict, which is what a body that cannot be read must not be taken for.
        assert str(site.status) in str(error)
    else:
        assert "invalid JSON body" in str(error)
        assert "nests more than" in str(error)


@pytest.mark.parametrize("site", [s for s in SITES if s.carries], ids=lambda s: s.name)
def test_a_value_nested_just_past_the_limit_is_refused_before_it_is_written_back(
    site: Site,
) -> None:
    """The window between what a parser reads and what a body can hold. The value is nested only
    one level past the limit, so on every interpreter the old code read it and sent it on: this
    proves the refusal is the limit and not a failure of either end. The request that would have
    carried it must be missing from what reached the host."""
    assert site.carries is not None
    outcome, seen = _run(site, site.with_value_nested(MAX_REPLY_NESTING + 1))
    error = _assert_a_repo_error(outcome)
    assert "invalid JSON body" in str(error)
    method, prefix = site.carries
    assert not any(m == method and p.startswith(prefix) for m, p in seen), seen


@pytest.mark.parametrize("site", [s for s in SITES if s.carries], ids=lambda s: s.name)
def test_a_value_nested_to_the_limit_is_still_sent_on(site: Site) -> None:
    """The control: the limit refuses a nest past it and nothing at it, so the request that carries
    the value is sent (the host's answer to it is not the subject)."""
    assert site.carries is not None
    outcome, seen = _run(site, site.with_value_nested(MAX_REPLY_NESTING))
    assert not (
        isinstance(outcome, RepoClientError) and "invalid JSON body" in str(outcome)
    ), repr(outcome)
    method, prefix = site.carries
    assert any(m == method and p.startswith(prefix) for m, p in seen), seen


@pytest.mark.parametrize("site", SITES, ids=lambda s: s.name)
def test_the_error_for_a_deep_success_reply_holds_none_of_the_hosts_words(site: Site) -> None:
    """The text is this repository's own for a ``2xx`` reply (a ``4xx`` body is the host's error
    page, shown scrubbed and cut, as for any failure). The deep reply carries a marker in a shallow
    place, which must not come back."""
    marker = "FORGED-STATUS-LINE-9f3k"
    hostile = b'{"message": "' + marker.encode() + b'", "deep": ' + nest(DEEP) + b"}"
    outcome, _ = _run(site, hostile)
    error = _assert_a_repo_error(outcome)
    assert marker not in str(error)
    assert "the reply nests more than" in str(error)
