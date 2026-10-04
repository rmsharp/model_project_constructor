"""What a repository host's failure text may carry to a person or to disk.

``scrub_host_text`` is the one function every message that leaves an adapter goes through: the
host's words are untrusted (a gateway that echoes the request headers puts the access token in an
error body), and so is the HTTP library's description of a malformed reply (``h11`` quotes the bytes
the server sent). It removes the secret by value in every form a host is known to re-encode it in,
makes the text one line free of control characters, and bounds its length. ``scrubbed_errors``
applies it at the exit of an adapter method, so a message-building site added later cannot bypass
it; ``scrubbed_values`` does the same for the ``ProjectInfo`` and ``CommitInfo`` a method returns
(``BACKLOG.md`` route 8).
"""

from __future__ import annotations

import encodings.aliases
import html
import json
import re
import sys
import traceback
import unicodedata
from collections.abc import Iterator
from urllib.parse import quote, quote_plus

import httpx
import pytest

from model_project_constructor.agents.website._host_text import (
    MAX_HOST_TEXT,
    REDACTED,
    UNPRINTABLE,
    response_text,
    scrub_commit_info,
    scrub_host_text,
    scrub_project_info,
    scrubbed_errors,
    scrubbed_values,
)
from model_project_constructor.agents.website.protocol import (
    CommitInfo,
    ProjectInfo,
    RepoClientError,
    RepoNameConflictError,
)

TOKEN = "glpat-SECRET9f3kQ7xZ2mW"
# Every printable-ASCII character a re-encoder rewrites: both quotes, backslash, ampersand,
# angle brackets, percent and plus. A real token never looks like this; the validator admits it.
AWKWARD = "ab\"c\\d'e&f<g>h%i+jk=="


def _forms(secret: str) -> dict[str, str]:
    return {
        "raw": secret,
        "json": json.dumps(secret)[1:-1],
        "bytes repr (h11)": repr(secret.encode("ascii"))[2:-1],
        "str repr": repr(secret)[1:-1],
        "html": html.escape(secret),
        "percent": quote(secret, safe=""),
        "percent plus": quote_plus(secret),
        "a bytes repr inside a JSON body": json.dumps(repr(secret.encode("ascii"))[2:-1])[1:-1],
        "a JSON body inside a str repr": repr(json.dumps(secret)[1:-1])[1:-1],
    }


class TestTheSecret:
    @pytest.mark.parametrize("secret", [TOKEN, AWKWARD], ids=["a real-looking token", "awkward"])
    def test_every_known_form_is_replaced_wherever_it_appears(self, secret: str) -> None:
        for name, form in _forms(secret).items():
            text = f"500 echo: PRIVATE-TOKEN: {form}; again {form}!"
            out = scrub_host_text(text, secret)
            assert form not in out, name
            assert out == f"500 echo: PRIVATE-TOKEN: {REDACTED}; again {REDACTED}!", name

    def test_bearer_scheme_keeps_the_scheme_and_loses_the_token(self) -> None:
        out = scrub_host_text(f"Authorization: Bearer {TOKEN}", TOKEN)
        assert out == f"Authorization: Bearer {REDACTED}"

    def test_a_non_ascii_secret_is_removed_in_the_form_h11_quotes_it(self) -> None:
        """The validator admits only printable ASCII, where a bytes repr and a ``str`` repr are the
        same text; the function takes any secret, and ``h11`` quotes non-ASCII bytes escaped."""
        secret = "tök-é9"
        quoted = repr(secret.encode("utf-8"))[2:-1]
        assert quoted != secret and quoted != repr(secret)[1:-1]
        out = scrub_host_text(f"illegal header line: bytearray(b'X {quoted}')", secret)
        assert out == f"illegal header line: bytearray(b'X {REDACTED}')"

    @pytest.mark.parametrize(
        "secret",
        ["tok'en9f3kQ7xZ2mW", 'tok"en9f3kQ7xZ2mW', "Zq7'xK9\"mW\\pL3&4<5>6%7+8=="],
        ids=["single quote", "double quote", "awkward"],
    )
    def test_a_secret_is_removed_from_the_repr_of_a_longer_message(self, secret: str) -> None:
        """A ``repr`` writes a quote as ``\\'`` only when the string it quotes holds both kinds, so
        the repr of the secret alone never shows that form; the repr of a message around it does."""
        runs = re.findall(r"[A-Za-z0-9]{3,}", secret)
        assert runs
        for message in (f"{secret} \"q\" 'q'", f'{secret} "q"', f"{secret} 'q'"):
            for text in (repr(message), repr(message.encode())[2:-1]):
                out = scrub_host_text(text, secret)
                assert REDACTED in out, text
                assert [run for run in runs if run in out] == [], (text, out)

    def test_the_match_ignores_case(self) -> None:
        """A proxy that lower-cases what it echoes still gives away most of the token."""
        assert TOKEN.lower() not in scrub_host_text(f"x {TOKEN.lower()} y", TOKEN)
        assert TOKEN.upper() not in scrub_host_text(f"x {TOKEN.upper()} y", TOKEN)

    def test_a_form_that_contains_a_shorter_form_is_replaced_whole(self) -> None:
        """The longest form goes first. A secret ending in a backslash is a prefix of its own JSON
        form, so replacing the short one first would leave a stray backslash."""
        secret = "k\\"
        out = scrub_host_text("x k\\\\ y and k\\ z", secret)
        assert out == f"x {REDACTED} y and {REDACTED} z"

    def test_text_that_never_held_the_secret_is_left_as_it_was(self) -> None:
        assert scrub_host_text("404 Not Found", TOKEN) == "404 Not Found"
        assert scrub_host_text("500 " + '{"message":"boom"}', TOKEN) == '500 {"message":"boom"}'

    def test_an_empty_secret_removes_nothing_and_does_not_hang(self) -> None:
        assert scrub_host_text("500 boom", "") == "500 boom"

    def test_a_secret_made_of_regex_metacharacters_is_matched_literally(self) -> None:
        secret = "a.*+?^${}()|[]b"
        assert scrub_host_text(f"x {secret} y axxb", secret) == f"x {REDACTED} y axxb"

    def test_the_placeholder_itself_is_not_a_secret_to_remove_twice(self) -> None:
        once = scrub_host_text(f"t {TOKEN}", TOKEN)
        assert scrub_host_text(once, TOKEN) == once


class TestTheShape:
    def test_control_characters_become_spaces_and_the_text_is_one_line(self) -> None:
        raw = "500 \x1b[2J\x07bell\r\nsecond\tline\x00\x7f\x85end"
        out = scrub_host_text(raw, TOKEN)
        assert out == "500 [2J bell second line end"
        assert not any(ord(c) < 0x20 or 0x7F <= ord(c) <= 0x9F for c in out)

    def test_the_secret_is_removed_even_when_a_control_character_sits_beside_it(self) -> None:
        out = scrub_host_text(f"\x1b{TOKEN}\x07 and\n{TOKEN}\r\n", TOKEN)
        assert TOKEN not in out
        assert out == f"{REDACTED} and {REDACTED}"

    def test_a_secret_that_only_matches_once_the_line_is_joined_is_removed_too(self) -> None:
        """A secret holding a space is not a token the validator admits, but the function takes any
        secret: here it appears in the text only after the control character is turned into one."""
        out = scrub_host_text("x ab\x1bcd y", "ab cd")
        assert out == f"x {REDACTED} y"

    def test_every_control_character_becomes_a_space(self) -> None:
        """All 65 characters of Unicode category ``Cc``, from the Unicode database of the running
        interpreter and not from a list typed here (the data agent pins its copy the same way). A
        few are whitespace to ``str.split`` and would pass unaided; most are not."""
        controls = [
            chr(code)
            for code in range(sys.maxunicode + 1)
            if unicodedata.category(chr(code)) == "Cc"
        ]
        assert len(controls) == 65
        for control in controls:
            assert scrub_host_text(f"a{control}b", TOKEN) == "a b", hex(ord(control))

    def test_no_printable_ascii_character_is_changed(self) -> None:
        for code in range(0x21, 0x7F):
            assert scrub_host_text(f"a{chr(code)}b", "") == f"a{chr(code)}b", chr(code)

    def test_the_cut_keeps_limit_characters_and_counts_the_rest(self) -> None:
        assert scrub_host_text("x" * 5000, "", limit=10) == "x" * 10 + (
            "... [4990 more characters not shown]"
        )
        assert scrub_host_text("x" * 11, "", limit=10) == "x" * 10 + (
            "... [1 more characters not shown]"
        )
        assert scrub_host_text("x" * 10, "", limit=10) == "x" * 10

    @pytest.mark.parametrize("limit", [0, -1, -5])
    def test_a_limit_of_zero_or_less_keeps_nothing(self, limit: int) -> None:
        assert scrub_host_text("abc", "", limit=limit) == "... [3 more characters not shown]"

    @pytest.mark.parametrize("secret", [None, b"tok", 1234], ids=["None", "bytes", "int"])
    def test_a_secret_that_is_not_text_fails_closed(self, secret: object) -> None:
        """Not read as 'no secret': that would return the text with the token still in it."""
        assert scrub_host_text(f"500 {TOKEN}", secret) == UNPRINTABLE  # type: ignore[arg-type]

    def test_a_long_body_is_cut_and_says_so(self) -> None:
        out = scrub_host_text("500 " + "x" * 5000, TOKEN)
        assert out.startswith("500 xxx")
        assert len(out) < MAX_HOST_TEXT + 80
        assert "more characters" in out

    def test_text_exactly_at_the_limit_is_not_cut(self) -> None:
        text = "y" * MAX_HOST_TEXT
        assert scrub_host_text(text, TOKEN) == text

    def test_the_cut_never_leaves_the_front_of_a_secret(self) -> None:
        """Replace first, then cut: a token straddling the limit would survive as a prefix."""
        for offset in range(len(TOKEN) + 2):
            text = "z" * (MAX_HOST_TEXT - offset) + TOKEN + " tail"
            out = scrub_host_text(text, TOKEN)
            assert TOKEN[:6] not in out.replace(REDACTED, ""), offset

    def test_the_limit_is_adjustable(self) -> None:
        assert scrub_host_text("abcdefghij", "", limit=4).startswith("abcd")
        assert "more characters" in scrub_host_text("abcdefghij", "", limit=4)

    def test_a_lone_surrogate_does_not_survive_to_break_a_file_write(self) -> None:
        """``json.dumps`` would escape it to ASCII; ``model_dump_json`` and a UTF-8 write raise."""
        out = scrub_host_text("bad \ud800 text", TOKEN)
        assert out.encode("utf-8").decode("utf-8") == out
        assert out.startswith("bad ") and out.endswith(" text")

    def test_a_message_that_cannot_be_rendered_fails_closed(self) -> None:
        class Broken:
            def __str__(self) -> str:
                raise RuntimeError("no")

        assert scrub_host_text(Broken(), TOKEN) == "<unprintable>"

    def test_it_takes_an_exception_or_anything_with_a_str(self) -> None:
        assert scrub_host_text(ValueError(f"bad {TOKEN}"), TOKEN) == f"bad {REDACTED}"
        assert scrub_host_text(1234, TOKEN) == "1234"


class _Adapter:
    """A stand-in with the one attribute ``scrubbed_errors`` reads."""

    def __init__(self, secret: str) -> None:
        self._secret = secret

    @scrubbed_errors
    def fails(self, message: str) -> None:
        try:
            raise ConnectionError(f"quoted {self._secret}")
        except ConnectionError as cause:
            raise RepoClientError(message) from cause

    @scrubbed_errors
    def conflicts(self) -> None:
        raise RepoNameConflictError("demo")

    @scrubbed_errors
    def works(self, value: int, *, extra: int = 0) -> int:
        """Add two numbers."""
        return value + extra

    @scrubbed_errors
    def crashes(self) -> None:
        raise KeyError("id")


def _chain(error: BaseException) -> Iterator[BaseException]:
    seen: set[int] = set()
    pending: list[BaseException | None] = [error]
    while pending:
        current = pending.pop()
        if current is None or id(current) in seen:
            continue
        seen.add(id(current))
        yield current
        pending += [current.__cause__, current.__context__]


class TestTheDecorator:
    def test_a_repo_client_error_leaves_with_the_secret_removed(self) -> None:
        with pytest.raises(RepoClientError) as caught:
            _Adapter(TOKEN).fails(f"create_project failed: 500 PRIVATE-TOKEN: {TOKEN}\n\x1b[2J")
        assert str(caught.value) == f"create_project failed: 500 PRIVATE-TOKEN: {REDACTED} [2J"

    def test_nothing_that_quotes_the_secret_is_reachable_from_it(self) -> None:
        """The original was built ``from`` an exception that quotes the secret, as the adapters'
        ``except httpx.HTTPError`` blocks do; the replacement is raised outside the handler so
        neither ``__cause__`` nor ``__context__`` leads back to it (learning #320)."""
        with pytest.raises(RepoClientError) as caught:
            _Adapter(TOKEN).fails("x")
        assert caught.value.__cause__ is None
        assert caught.value.__context__ is None
        assert [e for e in _chain(caught.value) if TOKEN in str(e)] == []
        assert TOKEN not in "".join(traceback.format_exception(caught.value))

    def test_it_is_a_plain_repo_client_error(self) -> None:
        with pytest.raises(RepoClientError) as caught:
            _Adapter(TOKEN).fails("x")
        assert type(caught.value) is RepoClientError

    def test_a_name_conflict_passes_through_as_it_is(self) -> None:
        """Its message is ours (the name the caller chose), and the nodes catch it by class."""
        with pytest.raises(RepoNameConflictError) as caught:
            _Adapter(TOKEN).conflicts()
        assert caught.value.name == "demo"

    def test_a_return_value_and_the_arguments_pass_through(self) -> None:
        assert _Adapter(TOKEN).works(2, extra=3) == 5

    def test_an_error_that_is_not_a_repo_client_error_is_not_swallowed_or_converted(self) -> None:
        with pytest.raises(KeyError):
            _Adapter(TOKEN).crashes()

    def test_the_wrapped_method_keeps_its_name_and_docstring(self) -> None:
        assert _Adapter.works.__name__ == "works"
        assert _Adapter.works.__doc__ == "Add two numbers."

    def test_the_wrapper_carries_the_marker_a_registry_test_looks_for(self) -> None:
        """``__wrapped__`` is set by every ``functools.wraps`` decorator, so it cannot tell this one
        from a retry or a timer that scrubs nothing."""
        assert _Adapter.fails.__scrubs_host_text__ is True  # type: ignore[attr-defined]
        assert not hasattr(_Adapter.fails.__wrapped__, "__scrubs_host_text__")

    def test_a_holder_without_a_secret_fails_closed_and_chains_nothing(self) -> None:
        """Reading ``self._secret`` in the handler would raise there, with the unscrubbed original
        on ``__context__``."""

        class NoSecret:
            @scrubbed_errors
            def fails(self) -> None:
                raise RepoClientError(f"500 PRIVATE-TOKEN: {TOKEN}")

        with pytest.raises(RepoClientError) as caught:
            NoSecret().fails()  # type: ignore[arg-type]
        assert str(caught.value) == UNPRINTABLE
        assert caught.value.__cause__ is None
        assert caught.value.__context__ is None


class TestScrubProjectInfo:
    def test_each_of_the_three_fields_is_scrubbed(self) -> None:
        out = scrub_project_info(
            ProjectInfo(id="1\x1b[2J2", url="https://h/p\x1b]0;x\x07", default_branch="m\r\nain")
        )
        assert out == ProjectInfo(id="1 [2J2", url="https://h/p ]0;x", default_branch="m ain")

    def test_it_is_a_new_object_and_the_argument_is_left_alone(self) -> None:
        info = ProjectInfo(id="1\x07", url="u", default_branch="b")
        out = scrub_project_info(info)
        assert out is not info
        assert info.id == "1\x07"

    @pytest.mark.parametrize(
        ("id_", "url", "branch"),
        [
            ("42", "https://gitlab.example.com/g/p", "main"),
            ("owner/name", "https://github.com/owner/name", "release/1.0_rc-2"),
            ("7", "https://gitlab.exämple.org:8443/g/sub/p-1?x=1&y=2#frag", "develop"),
        ],
    )
    def test_text_with_nothing_to_remove_comes_back_as_it_went_in(
        self, id_: str, url: str, branch: str
    ) -> None:
        info = ProjectInfo(id=id_, url=url, default_branch=branch)
        assert scrub_project_info(info, TOKEN) == info

    def test_the_secret_is_removed_from_every_field(self) -> None:
        out = scrub_project_info(
            ProjectInfo(id=f"1-{TOKEN}", url=f"https://h/{TOKEN}/p", default_branch=f"b-{TOKEN}"),
            TOKEN,
        )
        assert TOKEN not in repr(out)
        assert out == ProjectInfo(
            id=f"1-{REDACTED}", url=f"https://h/{REDACTED}/p", default_branch=f"b-{REDACTED}"
        )

    def test_a_value_that_is_only_control_codes_becomes_empty_as_an_empty_one_already_was(
        self,
    ) -> None:
        """Pinned, not endorsed: an empty id, address or branch was accepted before (the adapters
        write ``main`` for a missing branch BEFORE the scrub sees it), and a host that sends only
        control codes now gets the same treatment as one that sends nothing."""
        assert scrub_project_info(
            ProjectInfo(id="\x1b\x07", url="\x00", default_branch="\x7f")
        ) == ProjectInfo(id="", url="", default_branch="")

    def test_a_value_over_the_limit_is_cut_with_the_notice_a_url_may_not_want(self) -> None:
        """Pinned, not endorsed (``BACKLOG.md`` route 8 names it): the cut and its notice apply to
        an address as to any other host text. No real address, id, branch or sha is this long."""
        exact = "u" * MAX_HOST_TEXT
        assert scrub_project_info(ProjectInfo("1", exact, "main")).url == exact
        cut = scrub_project_info(ProjectInfo("1", exact + "x", "main")).url
        assert cut == exact + "... [1 more characters not shown]"

    def test_a_value_that_is_not_text_comes_back_as_its_text(self) -> None:
        out = scrub_project_info(ProjectInfo(id=5, url=None, default_branch=1.5))  # type: ignore[arg-type]
        assert out == ProjectInfo(id="5", url="None", default_branch="1.5")

    def test_a_secret_that_is_not_text_fails_closed(self) -> None:
        out = scrub_project_info(ProjectInfo("1", "u", "b"), 5)  # type: ignore[arg-type]
        assert out == ProjectInfo(UNPRINTABLE, UNPRINTABLE, UNPRINTABLE)

    def test_it_is_idempotent(self) -> None:
        once = scrub_project_info(ProjectInfo("1\x1b2", "u\x07", "b\r\n"), TOKEN)
        assert scrub_project_info(once, TOKEN) == once


class TestScrubCommitInfo:
    def test_the_sha_is_scrubbed_and_the_paths_are_copied_as_they_are(self) -> None:
        files = ["README.md", "analysis/01 plan.qmd", "a\tb.txt"]
        out = scrub_commit_info(CommitInfo(sha="abc\x1b]0;x\x07def", files_committed=files))
        assert out.sha == "abc ]0;x def"
        assert out.files_committed == files
        # A copy: the caller's list is not shared with the result.
        assert out.files_committed is not files

    def test_the_secret_is_removed_from_the_sha(self) -> None:
        out = scrub_commit_info(CommitInfo(sha=f"x{TOKEN}y", files_committed=[]), TOKEN)
        assert out.sha == f"x{REDACTED}y"

    def test_a_full_sha_comes_back_as_it_went_in(self) -> None:
        sha = "0123456789abcdef0123456789abcdef01234567"
        assert scrub_commit_info(CommitInfo(sha, ["a"]), TOKEN).sha == sha

    def test_a_sha_that_is_not_text_comes_back_as_its_text(self) -> None:
        """GitHub's adapter does not ``str()`` the sha it reads, GitLab's does: the scrub makes the
        two agree, where before an integer or a list was a pydantic error in the result."""
        assert scrub_commit_info(CommitInfo(sha=5, files_committed=[])).sha == "5"  # type: ignore[arg-type]


class _Holder:
    """A stand-in with the one attribute ``scrubbed_values`` reads."""

    def __init__(self, secret: str) -> None:
        self._secret = secret

    @scrubbed_values
    def project(self, raw: str) -> ProjectInfo:
        """Make a project."""
        return ProjectInfo(id=raw, url=f"https://h/{self._secret}", default_branch="main")

    @scrubbed_values
    def commit(self, sha: str) -> CommitInfo:
        return CommitInfo(sha=sha, files_committed=["a b"])

    @scrubbed_values
    def fails(self) -> ProjectInfo:
        raise RepoClientError(f"quoted {self._secret}")

    @scrubbed_values
    def wrong_type(self) -> ProjectInfo:
        return "not a project"  # type: ignore[return-value]


class TestScrubbedValues:
    def test_a_project_leaves_scrubbed_with_the_holders_secret_removed(self) -> None:
        out = _Holder(TOKEN).project("12\x1b[2J3")
        assert out == ProjectInfo(id="12 [2J3", url=f"https://h/{REDACTED}", default_branch="main")

    def test_a_commit_leaves_scrubbed(self) -> None:
        out = _Holder(TOKEN).commit("abc\x07")
        assert out == CommitInfo(sha="abc", files_committed=["a b"])

    def test_an_exception_is_not_touched(self) -> None:
        """It is ``scrubbed_errors``' to handle, and the one stacked above this decorator does."""
        with pytest.raises(RepoClientError) as caught:
            _Holder(TOKEN).fails()
        assert str(caught.value) == f"quoted {TOKEN}"

    def test_a_result_of_any_other_type_fails_closed(self) -> None:
        """No method of ``RepoClient`` returns one. A method added that does would carry the marker
        and scrub nothing, so it raises the first time it is called."""
        with pytest.raises(TypeError, match="ProjectInfo or CommitInfo, not str"):
            _Holder(TOKEN).wrong_type()

    def test_the_wrapped_method_keeps_its_name_and_docstring(self) -> None:
        assert _Holder.project.__name__ == "project"
        assert _Holder.project.__doc__ == "Make a project."

    def test_the_wrapper_carries_its_own_marker_and_not_the_errors_one(self) -> None:
        """Each decorator sets its marker alone, so a registry test can tell which one ran."""
        assert _Holder.project.__scrubs_host_values__ is True  # type: ignore[attr-defined]
        assert not hasattr(_Holder.project, "__scrubs_host_text__")
        assert not hasattr(_Holder.project.__wrapped__, "__scrubs_host_values__")

    def test_stacked_under_scrubbed_errors_both_markers_show_and_both_work(self) -> None:
        class Both:
            _secret = TOKEN

            @scrubbed_errors
            @scrubbed_values
            def project(self, fail: bool) -> ProjectInfo:
                if fail:
                    raise RepoClientError(f"500 {TOKEN}")
                return ProjectInfo("1\x07", "u", "b")

        assert Both.project.__scrubs_host_text__ is True  # type: ignore[attr-defined]
        assert Both.project.__scrubs_host_values__ is True  # type: ignore[attr-defined]
        assert Both().project(False) == ProjectInfo("1", "u", "b")
        with pytest.raises(RepoClientError) as caught:
            Both().project(True)
        assert str(caught.value) == f"500 {REDACTED}"


class TestResponseText:
    """``response.text`` raises when a reply declares a charset its body is not in, or one that is
    not a text codec at all, and the adapters read it while building the message for a failure: the
    error that results is not a ``RepoClientError``, so it would leave the adapter as a crash, past
    ``scrubbed_errors``. The class it raises differs by interpreter (``UnicodeDecodeError`` on 3.13,
    a plain ``UnicodeError`` on 3.11 and 3.12, which is what CI runs), so the premises below ask for
    the common base."""

    def test_an_ordinary_body_is_its_text(self) -> None:
        assert response_text(httpx.Response(500, text="héllo")) == "héllo"
        assert response_text(httpx.Response(204)) == ""

    def test_a_declared_charset_the_body_is_not_in_does_not_raise(self) -> None:
        body = b"PRIVATE-TOKEN: " + TOKEN.encode() + b"!"  # odd length: not valid UTF-16
        response = httpx.Response(
            500, content=body, headers={"content-type": "text/plain; charset=utf-16"}
        )
        with pytest.raises(UnicodeError):
            response.text  # noqa: B018 - the premise: the library itself raises here
        assert response_text(response) == body.decode("utf-8")

    def test_bytes_that_are_not_utf8_either_come_back_replaced(self) -> None:
        # Odd length (UTF-16 refuses it), no BOM, and not UTF-8 either.
        response = httpx.Response(
            500,
            content=b"\xff oops \x80!",
            headers={"content-type": "text/plain; charset=utf-16"},
        )
        with pytest.raises(UnicodeError):
            response.text  # noqa: B018 - the premise
        assert "oops" in response_text(response)
        assert "\ufffd" in response_text(response)

    def test_an_unknown_charset_name_does_not_raise(self) -> None:
        """A must-not-regress case: ``httpx`` 0.28 falls back to UTF-8 for a name it does not know,
        so this passes with a bare ``return response.text`` too."""
        response = httpx.Response(
            500, content=b"boom", headers={"content-type": "text/plain; charset=no-such-codec"}
        )
        assert response_text(response) == "boom"

    def test_a_correctly_declared_charset_is_honoured(self) -> None:
        response = httpx.Response(
            500,
            content="h\u00e9llo".encode("latin-1"),
            headers={"content-type": "text/plain; charset=iso-8859-1"},
        )
        assert response_text(response) == "h\u00e9llo"

    @pytest.mark.parametrize("charset", ["undefined", "rot13", "hex", "zlib", "idna", "base64"])
    def test_a_charset_that_is_not_a_text_codec_does_not_raise(self, charset: str) -> None:
        """Names ``codecs.lookup`` accepts and ``httpx`` therefore uses: ``response.text`` raises
        ``UnicodeError``, ``TypeError`` or ``AssertionError``, depending on the codec."""
        body = b"PRIVATE-TOKEN: " + TOKEN.encode()
        response = httpx.Response(
            500, content=body, headers={"content-type": f"text/plain; charset={charset}"}
        )
        with pytest.raises((UnicodeError, TypeError, AssertionError)):
            response.text  # noqa: B018 - the premise
        assert response_text(response) == body.decode()

    def test_no_charset_the_standard_library_knows_makes_it_raise(self) -> None:
        names = sorted(set(encodings.aliases.aliases.values()) | set(encodings.aliases.aliases))
        assert len(names) > 100
        for name in names:
            response = httpx.Response(
                500, content=b"abc", headers={"content-type": f"text/plain; charset={name}"}
            )
            assert isinstance(response_text(response), str), name
