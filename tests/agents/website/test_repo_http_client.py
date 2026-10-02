"""The shared adapter client withholds the HTTP library's protocol-error text.

``h11`` quotes the header values it refuses, and a credential is one. ``test_repo_token.py`` holds
the first line of defence, a validator that keeps such a value from being sent; this file holds the
second, which does not depend on the validator being complete. The adapters cannot reach the real
error (their constructors refuse the value first), so most tests drive ``RepoHttpClient`` through
``httpx.MockTransport`` raising the error ``h11`` raises; two build the client directly with a
refused header and talk to a real socket, which is the only thing that shows the installed stack
still raises the class this client catches.
"""

from __future__ import annotations

import traceback
from collections.abc import Iterator

import httpx
import pytest

from model_project_constructor.agents.website import GitHubAdapter, GitLabAdapter
from model_project_constructor.agents.website._http import (
    PROTOCOL_ERROR_TEXT,
    RepoHttpClient,
)
from model_project_constructor.agents.website.protocol import RepoClientError
from tests.agents.website.loopback import Loopback

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
