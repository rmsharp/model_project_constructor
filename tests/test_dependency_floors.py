"""Hold the declared ``typer`` floor at, or above, the release the CLIs were measured to need.

``uv.lock`` resolves a Typer far newer than any floor, so CI and ordinary installs never exercise
the declared minimum. That is how ``typer>=0.12`` stayed in both package files while no Typer below
0.16.0 can serve these CLIs beside the Click an installer resolves today (found by Session 267's
review, measured by Session 268). On Python 3.11 to 3.13, 0.12.0 to 0.12.3 cannot build them
(``X | None`` annotations); on 3.14 they build and then fail like the rest. Every release from
0.12.4 to 0.15.3 builds them and then crashes ``--help`` under Click 8.2 or later, and 0.15.4 pins
``click<8.2``, so it cannot be installed beside one.

``TYPER_MEASURED_FLOOR`` is the lowest release for which all three shipped CLIs (intake, website,
data agent) build, render ``--help`` for the app and for every command, and pass their CLI tests
beside Click 8.2 or later. Measured for 0.16.0: the real console scripts render ``--help`` on every
pairing of Python 3.11 to 3.14 with Click 8.2.0 to 8.5.0 (all ten releases), and the 69 CLI tests
pass on all ten Clicks on Python 3.11 and on Click 8.5.0 on 3.12 to 3.14. The figures and the
wrong claims they replaced are in the CHANGELOG entries for Session 268.

What this reads: the dependency lists of the root ``pyproject.toml`` and of every workspace member
it names, plus ``[tool.uv] override-dependencies``. Each list is judged on its own, because each is
a separate install path; within one list the highest lower bound among its Typer requirements
counts. What it does not do: interpret environment markers, direct URLs or sibling distributions
such as ``typer-slim``, or tell whether a floor is TRUE; it only keeps a declaration from drifting
below the number. Nothing enforces the constant either (this repository declares no quality gate
that would hold it): re-measure before changing it, and change it only upward, on evidence, because
a floor that can be lowered under pressure is a suggestion (SAFEGUARDS.md, Blast Radius).
"""

from __future__ import annotations

import pathlib
import tomllib
from typing import Any

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

TYPER_MEASURED_FLOOR = Version("0.16.0")

# The two files that declare Typer today, named so a parse that finds nothing fails instead of
# passing for want of anything to check.
ROOT_PYPROJECT = REPO_ROOT / "pyproject.toml"
DATA_AGENT_PYPROJECT = REPO_ROOT / "packages" / "data-agent" / "pyproject.toml"

_LOWER_BOUND_OPERATORS = {">=", ">", "~=", "==", "==="}


def _label(pyproject: pathlib.Path) -> str:
    return str(pyproject.relative_to(REPO_ROOT))


def _load(pyproject: pathlib.Path) -> dict[str, Any]:
    return tomllib.loads(pyproject.read_text())


def _workspace_pyprojects() -> list[pathlib.Path]:
    """The root file and the ``pyproject.toml`` of every member the root's workspace names."""
    uv: dict[str, Any] = _load(ROOT_PYPROJECT).get("tool", {}).get("uv", {})
    workspace: dict[str, Any] = uv.get("workspace", {})
    excluded = {p for pattern in workspace.get("exclude", []) for p in REPO_ROOT.glob(pattern)}
    members = {
        p
        for pattern in workspace.get("members", [])
        for p in REPO_ROOT.glob(pattern)
        if p not in excluded and (p / "pyproject.toml").is_file()
    }
    return [ROOT_PYPROJECT, *sorted(m / "pyproject.toml" for m in members)]


WORKSPACE_PYPROJECTS = _workspace_pyprojects()


def _requirement_lists(pyproject: pathlib.Path) -> dict[str, list[str]]:
    """Each dependency list the file declares, by a label naming where it sits."""
    data = _load(pyproject)
    project: dict[str, Any] = data.get("project", {})
    uv: dict[str, Any] = data.get("tool", {}).get("uv", {})
    lists: dict[str, list[Any]] = {"[project].dependencies": project.get("dependencies", [])}
    for name, items in project.get("optional-dependencies", {}).items():
        lists[f"[project.optional-dependencies].{name}"] = items
    for name, items in data.get("dependency-groups", {}).items():
        lists[f"[dependency-groups].{name}"] = items
    lists["[tool.uv].dev-dependencies"] = uv.get("dev-dependencies", [])
    lists["[tool.uv].override-dependencies"] = uv.get("override-dependencies", [])
    # A dependency group may also hold {include-group = ...} tables; only strings are requirements.
    return {label: [i for i in items if isinstance(i, str)] for label, items in lists.items()}


def _lower_bound(requirement: Requirement) -> Version | None:
    bounds = [
        Version(spec.version.removesuffix(".*"))
        for spec in requirement.specifier
        if spec.operator in _LOWER_BOUND_OPERATORS
    ]
    return max(bounds, default=None)


def _typer_floors(pyproject: pathlib.Path) -> dict[str, Version | None]:
    """For each list that names Typer: the highest lower bound its Typer requirements give."""
    floors: dict[str, Version | None] = {}
    for label, items in _requirement_lists(pyproject).items():
        bounds: list[Version] = []
        named = False
        for text in items:
            requirement = Requirement(text)
            if canonicalize_name(requirement.name) == "typer":
                named = True
                bound = _lower_bound(requirement)
                if bound is not None:
                    bounds.append(bound)
        if named:
            floors[label] = max(bounds, default=None)
    return floors


@pytest.mark.parametrize("pyproject", [ROOT_PYPROJECT, DATA_AGENT_PYPROJECT], ids=_label)
def test_the_package_file_declares_typer(pyproject: pathlib.Path) -> None:
    declared = [label for label in _typer_floors(pyproject) if "override" not in label]
    assert declared, (
        f"{_label(pyproject)} declares no Typer requirement, so the floor check below would pass "
        f"for want of anything to check; if Typer moved, move this test with it"
    )


@pytest.mark.parametrize("pyproject", WORKSPACE_PYPROJECTS, ids=_label)
def test_every_declared_typer_floor_is_at_least_the_measured_one(pyproject: pathlib.Path) -> None:
    below = [
        f"{label} gives {floor or 'no lower bound'}"
        for label, floor in _typer_floors(pyproject).items()
        if floor is None or floor < TYPER_MEASURED_FLOOR
    ]
    assert not below, (
        f"{_label(pyproject)} declares a Typer floor below {TYPER_MEASURED_FLOOR}, the lowest "
        f"release measured to build these CLIs and render --help beside Click 8.2 or later: "
        + "; ".join(below)
        + ". Raise it, or re-measure before lowering TYPER_MEASURED_FLOOR (see this module's "
        "docstring)."
    )
