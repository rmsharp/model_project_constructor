"""What a repository host's words may carry out of an adapter.

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

A host's SUCCESS replies are its words too (``BACKLOG.md`` route 8): the project address, the
project id, the default branch and the commit id in a ``2xx`` become the fields of ``ProjectInfo``
and ``CommitInfo``, then of ``RepoProjectResult``, which the website command and the pipeline
script print and the pipeline saves; and the id and the branch go back to the host inside a request
path, where a control character makes ``httpx`` raise ``InvalidURL`` out of the adapter, past
:func:`scrubbed_errors`, because it is not a ``RepoClientError``. :func:`scrubbed_values` applies
the same scrub to what a protocol method RETURNS.

What this does not cover. The party that echoes the headers already holds the token, so these are
the limits of an INNOCENT echo, not defences against a hostile host: a token transformed in a way
not listed in :func:`_rewrites` (base64, a hash, or a different escaping of some of its characters
only); one with characters inserted in it, or cut short, or split across lines by the host; a second
credential (userinfo in the host URL travels as ``Authorization: Basic base64(user:password)``); a
message built, or a value returned, by a ``RepoClient`` other than the two adapters; and a value an
adapter reads from one reply and puts in its next request, which :func:`scrubbed_values` never
sees because it is not on what the method returns (GitHub's ``parent_sha`` and commit sha: a
control character or a lone surrogate there raises ``InvalidURL`` or ``UnicodeEncodeError``;
``BACKLOG.md``).
"""

from __future__ import annotations

import functools
import html
import json
import re
from collections.abc import Callable
from typing import Concatenate, ParamSpec, Protocol, TypeVar, cast
from urllib.parse import quote, quote_plus

import httpx

from model_project_constructor.agents.website.protocol import (
    CommitInfo,
    ProjectInfo,
    RepoClientError,
    RepoNameConflictError,
)

#: How much of a message is kept, in characters; a cut message is followed by a one-line notice of
#: about 40 more. A host's error page (a gateway's HTML, a stack trace) can run to megabytes; an
#: operator needs the status and the first lines of it.
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
    # h11: ``bytearray(b'...')``; for printable ASCII it is also what a Python ``repr`` in a log
    # line writes (a ``str`` repr is the same text, so it has no escaper of its own).
    lambda s: repr(s.encode("utf-8", "replace"))[2:-1],
    # A ``repr`` writes a quote as ``\'`` only when the string it quotes holds both kinds, so the
    # secret alone never shows this form: it is the one a longer message gives it.
    lambda s: s.replace("\\", "\\\\").replace("'", "\\'"),
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
    if not isinstance(secret, str):
        # Raised, not skipped: the caller's ``except`` turns it into UNPRINTABLE. A secret that was
        # not removed must not look like text that never held one.
        raise TypeError("the secret must be a str")
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

    Runs inside the ``except`` blocks that deliver a ``failure_reason``, and over the values a
    success reply returns, so it must not be a raise site itself: any failure returns
    :data:`UNPRINTABLE`. A lone surrogate is replaced first, because text holding one makes a file
    write or ``model_dump_json`` raise.
    """
    try:
        limit = max(limit, 0)
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
    """``response.text``, or the body as UTF-8 with replacement if reading it as declared fails.

    The host chooses the charset, and ``httpx`` takes any name ``codecs.lookup`` knows. A name
    that is not a text codec (``undefined``, ``rot13``, ``hex``, ``zlib``, ``idna``...) makes
    ``response.text`` raise ``UnicodeError``, ``TypeError`` or ``AssertionError``, and a body that
    is not in the charset it declares raises ``UnicodeDecodeError`` on Python 3.13 but a plain
    ``UnicodeError`` on 3.11 and 3.12 (CI runs 3.12). The adapters read the body while building
    the message for a failure, so any of these would leave the adapter as a crash that is not a
    ``RepoClientError``, past :func:`scrubbed_errors`. So the fallback catches ``Exception``: this
    function is total. The adapters read a body in no other way (a test holds that).
    """
    try:
        return response.text
    except Exception:
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
            replacement = RepoClientError(_scrubbed_message(exc, self))
        raise replacement

    # What a registry-wide test looks for. ``__wrapped__`` is set by every ``functools.wraps``
    # decorator (a retry, a timer), so it cannot tell this one from one that scrubs nothing.
    wrapper.__scrubs_host_text__ = True  # type: ignore[attr-defined]
    return wrapper


def _scrubbed_message(error: RepoClientError, holder: _HoldsSecret) -> str:
    """``scrub_host_text`` of the error with the holder's secret; UNPRINTABLE if it has none.

    Read here, inside a guard, and not in the handler: an ``AttributeError`` raised in the handler
    would chain the unscrubbed original onto ``__context__``.
    """
    try:
        return scrub_host_text(error, holder._secret)
    except Exception:
        return UNPRINTABLE


def scrub_project_info(info: ProjectInfo, secret: str = "") -> ProjectInfo:
    """A new ``ProjectInfo`` whose three fields went through :func:`scrub_host_text`.

    ``id``, ``url`` and ``default_branch`` are all the host's words. Text with nothing to remove (an
    address with a port, a query and non-ASCII letters, a GitHub ``owner/name``, a branch with a
    slash) comes out as it went in. An id or a branch that held a control character comes out with
    a space where it was, so it names nothing the host has and the next request fails the way a
    request for any unknown project does, instead of ``httpx`` refusing the path.
    """
    return ProjectInfo(
        id=scrub_host_text(info.id, secret),
        url=scrub_host_text(info.url, secret),
        default_branch=scrub_host_text(info.default_branch, secret),
    )


def scrub_commit_info(commit: CommitInfo, secret: str = "") -> CommitInfo:
    """A new ``CommitInfo`` whose ``sha`` went through :func:`scrub_host_text`.

    ``files_committed`` is the caller's own list of paths, not anything the host said, and is copied
    as it is: a scrub would collapse the spaces in a path the project really holds.
    """
    return CommitInfo(
        sha=scrub_host_text(commit.sha, secret),
        files_committed=list(commit.files_committed),
    )


_V = TypeVar("_V", ProjectInfo, CommitInfo)


def scrubbed_values(
    method: Callable[Concatenate[_S, _P], _V],
) -> Callable[Concatenate[_S, _P], _V]:
    """Scrub the host's words out of the ``ProjectInfo`` or ``CommitInfo`` a method returns.

    Applied where a value LEAVES an adapter, for the reason :func:`scrubbed_errors` is: the many
    places a reply is read cannot each be remembered. ``self._secret`` is removed by value, the one
    :func:`scrubbed_errors` removes, because a host that echoes the request headers can put the
    token in a ``2xx`` as easily as in an error page. The result is a new object, so what a test
    double returned is not changed. An exception is not touched: stack this UNDER
    :func:`scrubbed_errors`, which owns it.

    Fails closed on a result of any other type, which no method of the protocol returns: a method
    added to ``RepoClient`` would otherwise carry this marker and scrub nothing.
    """

    @functools.wraps(method)
    def wrapper(self: _S, /, *args: _P.args, **kwargs: _P.kwargs) -> _V:
        # ``_scrubbed_result`` returns the kind it was given, which a type checker cannot see.
        return cast("_V", _scrubbed_result(method(self, *args, **kwargs), self._secret))

    # What a registry-wide test looks for, set by this decorator alone (see ``scrubbed_errors``).
    wrapper.__scrubs_host_values__ = True  # type: ignore[attr-defined]
    return wrapper


def _scrubbed_result(
    result: ProjectInfo | CommitInfo, secret: str
) -> ProjectInfo | CommitInfo:
    if isinstance(result, ProjectInfo):
        return scrub_project_info(result, secret)
    if isinstance(result, CommitInfo):
        return scrub_commit_info(result, secret)
    raise TypeError(
        f"scrubbed_values wraps a method that returns ProjectInfo or CommitInfo, "
        f"not {type(result).__name__}"
    )
