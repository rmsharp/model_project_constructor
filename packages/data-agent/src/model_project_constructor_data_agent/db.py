"""Read-only database access for the EXECUTE_QC node.

Read-only enforcement is a database-credential concern in production (§9.1).
This wrapper deliberately does not attempt to parse or reject mutating SQL —
the Data Agent's LLM is prompted to emit SELECTs, and the pipeline is
configured with a SELECT-only role at deployment time. The wrapper's sole
job is to surface a clean :class:`DBConnectionError` on connect failure so
the graph can take the SKIP_EXECUTION off-ramp described in §10.
"""

from __future__ import annotations

import contextlib
import logging
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import unquote

import sqlalchemy as sa

_LOG = logging.getLogger(__name__)

# A ``--db-url`` carries a secret in two places, and both reach the operator-
# facing DataReport once EXECUTE_QC starts reporting the connect error
# (``agent.py``'s ``data_quality_concerns``), and a third place once a driver
# echoes a secret-bearing DSN or header inside its own exception text
# (``discovery.py``'s reflection note). Measured, not assumed:
#
#   postgresql://user:hunter2@host/claims          -> userinfo
#   postgresql://host/claims?password=hunter2      -> query string, and
#       SQLAlchemy passes it to the DBAPI as a real password
#   PWD=hunter2;Database=claims                    -> a libpq/ODBC DSN a
#       driver may echo back verbatim inside its own error text
#
# Session 261 shipped ``_SECRET_KV`` keyed on a bare word boundary before an
# unquoted, unbroken value. Session 261's own item measured what that missed:
# a PREFIXED key (``DB_PASSWORD=``, ``\b`` does not cross ``_``), a camel-cased
# or hyphenated one (``AccessToken``, ``X-Amz-Signature``), a QUOTED or braced
# value (the libpq/ODBC form a password containing a space or ``;`` requires),
# a ``:`` or spaced ``=`` separator (JSON, YAML-ish log lines), a value whose
# OWN tail leaks past a ``&``/``;`` that does not start a new ``key=`` pair,
# a username containing ``@`` (Azure/email-login form — SQLAlchemy accepts it
# unencoded, and it defeated a pattern that stops at the FIRST ``@``), and a
# secret percent-encoded inside ``odbc_connect=``. ``_SECRET_KEY`` widens the
# key list and drops the ``\b``/word-character assumption; ``_SECRET_KV`` adds
# the quoted/braced/bare value alternation; ``_mask_kv`` percent-decodes a
# COPY of the text to find matches (so ``PWD%3Dx%3B`` is seen as ``PWD=x;``)
# while editing the original, so nothing outside a matched span is disturbed.
# It still does not cover a secret under a key not in ``_SECRET_KEY``, nor a
# bare-key, header, ``Bearer``, or SigV4-signature shape with no ``key=``/
# ``key:`` form at all (`BACKLOG.md`, "the password masker misses common
# shapes").
_SECRET_KEY = (
    r"(?:password|passwd|pwd|passphrase|passcode|sslpassword|secret[_-]?key"
    r"|private[_-]?key|access[_-]?key|api[_-]?key|secret|token|credentials?|signature)"
)
_SECRET_VALUE = (
    r'(?:"(?:[^"\\]|\\.)*(?:"|\Z)'  # double-quoted, backslash-escaped
    r"|'(?:[^'\\]|\\.|'')*(?:'|\Z)"  # single- or doubled-single-quoted
    r"|\{(?:[^{}]|\{[^{}]*\})*(?:\}|\Z)"  # one level of {...} (ODBC braces)
    # bare: any run of non-space chars, but stop before a `;`/`&`/`,` that
    # itself opens a fresh `key=` pair or ends the string -- otherwise a
    # secret's own unescaped tail (`password=x&y`, `PWD={x y};`) survives.
    r"|(?:(?![;&,](?:\s|\Z|[\w.\-]+\s*=))\S)+)"
)
_SECRET_KV = re.compile(
    rf"(?is)({_SECRET_KEY}[\"']?\s*(?:=>|=|:)\s*)({_SECRET_VALUE})"
)

# Free-form text is matched conservatively: the value stops at the first whitespace, so
# the pass cannot span from one URL to an unrelated ``@`` later in the message. The operator's
# OWN address is not free-form text and is handled by ``redact_db_url`` below, which knows the
# structure and can therefore also tell when SQLAlchemy has read it wrongly.
_USERINFO_TEXT = re.compile(r"(://[^:/\s]*:)[^\s]*(@)")

# One byte (or one percent-escape triple) at a time, for _mask_kv's decoded view.
_BYTE_OR_PCT = re.compile(r"%[0-9A-Fa-f]{2}|.", re.DOTALL)


def _mask_kv(text: str) -> str:
    """Mask every ``_SECRET_KV`` match, matching against a percent-DECODED view
    of ``text`` so ``PWD%3Dhunter2%3B`` (an ``odbc_connect=`` payload) is seen
    as ``PWD=hunter2;``, while editing ``text`` itself byte-range-for-byte-range
    so nothing outside a matched span — encoded or not — is disturbed.
    """
    units = _BYTE_OR_PCT.findall(text)
    offsets, pos = [0], 0
    decoded = []
    for unit in units:
        pos += len(unit)
        offsets.append(pos)
        if len(unit) == 3:  # a %XX triple
            byte = int(unit[1:], 16)
            decoded.append(chr(byte) if byte < 0x80 else "�")
        else:
            decoded.append(unit)
    view = "".join(decoded)
    out, last = [], 0
    for m in _SECRET_KV.finditer(view):
        out.append(text[last : offsets[m.end(1)]])
        out.append("***")
        last = offsets[m.end()]
    out.append(text[last:])
    return "".join(out)


_ASCII_RUN = re.compile(r"[A-Za-z0-9]+")
_WORD_RUN = re.compile(r"[^\W_]+")
#: A token of this many characters is removed from a driver's text wherever it appears; a shorter
#: one only beside the ``@`` that follows it. Four is the least a reader can search for. On the
#: Session 271 over-masking lens's echo matrix, three buys nothing and each step above four leaks
#: more.
_MIN_TOKEN_ANYWHERE = 4
#: What a chain of tokens may have between them: up to six characters that are not alphanumeric,
#: which outlasts a doubled backslash, a bracket and a quote together. Not tied to ``_MAX_CHAIN``.
_ASCII_GAP = r"[^A-Za-z0-9]{0,6}"
_WORD_GAP = r"[\W_]{0,6}"
#: Bounds. The scrub runs inside an ``except`` block that must not stall, and a password this long
#: is the operator's own argument gone wrong. ``_MAX_EXACT`` and ``_MAX_TAILS`` are performance
#: bounds: an address of 100,000 ``@`` took 8.6 s while the first was missing (the Session 271
#: review) and 0.001 s with both. Chains cost about 12 microseconds a token, linear, and need
#: none. The values are not tuned (4 to 8 tokens a chain, 1 to 6 tails and 128 to 1,024 patterns
#: all measure the same).
_MAX_CHAIN = 6  # tokens in one chain
_MAX_TAILS = 4  # tails of the password taken after an '@'
_MAX_EXACT = 1024  # characters in one exact piece
_MAX_PATTERNS = 256


def _split_userinfo(url: str) -> tuple[str, str, str] | None:
    """Split an address at its userinfo the way an operator means it: ``(text through the user's
    colon, the password, the text from the last '@' on)``, or ``None`` when no password is there.

    The password ends at the LAST ``@``, because a password may contain one and a host may not.
    The user's colon is the first one after the scheme separator. With no ``://`` that is the first
    colon in the address, so the scheme's own colon is read as the user's in a mistyped
    ``postgresql:/bob:pw@h`` and the user name is masked with the password: a password that begins
    with a slash reads the same way, and an echoed password costs more than a masked user name. A
    ``://`` after a ``:``, ``/`` or ``@`` is not the scheme's but part of a password.
    """
    scheme_end = url.find("://")
    if scheme_end >= 0 and re.search(r"[:/@]", url[:scheme_end]):
        scheme_end = -1
    start = scheme_end + 3 if scheme_end >= 0 else 0
    at = url.rfind("@", start)
    if at < 0:
        return None
    colon = url.find(":", start, at)
    if colon < 0:
        return None
    return url[: colon + 1], url[colon + 1 : at], url[at:]


def _unaccounted_at(url: str, parsed: sa.engine.URL) -> bool:
    """Whether ``url`` holds an ``@`` that SQLAlchemy's parse does not account for.

    Accounted for: the one that ends the userinfo, any in the user name or the password, and any in
    a query VALUE when a host came before the query, or when the address is only a query (no
    userinfo, no host, no database: a raw ``odbc_connect`` payload holding ``Uid=ann@srv``). Not
    accounted for: one in the host or the database, in a query KEY (never legitimate), or in a query
    that follows userinfo or a database with no host before it. SQLAlchemy ends a password at the
    FIRST ``@``, so a password containing one leaves its tail where a host, a port, a database or
    a query belongs, and the driver then echoes it. The count is of the percent-DECODED address,
    so ``%40`` counts on both sides.

    No syntax separates three shapes from a legitimate address, so each is read as the legitimate
    one and the password's tail is shown: a password whose tail reads ``host?k=v`` before the real
    ``@host`` (the fragment makes the host truthy, and the query's ``@`` is then accounted for); a
    user name holding ``/`` with a ``?`` in the password; and a scheme-less address whose password
    begins ``//``, which parses as another scheme and another user. The converse costs a legitimate
    address its host: userinfo with no host and an ``@`` in the query (a unix socket), or an ``@``
    in the database name, is read as misparsed and masked from the user's colon to the last ``@``.
    """
    has_userinfo = parsed.username is not None or parsed.password is not None
    accounted = 1 if has_userinfo else 0
    accounted += (parsed.username or "").count("@") + (parsed.password or "").count("@")
    if parsed.host or (not has_userinfo and not parsed.database):
        for value in parsed.query.values():
            accounted += sum(v.count("@") for v in ((value,) if isinstance(value, str) else value))
    return unquote(url).count("@") > accounted


def _untrusted_userinfo(url: str | sa.engine.URL) -> tuple[str, str, str] | None:
    """:func:`_split_userinfo` of ``url`` when SQLAlchemy cannot be trusted to have split it.

    That is an address it cannot parse (a mistyped scheme separator, a non-numeric port) or one it
    parses with an unaccounted ``@`` (see :func:`_unaccounted_at`). Anything else is trusted: the
    parse and ``render_as_string`` are exact. A SQLite address that names no user or password has
    only a path, and a path may hold an ``@``; ``sqlite+pysqlcipher`` keeps a passphrase in the
    password and is not exempt. A URL object is read as the string it renders, which restores the
    ``@`` a ``make_url`` of an ambiguous string had already split wrongly.
    """
    if isinstance(url, sa.engine.URL):
        url = url.render_as_string(hide_password=False)
    elif not isinstance(url, str):
        return None
    try:
        parsed = sa.make_url(url)
    except Exception:
        return _split_userinfo(url)
    is_path = parsed.get_backend_name() == "sqlite" and not (parsed.username or parsed.password)
    if is_path or not _unaccounted_at(url, parsed):
        return None
    return _split_userinfo(url)


def redact_db_url(url: str | sa.engine.URL) -> str:
    """Return ``url`` with any password masked, for display in an error or log.

    Structural where SQLAlchemy can be trusted: :func:`sqlalchemy.make_url` plus
    ``render_as_string(hide_password=True)``. Where it cannot (see :func:`_untrusted_userinfo`) the
    address is read as the operator typed it and everything from the user's colon to the last
    ``@`` is masked: an unexpanded ``$DB_PORT``, a mistyped ``://``, or a password containing an
    unencoded ``@``, the first of which this project hits in practice. The host, port and database
    stay, because the operator needs them, except where an ``@`` follows them that cannot be told
    from a password's tail (see :func:`_unaccounted_at`): then they go with the password. An
    address with no ``@`` has no password to find and is shown as typed. Idempotent for every
    address measured (the fixed-point test), so a message composed from an address already
    redacted is unchanged.
    """
    parts = _untrusted_userinfo(url)
    if parts is not None:
        head, _, tail = parts
        rendered = f"{head}***{tail}"
        if _untrusted_userinfo(rendered) is None:
            # Masked, it reads soundly: render it as any sound address is rendered, so a second
            # pass takes that same path and changes nothing (``bob@corp`` would otherwise come
            # out as ``bob@corp`` once and ``bob%40corp`` the next time). ``render_as_string``
            # raises on a lone surrogate, which the address may hold.
            with contextlib.suppress(Exception):
                rendered = sa.make_url(rendered).render_as_string(hide_password=True)
    else:
        try:
            rendered = sa.make_url(url).render_as_string(hide_password=True)
        except Exception:
            rendered = str(url)
    return _mask_kv(rendered)


def _password_patterns(password: str) -> tuple[list[str], list[str]]:
    """``(patterns removed wherever they appear, short tokens removed only before an '@')``.

    Removed wherever they appear: the password whole and its tail after each of the first few
    ``@`` (what SQLAlchemy hands a driver as a host), as typed and percent-decoded; and every CHAIN
    of consecutive alphanumeric tokens that holds four characters or more, the tokens joined by a
    short run of anything that is not alphanumeric. A chain covers the tail of ``kT@9x!Qp#2``,
    whose every token is under four characters. Tokens are read twice when the password is not
    ASCII: the ASCII runs, which are what survives a driver that prints a bytes repr, and the
    Unicode runs, which are what a driver that prints the text prints. A Unicode token is removed
    in its bytes-repr form too (``\\xd0\\xbf``). Past ``_MAX_PATTERNS`` the chains of fewest
    tokens are kept, since they are what a driver echoes of one field.
    """
    exact: set[str] = set()
    chains: dict[str, int] = {}
    short: set[str] = set()
    for form in {password, unquote(password)}:
        exact.add(form)
        at_positions = [i for i, ch in enumerate(form) if ch == "@"]
        exact.update(form[i + 1 :] for i in at_positions[:_MAX_TAILS])
        tokenisations = [(_ASCII_RUN, _ASCII_GAP)]
        if not form.isascii():
            tokenisations.append((_WORD_RUN, _WORD_GAP))
        for run, gap in tokenisations:
            tokens = run.findall(form)
            for first in range(len(tokens)):
                total = 0
                for last in range(first, min(first + _MAX_CHAIN, len(tokens))):
                    total += len(tokens[last])
                    if total >= _MIN_TOKEN_ANYWHERE:
                        chain = gap.join(map(re.escape, tokens[first : last + 1]))
                        chains[chain] = last - first + 1
            short.update(t for t in tokens if len(t) < _MIN_TOKEN_ANYWHERE)
            if run is _WORD_RUN:
                exact.update(
                    "".join(f"\\x{b:02x}" for b in t.encode("utf-8"))
                    for t in tokens
                    if not t.isascii()
                )
    # An alternation takes the first pattern that matches where it starts, not the longest, so the
    # exact pieces go first, longest first, then the chains, the ones of most tokens first. The cap
    # is applied BEFORE that order: it keeps the chains of fewest tokens.
    exact_patterns = sorted(
        (e for e in exact if _MIN_TOKEN_ANYWHERE <= len(e) <= _MAX_EXACT), key=len, reverse=True
    )[:_MAX_PATTERNS]
    kept = sorted(chains.items(), key=lambda item: (item[1], item[0]))
    kept = kept[: _MAX_PATTERNS - len(exact_patterns)]
    kept.sort(key=lambda item: (-item[1], item[0]))
    patterns = [re.escape(e) for e in exact_patterns] + [pattern for pattern, _ in kept]
    return patterns, sorted(short)


def _scrub_address_password(text: str, url: str | sa.engine.URL) -> str:
    """Remove from ``text`` what a parser or a driver could print of the password in ``url``.

    Where SQLAlchemy parsed the address wrongly it hands the driver the tail of the password as a
    host, a port or a database, and the driver echoes it (psycopg 3: ``failed to resolve host
    'ssw0rdXYZ@127.0.0.1'``); and SQLAlchemy 2.0.40, which ``sqlalchemy>=2.0,<3`` admits, puts the
    whole address in its own parse error. The password is known by exact value, so it is removed by
    value, not by shape.

    What is matched is the password's ALPHANUMERIC TOKENS (see :func:`_password_patterns`) and
    not the text around them, because a driver re-escapes (backslash, quote, bytes repr),
    brackets, strips, splits on ``,``, cuts at ``#`` and lower-cases what it echoes, and none of
    that alters an alphanumeric run (measured on fifteen driver setups: 168 of 2,484 rows leaked
    under matching the typed text of a piece, none under tokens). Matching is case-insensitive.

    A piece of four characters or more goes wherever it appears; a shorter token only where an
    ``@`` follows it, after up to six characters that are not alphanumeric, and it does not end a
    longer word: the shape a mis-assigned host or port takes. So a password whose tokens are
    ordinary words (``Server@123``) takes those words out of the text: the price of removing by
    value, paid only on an address SQLAlchemy could not read, and it errs toward the secret.
    Not covered: a token or a tail under four characters that a driver prints alone with nothing
    after it (``'abc'`` as a whole port field), and a delimiter-free run over 63 bytes that a
    server truncates in echoing a database name.

    Runs on the RAW driver text, before ``safe_message`` flattens it. The exact pieces match the
    password as typed, and a tab that is a space once flattened no longer matches them. A chain's
    gap bridges that, so for four characters or more the order does not matter; for less it does:
    ``@ab<TAB>c`` leaves ``ab`` when flattened first (measured on psycopg2, pg8000, mysql-connector;
    the review found it, and a test holds the exact output).

    A scrub that cannot finish returns ``<unprintable>``: it has not removed the password.
    """
    try:
        parts = _untrusted_userinfo(url)
        if parts is None or not parts[1]:
            return text
        patterns, short_tokens = _password_patterns(parts[1])
        if patterns:
            text = re.sub("|".join(patterns), "***", text, flags=re.IGNORECASE)
        if short_tokens:
            text = re.sub(
                r"(?<![^\W_])(?:"
                + "|".join(map(re.escape, short_tokens))
                + r")[^A-Za-z0-9@]{0,6}(?=@)",
                "***",
                text,
                flags=re.IGNORECASE,
            )
        return text
    except Exception:
        # Fails CLOSED. This runs inside the ``except`` blocks that deliver "never raises", and a
        # scrub that could not finish has not removed the password.
        return "<unprintable>"


def redact_secrets(text: str) -> str:
    """Return ``text`` with any embedded URL password or ``key=value`` secret
    masked — best-effort, per the module comment above.

    For arbitrary text — a driver's own exception message, which may echo the
    connection string back. :func:`redact_db_url` is the right call when the
    whole string IS a URL. To print, log, persist or report such text, call
    :func:`safe_message`, which redacts and also removes what a terminal would
    act on, and removes by value a password SQLAlchemy read wrongly (its ``url``).
    """
    return _mask_kv(_USERINFO_TEXT.sub(r"\1***\2", text))


#: What a terminal acts on instead of printing: the C0 controls, DEL and the C1
#: controls, which are Unicode's ``Cc`` category (65 characters; a test compares
#: this pattern with the Unicode database over every code point).
#: :func:`safe_message` replaces each with a space. ``str.split`` already treats
#: ten of them as whitespace, so the range stays whole instead of naming only
#: what the flatten still lets through.
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def safe_message(
    error: object, *, redact: bool = True, url: str | sa.engine.URL | None = None
) -> str:
    """``str(error)`` made safe to print, to log, to persist and to put in a report.

    The function behind each route that has been closed for carrying database or
    driver text to a person: the schema probe's three messages (``discovery.py``),
    the connect error (:meth:`ReadOnlyDB.connect`), the quality-check and baseline
    SQL errors (``nodes.py``) and, with ``redact=False`` (below), ``discover``'s
    echo of the connect error and ``agent.py``'s "database unreachable" concern.
    The concern and the baseline caveat are written into a committed project's
    markdown; a quality check's ``result_summary`` goes to the report JSON and the
    summarise prompt. ``BACKLOG.md`` lists the routes that still do not pass
    through it. It takes anything with a ``str``: the exception itself, or the
    text a caller already holds. Session 269 wrote it for the probe; Session 270
    moved it here, beside :func:`redact_secrets`, for the rest.

    Runs inside the ``except`` blocks that deliver "never raises", so it must not
    be a raise site itself. The whole body is guarded, not just ``str(error)``:
    a broken ``__str__`` raises there, and one returning a ``str`` *subclass*
    raises later, from that subclass's own ``encode`` / ``split`` (measured).

    Lone surrogates are scrubbed because a note holding one makes
    ``model_dump_json`` raise and the written file fail to reload (measured).
    An OS-raised ``OSError`` repr-escapes its filename, so it carries none; a
    message built by formatting an ``os.fsdecode``-d path into text does.

    Control characters are replaced with a space, because a terminal acts on ESC,
    BEL, NUL, DEL and the C1 controls instead of printing them (measured: the ESC
    and BEL of a title sequence and a colour code in a table name reached stderr
    raw). A space, not nothing, so ``a<ESC>b`` does not read ``ab``.

    Redaction runs on BOTH sides of the scrub, because each order alone leaks in
    the other's case (all measured, with the 55 controls that are not whitespace
    to :func:`redact_secrets`). Before it: the masker reads an unquoted secret as
    a run of non-whitespace, so scrubbing first would end the value at the control
    and print what follows (``password=abc<ESC>def`` came out ``password=***
    def``). After it: a control between a key and its separator hides the key from
    the masker, and only the scrub turns that control into the space the masker
    tolerates there (``password<ESC>=hunter2`` came out ``password =hunter2``).

    **Apply it once, to the raw text.** It is not a fixed point: the masker reads a
    quoted value glued to the text after it as the whole value, so
    ``password=''hunter2`` becomes ``password=***hunter2`` and a second pass makes
    it ``password=***`` (measured, Session 270 review). Nor is the masker safe to
    run over a message that was composed from text it already cleaned: it reads a
    key, a separator and a run of non-whitespace wherever it finds them, so
    ``cannot connect to 'postgresql://h/db?password=***': cause`` loses its closing
    ``':`` and ``...secret': (sqlite3.OperationalError) ...`` loses the exception
    type (both measured). Pass ``redact=False`` for text that was redacted where it
    was built, as :meth:`ReadOnlyDB.connect` builds the connect error: only the
    control characters are replaced and the text put on one line.

    What neither redaction pass closes are the masker's own limits: an unquoted
    value ends at whitespace, so ``password=<ESC> hunter2`` prints ``hunter2``, as
    ``password=x hunter2`` always has; and a control between the separator and an
    opening quote or brace makes the quote part of a bare value, so the rest of a
    multi-word secret survives (``password=<ESC>"Zq7xK9mW Qw3rT5yU" end`` prints
    ``Qw3rT5yU" end``; without the control it is masked whole; the masker alone
    does the same).

    ``url`` is the address the failure was about. When SQLAlchemy cannot be trusted to have read it
    (:func:`_untrusted_userinfo`) the password is removed by value from the RAW text, before the
    redaction and before the whitespace is flattened (:func:`_scrub_address_password` says why
    the order is required). It applies only with ``redact``.

    Redaction is **best-effort**. :func:`redact_secrets` masks URL userinfo, a
    wide `key=value`/`key: value`/quoted/braced key list (Session 262), and a
    secret percent-encoded inside `odbc_connect=`; it still does not see a
    bare-key, header, ``Bearer``, or SigV4-signature shape with no `key=`/`key:`
    form at all, nor a key outside its fixed list. The result is one line, so it
    is also one log record and one markdown bullet: SQLAlchemy puts its help URL
    after a newline on every ``DBAPIError``.
    """
    try:
        raw = str(error).encode("utf-8", "replace").decode("utf-8")
        if not redact:
            return " ".join(_CONTROL_CHARACTERS.sub(" ", raw).split())
        if url is not None:
            raw = _scrub_address_password(raw, url)
        scrubbed = _CONTROL_CHARACTERS.sub(" ", redact_secrets(raw))
        return " ".join(redact_secrets(scrubbed).split())
    except Exception:
        return "<unprintable>"


def safe_class_name(error: BaseException) -> str:
    """The exception's class name, or ``<unprintable>`` when it is not a short ASCII identifier.

    For an exception that is not the database's: what an LLM client raised, which the agent turns
    into a report. :func:`safe_message` is for database and driver text, whose masking is best
    effort. This is for text whose author is a gateway or an upstream model provider: an SDK
    ``APIError`` carries the reply, which a proxy that echoes request headers fills with the API
    key (measured: a bare ``sk-ant-`` token survives :func:`safe_message`), and opencode's error
    events carry upstream text. So the report names the class and nothing the exception said.

    A class name is chosen by code, never by the gateway or the driver, so it is safe to carry; a
    class built at run time (``type(name, ...)``) can be named anything, and a name that is not a
    plain identifier is replaced rather than carried.

    It runs inside the ``except`` blocks that deliver "never raises", so it must not be a raise
    site: a metaclass whose ``__name__`` raises would otherwise replace the report with a crash,
    which is why it reads nothing from the exception itself (``f"{e}"`` was one: a ``__str__``
    that raises). The name must be an exact ``str``, because a subclass can answer ``isascii`` and
    ``len`` however it likes.

    The same rule as ``model_project_constructor.orchestrator.logging._class_name``, which this
    package cannot import (it is standalone); ``tests/data_agent_package/test_db.py`` holds the two
    in step.
    """
    try:
        name = type(error).__name__
        if type(name) is str and name.isascii() and name.isidentifier() and len(name) <= 100:
            return name
    except Exception:
        pass
    return "<unprintable>"


class DBConnectionError(Exception):
    """Raised when the Data Agent cannot reach its database."""


@dataclass(frozen=True)
class SkippedEntity:
    """A table or view :meth:`ReadOnlyDB.get_information_schema` could not reflect.

    ``error`` is the database error that reflecting it raised. Measured Session
    265: a view whose base table was dropped gives ``OperationalError`` on
    SQLite and ``UnreflectableTableError`` on MySQL 8.4 (wrapping error 1356);
    a table dropped while the walk ran gives ``NoSuchTableError`` (SQLite and
    PostgreSQL 17). PostgreSQL refuses to drop a table a view depends on.

    ``error`` is left out of the ``repr``: a driver's message can echo the
    connection string, and a caller that logs its list would print it unredacted.
    """

    namespace: str
    name: str
    entity_kind: str
    error: sa.exc.SQLAlchemyError = field(repr=False)


def sql_dialect_from_url(url: str) -> str | None:
    """Return the SQLAlchemy backend name for ``url`` (e.g. ``"sqlite"``).

    The generated SQL has to run on *this* database, so the LLM needs to know
    which dialect it is writing for. ``make_url`` parses the URL string only —
    it neither connects nor requires the driver package to be installed, so the
    dialect is knowable before the first node runs (and even when the DB is
    unreachable). ``get_backend_name()`` strips any ``+driver`` suffix, so
    ``postgresql+psycopg://…`` yields ``"postgresql"``, not ``"postgresql+psycopg"``.

    Returns ``None`` for a URL SQLAlchemy cannot parse, so a malformed
    ``--db-url`` degrades to today's dialect-silent prompt rather than raising
    here — the URL's real failure surfaces at :meth:`ReadOnlyDB.connect`, which
    is the error path callers already handle.

    That clause is true as written since Session 260, and was not before it:
    ``nodes.py``'s ``execute_qc`` now BINDS the :class:`DBConnectionError` and
    carries its text into the state as ``db_error``, which ``agent.py`` appends
    to the canned "database unreachable at QC execution time" concern, so the
    cause reaches ``DataReport.data_quality_concerns`` instead of being
    discarded. Session 223 had verified the opposite and said so here; the
    history is in ``CHANGELOG.md`` rather than in this docstring.

    Two limits still hold, deliberately. The report's status stays
    ``"COMPLETE"``, so ``pipeline.py``'s ``FAILED_AT_DATA`` halt still does not
    fire on an unreachable database — that is filed as a separate change
    needing an operator ruling, because it turns runs that succeed today into
    failures. And a *parse* failure never reaches ``connect`` at all, which is
    why this function logs a WARNING of its own rather than relying on the
    connect path to describe it.

    **Both** exception types are required to honour that contract, and neither
    subsumes the other: ``ArgumentError`` derives from ``SQLAlchemyError``, not
    from ``ValueError``. ``make_url`` reports a structurally unparseable URL
    (and a non-string argument) as ``ArgumentError``, but it coerces the port
    segment with a bare ``int()``, so a *non-numeric port* escapes as the raw
    ``ValueError`` that ``int()`` raises. Measured against SQLAlchemy 2.0.49,
    five inputs take that second path: an unexpanded environment variable
    (``@host:$DB_PORT/``), an alphabetic port, an **empty** port (``@host:/``),
    a float port, and an IPv6 host with either of those. The first is the one
    that bites in practice — a ``--db-url`` templated from a shell environment
    where the port variable was never exported. Catching only ``ArgumentError``
    made the paragraph above false for exactly those cases (fixed Session 223;
    filed Session 218).

    The catch is bounded on the other side too: only *parse* failures degrade.
    An unexpected exception propagates, because silently returning ``None`` for
    a genuine defect would drop the dialect from the prompt and reintroduce the
    wrong-database SQL this function exists to prevent.

    Note this deliberately does *not* validate the port's range or meaning: a
    negative or absurdly large port parses fine here, because ``int()`` accepts
    it and dialect derivation is not URL validation. Judging the URL remains
    :meth:`ReadOnlyDB.connect`'s job.
    """
    try:
        return str(sa.make_url(url).get_backend_name())
    except (sa.exc.ArgumentError, ValueError) as e:
        _LOG.warning(
            "cannot derive a SQL dialect from --db-url %s: %s. The URL did not "
            "PARSE, so the prompt will not name a dialect. This is distinct "
            "from a URL that parses but cannot be connected to, which is "
            "reported in the DataReport's data_quality_concerns.",
            redact_db_url(url),
            safe_message(e, url=url),
        )
        return None


def _answers_select_1(engine: sa.Engine) -> bool:
    """Whether a fresh connection can still run ``SELECT 1``.

    Tells "this entity cannot be reflected" from "the database has gone away"
    for :meth:`ReadOnlyDB.get_information_schema`. Any exception at all counts
    as gone: the caller then re-raises the reflection error, so a doubtful
    answer fails loudly rather than skipping.
    """
    try:
        with engine.connect() as conn:
            conn.execute(sa.text("SELECT 1"))
    except Exception:
        return False
    return True


class ReadOnlyDB:
    """Thin SQLAlchemy wrapper used by EXECUTE_QC."""

    def __init__(self, url: str) -> None:
        self.url = url
        self._engine: sa.Engine | None = None

    @property
    def dialect(self) -> str | None:
        """The SQL dialect of this database, or ``None`` if the URL is unparseable.

        Available before :meth:`connect` — see :func:`sql_dialect_from_url`.
        """
        return sql_dialect_from_url(self.url)

    def connect(self) -> None:
        """Open the engine and round-trip ``SELECT 1`` to prove reachability."""
        try:
            engine = sa.create_engine(self.url)
            with engine.connect() as conn:
                conn.execute(sa.text("SELECT 1"))
        except Exception as e:
            # The URL half is ``repr``-quoted, which escapes every control character.
            # The cause is the driver's own text, so it goes through ``safe_message``:
            # ``discover`` prints this message and ``run`` writes it into the report.
            # A DBAPI error reaches here wrapped by SQLAlchemy, whose text names its
            # type; a bare ``TimeoutError()`` has no text at all, and the message
            # would end in a colon, so fall back to the type's name.
            raise DBConnectionError(
                f"cannot connect to {redact_db_url(self.url)!r}: "
                f"{safe_message(e, url=self.url) or type(e).__name__}"
            ) from e
        self._engine = engine

    def execute(self, sql: str) -> list[dict[str, Any]]:
        """Execute a SELECT and return a list of row dicts."""
        if self._engine is None:
            raise RuntimeError("ReadOnlyDB.execute called before connect()")
        with self._engine.connect() as conn:
            result = conn.execute(sa.text(sql))
            return [dict(row) for row in result.mappings().all()]

    def get_information_schema(
        self,
        schemas: list[str] | None = None,
        *,
        skipped: list[SkippedEntity] | None = None,
    ) -> list[dict[str, Any]]:
        """Introspect the database and return table/view metadata.

        Delegates to SQLAlchemy's ``Inspector`` so the implementation is
        dialect-agnostic — PostgreSQL, SQLite, MySQL, and most other
        SQLAlchemy-supported dialects are handled transparently. System
        schemas (``information_schema``, ``pg_catalog``) are skipped by
        default; pass ``schemas=[...]`` to limit discovery to specific
        schemas (in which case no filtering is applied beyond the user's
        choice).

        Returns a list of dicts, one per discovered table or view. Each dict
        has keys: ``namespace`` (schema name), ``name`` (table name),
        ``entity_kind`` (``"table"`` or ``"view"``), ``columns`` (a list of
        per-column dicts with ``name``, ``data_type``, ``nullable``,
        ``is_primary_key``, ``is_foreign_key``, ``foreign_key_target``), and
        ``primary_key_columns`` (a list of PK column names).

        Pass a list as ``skipped`` to keep going past a table or view the
        database cannot reflect: each is appended to it as a
        :class:`SkippedEntity` and left out of the result. The case that forced
        it is a view whose base table was dropped — SQLite and MySQL allow the
        drop — which, before Session 265, emptied the whole inventory, naming
        only the first such view. Only a
        :class:`sqlalchemy.exc.SQLAlchemyError` from reflecting ONE entity is
        collected. Any other exception is a defect, not a database fault, and
        propagates; so does an error listing the schemas, tables or views.

        **A lost connection is never a skip** (Session 265's review, measured on
        PostgreSQL 17). Without these two checks it would be collected like any
        other database error — a healthy table blamed for a dropped connection,
        or every entity after an outage — and ``discover --allow-skipped`` would
        exit 0 over it. So: an error SQLAlchemy flags as a disconnect is retried
        once on a fresh connection, and propagates if it happens again; and any
        other error is collected only if a fresh ``SELECT 1`` — :meth:`connect`'s
        own test — still succeeds, and propagates if it does not.

        Without ``skipped`` nothing is collected, and the first error of any
        kind propagates, as it always has. Raises :class:`RuntimeError` if
        called before :meth:`connect`.
        """
        engine = self._engine
        if engine is None:
            raise RuntimeError(
                "ReadOnlyDB.get_information_schema called before connect()"
            )

        inspector = sa.inspect(engine)
        all_schemas = inspector.get_schema_names()
        if schemas is not None:
            target_schemas = [s for s in all_schemas if s in schemas]
        else:
            target_schemas = [
                s for s in all_schemas if s not in {"information_schema", "pg_catalog"}
            ]

        result: list[dict[str, Any]] = []

        def reflect(schema: str, name: str, entity_kind: str, *, retry: bool = True) -> None:
            try:
                result.append(self._reflect_entity(inspector, schema, name, entity_kind))
            except sa.exc.SQLAlchemyError as e:
                if skipped is None:
                    raise
                if isinstance(e, sa.exc.DBAPIError) and e.connection_invalidated:
                    if not retry:
                        raise
                    # The pool has discarded that connection, so this attempt
                    # gets a fresh one.
                    reflect(schema, name, entity_kind, retry=False)
                    return
                if not _answers_select_1(engine):
                    raise
                skipped.append(SkippedEntity(schema, name, entity_kind, e))

        for schema in target_schemas:
            for table_name in inspector.get_table_names(schema=schema):
                reflect(schema, table_name, "table")
            for view_name in inspector.get_view_names(schema=schema):
                reflect(schema, view_name, "view")
        return result

    @staticmethod
    def _reflect_entity(
        inspector: sa.Inspector,
        schema: str,
        name: str,
        entity_kind: str,
    ) -> dict[str, Any]:
        columns_info = inspector.get_columns(name, schema=schema)
        pk_columns: list[str]
        try:
            pk_info = inspector.get_pk_constraint(name, schema=schema)
            pk_columns = list(pk_info.get("constrained_columns") or [])
        except sa.exc.NoSuchTableError:
            pk_columns = []
        try:
            fk_info = inspector.get_foreign_keys(name, schema=schema)
        except sa.exc.NoSuchTableError:
            fk_info = []
        fk_map: dict[str, str] = {}
        for fk in fk_info:
            ref_schema = fk.get("referred_schema") or schema
            ref_table = fk["referred_table"]
            for local_col, ref_col in zip(
                fk["constrained_columns"], fk["referred_columns"], strict=False
            ):
                fk_map[local_col] = f"{ref_schema}.{ref_table}.{ref_col}"

        columns: list[dict[str, Any]] = []
        for col in columns_info:
            col_name = col["name"]
            columns.append(
                {
                    "name": col_name,
                    "data_type": str(col["type"]),
                    "nullable": col.get("nullable"),
                    "is_primary_key": col_name in pk_columns,
                    "is_foreign_key": col_name in fk_map,
                    "foreign_key_target": fk_map.get(col_name),
                }
            )

        return {
            "namespace": schema,
            "name": name,
            "entity_kind": entity_kind,
            "columns": columns,
            "primary_key_columns": pk_columns,
        }

    def close(self) -> None:
        """Dispose the SQLAlchemy engine, releasing pooled connections.

        Safe to call without a prior ``connect()`` and safe to call twice.
        """
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
