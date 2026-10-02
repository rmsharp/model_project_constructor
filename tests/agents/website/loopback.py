"""A loopback HTTP server for the tests that need the real HTTP stack.

``httpx.MockTransport`` skips ``httpcore`` and ``h11`` altogether, so a test that wants to know
what the installed stack really sends, or refuses, has to talk to a socket. This is that socket:
it answers every request with ``200 {}`` and records the request headers it received.
"""

from __future__ import annotations

import http.server
import socketserver
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass
class Loopback:
    url: str
    seen: list[dict[str, str]]


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
    threading.Thread(target=server.serve_forever, daemon=True).start()
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
    """
    seen: list[dict[str, str]] = []

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
            self.request.sendall(reply(header_block + b"\r\n\r\n" + body))

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    server = Server(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield Loopback(url=f"http://127.0.0.1:{server.server_address[1]}", seen=seen)
    finally:
        server.shutdown()
        server.server_close()
