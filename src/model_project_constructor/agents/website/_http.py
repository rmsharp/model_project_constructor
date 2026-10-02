"""The HTTP client both repository adapters share.

``h11`` quotes a header value it refuses (``Illegal header value b'glpat-...'``), and the token is
a header value. :func:`validate_repo_token` keeps a token that ``h11`` would refuse from ever being
sent, which is the fix; this client is the second line, so that a value the validator ever let
through, or any other part of a request ``h11`` objects to, is not quoted back in an exception
message, in the ``-o`` file, or in a traceback or a walk of the exception's chain.
"""

from __future__ import annotations

import contextlib
from typing import Any

import httpx

PROTOCOL_ERROR_TEXT = (
    "the request could not be sent: the HTTP library refused it as malformed. Its own message "
    "is withheld because it can quote the header values it refused, and the credential is one."
)


class RepoHttpClient(httpx.Client):
    """An :class:`httpx.Client` whose local protocol errors never quote the request.

    Every method (``get``, ``post``, ``patch``, ``request``, ``stream``) reaches the transport
    through :meth:`send`, so one override covers every call the adapters make. Any other failure,
    a refused connection or a timeout or a malformed response for instance, passes through with
    its own message.
    """

    def send(self, request: httpx.Request, **kwargs: Any) -> httpx.Response:
        with contextlib.suppress(httpx.LocalProtocolError):
            return super().send(request, **kwargs)
        # Raised here, after the handler, on purpose: inside it the original would stay reachable
        # on ``__context__`` (``from None`` only keeps it out of a printed traceback), and the
        # original is the thing that quotes the value.
        raise httpx.LocalProtocolError(PROTOCOL_ERROR_TEXT, request=request)
