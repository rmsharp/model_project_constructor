"""The shared adapter client withholds the HTTP library's protocol-error text.

``h11`` quotes the header values it refuses, and a credential is one. ``test_repo_token.py`` holds
the first line of defence, a validator that keeps such a value from being sent; this file holds the
second, which does not depend on the validator being complete. The adapters cannot reach the real
error (their constructors refuse the value first), so most tests drive ``RepoHttpClient`` through
``httpx.MockTransport`` raising the error ``h11`` raises; two build the client directly with a
refused header and talk to a real socket, which is the only thing that shows the installed stack
still raises the class this client catches.

The second half is the same rule one step earlier. ``httpx`` builds a request (the address, the
body and the ``Cookie`` header) before it sends one, and refuses to build some: ``InvalidURL`` for a
control character in a path, ``ValueError`` for a lone surrogate (``UnicodeEncodeError``) or a
number JSON cannot hold in a body, and ``UnicodeEncodeError`` for a non-ASCII cookie a host set.
None of them is an ``httpx.HTTPError``, so none reached the adapters' ``except`` blocks. The
library's own message repeats only part of what it refused (one character and its position, or the
number), so the tests that hold the converter are the exact fixed text and the empty chain; the
assertions that the secret is absent are kept, and they cannot fail for any ``httpx`` today.
"""

from __future__ import annotations

import traceback
from collections.abc import Callable, Iterator

import httpx
import pytest

from model_project_constructor.agents.website import GitHubAdapter, GitLabAdapter
from model_project_constructor.agents.website._http import (
    PROTOCOL_ERROR_TEXT,
    UNBUILDABLE_REQUEST_TEXT,
    RepoHttpClient,
)
from model_project_constructor.agents.website.protocol import RepoClientError
from tests.agents.website.loopback import Loopback
from tests.agents.website.success_hosts import HTTPX_WRITES_JSON_AS_UTF8

SECRET = "glpat-SECRET9f3kQ7"
# A realistic token: the adapter removes its token from every error message, so a one-letter
# stand-in would take letters out of the words around it.
TOKEN = "glpat-ADAPTERTOKEN0123456789"
URL = "https://host.example/api"


def _refusing(message: str, error: type[Exception] = httpx.LocalProtocolError) -> RepoHttpClient:
    def handler(request: httpx.Request) -> httpx.Response:
        raise error(message)

    return RepoHttpClient(transport=httpx.MockTransport(handler))


def _chain(error: BaseException) -> Iterator[BaseException]:
    """The exception and everything reachable from it, by cause or by context."""
    seen: set[int] = set()
    pending: list[BaseException | None] = [error]
    while pending:
        current = pending.pop()
        if current is None or id(current) in seen:
            continue
        seen.add(id(current))
        yield current
        pending += [current.__cause__, current.__context__]


def _assert_nothing_quotes_the_secret(error: BaseException) -> None:
    assert [e for e in _chain(error) if SECRET in str(e)] == []
    assert SECRET not in "".join(traceback.format_exception(error))


def test_the_replacement_has_the_fixed_text_and_no_original_behind_it() -> None:
    client = _refusing(f"Illegal header value b'{SECRET}\\r'")
    with pytest.raises(httpx.LocalProtocolError) as caught:
        client.get(URL)
    assert str(caught.value) == PROTOCOL_ERROR_TEXT
    # Not merely hidden from a printed traceback (``from None``): not reachable at all.
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    _assert_nothing_quotes_the_secret(caught.value)
    # ``httpx`` documents ``exc.request`` on every transport error, so it is kept.
    assert str(caught.value.request.url) == URL


def test_the_fixed_text_says_what_happened_without_naming_a_cause_it_cannot_know() -> None:
    assert "could not be sent" in PROTOCOL_ERROR_TEXT
    assert "withheld" in PROTOCOL_ERROR_TEXT
    assert "can quote" in PROTOCOL_ERROR_TEXT


@pytest.mark.parametrize("method", ["get", "post", "patch", "put", "delete"])
def test_every_method_goes_through_the_override(method: str) -> None:
    client = _refusing(f"Illegal header value b'{SECRET}\\r'")
    with pytest.raises(httpx.LocalProtocolError) as caught:
        getattr(client, method)(URL)
    _assert_nothing_quotes_the_secret(caught.value)


def test_the_stream_path_goes_through_the_override_too() -> None:
    client = _refusing(f"Illegal header value b'{SECRET}\\r'")
    with pytest.raises(httpx.LocalProtocolError) as caught, client.stream("GET", URL):
        pass
    _assert_nothing_quotes_the_secret(caught.value)


@pytest.mark.parametrize(
    "error", [httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError]
)
def test_any_other_failure_keeps_its_own_message(error: type[Exception]) -> None:
    client = _refusing("the host said no", error)
    with pytest.raises(error, match="the host said no"):
        client.get(URL)


def test_a_normal_response_is_returned_untouched() -> None:
    client = RepoHttpClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"ok": True}))
    )
    assert client.get(URL).json() == {"ok": True}


def test_the_keyword_arguments_reach_the_real_send() -> None:
    """``send`` takes ``stream``, ``auth`` and ``follow_redirects``; the override forwards them."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/start":
            return httpx.Response(302, headers={"Location": "/end"})
        # A stream, not ``content=``: ``content=`` is read at once, so it could not show the gap.
        return httpx.Response(200, stream=httpx.ByteStream(b"done"))

    client = RepoHttpClient(base_url="https://host.example", transport=httpx.MockTransport(handler))
    # follow_redirects: without it the 302 is returned as it is.
    assert client.get("/start").status_code == 302
    assert client.get("/start", follow_redirects=True).text == "done"
    # auth: becomes an Authorization header.
    seen.clear()
    client.get("/end", auth=("user", "pass"))
    assert seen[-1].headers["authorization"].startswith("Basic ")
    # stream: the body is not read before the caller asks.
    streamed = client.send(client.build_request("GET", "/end"), stream=True)
    assert not streamed.is_stream_consumed
    streamed.close()


@pytest.mark.parametrize(
    "header_value",
    [SECRET + "\r", SECRET + "\t", SECRET[:9] + "\x00" + SECRET[9:]],
    ids=["trailing-cr", "trailing-tab", "inside-nul"],
)
def test_the_real_error_from_the_installed_stack_is_replaced(
    loopback: Loopback, header_value: str
) -> None:
    """Built directly, so the validator is out of the picture: this is the only test that shows
    ``httpx``, ``httpcore`` and ``h11`` still raise the class this client catches, and that they
    quote the value if nothing intervenes."""
    client = RepoHttpClient(base_url=loopback.url, headers={"PRIVATE-TOKEN": header_value})
    with pytest.raises(httpx.LocalProtocolError) as caught:
        client.get("/x")
    assert str(caught.value) == PROTOCOL_ERROR_TEXT
    _assert_nothing_quotes_the_secret(caught.value)
    with pytest.raises(httpx.LocalProtocolError) as streamed, client.stream("GET", "/x"):
        pass
    _assert_nothing_quotes_the_secret(streamed.value)
    client.close()


@pytest.mark.parametrize("adapter", [GitLabAdapter, GitHubAdapter], ids=["gitlab", "github"])
def test_the_adapters_build_their_client_from_it(
    adapter: type[GitLabAdapter] | type[GitHubAdapter],
) -> None:
    built = adapter(host_url="https://host.example", private_token=TOKEN)
    assert isinstance(built._client, RepoHttpClient)


@pytest.mark.parametrize("adapter", [GitLabAdapter, GitHubAdapter], ids=["gitlab", "github"])
def test_an_adapter_never_repeats_the_quoted_value_in_its_error(
    adapter: type[GitLabAdapter] | type[GitHubAdapter],
) -> None:
    built = adapter(host_url="https://host.example", private_token=TOKEN)
    built._client = _refusing(f"Illegal header value b'{SECRET}\\r'")
    with pytest.raises(RepoClientError) as caught:
        built.create_project(namespace="g", name="n", visibility="private")
    assert PROTOCOL_ERROR_TEXT in str(caught.value)
    _assert_nothing_quotes_the_secret(caught.value)


# ---------------------------------------------------------------------------------------------
# A request ``httpx`` cannot build.
# ---------------------------------------------------------------------------------------------

#: What ``httpx`` refuses to put in a request PATH, each carrying the secret: a C0 control, DEL
#: and a lone surrogate (0.27.2 and 0.28.1).
UNBUILDABLE_PATHS = [
    pytest.param(f"/x/{SECRET}\x1b]0;PWNED\x07", httpx.InvalidURL, id="escape-and-bell"),
    pytest.param(f"/x/{SECRET}\x00", httpx.InvalidURL, id="nul"),
    pytest.param(f"/x/{SECRET}\x7f", httpx.InvalidURL, id="del"),
    pytest.param(f"/x/{SECRET}\r\nStatus: COMPLETE", httpx.InvalidURL, id="line-break"),
    pytest.param(f"/x/{SECRET}\ud800", UnicodeEncodeError, id="lone-surrogate"),
]


#: What ``httpx`` 0.28 refuses to write into a JSON body (``ensure_ascii=False`` and
#: ``allow_nan=False``); 0.27 escapes the surrogate and sends a ``NaN``. The overflowing float is
#: ``inf`` once parsed.
BODY_VALUES = [
    pytest.param(f"{SECRET}\ud800", id="lone-surrogate"),
    pytest.param(float("nan"), id="nan"),
    pytest.param(float("inf"), id="infinity"),
    pytest.param(-float("inf"), id="minus-infinity"),
    pytest.param(1e999, id="overflowing-float"),
]
skip_before_0_28 = pytest.mark.skipif(
    not HTTPX_WRITES_JSON_AS_UTF8,
    reason="httpx < 0.28 escapes a lone surrogate in a JSON body and sends a NaN",
)


def _accepting(sent: list[httpx.Request]) -> RepoHttpClient:
    """A client whose transport answers every request it is given, and keeps it."""

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200, json={})

    return RepoHttpClient(base_url="https://host.example", transport=httpx.MockTransport(handler))


@pytest.mark.parametrize(("path", "refused"), UNBUILDABLE_PATHS)
def test_the_installed_httpx_still_refuses_what_this_client_converts(
    path: str, refused: type[Exception]
) -> None:
    """The canary: the plain client raises the classes below at BUILD time, which is the only
    reason an override of ``build_request`` (and not ``send``) can reach them, and neither is an
    ``httpx.HTTPError``, which is why the adapters' ``except`` blocks never caught them."""
    plain = httpx.Client(base_url="https://host.example")
    with pytest.raises(refused) as caught:
        plain.build_request("GET", path)
    assert not isinstance(caught.value, httpx.HTTPError)
    plain.close()


@pytest.mark.parametrize(("path", "refused"), UNBUILDABLE_PATHS)
@pytest.mark.parametrize("method", ["get", "post", "patch", "put", "delete"])
def test_a_path_httpx_cannot_build_is_the_fixed_text_and_is_never_sent(
    method: str, path: str, refused: type[Exception]
) -> None:
    sent: list[httpx.Request] = []
    client = _accepting(sent)
    with pytest.raises(httpx.LocalProtocolError) as caught:
        getattr(client, method)(path)
    assert isinstance(caught.value, httpx.HTTPError)
    assert str(caught.value) == UNBUILDABLE_REQUEST_TEXT
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    _assert_nothing_quotes_the_secret(caught.value)
    assert "PWNED" not in "".join(traceback.format_exception(caught.value))
    assert sent == []


@pytest.mark.parametrize(("path", "refused"), UNBUILDABLE_PATHS)
def test_the_other_ways_in_are_covered_too(path: str, refused: type[Exception]) -> None:
    """``request``, ``stream`` and ``build_request`` itself: one override covers them all."""
    client = _accepting([])
    with pytest.raises(httpx.LocalProtocolError) as built:
        client.build_request("GET", path)
    with pytest.raises(httpx.LocalProtocolError) as requested:
        client.request("GET", path)
    with pytest.raises(httpx.LocalProtocolError) as streamed, client.stream("GET", path):
        pass
    for caught in (built, requested, streamed):
        assert str(caught.value) == UNBUILDABLE_REQUEST_TEXT
        _assert_nothing_quotes_the_secret(caught.value)


@skip_before_0_28
@pytest.mark.parametrize("value", BODY_VALUES)
def test_the_installed_httpx_still_refuses_a_body_this_client_converts(value: object) -> None:
    """The canary for the body: ``ValueError`` (``UnicodeEncodeError`` is one), not an
    ``httpx.HTTPError``."""
    plain = httpx.Client(base_url="https://host.example")
    with pytest.raises(ValueError) as caught:
        plain.build_request("POST", "/x", json={"sha": value})
    assert not isinstance(caught.value, httpx.HTTPError)
    plain.close()


@skip_before_0_28
@pytest.mark.parametrize("value", BODY_VALUES)
@pytest.mark.parametrize("method", ["post", "patch", "put"])
def test_a_json_body_httpx_cannot_encode_is_the_fixed_text_and_is_never_sent(
    method: str, value: object
) -> None:
    sent: list[httpx.Request] = []
    client = _accepting(sent)
    with pytest.raises(httpx.LocalProtocolError) as caught:
        getattr(client, method)("/x", json={"sha": value})
    assert str(caught.value) == UNBUILDABLE_REQUEST_TEXT
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    _assert_nothing_quotes_the_secret(caught.value)
    assert sent == []


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(lambda c: c.get("/a/b%20c?q=1"), id="get-with-a-query"),
        pytest.param(lambda c: c.post("/a", json={"k": "v", "n": [1, 2]}), id="post-json"),
        pytest.param(lambda c: c.patch("/a", json={"sha": "abc\x1b"}), id="json-escapes-a-control"),
        pytest.param(lambda c: c.get("/a/%C2%9B"), id="encoded-c1"),
        pytest.param(lambda c: c.get("/a/\x9b2J"), id="c1-httpx-percent-encodes"),
    ],
)
def test_a_request_httpx_can_build_is_built_and_sent_exactly_as_before(
    build: Callable[[httpx.Client], httpx.Response],
) -> None:
    sent: list[httpx.Request] = []
    build(_accepting(sent))
    plain_sent: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        plain_sent.append(request)
        return httpx.Response(200, json={})

    build(httpx.Client(base_url="https://host.example", transport=httpx.MockTransport(handler)))
    # The headers too: ``Content-Type``, ``Accept``, ``Host``, ``User-Agent`` and the length.
    assert [(r.method, str(r.url), r.content, sorted(r.headers.items())) for r in sent] == [
        (r.method, str(r.url), r.content, sorted(r.headers.items())) for r in plain_sent
    ]
    assert len(sent) == 1
    assert "accept" in sent[0].headers and "user-agent" in sent[0].headers


def test_a_failure_that_is_not_a_refused_request_passes_through_untouched() -> None:
    """Only what a host's words can cause is converted. A value of a type JSON cannot hold is the
    caller's own mistake (a JSON reply holds no such value), a bug somebody has to see with its
    own message."""
    client = _accepting([])
    with pytest.raises(TypeError, match="JSON serializable"):
        client.post("/x", json={"a": object()})


def test_the_text_for_an_unbuildable_request_says_what_happened_and_what_it_withholds() -> None:
    assert "could not be built" in UNBUILDABLE_REQUEST_TEXT
    assert "withheld" in UNBUILDABLE_REQUEST_TEXT
    assert "repeats part of what was refused" in UNBUILDABLE_REQUEST_TEXT
    assert "cookie" in UNBUILDABLE_REQUEST_TEXT
    assert UNBUILDABLE_REQUEST_TEXT != PROTOCOL_ERROR_TEXT


def _setting_a_cookie(
    value: bytes, sent: list[httpx.Request]
) -> Callable[[httpx.Request], httpx.Response]:
    """A transport handler whose every reply sets the cookie ``value`` (raw bytes: a header)."""

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200, headers=[(b"set-cookie", value)], json={})

    return handler


@pytest.mark.parametrize("client_class", [httpx.Client, RepoHttpClient], ids=["plain", "ours"])
def test_a_cookie_a_host_set_that_httpx_cannot_send_back_refuses_every_later_request(
    client_class: type[httpx.Client],
) -> None:
    """The third build-time cause, and a permanent one: the client keeps the cookie, builds a
    ``Cookie`` header from it for every later request, and cannot encode a non-ASCII value. The
    plain client raises ``UnicodeEncodeError`` each time (not an ``httpx.HTTPError``); this client
    raises the fixed text. A cookie it can send changes nothing."""
    sent: list[httpx.Request] = []
    handler = _setting_a_cookie("a=caf\xe9".encode("latin-1"), sent)
    client = client_class(base_url="https://host.example", transport=httpx.MockTransport(handler))
    assert client.get("/first").status_code == 200
    for _ in range(3):
        if client_class is httpx.Client:
            with pytest.raises(UnicodeEncodeError):
                client.get("/later")
        else:
            with pytest.raises(httpx.LocalProtocolError) as caught:
                client.get("/later")
            assert str(caught.value) == UNBUILDABLE_REQUEST_TEXT
            assert caught.value.__cause__ is None and caught.value.__context__ is None
    assert [r.url.path for r in sent] == ["/first"]


def test_a_cookie_httpx_can_send_back_is_sent_back_by_this_client_as_by_the_plain_one() -> None:
    sent: list[httpx.Request] = []
    handler = _setting_a_cookie(b"a=b", sent)
    ours = RepoHttpClient(base_url="https://host.example", transport=httpx.MockTransport(handler))
    ours.get("/first")
    ours.get("/second")
    assert sent[1].headers["cookie"] == "a=b"


@pytest.mark.parametrize("adapter", [GitLabAdapter, GitHubAdapter], ids=["gitlab", "github"])
def test_an_adapter_turns_an_unbuildable_request_into_its_own_error(
    adapter: type[GitLabAdapter] | type[GitHubAdapter],
) -> None:
    """The adapters' ``except httpx.HTTPError`` blocks catch it now. The project id is the value
    both put in a path unquoted (GitLab quotes the namespace, so a control code there is built)."""
    built = adapter(host_url="https://host.example", private_token=TOKEN)
    sent: list[httpx.Request] = []
    built._client = _accepting(sent)
    with pytest.raises(RepoClientError) as caught:
        built.commit_files(project_id="g/n\x1b", branch="main", files={"a": "b"}, message="m")
    assert UNBUILDABLE_REQUEST_TEXT in str(caught.value)
    assert "non-printable" not in str(caught.value)  # ``httpx``'s own words
    assert caught.value.__cause__ is None and caught.value.__context__ is None
    assert sent == []
