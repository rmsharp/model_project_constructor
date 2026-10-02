"""A repository host token is one run of printable ASCII, checked before it reaches a header.

Why this exists. ``h11`` refuses a header value that holds a NUL, line feed, vertical tab, form
feed or carriage return, or that begins or ends with a space or tab, and **its error quotes the
whole value**: ``Illegal header value b'glpat-...\\r'``. The adapters put that text in
``RepoClientError``, the website agent stores it as ``failure_reason``, and the CLI prints the
result on stdout and writes it to ``-o``. So ``--private-token "$(cat token.txt)"`` from a file
with Windows line endings printed the credential (BACKLOG.md, found by Session 272's review).
The same library accepts DEL and the controls U+0001-U+0008 and U+000E-U+001F and sends them, and
refuses a non-ASCII value at construction.

The rule is defined here and not borrowed from the library: a token is one or more characters in
U+0021-U+007E. That refuses everything ``h11`` refuses today and more, and
``test_every_accepted_character_reaches_the_wire_intact`` holds the other half against the
installed ``httpx``, ``httpcore`` and ``h11`` over a real socket: a release of ``h11`` that began
refusing a character the rule accepts would fail that test on the bump, and ``RepoHttpClient``
withholds the text in the meantime. ``httpx.MockTransport`` skips ``h11`` altogether, which is why
no adapter test could ever see this.
"""

from __future__ import annotations

import copy
import pickle
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from typer.testing import CliRunner

from model_project_constructor.agents.website import GitHubAdapter, GitLabAdapter
from model_project_constructor.agents.website.cli import app
from model_project_constructor.agents.website.protocol import (
    InvalidRepoTokenError,
    validate_repo_token,
)
from model_project_constructor.orchestrator.config import REPO_PLATFORMS
from tests.agents.website.loopback import Loopback

SECRET = "glpat-SECRET9f3kQ7"

# What an operator reads: the option's name, then the one fixed sentence.
REFUSAL = f"ERROR: --private-token: {InvalidRepoTokenError()}"

# NUL to U+02FF takes in the C0 and C1 controls, DEL, NBSP and Latin-1; the last two are a BMP
# and an astral character.
CODE_POINTS = [*range(0x300), 0x2603, 0x1F600]
PRINTABLE_ASCII = range(0x21, 0x7F)

POSITIONS: dict[str, Callable[[str], str]] = {
    "leading": lambda c: c + SECRET,
    "inside": lambda c: SECRET[:9] + c + SECRET[9:],
    "trailing": lambda c: SECRET + c,
}

# The characters a file with Windows line endings or a careless paste leaves behind, and one of each
# other class the rule refuses.
BAD_SUFFIXES = {
    "carriage-return": "\r",
    "tab": "\t",
    "line-feed": "\n",
    "space": " ",
    "nul": "\x00",
    "del": "\x7f",
    "non-ascii": "é",
}

runner = CliRunner()


def _accepts(token: str) -> bool:
    try:
        validate_repo_token(token)
    except InvalidRepoTokenError:
        return False
    return True


# ---------------------------------------------------------------------------
# The rule itself.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("position", POSITIONS)
def test_exactly_the_printable_ascii_characters_are_accepted(position: str) -> None:
    build = POSITIONS[position]
    wrongly_accepted = [
        hex(cp) for cp in CODE_POINTS if _accepts(build(chr(cp))) and cp not in PRINTABLE_ASCII
    ]
    wrongly_rejected = [hex(cp) for cp in PRINTABLE_ASCII if not _accepts(build(chr(cp)))]
    assert wrongly_accepted == []
    assert wrongly_rejected == []


@pytest.mark.parametrize(
    "token",
    [
        "glpat-xxxxxxxxxxxxxxxxxxxx",
        "ghp_" + "A1b2C3d4" * 4 + "wxyz",
        "github_pat_11ABCDEFG0aBcDeFgHiJkL_mNoPqRsTuVwXyZ0123456789",
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.c2ln-bmF0_dXJl",
        "a+b/c==",
        "t",
    ],
)
def test_realistic_tokens_are_accepted(token: str) -> None:
    validate_repo_token(token)


@pytest.mark.parametrize("token", ["", " ", "\t", "\r\n", "\xa0"])
def test_an_empty_or_blank_token_is_rejected(token: str) -> None:
    assert not _accepts(token)


def test_the_error_is_one_fixed_sentence_that_cannot_carry_the_value() -> None:
    messages = set()
    for bad in (SECRET + "\r", SECRET + "\n", "\t" + SECRET, SECRET[:5] + "é" + SECRET[5:], ""):
        with pytest.raises(InvalidRepoTokenError) as caught:
            validate_repo_token(bad)
        assert SECRET not in str(caught.value)
        assert SECRET not in repr(caught.value)
        assert caught.value.__cause__ is None
        messages.add(str(caught.value))
    assert len(messages) == 1
    assert issubclass(InvalidRepoTokenError, ValueError)


def test_the_error_survives_pickle_copy_and_deepcopy() -> None:
    """Its constructor takes no argument, so the default reduction (``cls(*args)``) would fail:
    a worker process or an exception-forwarding layer must still get the same refusal back."""
    error = InvalidRepoTokenError()
    for clone in (pickle.loads(pickle.dumps(error)), copy.copy(error), copy.deepcopy(error)):
        assert type(clone) is InvalidRepoTokenError
        assert str(clone) == str(error)


# ---------------------------------------------------------------------------
# A real socket: the rule is a subset of what the installed HTTP stack sends.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("adapter", "header", "prefix"),
    [
        pytest.param(GitLabAdapter, "private-token", "", id="gitlab"),
        pytest.param(GitHubAdapter, "authorization", "Bearer ", id="github"),
    ],
)
def test_every_accepted_character_reaches_the_wire_intact(
    adapter: type[GitLabAdapter] | type[GitHubAdapter],
    header: str,
    prefix: str,
    loopback: Loopback,
) -> None:
    for position, build in POSITIONS.items():
        for cp in PRINTABLE_ASCII:
            token = build(chr(cp))
            loopback.seen.clear()
            built = adapter(host_url=loopback.url, private_token=token)
            try:
                response = built._client.get("/probe")
            finally:
                built._client.close()
            assert response.status_code == 200, (position, hex(cp))
            assert loopback.seen[-1][header] == prefix + token, (position, hex(cp))


# ---------------------------------------------------------------------------
# Every route to a token ends at an adapter constructor, so the constructors refuse it.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("adapter", [GitLabAdapter, GitHubAdapter], ids=["gitlab", "github"])
@pytest.mark.parametrize("suffix", BAD_SUFFIXES.values(), ids=BAD_SUFFIXES.keys())
def test_an_adapter_refuses_a_bad_token_without_repeating_it(
    adapter: type[GitLabAdapter] | type[GitHubAdapter], suffix: str
) -> None:
    with pytest.raises(InvalidRepoTokenError) as caught:
        adapter(host_url="http://127.0.0.1:9", private_token=SECRET + suffix)
    assert SECRET not in str(caught.value)


@pytest.mark.parametrize("host", sorted(REPO_PLATFORMS))
def test_every_registered_host_refuses_a_bad_token_without_repeating_it(host: str) -> None:
    """The pipeline script builds its adapter from the registry and validates nothing itself, so
    a host added there whose adapter forgets the check would reopen the leak: this goes red."""
    with pytest.raises(InvalidRepoTokenError) as caught:
        REPO_PLATFORMS[host].adapter_factory(
            host_url="http://127.0.0.1:9", private_token=SECRET + "\r"
        )
    assert SECRET not in str(caught.value)


# ---------------------------------------------------------------------------
# The website CLI, in process and as the real command.
# ---------------------------------------------------------------------------


def _everything_the_command_showed(printed: str, out: Path) -> str:
    """What reached the operator or a file: the terminal's text plus the ``-o`` file, if written.

    The result JSON goes to the file when ``-o`` is given, so a test that read only the terminal
    would pass on the very leak this file exists for.
    """
    return printed + (out.read_text() if out.exists() else "")


@pytest.mark.parametrize("host", ["gitlab", "github"])
@pytest.mark.parametrize("suffix", BAD_SUFFIXES.values(), ids=BAD_SUFFIXES.keys())
def test_cli_rejects_a_bad_token_and_prints_none_of_it(
    intake_report_path: Path,
    data_report_path: Path,
    loopback: Loopback,
    tmp_path: Path,
    host: str,
    suffix: str,
) -> None:
    out = tmp_path / "result.json"
    result = runner.invoke(
        app,
        [
            "--intake",
            str(intake_report_path),
            "--data",
            str(data_report_path),
            "--host",
            host,
            "--host-url",
            loopback.url,
            "--private-token",
            SECRET + suffix,
            "-o",
            str(out),
        ],
    )
    shown = result.stdout + result.stderr
    assert SECRET not in _everything_the_command_showed(shown, out)
    assert result.exit_code == 2, shown
    assert result.stdout == ""
    assert result.stderr.strip() == REFUSAL
    assert not out.exists()


def test_cli_ignores_the_token_under_fake(
    intake_report_path: Path, data_report_path: Path
) -> None:
    """``--fake`` never builds an adapter, so a token it will not use is not judged."""
    result = runner.invoke(
        app,
        [
            "--intake",
            str(intake_report_path),
            "--data",
            str(data_report_path),
            "--fake",
            "--private-token",
            SECRET + "\r",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert SECRET not in result.stdout + result.stderr


def test_cli_checks_the_token_before_reading_any_file(tmp_path: Path) -> None:
    """A bad token is reported even when the report files are unreadable, so the check is not
    behind the parsing that comes next."""
    not_json = tmp_path / "not.json"
    not_json.write_text("{ not json")
    result = runner.invoke(
        app,
        ["--intake", str(not_json), "--data", str(not_json), "--private-token", SECRET + "\r"],
    )
    assert result.exit_code == 2, result.stdout + result.stderr
    assert result.stderr.strip() == REFUSAL


@pytest.mark.parametrize("suffix", ["\r", "\t", "\n"], ids=["carriage-return", "tab", "line-feed"])
def test_the_real_command_prints_none_of_a_bad_token_and_exits_2(
    intake_report_path: Path,
    data_report_path: Path,
    loopback: Loopback,
    tmp_path: Path,
    suffix: str,
) -> None:
    out = tmp_path / "result.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "model_project_constructor.agents.website",
            "--intake",
            str(intake_report_path),
            "--data",
            str(data_report_path),
            "--host-url",
            loopback.url,
            "--private-token",
            SECRET + suffix,
            "-o",
            str(out),
        ],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        stdin=subprocess.DEVNULL,
        timeout=120,
    )
    shown = completed.stdout + completed.stderr
    assert SECRET not in _everything_the_command_showed(shown, out)
    assert completed.returncode == 2, shown
    assert completed.stdout == ""
    assert completed.stderr.strip() == REFUSAL
    assert not out.exists()
