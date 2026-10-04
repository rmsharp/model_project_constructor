"""Thin direct-``httpx`` adapter for :class:`RepoClient` (GitLab).

This is the production adapter for the Website Agent's GitLab path. It is
intentionally thin:

- The constructor builds an ``httpx.Client`` scoped to ``{host_url}/api/v4``
  with a ``PRIVATE-TOKEN`` auth header, after refusing a token that is not
  printable ASCII (:func:`validate_repo_token`). No network call happens at
  construction time.
- ``create_project`` resolves the target group, creates a project inside
  it, and translates name collisions to :class:`RepoNameConflictError` and
  every other GitLab error to :class:`RepoClientError`.
- ``commit_files`` issues a single multi-file commit through the GitLab
  commits API.

Per the Phase 4B handoff (architecture-plan §14): this module is **not**
unit-tested against a live GitLab. The test suite drives it against
``httpx.MockTransport`` and confirms it implements the protocol and maps
representative wire-level responses; anything stronger requires a test
GitLab instance and is a Phase 5 concern.

Migrated off ``python-gitlab`` (LGPL-3.0-or-later) to direct ``httpx``
calls per ``docs/planning/httpx-adapter-migration.md`` Phase 1 — the
needed surface is 4 REST calls, so a full SDK adds licensing weight
without functional benefit.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from model_project_constructor.agents.website._host_text import (
    reading_a_creation_reply,
    reply_id,
    reply_json,
    reply_object,
    reply_string,
    response_text,
    scrubbed_errors,
    scrubbed_values,
)
from model_project_constructor.agents.website._http import RepoHttpClient
from model_project_constructor.agents.website.protocol import (
    CommitInfo,
    ProjectInfo,
    RepoClient,
    RepoClientError,
    RepoNameConflictError,
    validate_repo_token,
)


class GitLabAdapter(RepoClient):
    """``RepoClient`` implementation backed by direct calls to the GitLab
    REST API (``/api/v4``).

    Usage::

        from model_project_constructor.agents.website import (
            GitLabAdapter, WebsiteAgent,
        )
        client = GitLabAdapter(
            host_url="https://gitlab.example.com",
            private_token=os.environ["GITLAB_TOKEN"],
        )
        agent = WebsiteAgent(client)
    """

    def __init__(
        self,
        *,
        host_url: str,
        private_token: str,
        ssl_verify: bool = True,
    ) -> None:
        validate_repo_token(private_token)
        # Kept so that an error leaving this adapter can have the token removed from its message
        # (``scrubbed_errors``): the host's own words reach that message, and a host that echoes
        # the request headers has put the token in them.
        self._secret = private_token
        self._client = RepoHttpClient(
            base_url=f"{host_url.rstrip('/')}/api/v4",
            headers={"PRIVATE-TOKEN": private_token},
            verify=ssl_verify,
        )

    # ------------------------------------------------------------------
    # RepoClient protocol
    # ------------------------------------------------------------------

    @scrubbed_errors
    @scrubbed_values
    def create_project(
        self,
        *,
        namespace: str,
        name: str,
        visibility: str,
    ) -> ProjectInfo:
        try:
            group_path = f"/groups/{quote(namespace, safe='')}"
        except UnicodeEncodeError as exc:
            # ``quote`` writes the namespace as UTF-8 and raises for a lone surrogate (a
            # command-line argument whose bytes are not UTF-8 arrives as one) before ``httpx`` is
            # reached, so the client's conversion of an unbuildable request never sees it. The
            # namespace is the caller's text, not the host's, so the message may show it (``repr``
            # escapes the character); it is refused, not sent with the character cleaned out.
            raise RepoClientError(
                f"group lookup failed for {namespace!r}: the namespace holds a character that "
                "cannot be written into an address (an unpaired surrogate)"
            ) from exc
        try:
            response = self._client.get(group_path)
        except httpx.HTTPError as exc:
            raise RepoClientError(
                f"group lookup failed for {namespace!r}: {exc}"
            ) from exc
        lookup = f"group lookup failed for {namespace!r}"
        _ok_or_raise(response, lookup)
        # What the group's id is goes back in the next request as the host sent it (an integer
        # stays one), so a reply without a usable one is refused here and the request never made.
        namespace_id = reply_id(_parse_json(response, lookup), "id", context=lookup)

        try:
            response = self._client.post(
                "/projects",
                json={
                    "name": name,
                    "path": name,
                    "namespace_id": namespace_id,
                    "visibility": visibility,
                },
            )
        except httpx.HTTPError as exc:
            raise RepoClientError(f"create_project failed for {name!r}: {exc}") from exc
        if not _is_2xx(response):
            if _is_name_conflict(response):
                raise RepoNameConflictError(name)
            raise RepoClientError(
                f"create_project failed for {name!r}: "
                f"{response.status_code} {response_text(response)}"
            )
        # The host answered 2xx: a project may exist, so a failure to read the reply says so.
        created = f"create_project failed for {name!r}"
        with reading_a_creation_reply():
            project = reply_object(_parse_json(response, created), context=created)
            info = ProjectInfo(
                id=str(reply_id(project, "id", context=created)),
                url=reply_string(project, "web_url", context=created),
                default_branch=str(project.get("default_branch") or "main"),
            )
        return info

    @scrubbed_errors
    @scrubbed_values
    def commit_files(
        self,
        *,
        project_id: str,
        branch: str,
        files: dict[str, str],
        message: str,
    ) -> CommitInfo:
        try:
            response = self._client.get(f"/projects/{project_id}")
        except httpx.HTTPError as exc:
            raise RepoClientError(
                f"project lookup failed for id={project_id}: {exc}"
            ) from exc
        _ok_or_raise(response, f"project lookup failed for id={project_id}")

        actions = [
            {
                "action": "create",
                "file_path": path,
                "content": content,
            }
            for path, content in sorted(files.items())
        ]
        try:
            response = self._client.post(
                f"/projects/{project_id}/repository/commits",
                json={
                    "branch": branch,
                    "commit_message": message,
                    "actions": actions,
                },
            )
        except httpx.HTTPError as exc:
            raise RepoClientError(
                f"commit_files failed (project={project_id}, branch={branch}): {exc}"
            ) from exc
        context = f"commit_files failed (project={project_id}, branch={branch})"
        _ok_or_raise(response, context)
        commit = _parse_json(response, context)

        return CommitInfo(
            sha=reply_string(commit, "id", context=context),
            files_committed=sorted(files),
        )


def _is_2xx(response: httpx.Response) -> bool:
    return 200 <= response.status_code < 300


def _ok_or_raise(response: httpx.Response, context: str) -> None:
    """Raise :class:`RepoClientError` if ``response`` is not a 2xx.

    Deliberately stricter than "not >= 400": ``httpx.Client`` does not
    follow redirects by default (unlike the ``requests``-based transport
    the old ``python-gitlab`` adapter used), so a 3xx must also be treated
    as a failure rather than silently falling through to a body parse.
    """

    if not _is_2xx(response):
        raise RepoClientError(f"{context}: {response.status_code} {response_text(response)}")


def _parse_json(response: httpx.Response, context: str) -> Any:
    """Parse a 2xx response body, raising :class:`RepoClientError` on
    malformed JSON, or JSON nested too deeply to use (:func:`reply_json`), instead of letting a
    raw ``ValueError`` or ``RecursionError`` escape.

    Returns whatever JSON the host sent, which is not necessarily an object: what is read from it
    goes through :func:`reply_object`, :func:`reply_string` or :func:`reply_id`, never a subscript.
    """

    try:
        return reply_json(response)
    except ValueError as exc:
        raise RepoClientError(f"{context}: invalid JSON body: {exc}") from exc


def _is_name_conflict(response: httpx.Response) -> bool:
    """Detect a GitLab "name already taken" error from a create-project response.

    GitLab returns a 400/409 with a body that looks like
    ``{"name":["has already been taken"],"path":["has already been taken"]}``.
    We match loosely so minor wording changes don't break the adapter.
    """

    if response.status_code not in (400, 409):
        return False
    try:
        body: Any = reply_json(response)
    except ValueError:
        body = None
    text = str(body) if body is not None else response_text(response)
    lowered = text.lower()
    return "already been taken" in lowered or "already exists" in lowered


__all__ = ["GitLabAdapter"]
