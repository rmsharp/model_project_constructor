"""Repo client boundary for the Website Agent.

Per architecture-plan §4.3 the agent talks to a repository host (GitLab or
GitHub) via a thin adapter, but nodes must be unit-testable without a live
host. This ``Protocol`` is the boundary: tests pass a ``FakeRepoClient``,
production passes a thin wrapper around direct ``httpx`` calls to either
host's REST API.

The Phase 4A CLI (`--fake`) uses the fake client so it can show a file tree
of what *would* have been committed without needing credentials.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol


@dataclass
class ProjectInfo:
    """Information returned by :meth:`RepoClient.create_project`.

    ``id`` is a host-opaque string identifier: GitLab uses a stringified
    integer project ID, GitHub uses ``"owner/name"``. Callers should treat
    it as an opaque token and pass it back to :meth:`RepoClient.commit_files`
    as they got it.

    All three fields are the host's words. The two shipped adapters hand
    them back through ``scrubbed_values`` (``_host_text.py``): control
    characters become spaces, the text is one line of at most 1,000
    characters, and the adapter's token is removed. For every real id,
    address and branch that is the identical string. An implementation of
    this protocol that is not one of the two owns the safety of its own
    values (``BACKLOG.md``, route 8).
    """

    id: str
    url: str
    default_branch: str


@dataclass
class CommitInfo:
    """Information returned by :meth:`RepoClient.commit_files`.

    ``sha`` is the host's word and is scrubbed by the shipped adapters like
    :class:`ProjectInfo`'s fields; ``files_committed`` is the caller's own
    list of paths, not the host's.
    """

    sha: str
    files_committed: list[str]


class RepoClient(Protocol):
    """Strategy for the website agent's repository host operations.

    Implementations MUST raise :class:`RepoNameConflictError` when a
    create-project call collides with an existing project name in the
    target namespace. Any other host failure should raise
    :class:`RepoClientError`.
    """

    def create_project(
        self,
        *,
        namespace: str,
        name: str,
        visibility: str,
    ) -> ProjectInfo: ...

    def commit_files(
        self,
        *,
        project_id: str,
        branch: str,
        files: dict[str, str],
        message: str,
    ) -> CommitInfo: ...


class RepoClientError(RuntimeError):
    """Base class for all RepoClient failures the agent handles."""


class RepoNameConflictError(RepoClientError):
    """Raised when the requested project name already exists."""

    def __init__(self, name: str):
        super().__init__(f"Project name already exists: {name!r}")
        self.name = name


class InvalidRepoTokenError(ValueError):
    """Raised when a repository host token is not one run of printable ASCII.

    The message is one fixed sentence and the constructor takes no arguments, so the error cannot
    carry the token it refused: ``h11`` quotes a header value it rejects, which put the whole
    credential into the result JSON and the ``-o`` file.
    """

    def __init__(self) -> None:
        super().__init__(
            "a repository host token may contain only printable ASCII characters: no whitespace "
            "(a token read from a file with Windows line endings ends in a carriage return), no "
            "control characters and no non-ASCII characters. The value is not shown."
        )

    def __reduce__(self) -> tuple[type[InvalidRepoTokenError], tuple[()]]:
        # The default reduction rebuilds with ``cls(*args)``, and ``args`` holds the message.
        return (type(self), ())


_TOKEN_CHARACTERS = re.compile(r"[\x21-\x7e]+")


def validate_repo_token(token: str) -> None:
    """Refuse a token that is not one or more characters in U+0021-U+007E.

    Defined here, not borrowed from the HTTP library. Of the characters outside that range ``h11``
    refuses only some (NUL, CR, LF, VT and FF anywhere; a space or tab at either end) and sends the
    rest, and ``httpx`` refuses a non-ASCII value at construction. Every adapter constructor calls
    this, so every route to a token (the website CLI's ``--private-token``; ``GITLAB_TOKEN`` and
    ``GITHUB_TOKEN`` through the pipeline script; a library caller) is checked once, before the
    value is put in a header.
    """

    if _TOKEN_CHARACTERS.fullmatch(token) is None:
        raise InvalidRepoTokenError
