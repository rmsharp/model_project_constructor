"""A model of what a git tree, a checkout and a repository host refuse in a path.

``FakeRepoClient`` keeps every committed path as a dictionary key and looks at none of it, and the
host stand-ins in ``success_hosts.py`` and ``loopback.py`` never inspect a path either, so no test
could see a report name that steered a path fail anywhere but in an assertion written for it
(Session 296's critic, BACKLOG (7)(a)). ``PathCheckingRepoClient`` refuses what a real host or
checkout would, and a test that ends ``COMPLETE`` on it is a test that the whole tree is a tree a
developer can clone on Linux, macOS and Windows.

The rules were measured where they could be: local git 2.56.0 (``git update-index --cacheinfo``)
refuses ``..``, ``.``, an empty component, ``//`` and any ``.git`` component, and accepts a
trailing dot, ``CON.sql`` and ``a/b.sql``. The Windows and macOS rules are the documented ones
and were not run on those systems (the model errs towards refusing). This module imports nothing
from ``_file_stems``: a list of device names copied from the code under test would share its
mistakes.
"""

from __future__ import annotations

import unicodedata

from model_project_constructor.agents.website.fake_client import FakeRepoClient
from model_project_constructor.agents.website.protocol import CommitInfo, RepoClientError

# Microsoft's list of names that cannot be a file name on Windows, with or without an extension.
_DEVICES = (
    {"con", "prn", "aux", "nul", "conin$", "conout$"}
    | {f"com{n}" for n in range(1, 10)}
    | {f"lpt{n}" for n in range(1, 10)}
)
_FORBIDDEN_ON_WINDOWS = set('\\:*?"<>|')
MAX_COMPONENT_BYTES = 255


def unsafe_reason(path: str) -> str | None:
    """Why a host, git or a checkout would refuse ``path``, or ``None`` if none would."""

    if not path:
        return "the path is empty"
    if path.startswith("/"):
        return "the path is absolute"
    try:
        path.encode("utf-8")
    except UnicodeEncodeError:
        return "the path cannot be written as UTF-8"
    for char in path:
        if ord(char) < 0x20 or ord(char) == 0x7F:
            return f"a control character ({ord(char):#x})"
        if char in _FORBIDDEN_ON_WINDOWS:
            return f"{char!r} is not allowed in a Windows file name"
    for component in path.split("/"):
        folded = component.casefold()
        if component == "":
            return "an empty component"
        if component in (".", ".."):
            return f"the component {component!r} steers the path"
        if folded == ".git":
            return "a .git component"
        if folded.startswith("git~"):
            return "a name that Windows may read as the short name of .git"
        if component.endswith((".", " ")):
            return "a component that ends with a dot or a space"
        if len(component.encode("utf-8")) > MAX_COMPONENT_BYTES:
            return "a component of more than 255 bytes"
        if folded.split(".")[0].rstrip(" ") in _DEVICES:
            return f"{component!r} is a Windows device name"
    return None


def _collision_key(path: str) -> str:
    """Two paths with one key are one file on a case-insensitive or normalising file system."""

    return unicodedata.normalize("NFC", path).casefold()


def collision(paths: list[str]) -> str | None:
    """Why two of ``paths`` cannot both exist in a checkout, or ``None``."""

    seen: dict[str, str] = {}
    for path in paths:
        key = _collision_key(path)
        if key in seen:
            return f"{path!r} and {seen[key]!r} are one file"
        seen[key] = path
    keys = sorted(seen)
    for key in keys:
        parent = key.rsplit("/", 1)[0] if "/" in key else ""
        while parent:
            if parent in seen:
                return f"{seen[key]!r} is inside {seen[parent]!r}, which is a file"
            parent = parent.rsplit("/", 1)[0] if "/" in parent else ""
    return None


class PathCheckingRepoClient(FakeRepoClient):
    """A ``FakeRepoClient`` that refuses a commit a real tree would refuse."""

    def commit_files(
        self,
        *,
        project_id: str,
        branch: str,
        files: dict[str, str],
        message: str,
    ) -> CommitInfo:
        for path in files:
            reason = unsafe_reason(path)
            if reason is not None:
                raise RepoClientError(f"path refused: {path!r}: {reason}")
        every = [*self.projects[project_id].files, *files]
        reason = collision(sorted(set(every)))
        if reason is not None:
            raise RepoClientError(f"path refused: {reason}")
        return super().commit_files(
            project_id=project_id, branch=branch, files=files, message=message
        )
