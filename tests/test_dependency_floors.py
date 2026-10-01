"""Hold the declared ``typer`` floor at, or above, the release the CLIs were measured to need.

``uv.lock`` resolves a Typer far newer than any floor, so CI and ordinary installs never exercise
the declared minimum. That is how ``typer>=0.12`` stayed in both package files while no release
below 0.12.4 can build these CLIs at all, and no release below 0.16.0 can render ``--help`` under
the Click an installer resolves today (found by Session 267's review, measured by Session 268).

``TYPER_MEASURED_FLOOR`` is the lowest release for which all three shipped CLIs (intake, website,
data agent) build, render ``--help`` for the app and for every command, and pass their CLI tests,
on Python 3.11 to 3.14 with Click 8.2.0 through 8.5.0 resolved beside it. This test cannot measure
that again: it only keeps a declaration from drifting below the number. Re-measure before changing
the constant, and change it only upward, on evidence; a floor that can be lowered under pressure is
a suggestion (SAFEGUARDS.md, Blast Radius).
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
WORKSPACE_PYPROJECTS = [ROOT_PYPROJECT, *sorted((REPO_ROOT / "packages").glob("*/pyproject.toml"))]

_LOWER_BOUND_OPERATORS = {">=", ">", "~=", "=="}


def _label(pyproject: pathlib.Path) -> str:
    return str(pyproject.relative_to(REPO_ROOT))


def _requirement_strings(pyproject: pathlib.Path) -> list[str]:
    """Every requirement the file declares, in any group a package manager reads."""
    data: dict[str, Any] = tomllib.loads(pyproject.read_text())
    project: dict[str, Any] = data.get("project", {})
    groups: list[Any] = [project.get("dependencies", [])]
    groups += project.get("optional-dependencies", {}).values()
    groups += data.get("dependency-groups", {}).values()
    groups.append(data.get("tool", {}).get("uv", {}).get("dev-dependencies", []))
    # A dependency group may also hold {include-group = ...} tables; only strings are requirements.
    return [item for group in groups for item in group if isinstance(item, str)]


def _lower_bound(requirement: Requirement) -> Version | None:
    bounds = [
        Version(spec.version.removesuffix(".*"))
        for spec in requirement.specifier
        if spec.operator in _LOWER_BOUND_OPERATORS
    ]
    return max(bounds, default=None)


def _typer_declarations(pyproject: pathlib.Path) -> list[tuple[str, Version | None]]:
    declared: list[tuple[str, Version | None]] = []
    for text in _requirement_strings(pyproject):
        requirement = Requirement(text)
        if canonicalize_name(requirement.name) == "typer":
            declared.append((text, _lower_bound(requirement)))
    return declared


@pytest.mark.parametrize("pyproject", [ROOT_PYPROJECT, DATA_AGENT_PYPROJECT], ids=_label)
def test_the_package_file_declares_typer(pyproject: pathlib.Path) -> None:
    assert _typer_declarations(pyproject), (
        f"{_label(pyproject)} declares no Typer requirement, so the floor check below would pass "
        f"for want of anything to check; if Typer moved, move this test with it"
    )


@pytest.mark.parametrize("pyproject", WORKSPACE_PYPROJECTS, ids=_label)
def test_every_declared_typer_floor_is_at_least_the_measured_one(pyproject: pathlib.Path) -> None:
    below = [
        f"{text!r} (lower bound: {bound or 'none'})"
        for text, bound in _typer_declarations(pyproject)
        if bound is None or bound < TYPER_MEASURED_FLOOR
    ]
    assert not below, (
        f"{_label(pyproject)} declares a Typer floor below {TYPER_MEASURED_FLOOR}, the lowest "
        f"release measured to build these CLIs and render --help under the Click an installer "
        f"resolves today: " + "; ".join(below) + ". Raise it, or re-measure before lowering "
        "TYPER_MEASURED_FLOOR (see this module's docstring)."
    )
