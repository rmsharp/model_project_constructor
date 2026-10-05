"""A reply of the wrong shape fails as a ``RepoClientError`` that names the field it lacked.

An adapter read a host's ``2xx`` reply by subscripting it (``reply["object"]["sha"]``), so a reply
that was valid JSON and not the object the adapter expected ended the call as a bare ``KeyError``
(an empty object) or ``TypeError`` (an array, ``null``, a string, a number), at each of the nine
places an adapter reads one. The website command ended in a traceback and the pipeline saved
``unexpected_error: KeyError`` (Session 275's net), which says a project may exist whether or not a
reply was about one. ``BACKLOG.md`` held it as *A reply of the wrong shape ends as a raw
``KeyError`` or ``TypeError`` out of the adapter*, points 1 and 3; Session 285 closed them.

Each field is checked where it is read (``_host_text.reply_string`` / ``reply_id``) and the failure
names it, in this repository's own words and never the host's: a text field must be a non-empty
string, and an identifier a non-empty string or an integer that is not a boolean. The reply to a
request that CREATES a project says that a project may already exist, as the net does, because the
host answered ``2xx``; that holds for a reply that is not JSON as well (point 3). A wrong shape is
retried on the commit path exactly as a reply that is not JSON is (the operator's ruling), and ends
the run at once on the creation.

Three levels, as for the neighbouring failures: each of the nine places an adapter reads a reply
(a real socket that RECORDS what reached it, so a request that would carry a refused value is shown
never to have been sent), the whole website graph over a real adapter (what the node does with the
error), and the helpers themselves at the foot of the file.
"""

from __future__ import annotations

import ast
import copy
import inspect
import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx
import pytest

from model_project_constructor.agents.website import github_adapter, gitlab_adapter
from model_project_constructor.agents.website._host_text import (
    PROJECT_MAY_EXIST,
    reading_a_creation_reply,
    reply_id,
    reply_object,
    reply_string,
)
from model_project_constructor.agents.website.agent import WebsiteAgent
from model_project_constructor.agents.website.governance_templates import CIHostConfig
from model_project_constructor.agents.website.graph import build_website_graph
from model_project_constructor.agents.website.protocol import (
    RepoClient,
    RepoClientError,
    RepoNameConflictError,
)
from model_project_constructor.agents.website.state import MAX_COMMIT_ATTEMPTS
from model_project_constructor.schemas.v1.data import DataReport
from model_project_constructor.schemas.v1.intake import IntakeReport
from model_project_constructor.schemas.v1.repo import RepoTarget
from tests.agents.website.loopback import serving_raw
from tests.agents.website.success_hosts import SHIPPED, Shipped, is_clean, serve

URL = "https://h.example/g/p"
FILES = {"README.md": "# r\n"}
GITLAB = SHIPPED[0]
GITHUB = SHIPPED[1]
#: The same host answering for a personal account: ``GET /orgs/g`` is a 404, ``GET /users/g`` a
#: 200, and the project is created with ``POST /user/repos``.
GITHUB_USER = SHIPPED[2]

#: A field that must be a non-empty string (an address, a sha, GitHub's ``owner/name``) or an
#: identifier, which GitLab sends as an integer and which may also be a non-empty string.
TEXT = "text"
ID = "id"

#: Deep enough that ``json`` raises ``RecursionError`` on 3.11 to 3.13 and the reply limit refuses
#: it on 3.14 (``test_host_reply_nesting.py``).
DEEP = 100_000

#: Text a host chose, which no message may carry back.
FORGED = "FORGED-STATUS-LINE-7q2z"

#: The words a creation failure ends with; the test asserts a fixed fragment of it so that a
#: constant changed to something else cannot satisfy both sides.
MAY_EXIST = "a project may already exist"


@dataclass(frozen=True)
class Site:
    """One reply an adapter reads: the request it answers, what a good reply holds and which of it
    the adapter uses, and the request that would carry what it read."""

    name: str
    shipped: Shipped
    call: str
    method: str
    prefix: str
    status: int
    #: A reply the adapter accepts.
    honest: dict[str, Any]
    #: Each value the adapter reads from it, in the order it reads them, and what kind it must be.
    fields: dict[tuple[str, ...], str]
    #: The next request, which a refused reply must keep from reaching the host.
    carries: tuple[str, str] | None
    #: Whether this is the reply to a request that creates a project.
    creates: bool = False


SITES = [
    Site(
        "gitlab-group-lookup", GITLAB, "create_project", "GET", "/api/v4/groups/", 200,
        {"id": 7}, {("id",): ID}, ("POST", "/api/v4/projects"),
    ),
    Site(
        "gitlab-create", GITLAB, "create_project", "POST", "/api/v4/projects", 201,
        {"id": 42, "web_url": URL, "default_branch": "main"},
        {("id",): ID, ("web_url",): TEXT}, None, creates=True,
    ),
    Site(
        "gitlab-commit", GITLAB, "commit_files", "POST", "/api/v4/projects/42/repository/commits",
        201, {"id": "c1"}, {("id",): TEXT}, None,
    ),
    Site(
        "github-create", GITHUB, "create_project", "POST", "/orgs/g/repos", 201,
        {"full_name": "g/n", "html_url": URL, "default_branch": "main"},
        {("full_name",): TEXT, ("html_url",): TEXT}, None, creates=True,
    ),
    Site(
        "github-user-create", GITHUB_USER, "create_project", "POST", "/user/repos", 201,
        {"full_name": "g/n", "html_url": URL, "default_branch": "main"},
        {("full_name",): TEXT, ("html_url",): TEXT}, None, creates=True,
    ),
    Site(
        "github-ref", GITHUB, "commit_files", "GET", "/repos/g/n/git/ref/heads/main", 200,
        {"object": {"sha": "p1"}}, {("object", "sha"): TEXT}, ("GET", "/repos/g/n/git/commits/"),
    ),
    Site(
        "github-parent-commit", GITHUB, "commit_files", "GET", "/repos/g/n/git/commits/", 200,
        {"tree": {"sha": "t1"}}, {("tree", "sha"): TEXT}, ("POST", "/repos/g/n/git/trees"),
    ),
    Site(
        "github-blob", GITHUB, "commit_files", "POST", "/repos/g/n/git/blobs", 201,
        {"sha": "b1"}, {("sha",): TEXT}, ("POST", "/repos/g/n/git/trees"),
    ),
    Site(
        "github-tree", GITHUB, "commit_files", "POST", "/repos/g/n/git/trees", 201,
        {"sha": "t2"}, {("sha",): TEXT}, ("POST", "/repos/g/n/git/commits"),
    ),
    Site(
        "github-commit", GITHUB, "commit_files", "POST", "/repos/g/n/git/commits", 201,
        {"sha": "c1"}, {("sha",): TEXT}, ("PATCH", "/repos/g/n/git/refs/heads/main"),
    ),
]

COMMIT_SITES = [s for s in SITES if s.call == "commit_files"]
CREATE_SITES = [s for s in SITES if s.creates]


def context_of(site: Site) -> str:
    """The adapter's own words for the call, which every message about its reply starts with."""
    shipped = site.shipped
    if site.name == "gitlab-group-lookup":
        return f"group lookup failed for {shipped.namespace!r}"
    if site.creates:
        return "create_project failed for 'n'"
    if shipped.host == "gitlab":
        return "commit_files failed (project=42, branch=main)"
    return "commit_files failed (project='g/n', branch='main')"


# ---------------------------------------------------------------------------------------------
# What the host answers
# ---------------------------------------------------------------------------------------------

#: A reply that is valid JSON and not an object. ``{}`` is separate: it IS an object and lacks the
#: field.
NOT_AN_OBJECT = [
    ("array", b"[]"),
    ("null", b"null"),
    ("string", b'"text"'),
    ("number", b"5"),
    ("true", b"true"),
]

#: A value the adapter reads that is present and unusable, by kind. An integer is a good identifier
#: and a bad text, so ``number`` is in one and not the other.
BAD_TEXT: dict[str, Any] = {
    "null": None,
    "empty": "",
    "number": 5,
    "true": True,
    "float": 1.5,
    # ``json`` reads ``NaN`` and ``Infinity``, which are not JSON. ``httpx`` 0.28 refuses to write
    # one into a body and 0.27 sends it (``test_host_reuse_text.py``): refused here, neither does.
    "nan": float("nan"),
    "infinity": float("inf"),
    "array": [],
    "object": {},
}
BAD_ID = {label: value for label, value in BAD_TEXT.items() if label != "number"}

#: What may stand where an object that holds the field should.
BAD_CONTAINER: dict[str, Any] = {
    "null": None,
    "array": [],
    "string": "x",
    "number": 5,
    "empty": {},
}

#: A body a host sends that is not JSON at all, or too deeply nested to be used.
UNREADABLE = [
    ("not-json", b"not json"),
    ("empty-body", b""),
    ("cut-off", b'{"id": '),
    ("nested-too-deep", b"[" * DEEP + b"]" * DEEP),
]


@dataclass(frozen=True)
class Variant:
    label: str
    body: bytes
    #: What the message must say.
    names: str


def _json(value: object) -> bytes:
    return json.dumps(value).encode()


def _quoted(path: tuple[str, ...]) -> str:
    return '"' + ".".join(path) + '"'


def _set(honest: dict[str, Any], path: tuple[str, ...], value: object) -> dict[str, Any]:
    body = copy.deepcopy(honest)
    node = body
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    return body


def _drop(honest: dict[str, Any], path: tuple[str, ...]) -> dict[str, Any]:
    body = copy.deepcopy(honest)
    node = body
    for key in path[:-1]:
        node = node[key]
    del node[path[-1]]
    return body


def variants(site: Site) -> list[Variant]:
    """Every wrong shape of this site's reply: not an object at all, an object without the
    field, the field of a kind it must not be, and (where the field is nested) the object that
    should hold it of a kind it must not be."""
    first = next(iter(site.fields))
    out = [Variant("empty-object", b"{}", _quoted(first))]
    out += [Variant(label, raw, "is not a JSON object") for label, raw in NOT_AN_OBJECT]
    for path, kind in site.fields.items():
        dotted = ".".join(path)
        out.append(Variant(f"without-{dotted}", _json(_drop(site.honest, path)), _quoted(path)))
        for label, value in (BAD_ID if kind == ID else BAD_TEXT).items():
            out.append(
                Variant(f"{dotted}-{label}", _json(_set(site.honest, path, value)), _quoted(path))
            )
        if len(path) > 1:
            for label, value in BAD_CONTAINER.items():
                body = _json(_set(site.honest, path[:-1], value))
                out.append(Variant(f"{path[0]}-{label}", body, _quoted(path)))
    # An empty object IS the field missing at a site with one flat field, and the object that
    # should hold a nested field empty IS that field missing: the same body would run twice.
    seen: set[bytes] = set()
    unique = []
    for variant in out:
        if variant.body not in seen:
            seen.add(variant.body)
            unique.append(variant)
    return unique


CASES = [
    pytest.param(site, variant, id=f"{site.name}-{variant.label}")
    for site in SITES
    for variant in variants(site)
]


def _raw(status: int, body: bytes) -> bytes:
    reason = {200: "OK", 201: "Created", 500: "Internal Server Error"}[status]
    head = (
        f"HTTP/1.1 {status} {reason}\r\nContent-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n"
    )
    return head.encode() + body


@contextmanager
def _host(
    site: Site, hostile: bytes, status: int | None = None
) -> Iterator[tuple[RepoClient, list[tuple[str, str]]]]:
    """An adapter over a host that answers the whole sequence honestly except for the one request
    ``site`` names, which it answers with ``hostile``; and what reached the host, in order."""
    shipped = site.shipped
    project = shipped.project_reply(id_text="", url=URL, branch="main")
    honest = serve(shipped.router(project, "c1"))
    seen: list[tuple[str, str]] = []

    def reply(request: bytes) -> bytes:
        method, target, _ = request.split(b"\r\n", 1)[0].decode("latin-1").split(" ", 2)
        path = urlsplit(target).path
        seen.append((method, path))
        if method == site.method and path.startswith(site.prefix):
            return _raw(status or site.status, hostile)
        return honest(request)

    with serving_raw(reply) as server:
        yield shipped.make(server.url), seen


def _call(site: Site, adapter: RepoClient) -> object:
    """What the adapter's call gives, or the exception, whatever its class."""
    shipped = site.shipped
    try:
        if site.call == "create_project":
            return adapter.create_project(
                namespace=shipped.namespace, name="n", visibility="private"
            )
        return adapter.commit_files(
            project_id="42" if shipped.host == "gitlab" else "g/n",
            branch="main",
            files=FILES,
            message="m",
        )
    except Exception as error:
        return error


def _run(
    site: Site, hostile: bytes, status: int | None = None
) -> tuple[object, list[tuple[str, str]]]:
    with _host(site, hostile, status) as (adapter, seen):
        return _call(site, adapter), seen


def _assert_a_repo_error(outcome: object) -> RepoClientError:
    assert isinstance(outcome, RepoClientError), repr(outcome)
    # Exactly the base class: a name conflict is not what an unusable reply is.
    assert type(outcome) is RepoClientError, repr(outcome)
    assert is_clean(str(outcome)), str(outcome)
    assert len(str(outcome)) < 2_000
    return outcome


def _was_sent(seen: list[tuple[str, str]], request: tuple[str, str]) -> bool:
    method, prefix = request
    return any(m == method and p.startswith(prefix) for m, p in seen)


# ---------------------------------------------------------------------------------------------
# Each place an adapter reads a reply
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("site", SITES, ids=lambda s: s.name)
def test_an_honest_reply_is_read_as_it_always_was(site: Site) -> None:
    """The control for everything below: the same sequence, with the reply the adapter wants."""
    outcome, _ = _run(site, _json(site.honest))
    assert not isinstance(outcome, Exception), repr(outcome)


@pytest.mark.parametrize(("site", "variant"), CASES)
def test_a_reply_of_the_wrong_shape_is_a_repo_client_error_naming_the_field(
    site: Site, variant: Variant
) -> None:
    """45 of 45 combinations of nine sites and five shapes were a ``KeyError`` or a ``TypeError``;
    this is those and every value of the wrong kind. The error says which field, says a project may
    exist only where one may (the creation), and the request that would have carried what was read
    never reaches the host."""
    outcome, seen = _run(site, variant.body)
    error = _assert_a_repo_error(outcome)
    assert str(error).startswith(f"{context_of(site)}: the reply "), str(error)
    assert variant.names in str(error), str(error)
    assert (MAY_EXIST in str(error)) is site.creates, str(error)
    if site.carries is not None:
        assert not _was_sent(seen, site.carries), seen


@pytest.mark.parametrize("site", SITES, ids=lambda s: s.name)
@pytest.mark.parametrize(("label", "body"), UNREADABLE, ids=[label for label, _ in UNREADABLE])
def test_a_reply_that_is_not_usable_json_says_a_project_may_exist_where_one_may(
    site: Site, label: str, body: bytes
) -> None:
    """Point 3. A ``2xx`` that is not JSON, or is nested past the limit, was a clean error that did
    not say the host had answered ``2xx``: ``--resume`` refused anyway, and the operator read
    ``repo_error: create_project failed ... invalid JSON body`` with no hint that a project may be
    there. The same text now follows it on the creation, and on no other request."""
    outcome, seen = _run(site, body)
    error = _assert_a_repo_error(outcome)
    assert str(error).startswith(f"{context_of(site)}: invalid JSON body: "), str(error)
    assert (MAY_EXIST in str(error)) is site.creates, str(error)
    if site.carries is not None:
        assert not _was_sent(seen, site.carries), seen


@pytest.mark.parametrize("site", CREATE_SITES, ids=lambda s: s.name)
def test_a_creation_the_host_refused_does_not_say_a_project_may_exist(site: Site) -> None:
    """The note is for a ``2xx`` whose reply cannot be read. A ``500`` says what it always said:
    whether one made a project is not known (``BACKLOG.md``, point 8), and this change does not
    widen the note to it."""
    outcome, _ = _run(site, _json({"message": "boom"}), status=500)
    error = _assert_a_repo_error(outcome)
    assert "500" in str(error)
    assert "may already exist" not in str(error)


@pytest.mark.parametrize("site", SITES, ids=lambda s: s.name)
@pytest.mark.parametrize("where", ["in-the-field", "beside-it", "whole-reply"])
def test_the_message_holds_none_of_the_hosts_words(site: Site, where: str) -> None:
    """The text is this repository's own and the field's name. A host that puts a forged status
    line in the value that was wrong, in a field next to it, or in a reply that is an array, gets
    none of it echoed."""
    first = next(iter(site.fields))
    hostile: object
    if where == "in-the-field":
        hostile = _set(site.honest, first, [FORGED])
    elif where == "beside-it":
        hostile = {**_drop(site.honest, first), "message": FORGED, FORGED: FORGED}
    else:
        hostile = [FORGED]
    outcome, _ = _run(site, _json(hostile))
    error = _assert_a_repo_error(outcome)
    assert FORGED not in str(error), str(error)


@pytest.mark.parametrize(
    "site", [s for s in SITES if ID in s.fields.values()], ids=lambda s: s.name
)
@pytest.mark.parametrize("identifier", [7, "7", 0, "x/y"], ids=["int", "str", "zero", "path"])
def test_an_identifier_may_be_an_integer_or_a_string(site: Site, identifier: object) -> None:
    """GitLab sends its ids as integers; the field is read as either. (That what it holds goes back
    to the host as it was is held on the wire, by the tests that record the request, below.)"""
    path = next(p for p, kind in site.fields.items() if kind == ID)
    outcome, _ = _run(site, _json(_set(site.honest, path, identifier)))
    assert not isinstance(outcome, Exception), repr(outcome)


@pytest.mark.parametrize("site", CREATE_SITES, ids=lambda s: s.name)
@pytest.mark.parametrize(
    "branch", [None, "", "dev", 7], ids=["null", "empty", "named", "number"]
)
def test_the_default_branch_is_not_a_required_field(site: Site, branch: object) -> None:
    """Read as before: absent or empty gives ``main``, and no value of it is a reason to refuse a
    reply that names the project. Checking it is not part of this item: ``BACKLOG.md`` point 6
    puts it to the operator, and the ``number`` case is what changes if the answer is to refuse."""
    reply = _set(site.honest, ("default_branch",), branch)
    outcome, _ = _run(site, _json(reply))
    assert not isinstance(outcome, Exception), repr(outcome)
    default = getattr(outcome, "default_branch", None)
    assert default == ("main" if branch in (None, "") else str(branch))
    absent, _ = _run(site, _json(_drop(site.honest, ("default_branch",))))
    assert getattr(absent, "default_branch", None) == "main"


@pytest.mark.parametrize("site", SITES, ids=lambda s: s.name)
def test_fields_the_adapter_does_not_read_are_none_of_its_business(site: Site) -> None:
    """A real reply holds dozens of fields; the check is of the ones read."""
    busy = {
        **site.honest,
        "unused": [1, {"a": [None, "x"]}],
        "other": None,
        "url": 5,
        "web_url_extra": [],
    }
    outcome, _ = _run(site, _json(busy))
    assert not isinstance(outcome, Exception), repr(outcome)


# ---------------------------------------------------------------------------------------------
# What the website graph does with the error
# ---------------------------------------------------------------------------------------------


def _agent(client: RepoClient, platform: str) -> WebsiteAgent:
    agent = WebsiteAgent.__new__(WebsiteAgent)
    agent.client = client
    agent.ci_platform = platform  # type: ignore[assignment]
    agent.ci_host_config = CIHostConfig()
    agent.graph = build_website_graph(client, sleep=lambda _s: None)
    return agent


def _target(site: Site) -> RepoTarget:
    return RepoTarget(
        host_url="https://h.example.com",
        namespace=site.shipped.namespace,
        project_name_hint="Subrogation Recovery Model",
        visibility="private",
    )


@pytest.mark.parametrize("site", COMMIT_SITES, ids=lambda s: s.name)
@pytest.mark.parametrize(
    ("label", "body"),
    [("wrong-shape", b"{}"), ("not-json", b"not json")],
    ids=["wrong-shape", "not-json"],
)
def test_a_wrong_shape_on_the_commit_path_is_retried_as_invalid_json_is(
    site: Site,
    label: str,
    body: bytes,
    intake_report: IntakeReport,
    data_report: DataReport,
) -> None:
    """The operator's ruling: a wrong shape is a ``RepoClientError`` like any other and takes the
    node's ordinary retry, with no class of its own. The control is the reply that is not JSON,
    which always did: the same request reaches the host the same number of times."""
    with _host(site, body) as (adapter, seen):
        result = _agent(adapter, site.shipped.host).run(intake_report, data_report, _target(site))
    assert result.status == "FAILED"
    reason = result.failure_reason or ""
    assert reason.startswith("repo_error_retry_exhausted: commit_files failed"), reason
    assert f"(after {MAX_COMMIT_ATTEMPTS} attempts)" in reason
    assert "may already exist" not in reason
    assert result.initial_commit_sha == ""
    assert result.project_url != ""
    reads = [1 for m, p in seen if m == site.method and p.startswith(site.prefix)]
    assert len(reads) == MAX_COMMIT_ATTEMPTS, (label, seen)


@pytest.mark.parametrize("site", CREATE_SITES, ids=lambda s: s.name)
@pytest.mark.parametrize(
    "body", [b"{}", b"[]", b"not json"], ids=["empty-object", "array", "not-json"]
)
def test_a_wrong_shape_at_the_creation_ends_the_run_at_once_and_says_a_project_may_exist(
    site: Site,
    body: bytes,
    intake_report: IntakeReport,
    data_report: DataReport,
) -> None:
    with _host(site, body) as (adapter, seen):
        result = _agent(adapter, site.shipped.host).run(intake_report, data_report, _target(site))
    assert result.status == "FAILED"
    reason = result.failure_reason or ""
    assert reason.startswith("repo_error: create_project failed"), reason
    assert MAY_EXIST in reason, reason
    assert result.project_url == ""
    assert sum(1 for m, p in seen if m == site.method and p.startswith(site.prefix)) == 1
    assert not any(m == "POST" and "/commits" in p for m, p in seen), seen


# ---------------------------------------------------------------------------------------------
# The helpers
# ---------------------------------------------------------------------------------------------

CONTEXT = "create_project failed for 'x'"


def test_reply_object_returns_the_object_it_was_given() -> None:
    body = {"id": 1}
    assert reply_object(body, context=CONTEXT) is body
    assert reply_object({}, context=CONTEXT) == {}


@pytest.mark.parametrize("body", [[], None, "x", 5, 1.5, True, [{"id": 1}]], ids=repr)
def test_reply_object_refuses_anything_else_in_its_own_words(body: object) -> None:
    with pytest.raises(RepoClientError) as caught:
        reply_object(body, context=CONTEXT)
    assert str(caught.value) == f"{CONTEXT}: the reply is not a JSON object"
    assert type(caught.value) is RepoClientError


def test_reply_string_follows_the_path_and_returns_the_text_as_it_was() -> None:
    assert reply_string({"object": {"sha": "abc"}}, "object", "sha", context=CONTEXT) == "abc"
    assert reply_string({"a": {"b": {"c": " d "}}}, "a", "b", "c", context=CONTEXT) == " d "
    assert reply_string({"sha": "\x1b[2J"}, "sha", context=CONTEXT) == "\x1b[2J"


@pytest.mark.parametrize(
    ("body", "path"),
    [
        ({}, ("sha",)),
        ({"sha": None}, ("sha",)),
        ({"sha": ""}, ("sha",)),
        ({"sha": 5}, ("sha",)),
        ({"sha": True}, ("sha",)),
        ({"sha": []}, ("sha",)),
        ({"sha": {"sha": "x"}}, ("sha",)),
        ({"object": {}}, ("object", "sha")),
        ({"object": None}, ("object", "sha")),
        ({"object": "x"}, ("object", "sha")),
        ({"object": "sha"}, ("object", "sha")),
        ({"object": ["sha"]}, ("object", "sha")),
        ({"sha": "x"}, ("object", "sha")),
        ({"a": {"b": {}}}, ("a", "b", "c")),
        ([], ("sha",)),
        ("sha", ("sha",)),
    ],
    ids=repr,
)
def test_reply_string_names_the_dotted_path_it_could_not_use(
    body: object, path: tuple[str, ...]
) -> None:
    """A string that CONTAINS the key (``{"object": "sha"}``) is not an object that has it: ``in``
    would say so and the subscript would raise the ``TypeError`` this change removes."""
    expected = (
        f'{CONTEXT}: the reply has no usable "{".".join(path)}"'
        if isinstance(body, dict)
        else f"{CONTEXT}: the reply is not a JSON object"
    )
    with pytest.raises(RepoClientError) as caught:
        reply_string(body, *path, context=CONTEXT)
    assert str(caught.value) == expected
    assert type(caught.value) is RepoClientError


@pytest.mark.parametrize("text", ["a", " ", "x" * 5_000, "\u00e9\u4e2d", "\x1b[2J"], ids=len)
def test_any_non_empty_text_is_a_usable_text(text: str) -> None:
    """The rule is non-empty and nothing more (``BACKLOG.md``, point 7 puts a stricter one to the
    operator): one character, a long text and a text of only spaces are returned whole."""
    assert reply_string({"sha": text}, "sha", context=CONTEXT) == text


def test_reply_id_accepts_an_integer_of_any_size_and_says_exactly_what_it_lacks() -> None:
    assert reply_id({"id": 2**70}, "id", context=CONTEXT) == 2**70
    with pytest.raises(RepoClientError) as caught:
        reply_id({"id": None}, "id", context=CONTEXT)
    assert str(caught.value) == f'{CONTEXT}: the reply has no usable "id"'


def test_reply_id_keeps_what_the_host_sent() -> None:
    sent_int = reply_id({"id": 7}, "id", context=CONTEXT)
    sent_text = reply_id({"id": "7"}, "id", context=CONTEXT)
    assert sent_int == 7 and isinstance(sent_int, int)
    assert sent_text == "7" and isinstance(sent_text, str)
    assert reply_id({"id": 0}, "id", context=CONTEXT) == 0
    assert reply_id({"id": -3}, "id", context=CONTEXT) == -3
    assert reply_id({"g": {"id": 9}}, "g", "id", context=CONTEXT) == 9


@pytest.mark.parametrize(
    "value", [None, "", True, False, 1.5, 7.0, float("nan"), [], {}, [7], {"id": 7}], ids=repr
)
def test_reply_id_refuses_what_is_not_a_string_or_an_integer(value: object) -> None:
    """``True`` is an ``int`` to Python and would have been written as ``"True"``; ``7.0`` is not
    an identifier GitLab sends."""
    with pytest.raises(RepoClientError, match='has no usable "id"'):
        reply_id({"id": value}, "id", context=CONTEXT)


def test_a_failure_while_reading_a_creation_reply_says_a_project_may_exist() -> None:
    original = RepoClientError(f"{CONTEXT}: invalid JSON body: Expecting value")
    with pytest.raises(RepoClientError) as caught, reading_a_creation_reply():
        raise original
    assert str(caught.value) == f"{original} {PROJECT_MAY_EXIST}"
    assert type(caught.value) is RepoClientError
    assert caught.value.__cause__ is original


def test_a_creation_reply_that_reads_fine_is_untouched() -> None:
    with reading_a_creation_reply():
        result = reply_string({"web_url": URL}, "web_url", context=CONTEXT)
    assert result == URL


@pytest.mark.parametrize("error", [KeyError("id"), ValueError("x"), TypeError("y")], ids=repr)
def test_an_error_that_is_not_a_repo_error_is_not_dressed_up(error: Exception) -> None:
    """The note is for a failure to read a reply, which this module raises as a ``RepoClientError``
    and nothing else: a bug stays a bug, and Session 275's net reports it as one."""
    with pytest.raises(type(error)) as caught, reading_a_creation_reply():
        raise error
    assert caught.value is error


def test_a_name_conflict_passes_through_unchanged() -> None:
    """``RepoNameConflictError`` is caught by class in the node, as ``scrubbed_errors`` already
    allows, and is no failure to read a reply: it must stay one if a call that raises it is ever
    put inside the block."""
    conflict = RepoNameConflictError("n")
    with pytest.raises(RepoNameConflictError) as caught, reading_a_creation_reply():
        raise conflict
    assert caught.value is conflict


def test_the_note_is_fixed_words_that_say_a_project_may_exist() -> None:
    """Fixed words, none of them the host's, and the phrase the site tests look for."""
    assert MAY_EXIST in PROJECT_MAY_EXIST
    assert PROJECT_MAY_EXIST.startswith("(") and PROJECT_MAY_EXIST.endswith(")")
    assert is_clean(PROJECT_MAY_EXIST)


# ---------------------------------------------------------------------------------------------
# Where the note is not said, and what goes back to the host
# ---------------------------------------------------------------------------------------------


def _mocked(shipped: Shipped, handler: Callable[[httpx.Request], httpx.Response]) -> RepoClient:
    """The shipped adapter with its client swapped for one over a mock transport."""
    adapter = shipped.make("https://h.example")
    adapter._client = httpx.Client(  # type: ignore[assignment]
        base_url=adapter._client.base_url,
        headers=adapter._client.headers,
        transport=httpx.MockTransport(handler),
    )
    return adapter


def _answering(
    statuses: dict[tuple[str, str], int],
) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        status = statuses.get((request.method, request.url.path))
        if status is None:
            raise AssertionError(f"unexpected request: {request.method} {request.url.path}")
        return httpx.Response(status, json={"message": "no"})

    return handler


REFUSED_BEFORE_ANYTHING_IS_MADE = [
    pytest.param(
        GITHUB, {("GET", "/orgs/g"): 500}, "owner lookup failed for 'g'", id="github-org-500"
    ),
    pytest.param(
        GITHUB, {("GET", "/orgs/g"): 401}, "owner lookup failed for 'g'", id="github-org-401"
    ),
    *[
        pytest.param(
            GITHUB,
            {("GET", "/orgs/g"): 404, ("GET", "/users/g"): status},
            "owner lookup failed for 'g'",
            id=f"github-user-{status}",
        )
        for status in (401, 404, 500)
    ],
    *[
        pytest.param(
            GITLAB,
            {("GET", "/api/v4/groups/g"): status},
            "group lookup failed for 'g'",
            id=f"gitlab-group-{status}",
        )
        for status in (401, 404, 500)
    ],
]


@pytest.mark.parametrize(("shipped", "statuses", "starts"), REFUSED_BEFORE_ANYTHING_IS_MADE)
def test_a_refused_lookup_does_not_say_a_project_may_exist(
    shipped: Shipped, statuses: dict[tuple[str, str], int], starts: str
) -> None:
    """The lookups before the creation make nothing, and a host that refuses one is not describing
    a project. The note belongs to the creation's reply and to no step before it."""
    adapter = _mocked(shipped, _answering(statuses))
    with pytest.raises(RepoClientError) as caught:
        adapter.create_project(namespace="g", name="n", visibility="private")
    assert type(caught.value) is RepoClientError
    assert str(caught.value).startswith(f"{starts}: "), str(caught.value)
    assert "may already exist" not in str(caught.value)


@pytest.mark.parametrize("shipped", [GITLAB, GITHUB], ids=lambda s: s.name)
@pytest.mark.parametrize(
    "failure",
    [httpx.ConnectError("refused"), httpx.ReadTimeout("slow")],
    ids=["connect", "timeout"],
)
def test_a_creation_request_that_failed_in_transit_does_not_get_the_note(
    shipped: Shipped, failure: httpx.HTTPError
) -> None:
    """No reply was read, so nothing says the host answered ``2xx``; whether it made a project
    when the connection broke after the request left is not known (``BACKLOG.md``, point 8)."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            raise failure
        return httpx.Response(200, json={"id": 7})

    adapter = _mocked(shipped, handler)
    with pytest.raises(RepoClientError) as caught:
        adapter.create_project(namespace="g", name="n", visibility="private")
    assert type(caught.value) is RepoClientError
    assert str(caught.value).startswith("create_project failed for 'n': "), str(caught.value)
    assert "may already exist" not in str(caught.value)


@pytest.mark.parametrize(
    "identifier",
    [7, "7", "007", 0, 2**40, "x/y"],
    ids=["int", "str", "zeros", "zero", "big", "path"],
)
def test_a_group_id_goes_back_to_the_host_exactly_as_it_was_sent(identifier: object) -> None:
    """An integer stays an integer and a string a string: the id is the host's, and ``"007"`` is not
    ``7``. Recorded on the request, which is the only place it shows."""
    bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json={"id": identifier})
        bodies.append(json.loads(request.content))
        return httpx.Response(201, json={"id": 42, "web_url": URL})

    _mocked(GITLAB, handler).create_project(namespace="g", name="n", visibility="private")
    assert len(bodies) == 1
    sent = bodies[0]["namespace_id"]
    assert sent == identifier and type(sent) is type(identifier)


def test_the_shas_go_back_to_the_host_exactly_as_it_sent_them() -> None:
    """Odd but usable text (spaces, an accent, a leading space) is passed on untouched: the check
    refuses what is not text, and does not tidy what is."""
    parent, base, blob, tree, commit = " p1 ", "  t1", "b\u00e9", "t2 ", " c1"
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        route = (request.method, request.url.path)
        if route == ("GET", "/repos/g/n"):
            return httpx.Response(200, json={})
        if route == ("GET", "/repos/g/n/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": parent}})
        if request.method == "GET" and request.url.path.startswith("/repos/g/n/git/commits/"):
            seen["parent_path"] = request.url.raw_path
            return httpx.Response(200, json={"tree": {"sha": base}})
        if route == ("POST", "/repos/g/n/git/blobs"):
            return httpx.Response(201, json={"sha": blob})
        if route == ("POST", "/repos/g/n/git/trees"):
            seen["trees"] = json.loads(request.content)
            return httpx.Response(201, json={"sha": tree})
        if route == ("POST", "/repos/g/n/git/commits"):
            seen["commits"] = json.loads(request.content)
            return httpx.Response(201, json={"sha": commit})
        if route == ("PATCH", "/repos/g/n/git/refs/heads/main"):
            seen["ref"] = json.loads(request.content)
            return httpx.Response(200, json={})
        raise AssertionError(f"unexpected request: {route}")

    result = _mocked(GITHUB, handler).commit_files(
        project_id="g/n", branch="main", files={"README.md": "x"}, message="m"
    )
    # What the method RETURNS is scrubbed (a leading space goes); what goes BACK to the host is not.
    assert result.sha == commit.strip()
    parent_path = seen["parent_path"]
    assert isinstance(parent_path, bytes) and parent_path.endswith(b"/git/commits/%20p1%20")
    trees = seen["trees"]
    assert isinstance(trees, dict)
    assert trees["base_tree"] == base and trees["tree"][0]["sha"] == blob
    assert seen["commits"] == {"message": "m", "tree": tree, "parents": [parent]}
    assert seen["ref"] == {"sha": commit}


# ---------------------------------------------------------------------------------------------
# Nothing reads a reply except through the helpers
# ---------------------------------------------------------------------------------------------

READERS = {"reply_object", "reply_string", "reply_id"}


def _parse_json_reads(module: object) -> list[tuple[int, bool]]:
    """Each call of ``_parse_json`` in an adapter, as (line, whether its result goes only to a
    ``reply_*`` helper): as an argument of one directly, or by way of a name that is used only as
    the first argument of one."""
    source = Path(inspect.getfile(module)).read_text()  # type: ignore[arg-type]
    tree = ast.parse(source)
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}

    def is_reader_argument(node: ast.AST) -> bool:
        parent = parents.get(node)
        return (
            isinstance(parent, ast.Call)
            and isinstance(parent.func, ast.Name)
            and parent.func.id in READERS
            and bool(parent.args)
            and parent.args[0] is node
        )

    reads = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_parse_json"
        ):
            continue
        parent = parents[node]
        if is_reader_argument(node):
            reads.append((node.lineno, True))
        elif isinstance(parent, ast.Assign) and len(parent.targets) == 1:
            target = parent.targets[0]
            assert isinstance(target, ast.Name)
            scope = parents[parent]
            uses = [
                n for n in ast.walk(scope)
                if isinstance(n, ast.Name) and n.id == target.id and isinstance(n.ctx, ast.Load)
            ]
            reads.append((node.lineno, bool(uses) and all(is_reader_argument(n) for n in uses)))
        else:
            reads.append((node.lineno, False))
    return reads


@pytest.mark.parametrize(
    ("module", "shipped"),
    [(gitlab_adapter, GITLAB), (github_adapter, GITHUB)],
    ids=["gitlab", "github"],
)
def test_every_reply_an_adapter_reads_goes_through_a_reply_helper(
    module: object, shipped: Shipped
) -> None:
    """The nine sites above are listed by hand; this is what makes a tenth show up. A new
    ``_parse_json`` read is counted here (so the list above must grow with it), and one whose
    result is subscripted, or used in any way but as the first argument of ``reply_object``,
    ``reply_string`` or ``reply_id``, is refused. The neighbouring failure classes have a guard of
    this kind (``test_host_failure_text.py``); ``_parse_json`` returns ``object``, which mypy
    holds for the subscript, and this holds the rest."""
    reads = _parse_json_reads(module)
    unchecked = [line for line, through_a_helper in reads if not through_a_helper]
    assert not unchecked, f"read without a reply helper at line(s) {unchecked}"
    # The personal-account creation is the same read as the organisation's: one site, two routes.
    expected = sum(
        1
        for site in SITES
        if site.shipped.host == shipped.host and site.shipped.name != "github-user"
    )
    assert len(reads) == expected, (len(reads), expected)
