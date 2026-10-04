"""The HTTP client both repository adapters share.

``h11`` quotes a header value it refuses (``Illegal header value b'glpat-...'``), and the token is
a header value. :func:`validate_repo_token` keeps a token that ``h11`` would refuse from ever being
sent, which is the fix; this client is the second line, so that a value the validator ever let
through, or any other part of a request ``h11`` objects to, is not quoted back in an exception
message, in the ``-o`` file, or in a traceback or a walk of the exception's chain.

A request can be refused at two stages, and each needs its own override. ``httpx`` BUILDS a request
(its address, its body and the ``Cookie`` header it makes from the cookies a host set) and then
SENDS it. ``h11`` objects at the second stage. The first raises ``InvalidURL`` for a control
character in a path and ``ValueError`` for what a body cannot hold: a lone surrogate (as
``UnicodeEncodeError``) or ``NaN`` or an infinity, from ``httpx`` 0.28, which writes a JSON body as
UTF-8 with ``allow_nan=False``; 0.27 escapes the first and sends the second. A non-ASCII cookie
value a host set is a third cause, and a permanent one: the client keeps the cookie and refuses
every later request. None of these is an ``httpx.HTTPError``, so the adapters' ``except
httpx.HTTPError`` blocks never caught them. An adapter writes values the host sent into its next
request, so what makes the request unbuildable is the host's to choose.

What the library's own message holds, measured on 0.27.2 and 0.28.1: for a control character or a
surrogate, that one character and its position; for ``NaN`` or an infinity, the number. (Its
refusals of a host or a port quote their text, but the adapters take those from their own
configuration.) It does not repeat the whole value, so that is not why it is withheld. It is
withheld because it repeats part of what a host chose, in the library's wording, which changes
between versions: the fixed text is the same for every refusal.
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
    "the request could not be built: the HTTP library refused part of it (its address, its body "
    "or a cookie) as malformed, for instance a control character, an unpaired surrogate or a "
    "number JSON cannot hold. Its own message is withheld because it repeats part of what was "
    "refused, and a host chose that text."
)


class RepoHttpClient(httpx.Client):
    """An :class:`httpx.Client` whose request errors never quote the request.

    Every method (``get``, ``post``, ``patch``, ``request``, ``stream``) builds its request with
    :meth:`build_request` and reaches the transport through :meth:`send`, so one override of each
    covers every call the adapters make. Both raise :class:`httpx.LocalProtocolError`, an
    :class:`httpx.HTTPError`, with a fixed text: a request that cannot be built fails the call as
    any other failed call does, and a retry builds it the same way and fails the same way. The one
    that :meth:`build_request` raises has no ``request`` (building one is what failed), so reading
    its ``.request`` raises ``RuntimeError``; nothing in this repository reads it. Any other
    failure, a refused connection or a timeout or a malformed response for instance, passes through
    with its own message.

    Only what a host's words can cause is converted: ``InvalidURL`` and ``ValueError`` (which
    holds ``UnicodeEncodeError``). A ``TypeError``, a value of a type JSON cannot hold, is the
    caller's own mistake, since a JSON reply holds no such value, and it passes through.
    """

    def build_request(self, *args: Any, **kwargs: Any) -> httpx.Request:
        with contextlib.suppress(httpx.InvalidURL, ValueError):
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
