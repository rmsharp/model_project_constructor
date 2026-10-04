"""No failure of any request, in any adapter, carries the access token or a control code out.

Each adapter runs its whole sequence (``create_project`` then ``commit_files``) against a real
socket that answers correctly, counts the requests, and then runs it again once per request with
THAT request answered by a hostile host: a valid ``500`` that echoes the request headers, the same
as JSON, a body of terminal control codes padded to megabytes, a malformed reply that makes ``h11``
quote the headers it read, and replies that declare a charset the body is not in, or one that is
not a text codec at all. One more kind raises from a transport with the token in the exception's
own text. The position loop is derived from the happy run, so a request an adapter gains later is
DETECTED here, not silently skipped: the routers below answer only the requests they know and the
request count is pinned, so the file goes red until both are updated.

GitHub has two ways to find the owner (an organisation, then a personal account), so it is run
both ways; the three sequences have 4, 10 and 11 requests.

What is asserted is what an operator, a log and a checkpoint can see: the message, the exception
chain and a formatted traceback. ``test_host_text.py`` holds the scrubbing function itself.
"""

from __future__ import annotations

import ast
import inspect
import json
import re
import traceback
from collections.abc import Callable, Iterator
from dataclasses import dataclass

import httpx
import pytest

from model_project_constructor.agents.website import GitHubAdapter, GitLabAdapter, github_adapter
from model_project_constructor.agents.website import gitlab_adapter as gitlab_adapter_module
from model_project_constructor.agents.website._host_text import MAX_HOST_TEXT, REDACTED
from model_project_constructor.agents.website._http import RepoHttpClient
from model_project_constructor.agents.website.protocol import RepoClient, RepoClientError
from model_project_constructor.orchestrator.config import REPO_PLATFORMS
from tests.agents.website.loopback import serving_raw

TOKEN = "glpat-SECRET9f3kQ7xZ2mW"
FILES = {"README.md": "# r\n", "analysis/01.qmd": "q\n"}
CONTROLS = re.compile(r"[\x00-\x1f\x7f-\x9f]")

Reply = tuple[int, object]
Router = Callable[[str, str], Reply]


def _gitlab(method: str, path: str) -> Reply:
    if method == "GET" and path.startswith("/api/v4/groups/"):
        return 200, {"id": 7}
    if method == "POST" and path == "/api/v4/projects":
        return 201, {"id": 42, "web_url": "https://h/p", "default_branch": "main"}
    if method == "GET" and path == "/api/v4/projects/42":
        return 200, {}
    if method == "POST" and path == "/api/v4/projects/42/repository/commits":
        return 201, {"id": "c0ffee"}
    raise AssertionError(f"unexpected request {method} {path}")


def _github_routes(owner: dict[tuple[str, str], Reply]) -> Router:
    routes: dict[tuple[str, str], Reply] = {
        **owner,
        ("GET", "/repos/g/n"): (200, {}),
        ("GET", "/repos/g/n/git/ref/heads/main"): (200, {"object": {"sha": "p1"}}),
        ("GET", "/repos/g/n/git/commits/p1"): (200, {"tree": {"sha": "t1"}}),
        ("POST", "/repos/g/n/git/blobs"): (201, {"sha": "b1"}),
        ("POST", "/repos/g/n/git/trees"): (201, {"sha": "t2"}),
        ("POST", "/repos/g/n/git/commits"): (201, {"sha": "c1"}),
        ("PATCH", "/repos/g/n/git/refs/heads/main"): (200, {}),
    }
    def router(method: str, path: str) -> Reply:
        try:
            return routes[(method, path)]
        except KeyError:
            raise AssertionError(f"unexpected request {method} {path}") from None

    return router


_CREATED = (
    201,
    {"full_name": "g/n", "html_url": "https://h/g/n", "default_branch": "main"},
)
# The owner is an organisation: ``GET /orgs/g`` answers 200.
_github = _github_routes({("GET", "/orgs/g"): (200, {}), ("POST", "/orgs/g/repos"): _CREATED})
# The owner is a personal account: the organisation lookup is a 404, and the repository is created
# under the authenticated user.
_github_user = _github_routes(
    {
        ("GET", "/orgs/g"): (404, {}),
        ("GET", "/users/g"): (200, {}),
        ("POST", "/user/repos"): _CREATED,
    }
)


@dataclass(frozen=True)
class Host:
    name: str
    router: Router
    make: Callable[[str], GitLabAdapter | GitHubAdapter]


HOSTS = [
    Host("gitlab", _gitlab, lambda url: GitLabAdapter(host_url=url, private_token=TOKEN)),
    Host("github", _github, lambda url: GitHubAdapter(host_url=url, private_token=TOKEN)),
    Host("github-user", _github_user, lambda url: GitHubAdapter(host_url=url, private_token=TOKEN)),
]
REQUESTS = {"gitlab": 4, "github": 10, "github-user": 11}


def _run(adapter: GitLabAdapter | GitHubAdapter) -> None:
    info = adapter.create_project(namespace="g", name="n", visibility="private")
    adapter.commit_files(
        project_id=info.id, branch=info.default_branch, files=FILES, message="scaffold"
    )


def _http(status: int, body: bytes, *, content_type: str = "application/json") -> bytes:
    reason = {200: "OK", 201: "Created", 404: "Not Found", 500: "Internal Server Error"}[status]
    return (
        f"HTTP/1.1 {status} {reason}\r\nContent-Type: {content_type}\r\n"
        f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n"
    ).encode() + body


def _happy(router: Router) -> Callable[[bytes], bytes]:
    def reply(request: bytes) -> bytes:
        method, path, _ = request.split(b"\r\n", 1)[0].decode().split(" ", 2)
        status, payload = router(method, path)
        return _http(status, json.dumps(payload).encode())

    return reply


def _head(request: bytes) -> str:
    return request.split(b"\r\n\r\n", 1)[0].decode("latin-1")


def _echo_as_text(request: bytes) -> bytes:
    return _http(500, _head(request).encode(), content_type="text/plain")


def _echo_as_json(request: bytes) -> bytes:
    body = json.dumps({"message": "boom", "you_sent": _head(request)}).encode()
    return _http(500, body)


def _controls_and_padding(request: bytes) -> bytes:
    body = b"\x1b[2J\x07\x00" + _head(request).encode() + b"\r\n" + b"x" * 3_000_000
    return _http(500, body, content_type="text/plain")


def _malformed_header_echo(request: bytes) -> bytes:
    """A header line with no colon, built from the credential line the request carried: ``h11``
    refuses it and quotes it in the error, ``bytearray(b'PRIVATE-TOKEN glpat-...')``. ``h11``
    quotes only the FIRST illegal line, so the credential line goes first, which is what a gateway
    that reflects the credential header into its reply looks like to the client."""
    lines = _head(request).split("\r\n")[1:]
    credential = [ln for ln in lines if ln.lower().startswith(("private-token", "authorization"))]
    assert credential, "the request carried no credential header"
    bad = "\r\n".join(line.replace(":", "", 1) for line in credential)
    return b"HTTP/1.1 200 OK\r\n" + bad.encode("latin-1") + b"\r\n\r\n"


def _undecodable_charset(request: bytes) -> bytes:
    """A valid ``500`` that declares a charset its body is not in: ``response.text`` raises
    ``UnicodeDecodeError`` on Python 3.13 and a plain ``UnicodeError`` on 3.11 and 3.12 (CI runs
    3.12), not an ``httpx.HTTPError`` and not a ``RepoClientError``, where the adapter builds its
    message. UTF-16 refuses a body of odd length, so the body is padded to one."""
    body = _head(request).encode()
    if len(body) % 2 == 0:
        body += b"!"
    return _http(500, body, content_type="text/plain; charset=utf-16")


def _charset(name: str) -> Callable[[bytes], bytes]:
    """A valid ``500`` echoing the request head that declares ``name``, which is not a text codec:
    ``response.text`` raises ``UnicodeError``, ``TypeError`` or ``AssertionError`` by codec."""

    def reply(request: bytes) -> bytes:
        return _http(500, _head(request).encode(), content_type=f"text/plain; charset={name}")

    return reply


HOSTILE: dict[str, Callable[[bytes], bytes]] = {
    "echo-as-text": _echo_as_text,
    "echo-as-json": _echo_as_json,
    "controls-and-padding": _controls_and_padding,
    "malformed-header-echo": _malformed_header_echo,
    "undecodable-charset": _undecodable_charset,
    "charset-undefined": _charset("undefined"),
    "charset-rot13": _charset("rot13"),
    "charset-hex": _charset("hex"),
}


def _sequence(host: Host, hostile: Callable[[bytes], bytes] | None, at: int | None) -> Callable[
    [bytes], bytes
]:
    """Answer correctly, except that request number ``at`` (from 0) gets the hostile reply."""
    happy = _happy(host.router)
    count = 0

    def reply(request: bytes) -> bytes:
        nonlocal count
        index, count = count, count + 1
        if hostile is not None and index == at:
            return hostile(request)
        return happy(request)

    return reply


def _request_count(host: Host) -> int:
    with serving_raw(_happy(host.router)) as server:
        _run(host.make(server.url))
        return len(server.seen)


def _chain(error: BaseException) -> Iterator[BaseException]:
    seen: set[int] = set()
    pending: list[BaseException | None] = [error]
    while pending:
        current = pending.pop()
        if current is None or id(current) in seen:
            continue
        seen.add(id(current))
        yield current
        pending += [current.__cause__, current.__context__]


def _assert_safe(error: RepoClientError) -> None:
    message = str(error)
    assert TOKEN not in message
    assert CONTROLS.search(message) is None
    assert "\n" not in message
    assert len(message) <= MAX_HOST_TEXT + 80
    assert error.__cause__ is None
    assert error.__context__ is None
    assert [e for e in _chain(error) if TOKEN in str(e)] == []
    assert TOKEN not in "".join(traceback.format_exception(error))


def test_the_undecodable_charset_reply_really_is_undecodable() -> None:
    """The premise of that hostile kind, checked for requests of both parities."""
    for extra in (b"", b"x"):
        reply = _undecodable_charset(b"GET /x HTTP/1.1\r\nPRIVATE-TOKEN: " + TOKEN.encode() + extra)
        response = httpx.Response(
            500,
            content=reply.split(b"\r\n\r\n", 1)[1],
            headers={"content-type": "text/plain; charset=utf-16"},
        )
        with pytest.raises(UnicodeError):
            response.text  # noqa: B018


@pytest.mark.parametrize("host", HOSTS, ids=lambda h: h.name)
def test_the_happy_sequence_works_and_makes_the_requests_the_loop_counts(host: Host) -> None:
    """The control: with no hostile reply the sequence completes, so every failure below is the
    hostile reply's doing, and the request count the loop uses is the real one."""
    count = _request_count(host)
    assert count >= 4
    assert count == REQUESTS[host.name]


@pytest.mark.parametrize("kind", sorted(HOSTILE))
@pytest.mark.parametrize("host", HOSTS, ids=lambda h: h.name)
def test_a_hostile_reply_to_any_request_leaks_nothing(host: Host, kind: str) -> None:
    for at in range(_request_count(host)):
        with serving_raw(_sequence(host, HOSTILE[kind], at)) as server:
            adapter = host.make(server.url)
            with pytest.raises(RepoClientError) as caught:
                _run(adapter)
        _assert_safe(caught.value)
        # The hostile reply really was the thing that failed, and it really did carry the token
        # (or the control codes) the message would have printed: the redaction is what is shown.
        if kind != "controls-and-padding":
            assert REDACTED in str(caught.value), (at, str(caught.value))
        else:
            assert "more characters not shown" in str(caught.value), at


def _raising_at(
    host: Host, error_class: type[httpx.TransportError], at: int
) -> Callable[[httpx.Request], httpx.Response]:
    """A mock transport that answers correctly, except request ``at``, which raises with the token
    and a control code in the exception's own text."""
    count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal count
        index, count = count, count + 1
        if index == at:
            raise error_class(f"PRIVATE-TOKEN: {TOKEN} was refused\r\n\x1b[2J")
        status, payload = host.router(request.method, request.url.path)
        return httpx.Response(status, json=payload)

    return handler


@pytest.mark.parametrize("host", HOSTS, ids=lambda h: h.name)
def test_an_exception_whose_own_text_quotes_the_token_leaks_nothing(host: Host) -> None:
    """A transport error is raised with the token in it, at every request in turn. Real libraries
    do this (``h11``'s protocol errors); the real-socket test above covers that one, this covers
    any other class whose message a host or a proxy can shape."""
    for error_class in (httpx.ReadError, httpx.ConnectError, httpx.RemoteProtocolError):
        for at in range(_request_count(host)):
            adapter = host.make("https://host.example")
            adapter._client = RepoHttpClient(
                base_url=adapter._client.base_url,
                headers=adapter._client.headers,
                transport=httpx.MockTransport(_raising_at(host, error_class, at)),
            )
            with pytest.raises(RepoClientError) as caught:
                _run(adapter)
            _assert_safe(caught.value)
            assert REDACTED in str(caught.value), (error_class, at)


@pytest.mark.parametrize(
    ("host", "status"), [(HOSTS[0], 409), (HOSTS[1], 422)], ids=["gitlab-409", "github-422"]
)
def test_a_name_conflict_check_on_an_undecodable_body_does_not_raise(
    host: Host, status: int
) -> None:
    """``_is_name_conflict`` reads ``response.text`` when the body is not JSON; it must not crash
    on a body the declared charset cannot decode, and still finds the words in it."""
    from model_project_constructor.agents.website.github_adapter import (
        _is_name_conflict as github_conflict,
    )
    from model_project_constructor.agents.website.gitlab_adapter import (
        _is_name_conflict as gitlab_conflict,
    )

    check = gitlab_conflict if host.name == "gitlab" else github_conflict
    headers = {"content-type": "text/plain; charset=utf-16"}
    taken = httpx.Response(status, content=b"name already exists!!", headers=headers)
    other = httpx.Response(status, content=b"something else entirely", headers=headers)
    with pytest.raises(UnicodeError):
        taken.text  # noqa: B018 - the premise
    assert check(taken) is True
    assert check(other) is False


@pytest.mark.parametrize("host", HOSTS, ids=lambda h: h.name)
def test_a_successful_run_is_untouched(host: Host) -> None:
    with serving_raw(_happy(host.router)) as server:
        adapter = host.make(server.url)
        info = adapter.create_project(namespace="g", name="n", visibility="private")
        commit = adapter.commit_files(
            project_id=info.id, branch=info.default_branch, files=FILES, message="m"
        )
    assert info.default_branch == "main"
    assert commit.files_committed == sorted(FILES)


@pytest.mark.parametrize("host", HOSTS, ids=lambda h: h.name)
def test_an_ordinary_error_body_still_reads_as_an_error(host: Host) -> None:
    """The point of keeping the body is that an operator can read why. A scrub that ate it would
    be a fix that breaks diagnosis."""

    def reply(request: bytes) -> bytes:
        return _http(500, b'{"message":"disk quota exceeded for group g"}')

    with serving_raw(reply) as server, pytest.raises(RepoClientError) as caught:
        host.make(server.url).create_project(namespace="g", name="n", visibility="private")
    assert "500" in str(caught.value)
    assert "disk quota exceeded for group g" in str(caught.value)


PROTOCOL_METHODS = sorted(
    name
    for name, member in vars(RepoClient).items()
    if not name.startswith("_") and callable(member)
)


@pytest.mark.parametrize("host", sorted(REPO_PLATFORMS))
def test_every_registered_host_scrubs_every_method_of_the_protocol(host: str) -> None:
    """The pipeline script builds its adapter from this registry. A host added to it, or a method
    added to ``RepoClient``, whose adapter does not leave through ``scrubbed_errors`` would reopen
    the leak without any test above noticing, because they name the two adapters and the two
    methods: this goes red instead. The marker is set by ``scrubbed_errors`` alone: ``__wrapped__``
    is set by every ``functools.wraps`` decorator, a retry or a timer included."""
    adapter = REPO_PLATFORMS[host].adapter_factory(
        host_url="http://127.0.0.1:9", private_token=TOKEN
    )
    assert PROTOCOL_METHODS
    for name in PROTOCOL_METHODS:
        method = getattr(type(adapter), name)
        assert getattr(method, "__scrubs_host_text__", False) is True, (host, name)
    assert getattr(adapter, "_secret") == TOKEN  # noqa: B009 - not on the Protocol


@pytest.mark.parametrize(
    "module", [gitlab_adapter_module, github_adapter], ids=["gitlab", "github"]
)
def test_the_adapters_read_a_response_body_only_through_response_text(module: object) -> None:
    """``response.text`` raises on a body its declared charset cannot decode, and on a charset that
    is not a text codec, and the adapters read a body while building the message for a failure;
    ``response_text`` is the one reader that does not. A direct ``.text`` or ``.content`` added
    later would reopen a crash that leaves the adapter as a ``UnicodeError`` or a ``TypeError``."""
    tree = ast.parse(inspect.getsource(module))  # type: ignore[arg-type]
    direct = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr in {"text", "content"}
    ]
    assert direct == []


@pytest.mark.parametrize(
    "module", [gitlab_adapter_module, github_adapter], ids=["gitlab", "github"]
)
def test_the_adapters_parse_a_response_body_only_through_reply_json(module: object) -> None:
    """``response.json()`` raises ``RecursionError`` for a body nested about 10,000 levels deep
    (CPython 3.11 to 3.13), which an ``except ValueError`` does not catch, and a body that parses
    can still be too deep to write into the next request; ``reply_json`` turns both into the
    ``ValueError`` the adapters already handle. A direct ``.json()`` added later would reopen the
    crash (the name conflict check, which reads a 4xx body, had its own copy of the call). The
    ``json=`` keyword of a request is not an attribute access and is not matched."""
    tree = ast.parse(inspect.getsource(module))  # type: ignore[arg-type]
    direct = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr == "json"
    ]
    assert direct == []
    calls = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "reply_json"
    ]
    # The two readers in each adapter (``_parse_json`` and ``_is_name_conflict``): a count, so that
    # deleting one reader outright is not what makes this pass.
    assert len(calls) == 2, calls
