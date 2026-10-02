"""The shared adapter client withholds the HTTP library's protocol-error text.

``h11`` quotes the header values it refuses, and a credential is one. ``test_repo_token.py`` holds
the first line of defence, a validator that keeps such a value from being sent; this file holds the
second, which does not depend on the validator being complete. Both are driven through
``httpx.MockTransport`` raising the error ``h11`` raises, because the validator makes the real
thing unreachable by design.
"""

from __future__ import annotations

import traceback

import httpx
import pytest

from model_project_constructor.agents.website import GitHubAdapter, GitLabAdapter
from model_project_constructor.agents.website._http import (
    PROTOCOL_ERROR_TEXT,
    RepoHttpClient,
)
from model_project_constructor.agents.website.protocol import RepoClientError

SECRET = "glpat-SECRET9f3kQ7"
URL = "https://host.example/api"


def _refusing(message: str, error: type[Exception] = httpx.LocalProtocolError) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        raise error(message)

    return RepoHttpClient(transport=httpx.MockTransport(handler))


def test_a_protocol_error_is_replaced_and_its_chain_is_cut() -> None:
    client = _refusing(f"Illegal header value b'{SECRET}\\r'")
    with pytest.raises(httpx.LocalProtocolError) as caught:
        client.get(URL)
    assert str(caught.value) == PROTOCOL_ERROR_TEXT
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True
    assert SECRET not in "".join(traceback.format_exception(caught.value))


@pytest.mark.parametrize("method", ["get", "post", "patch", "put", "delete"])
def test_every_method_goes_through_the_override(method: str) -> None:
    client = _refusing(f"Illegal header value b'{SECRET}\\r'")
    with pytest.raises(httpx.LocalProtocolError) as caught:
        getattr(client, method)(URL)
    assert SECRET not in str(caught.value)


def test_the_stream_path_goes_through_the_override_too() -> None:
    client = _refusing(f"Illegal header value b'{SECRET}\\r'")
    with pytest.raises(httpx.LocalProtocolError) as caught, client.stream("GET", URL):
        pass
    assert SECRET not in str(caught.value)


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


@pytest.mark.parametrize("adapter", [GitLabAdapter, GitHubAdapter], ids=["gitlab", "github"])
def test_the_adapters_build_their_client_from_it(
    adapter: type[GitLabAdapter] | type[GitHubAdapter],
) -> None:
    built = adapter(host_url="https://host.example", private_token="t")
    assert isinstance(built._client, RepoHttpClient)


@pytest.mark.parametrize("adapter", [GitLabAdapter, GitHubAdapter], ids=["gitlab", "github"])
def test_an_adapter_never_repeats_the_quoted_value_in_its_error(
    adapter: type[GitLabAdapter] | type[GitHubAdapter],
) -> None:
    built = adapter(host_url="https://host.example", private_token="t")
    built._client = _refusing(f"Illegal header value b'{SECRET}\\r'")
    with pytest.raises(RepoClientError) as caught:
        built.create_project(namespace="g", name="n", visibility="private")
    assert SECRET not in str(caught.value)
    assert PROTOCOL_ERROR_TEXT in str(caught.value)
    assert SECRET not in "".join(traceback.format_exception(caught.value))
