"""What a repository host's failure text may carry to a person or to disk.

``scrub_host_text`` is the one function every message that leaves an adapter goes through: the
host's words are untrusted (a gateway that echoes the request headers puts the access token in an
error body), and so is the HTTP library's description of a malformed reply (``h11`` quotes the bytes
the server sent). It removes the secret by value in every form a host is known to re-encode it in,
makes the text one line free of control characters, and bounds its length. ``scrubbed_errors``
applies it at the exit of an adapter method, so a message-building site added later cannot bypass
it.
"""

from __future__ import annotations

import html
import json
import traceback
from collections.abc import Iterator
from urllib.parse import quote, quote_plus

import pytest

from model_project_constructor.agents.website._host_text import (
    MAX_HOST_TEXT,
    REDACTED,
    scrub_host_text,
    scrubbed_errors,
)
from model_project_constructor.agents.website.protocol import (
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
