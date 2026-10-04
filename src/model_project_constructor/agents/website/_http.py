"""The HTTP client both repository adapters share.

``h11`` quotes a header value it refuses (``Illegal header value b'glpat-...'``), and the token is
a header value. :func:`validate_repo_token` keeps a token that ``h11`` would refuse from ever being
sent, which is the fix; this client is the second line, so that a value the validator ever let
through, or any other part of a request ``h11`` objects to, is not quoted back in an exception
message, in the ``-o`` file, or in a traceback or a walk of the exception's chain.

A request can be refused at two stages, and each needs its own override. ``httpx`` BUILDS a request
(its address and its body) and then SENDS it: ``h11`` objects at the second stage, and the first
raises ``InvalidURL`` for a control character in a path and ``UnicodeEncodeError`` for a lone
surrogate in a path or, from ``httpx`` 0.28, in a body. Neither of those is an ``httpx.HTTPError``,
so the adapters' ``except httpx.HTTPError`` blocks never caught them, and both quote the value
they refused. An adapter writes values the host sent into its next request, so the value is the
host's to choose.
"""

from __future__ import annotations

import contextlib
from typing import Any

import httpx

PROTOCOL_ERROR_TEXT = (
    "the request could not be sent: the HTTP library refused it as malformed. Its own message "
    "is withheld because it can quote the header values it refused, and the credential is one."
)

UNBUILDABLE_REQUEST_TEXT = (
    "the request could not be built: the HTTP library refused part of its address or body as "
    "malformed (a control character or an unpaired surrogate, for instance). Its own message is "
    "withheld because it can quote the value it refused, and a value a host sent can carry the "
    "credential."
)


class RepoHttpClient(httpx.Client):
    """An :class:`httpx.Client` whose request errors never quote the request.

    Every method (``get``, ``post``, ``patch``, ``request``, ``stream``) builds its request with
    :meth:`build_request` and reaches the transport through :meth:`send`, so one override of each
    covers every call the adapters make. Both raise :class:`httpx.LocalProtocolError`, an
    :class:`httpx.HTTPError`, with a fixed text: a request that cannot be built fails the call as
    any other failed call does, and a retry builds it the same way and fails the same way. Any other
    failure, a refused connection or a timeout or a malformed response for instance, passes through
    with its own message.
    """

    def build_request(self, *args: Any, **kwargs: Any) -> httpx.Request:
        with contextlib.suppress(httpx.InvalidURL, UnicodeEncodeError):
            return super().build_request(*args, **kwargs)
        # Raised here, after the handler, for the reason ``send`` does it below. There is no
        # request to attach: building one is what failed.
        raise httpx.LocalProtocolError(UNBUILDABLE_REQUEST_TEXT)

    def send(self, request: httpx.Request, **kwargs: Any) -> httpx.Response:
        with contextlib.suppress(httpx.LocalProtocolError):
            return super().send(request, **kwargs)
        # Raised here, after the handler, on purpose: inside it the original would stay reachable
        # on ``__context__`` (``from None`` only keeps it out of a printed traceback), and the
        # original is the thing that quotes the value.
        raise httpx.LocalProtocolError(PROTOCOL_ERROR_TEXT, request=request)
