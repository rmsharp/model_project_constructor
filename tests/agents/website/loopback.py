"""A loopback HTTP server for the tests that need the real HTTP stack.

``httpx.MockTransport`` skips ``httpcore`` and ``h11`` altogether, so a test that wants to know
what the installed stack really sends, or refuses, has to talk to a socket. This is that socket:
it answers every request with ``200 {}`` and records the request headers it received.
"""

from __future__ import annotations

import http.server
import threading
from collections.abc import Iterator
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
