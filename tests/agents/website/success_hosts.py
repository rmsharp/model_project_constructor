"""A repository host whose SUCCESS replies carry text of the test's choosing, for a real socket.

``loopback.serving_raw`` answers every request with whatever bytes a function returns for it; the
functions here are the ones that answer GitLab's request sequence and GitHub's (an organisation
owner, and a personal account) correctly, with the project address, the project id, the default
branch and the commit id taken from the arguments. A request the router does not know is a ``404``,
which is what a real host says to a path that names nothing.

Used by ``test_host_success_text.py`` (the adapters, through the agent) and
``test_host_success_end_to_end.py`` (the website command and the pipeline script).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

from model_project_constructor.agents.website import GitHubAdapter, GitLabAdapter

TOKEN = "glpat-SECRET9f3kQ7xZ2mW"

#: What a host can put in a value. Each is one piece of text the host chose: an OSC window-title
#: sequence (the website command's ``echo`` strips CSI but not this), a CSI screen clear, ``ESC c``
#: (a terminal reset), a bell and a NUL, a C1 control, DEL, a line break followed by a forged status
#: line, and a lone surrogate (valid in a JSON string, and the one text no file can be written
#: with: the graph's checkpointer raises on it).
HOSTILE = {
    "osc-title": "\x1b]0;PWNED-TITLE\x07",
    "csi-clear": "\x1b[2J",
    "reset": "\x1bc",
    "bell-and-nul": "\x07\x00",
    "c1-csi": "\x9b2J",
    "del": "\x7f",
    "forged-line": "\r\nStatus:  COMPLETE\r\n",
    "lone-surrogate": "\ud800",
}

#: Every terminal control above in one value, for the tests that run a subprocess and so pay for
#: each run. Without the lone surrogate, which a GitHub commit sha cannot carry through the
#: adapter's own next request (``test_host_success_text.GITHUB_REUSES_THE_SHA``).
EVERYTHING = "".join(text for kind, text in HOSTILE.items() if kind != "lone-surrogate")

Reply = tuple[int, object]
Router = Callable[[str, str], Reply]


def is_clean(text: str) -> bool:
    """Nothing a terminal acts on instead of printing (no C0 control, DEL or C1 control), and
    nothing that cannot be written to a file as UTF-8 (no lone surrogate)."""
    return not any(
        ord(c) < 0x20 or 0x7F <= ord(c) <= 0x9F or 0xD800 <= ord(c) <= 0xDFFF for c in text
    )


@dataclass(frozen=True)
class Shipped:
    """One of the host sequences this repository's adapters run."""

    name: str
    host: str
    make: Callable[[str], GitLabAdapter | GitHubAdapter]
    namespace: str
    personal_account: bool

    def router(self, project: dict[str, object], commit_id: object) -> Router:
        if self.host == "gitlab":
            return _gitlab_router(project, commit_id)
        return _github_router(project, commit_id, self.personal_account)

    def project_reply(self, *, id_text: str, url: str, branch: str) -> dict[str, object]:
        """The create-project reply; an empty ``id_text`` is the id the routers below expect."""
        if self.host == "gitlab":
            return {"id": id_text or 42, "web_url": url, "default_branch": branch}
        return {"full_name": id_text or "g/n", "html_url": url, "default_branch": branch}

    def raw_id(self, suffix: str) -> str:
        """The id the routers expect, followed by ``suffix``."""
        return f"42{suffix}" if self.host == "gitlab" else f"g/n{suffix}"


def _gitlab_router(project: dict[str, object], commit_id: object) -> Router:
    def route(method: str, path: str) -> Reply:
        if method == "GET" and path.startswith("/api/v4/groups/"):
            return 200, {"id": 7}
        if method == "POST" and path == "/api/v4/projects":
            return 201, project
        if method == "GET" and path == "/api/v4/projects/42":
            return 200, {}
        if method == "POST" and path == "/api/v4/projects/42/repository/commits":
            return 201, {"id": commit_id}
        return 404, {"message": "404 Project Not Found"}

    return route


def _github_router(project: dict[str, object], commit_sha: object, personal: bool) -> Router:
    owner: dict[tuple[str, str], Reply] = {
        ("GET", "/orgs/g"): (404, {}) if personal else (200, {}),
        ("GET", "/users/g"): (200, {}),
        ("POST", "/orgs/g/repos"): (201, project),
        ("POST", "/user/repos"): (201, project),
    }
    routes: dict[tuple[str, str], Reply] = {
        **owner,
        ("GET", "/repos/g/n"): (200, {}),
        ("GET", "/repos/g/n/git/ref/heads/main"): (200, {"object": {"sha": "p1"}}),
        ("GET", "/repos/g/n/git/commits/p1"): (200, {"tree": {"sha": "t1"}}),
        ("POST", "/repos/g/n/git/blobs"): (201, {"sha": "b1"}),
        ("POST", "/repos/g/n/git/trees"): (201, {"sha": "t2"}),
        ("POST", "/repos/g/n/git/commits"): (201, {"sha": commit_sha}),
        ("PATCH", "/repos/g/n/git/refs/heads/main"): (200, {}),
    }

    def route(method: str, path: str) -> Reply:
        return routes.get((method, path), (404, {"message": "Not Found"}))

    return route


SHIPPED = [
    Shipped(
        "gitlab",
        "gitlab",
        lambda url: GitLabAdapter(host_url=url, private_token=TOKEN),
        "data-science/model-drafts",
        False,
    ),
    Shipped(
        "github",
        "github",
        lambda url: GitHubAdapter(host_url=url, private_token=TOKEN),
        "g",
        False,
    ),
    Shipped(
        "github-user",
        "github",
        lambda url: GitHubAdapter(host_url=url, private_token=TOKEN),
        "g",
        True,
    ),
]


def _http(status: int, payload: object) -> bytes:
    body = json.dumps(payload).encode()
    reason = {200: "OK", 201: "Created", 404: "Not Found"}[status]
    return (
        f"HTTP/1.1 {status} {reason}\r\nContent-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n"
    ).encode() + body


def serve(router: Router) -> Callable[[bytes], bytes]:
    """The reply function ``loopback.serving_raw`` takes: each request answered by ``router``."""

    def reply(request: bytes) -> bytes:
        method, path, _ = request.split(b"\r\n", 1)[0].decode("latin-1").split(" ", 2)
        status, payload = router(method, path)
        return _http(status, payload)

    return reply
