"""The HTTP client both repository adapters share.

``h11`` quotes a header value it refuses (``Illegal header value b'glpat-...'``), and the token is
a header value. :func:`validate_repo_token` keeps a token that ``h11`` would refuse from ever being
sent, which is the fix; this client is the second line, so that a value the validator ever let
through, or any other part of a request ``h11`` objects to, is not quoted back in an exception
message, in the ``-o`` file, or in a traceback or a walk of the exception's chain.

A request can be refused at three points, and each needs its own override. ``httpx`` BUILDS a
request (its address, its body and the ``Cookie`` header it makes from the cookies a host set) and
then SENDS it; ``h11`` objects at the second. The first raises ``InvalidURL`` for a control
character in a path and ``ValueError`` for what a body cannot hold: a lone surrogate (as
``UnicodeEncodeError``) or ``NaN`` or an infinity, from ``httpx`` 0.28, which writes a JSON body as
UTF-8 with ``allow_nan=False``; 0.27 escapes the first and sends the second. A non-ASCII cookie
value a host set is a third cause, and a permanent one: the client keeps the cookie and refuses
every later request. None of these is an ``httpx.HTTPError``, so the adapters' ``except
httpx.HTTPError`` blocks never caught them. An adapter writes values the host sent into its next
request, so what makes the request unbuildable is the host's to choose.

The third point is a request built from the host's reply, not from the adapter's call: a 3xx's
``Location``. ``httpx`` builds the request a redirect asks for even when it is told not to follow
it, because it keeps that request as ``response.next_request``, so the header is read on every 3xx.
The library parses the address itself and converts what its parser refuses (``RemoteProtocolError``,
"Invalid URL in location header"), then joins what is left with the request's address, and that
step raises what the parser let through: ``InvalidURL`` for an address short enough alone and too
long joined (a window of about 26 characters of ``Location`` length, which moves with the length of
the request's own address), and ``ValueError`` from the standard library's and ``idna``'s parsers
(an unclosed ``[``, a malformed ``xn--`` label). A fuzz of 60,000 random values found those and
nothing else. The override is on ``_build_redirect_request``, a private method of ``httpx``,
because that is where the traceback shows the error raised and a catch in ``send`` would also hide
a ``ValueError`` from the transport; ``test_repo_http_client.py`` fails if a release stops raising
these or renames the method, so the conversion cannot go inert silently.

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

UNBUILDABLE_REDIRECT_TEXT = (
    "the host's reply redirected the request, and the HTTP library could not build the "
    "redirected request from the address the host gave (too long or malformed). Its own message "
    "is withheld because it repeats part of what the host sent."
)


class RepoHttpClient(httpx.Client):
    """An :class:`httpx.Client` whose request errors never quote the request.

    Every method (``get``, ``post``, ``patch``, ``request``, ``stream``) builds its request with
    :meth:`build_request` and reaches the transport through :meth:`send`, and a reply that
    redirects has its next request built by ``_build_redirect_request``, so one override of each
    covers every call the adapters make. The first two raise :class:`httpx.LocalProtocolError`, an
    :class:`httpx.HTTPError`, with a fixed text: a request that cannot be built fails the call as
    any other failed call does, and a retry builds it the same way and fails the same way. The one
    that :meth:`build_request` raises has no ``request`` (building one is what failed), so reading
    its ``.request`` raises ``RuntimeError``; nothing in this repository reads it. The third raises
    :class:`httpx.RemoteProtocolError`, the class the library uses itself for a redirect address it
    refuses, carrying the request that was sent. Any other failure, a refused connection or a
    timeout or a malformed response for instance, passes through with its own message.

    Only what a host's words can cause is converted: ``InvalidURL`` and ``ValueError`` (which
    holds ``UnicodeEncodeError`` and ``idna``'s errors), at the two points that build a request. A
    ``TypeError``, a value of a type JSON cannot hold, is the caller's own mistake, since a JSON
    reply holds no such value, and it passes through; so does a ``ValueError`` from anywhere else
    in ``send``, the transport's for instance.
    """

    def build_request(self, *args: Any, **kwargs: Any) -> httpx.Request:
        with contextlib.suppress(httpx.InvalidURL, ValueError):
            return super().build_request(*args, **kwargs)
        # Raised here, after the handler, for the reason ``send`` does it below. There is no
        # request to attach: building one is what failed.
        raise httpx.LocalProtocolError(UNBUILDABLE_REQUEST_TEXT)

    def _build_redirect_request(
        self, request: httpx.Request, response: httpx.Response
    ) -> httpx.Request:
        with contextlib.suppress(httpx.InvalidURL, ValueError):
            return super()._build_redirect_request(request, response)
        # Raised here, after the handler, for the reason ``send`` does it below. It is the class
        # the library raises itself for an address it refuses ("Invalid URL in location header"),
        # not ``LocalProtocolError``: ``send`` replaces that one with its own text.
        raise httpx.RemoteProtocolError(UNBUILDABLE_REDIRECT_TEXT, request=request)

    def send(self, request: httpx.Request, **kwargs: Any) -> httpx.Response:
        with contextlib.suppress(httpx.LocalProtocolError):
            return super().send(request, **kwargs)
        # Raised here, after the handler, on purpose: inside it the original would stay reachable
        # on ``__context__`` (``from None`` only keeps it out of a printed traceback), and the
        # original is the thing that quotes the value.
        raise httpx.LocalProtocolError(PROTOCOL_ERROR_TEXT, request=request)
