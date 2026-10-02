"""What a repository host's failure text may carry out of an adapter.

A ``RepoClientError`` message is built from words the host chose: an error body, or the HTTP
library's account of a reply it could not parse (``h11`` quotes the bytes the server sent). The
message becomes ``failure_reason``, which the website command prints and writes to ``-o`` and
the pipeline script prints and saves in its checkpoint. A host or proxy that echoes the request
headers puts the access token into all of that, and a body can also carry terminal control codes or
be any length.

:func:`scrub_host_text` removes the secret by value, in every form a host re-encodes it in, makes
the text one line free of control characters, and bounds its length. :func:`scrubbed_errors` applies
it where an error LEAVES an adapter, not at the many places a message is built, so a site added
later cannot bypass it.

What this does not cover: a host that echoes the token transformed in a way not listed in
:func:`_rewrites` (base64, a hash), a secret split across lines by the host, and a message built by
a ``RepoClient`` other than the two adapters.
"""

from __future__ import annotations

import functools
import html
import json
import re
from collections.abc import Callable
from typing import Concatenate, ParamSpec, Protocol, TypeVar
from urllib.parse import quote, quote_plus

import httpx

from model_project_constructor.agents.website.protocol import (
    RepoClientError,
    RepoNameConflictError,
)

#: Longest message that leaves an adapter, in characters. A host's error page (a gateway's HTML, a
#: stack trace) can run to megabytes; an operator needs the status and the first lines of it.
MAX_HOST_TEXT = 1000

#: What replaces the secret.
REDACTED = "***"

#: What :func:`scrub_host_text` returns when it cannot finish: a scrub that did not complete has not
#: removed the secret.
UNPRINTABLE = "<unprintable>"

#: What a terminal acts on instead of printing: the C0 controls, DEL and the C1 controls (Unicode
#: category ``Cc``). Each becomes a space, so ``a<ESC>b`` does not read ``ab``.
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f-\x9f]")

_ESCAPERS: tuple[Callable[[str], str], ...] = (
    lambda s: json.dumps(s)[1:-1],  # a JSON body
    lambda s: repr(s.encode("utf-8", "replace"))[2:-1],  # h11: ``bytearray(b'...')``
    lambda s: repr(s)[1:-1],  # a Python ``repr`` in a log line
    html.escape,  # an HTML error page
    lambda s: quote(s, safe=""),  # a URL, or a form body
    quote_plus,
)


def _rewrites(secret: str) -> set[str]:
    """The secret as written, and as each re-encoder a host is known to use writes it.

    Two levels, because one nests in another: ``h11``'s ``bytearray(b'...')`` inside a JSON body is
    the bytes repr, escaped again. A token made of letters, digits, ``-`` and ``_`` (every real one)
    is its own form in all of them; the others differ only for ``" ' \\ & < > % +`` and the like,
    which the validator admits.
    """
    forms = {secret}
    frontier = {secret}
    for _ in range(2):
        frontier = {escape(form) for form in frontier for escape in _ESCAPERS} - forms
        forms |= frontier
    return forms


def _secret_pattern(secret: str) -> re.Pattern[str] | None:
    if not secret:
        return None
    # An alternation takes the first alternative that matches where it starts, not the longest, so
    # the longest form goes first: a secret ending in a backslash is a prefix of its own JSON form.
    ordered = sorted(_rewrites(secret), key=lambda form: (-len(form), form))
    return re.compile("|".join(re.escape(form) for form in ordered), re.IGNORECASE)


def scrub_host_text(text: object, secret: str = "", *, limit: int = MAX_HOST_TEXT) -> str:
    """``str(text)`` made safe to print, log, persist and put in a report.

    Removes ``secret`` wherever it appears, in any case and in any form of :func:`_rewrites`
    (``Bearer <token>`` keeps its scheme and loses the token); replaces each control character
    with a space and joins the result onto one line; and cuts it to ``limit`` characters, saying
    how many were left out. The secret is removed BEFORE the cut, so one straddling the limit cannot
    survive as a prefix, and again after the line is joined, for a secret that only matches then.

    Runs inside the ``except`` blocks that deliver a ``failure_reason``, so it must not be a raise
    site itself: any failure returns :data:`UNPRINTABLE`. A lone surrogate is replaced first,
    because text holding one makes a file write or ``model_dump_json`` raise.
    """
    try:
        raw = str(text).encode("utf-8", "replace").decode("utf-8")
        pattern = _secret_pattern(secret)
        if pattern is not None:
            raw = pattern.sub(REDACTED, raw)
        line = " ".join(_CONTROL_CHARACTERS.sub(" ", raw).split())
        if pattern is not None:
            line = pattern.sub(REDACTED, line)
        if len(line) > limit:
            line = f"{line[:limit]}... [{len(line) - limit} more characters not shown]"
        return line
    except Exception:
        return UNPRINTABLE


def response_text(response: httpx.Response) -> str:
    """``response.text``, or the body as UTF-8 with replacement if its charset cannot decode it.

    A reply that declares a charset its body is not in (``charset=utf-16`` on ASCII of odd length)
    makes ``response.text`` raise ``UnicodeDecodeError``. The adapters read it while building the
    message for a failure, so the error that results is not a ``RepoClientError``: it would leave
    the adapter as a crash, past :func:`scrubbed_errors`, holding the body's bytes in its ``args``.
    The adapters read a response body in no other way (a test holds that).
    """
    try:
        return response.text
    except (UnicodeDecodeError, LookupError):
        return response.content.decode("utf-8", "replace")


class _HoldsSecret(Protocol):
    _secret: str


_S = TypeVar("_S", bound=_HoldsSecret)
_P = ParamSpec("_P")
_R = TypeVar("_R")


def scrubbed_errors(
    method: Callable[Concatenate[_S, _P], _R],
) -> Callable[Concatenate[_S, _P], _R]:
    """Re-raise a method's ``RepoClientError`` with ``self._secret`` and the rest scrubbed out.

    The replacement is a plain ``RepoClientError`` raised AFTER the handler, so it has no
    ``__cause__`` and no ``__context__``: the original was built ``from`` an ``httpx`` error whose
    message can quote what the server sent, and neither ``from None`` (which only hides it from a
    printed traceback) nor keeping it reachable is acceptable (``PROJECT_LEARNINGS.md`` #320).
    ``RepoNameConflictError`` passes through: its text is the name the caller chose, and the nodes
    catch it by class.
    """

    @functools.wraps(method)
    def wrapper(self: _S, /, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        try:
            return method(self, *args, **kwargs)
        except RepoNameConflictError:
            raise
        except RepoClientError as exc:
            replacement = RepoClientError(scrub_host_text(exc, self._secret))
        raise replacement

    return wrapper
