"""The HTTP client both repository adapters share.

``h11`` quotes a header value it refuses (``Illegal header value b'glpat-...'``), and the token is
a header value. :func:`validate_repo_token` keeps a token that ``h11`` would refuse from ever being
sent, which is the fix; this client is the second line, so that a value the validator ever let
through, or any other part of a request ``h11`` objects to, still cannot be quoted back in an
exception message, in the ``-o`` file, or in a traceback that prints the chained cause.
"""

from __future__ import annotations

from typing import Any

import httpx

PROTOCOL_ERROR_TEXT = (
    "the request could not be sent: the HTTP library refused it as malformed. Its own message "
    "is withheld because it quotes the header values it refused, and the credential is one."
)


class RepoHttpClient(httpx.Client):
    """An :class:`httpx.Client` whose local protocol errors never quote the request.

    Every method (``get``, ``post``, ``patch``, ``request``) reaches the transport through
    :meth:`send`, so one override covers every call the adapters make. Any other failure, a refused
    connection or a timeout for instance, passes through with its own message.
    """

    def send(self, request: httpx.Request, **kwargs: Any) -> httpx.Response:
        try:
            return super().send(request, **kwargs)
        except httpx.LocalProtocolError:
            # ``from None``: the chained original is the thing that quotes the value.
            raise httpx.LocalProtocolError(PROTOCOL_ERROR_TEXT) from None
