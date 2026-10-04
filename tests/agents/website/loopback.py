"""A loopback HTTP server for the tests that need the real HTTP stack.

``httpx.MockTransport`` skips ``httpcore`` and ``h11`` altogether, so a test that wants to know
what the installed stack really sends, or refuses, has to talk to a socket. This is that socket:
it answers every request with ``200 {}`` and records the request headers it received.
"""

from __future__ import annotations

import http.server
import json
import os
import socketserver
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from unittest import mock

# ``httpx.Client`` honours these, which is the normal setup on an enterprise machine: with one set,
# a request to 127.0.0.1 goes to the proxy and a test about what a socket sent fails for a reason
# that has nothing to do with the subject.
PROXY_VARIABLES = (
    "HTTP_PROXY",
    "http_proxy",
    "HTTPS_PROXY",
    "https_proxy",
    "ALL_PROXY",
    "all_proxy",
)

# ``serve_forever`` polls for a shutdown request every 0.5 s by default, and ``shutdown()`` waits
# for the poll: a test that starts a server per request position spent most of its time idle.
POLL_INTERVAL = 0.01


@dataclass
class Loopback:
    url: str
    seen: list[dict[str, str]]
    errors: list[BaseException] = field(default_factory=list)


@contextmanager
def without_proxies() -> Iterator[None]:
    """Proxy variables set aside and ``NO_PROXY`` set for the loopback address, then restored."""
    with mock.patch.dict(os.environ):
        for name in PROXY_VARIABLES:
            os.environ.pop(name, None)
        os.environ["NO_PROXY"] = os.environ["no_proxy"] = "127.0.0.1"
        yield


@contextmanager
def serving() -> Iterator[Loopback]:
    seen: list[dict[str, str]] = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def _reply(self) -> None:
            seen.append({k.lower(): v for k, v in self.headers.items()})
            body = b"{}"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_GET = _reply  # noqa: N815
        do_POST = _reply  # noqa: N815

        def log_message(self, format: str, *args: object) -> None:
            """Keep the test output quiet."""

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": POLL_INTERVAL}, daemon=True
    ).start()
    try:
        yield Loopback(url=f"http://127.0.0.1:{server.server_address[1]}", seen=seen)
    finally:
        server.shutdown()
        server.server_close()


@contextmanager
def serving_raw(reply: Callable[[bytes], bytes]) -> Iterator[Loopback]:
    """A socket that answers every request with exactly the bytes ``reply`` returns for it.

    ``reply`` gets the whole request as the client sent it (request line, headers, body) and
    returns the whole response, so a test can send a valid ``500`` that echoes the request headers,
    or a reply no HTTP server would, such as a header line without a colon, which is what makes
    ``h11`` quote what it read. The connection is closed after one reply; ``seen`` holds the
    request headers, lower-cased, in arrival order.

    The proxy variables are set aside while it runs (the client is built inside the ``with``, which
    is when ``httpx`` reads them). An exception raised by ``reply`` in the handler's thread would
    otherwise be swallowed by ``socketserver`` and show up as the client's ``Server disconnected
    without sending a response``; it is recorded and raised when the block exits, so the cause is
    the failure. A connection the client dropped first is not one.
    """
    seen: list[dict[str, str]] = []
    errors: list[BaseException] = []

    class Handler(socketserver.StreamRequestHandler):
        def handle(self) -> None:
            head = b""
            while b"\r\n\r\n" not in head:
                chunk = self.request.recv(65536)
                if not chunk:
                    return
                head += chunk
            header_block, _, body = head.partition(b"\r\n\r\n")
            headers: dict[str, str] = {}
            for line in header_block.split(b"\r\n")[1:]:
                name, _, value = line.partition(b":")
                headers[name.decode("latin-1").lower()] = value.decode("latin-1").strip()
            wanted = int(headers.get("content-length", "0"))
            while len(body) < wanted:
                chunk = self.request.recv(65536)
                if not chunk:
                    break
                body += chunk
            seen.append(headers)
            try:
                self.request.sendall(reply(header_block + b"\r\n\r\n" + body))
            except ConnectionError:
                pass  # the client closed first: its business
            except Exception as error:
                errors.append(error)
                raise

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    with without_proxies():
        server = Server(("127.0.0.1", 0), Handler)
        threading.Thread(
            target=server.serve_forever, kwargs={"poll_interval": POLL_INTERVAL}, daemon=True
        ).start()
        try:
            yield Loopback(
                url=f"http://127.0.0.1:{server.server_address[1]}", seen=seen, errors=errors
            )
        finally:
            server.shutdown()
            server.server_close()
            if errors:
                # Raised from the ``finally`` on purpose: when the test body is already failing
                # with the client's "Server disconnected", this puts the cause in front of it.
                raise RuntimeError(f"the raw server's handler raised {errors[0]!r}") from errors[0]


def echo_the_api_key_in_a_400(request: bytes) -> bytes:
    """The reply of a gateway that rejects a call and quotes the request headers it got.

    A ``400`` whose body carries the ``x-api-key`` the client sent, as a proxy that echoes request
    headers does. The Anthropic SDK puts that body into the text of the exception it raises, so
    whatever turns that exception into text publishes the key. For ``serving_raw``.
    """
    head = request.split(b"\r\n\r\n", 1)[0].split(b"\r\n")[1:]
    sent = {
        name.decode("latin-1").lower(): value.decode("latin-1").strip()
        for name, _, value in (line.partition(b":") for line in head)
    }
    body = json.dumps(
        {
            "type": "error",
            "error": {
                "type": "invalid_request_error",
                "message": f"rejected the request (x-api-key: {sent.get('x-api-key', '')})",
            },
        }
    ).encode()
    reply = (
        "HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n"
    )
    return reply.encode() + body


def message(text: str) -> bytes:
    """A valid Messages API reply whose one text block is ``text``. For ``serving_raw``."""
    body = json.dumps(
        {
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "model": "test-model",
            "content": [{"type": "text", "text": text}],
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }
    ).encode()
    head = (
        "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n"
    )
    return head.encode() + body
