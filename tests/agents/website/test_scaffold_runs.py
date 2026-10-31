"""The project the website agent writes has to pass its own checks.

Nothing else in the suite executes a rendered scaffold. ``FakeRepoClient`` stores the file text
it is given and never looks at it, and the template tests compare strings, so a placeholder the
templates never filled in (``<project_slug>``), a test whose body is ``pass`` inside
``pytest.raises``, and a command that cannot work in a fresh checkout all passed the suite while
every generated project failed 8 of 8 of its own tests (Session 286 found it by running one).

These tests drive the real agent against the fake client, write what it committed to a directory,
and run that project's own ``pytest``, ``ruff check`` and ``ruff format --check`` in a child
process: the three things its README, its CI and its pre-commit hook run.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tomllib
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pytest

from model_project_constructor.agents.website.agent import WebsiteAgent
from model_project_constructor.agents.website.fake_client import FakeRepoClient
from model_project_constructor.agents.website.templates import (
    derive_project_name,
    derive_project_slug,
)
from model_project_constructor.schemas.v1.data import DataReport
from model_project_constructor.schemas.v1.intake import IntakeReport
from model_project_constructor.schemas.v1.repo import RepoTarget

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"

# A project name is a free-form hint and nothing caps its length, so the slug can be long. The
# generated tests must stay ``ruff format``-stable whatever its length is.
LONG_NAME_HINT = (
    "Subrogation recovery model for the total loss first notice of loss pilot programme "
    "in the southeast region"
)


@dataclass(frozen=True)
class Variant:
    """One scaffold to generate: which intake, which CI host, which project name."""

    id: str
    intake_fixture: str
    ci_platform: Literal["gitlab", "github"]
    name_hint: str
    protected_attributes: bool


VARIANTS = [
    Variant("tier3-gitlab", "subrogation_intake.json", "gitlab", "Subrogation Model", False),
    Variant("tier1-github", "tier1_intake.json", "github", "Renewal Pricing Model", True),
    Variant("tier1-long-slug", "tier1_intake.json", "gitlab", LONG_NAME_HINT, True),
]


@dataclass(frozen=True)
class Scaffold:
    variant: Variant
    slug: str
    files: dict[str, str]
    root: Path


def _generate(variant: Variant) -> tuple[str, dict[str, str]]:
    intake = IntakeReport.model_validate_json((FIXTURES_DIR / variant.intake_fixture).read_text())
    data = DataReport.model_validate_json((FIXTURES_DIR / "sample_datareport.json").read_text())
    target = RepoTarget(
        host_url="https://gitlab.example.com",
        namespace="data-science/model-drafts",
        project_name_hint=variant.name_hint,
        visibility="private",
    )
    client = FakeRepoClient()
    result = WebsiteAgent(client, ci_platform=variant.ci_platform).run(intake, data, target)
    assert result.status == "COMPLETE", result.failure_reason
    files = client.get_files(result.project_id)
    slug = derive_project_slug(derive_project_name(variant.name_hint))
    assert f"src/{slug}/__init__.py" in files
    return slug, files


@pytest.fixture(scope="module", params=VARIANTS, ids=lambda v: v.id)
def scaffold(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Scaffold:
    variant: Variant = request.param
    slug, files = _generate(variant)
    root = tmp_path_factory.mktemp(variant.id) / "project"
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return Scaffold(variant=variant, slug=slug, files=files, root=root)


def _child_env() -> dict[str, str]:
    """The environment a developer's shell would give the generated project's tools.

    The suite itself runs under ``pytest-cov``, whose ``COV_CORE_*`` variables would start
    coverage inside the child, and ``PYTEST_ADDOPTS`` or ``PYTHONPATH`` would leak this
    repository's settings and source into a project that must stand on its own.
    """
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("PYTEST_", "COV_CORE", "COVERAGE", "PYTHON"))
    }
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _run(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=project,
        env=_child_env(),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _report(done: subprocess.CompletedProcess[str]) -> str:
    return f"exit {done.returncode}\n--- stdout ---\n{done.stdout}\n--- stderr ---\n{done.stderr}"


class TestTheGeneratedProjectChecksItself:
    def test_its_own_tests_pass(self, scaffold: Scaffold) -> None:
        done = _run(scaffold.root, "-m", "pytest", "-q", "-p", "no:cacheprovider")
        assert done.returncode == 0, _report(done)
        # Four stub modules, two tests each; the fairness test is a ninth.
        expected = 8 + (1 if scaffold.variant.protected_attributes else 0)
        assert re.search(rf"\b{expected} passed\b", done.stdout), _report(done)
        assert "skipped" not in done.stdout and "xfail" not in done.stdout, _report(done)

    def test_ruff_check_passes(self, scaffold: Scaffold) -> None:
        done = _run(scaffold.root, "-m", "ruff", "check", "--no-cache", ".")
        assert done.returncode == 0, _report(done)

    def test_ruff_format_would_change_nothing(self, scaffold: Scaffold) -> None:
        # The generated pre-commit config runs ``ruff-format``; a file it rewrites makes the
        # first commit fail.
        done = _run(scaffold.root, "-m", "ruff", "format", "--check", "--no-cache", ".")
        assert done.returncode == 0, _report(done)


class TestTheCommandsInstallWhatTheyRun:
    """The README, the CI file and the pre-commit hook run tools that must be installed first.

    ``pytest`` and ``ruff`` are declared under ``[project.optional-dependencies] dev``, which a
    bare ``uv sync`` does not install, so ``uv run pytest`` failed with "Failed to spawn" on any
    machine without a global ``pytest`` (it appeared to work on the Mac where Session 286 ran it
    only because a ``pytest`` from another environment was on ``PATH``). Installing needs the
    network, so what is checked here is the link between the three: every ``uv sync`` asks for
    the extra, and the extra declares every tool a ``uv run`` names.
    """

    TOOLS = ("pytest", "ruff")

    @staticmethod
    def _ci_file(scaffold: Scaffold) -> str:
        if scaffold.variant.ci_platform == "gitlab":
            return ".gitlab-ci.yml"
        return ".github/workflows/ci.yml"

    def _documents(self, scaffold: Scaffold) -> dict[str, str]:
        names = ("README.md", self._ci_file(scaffold))
        return {name: scaffold.files[name] for name in names}

    def test_every_uv_sync_installs_the_dev_extra(self, scaffold: Scaffold) -> None:
        for name, text in self._documents(scaffold).items():
            syncs = [line.strip() for line in text.splitlines() if "uv sync" in line]
            assert syncs, f"{name} never installs the project"
            assert all(line.endswith("uv sync --extra dev") for line in syncs), (name, syncs)

    def test_a_ci_job_installs_before_it_runs_a_tool(self, scaffold: Scaffold) -> None:
        # GitLab installs once in ``default.before_script``; GitHub repeats the install in
        # every job. Either way an install line has to come before the first ``uv run``.
        lines = scaffold.files[self._ci_file(scaffold)].splitlines()
        runs = [i for i, line in enumerate(lines) if "uv run" in line]
        syncs = [i for i, line in enumerate(lines) if "uv sync" in line]
        assert runs
        assert syncs
        assert min(syncs) < min(runs)
        if scaffold.variant.ci_platform == "github":
            after_jobs = lines[lines.index("jobs:") + 1 :]
            jobs = [line for line in after_jobs if re.fullmatch(r"  [\w-]+:", line)]
            assert len(jobs) == len(syncs) == 3, (jobs, syncs)

    def test_the_dev_extra_declares_every_tool_the_commands_run(self, scaffold: Scaffold) -> None:
        declared = tomllib.loads(scaffold.files["pyproject.toml"])["project"][
            "optional-dependencies"
        ]["dev"]
        names = {re.split(r"[<>=!~\[ ]", requirement)[0] for requirement in declared}
        used = {
            tool
            for text in self._documents(scaffold).values()
            for tool in re.findall(r"uv run (\w+)", text)
        }
        assert set(self.TOOLS) <= used, used
        assert used & set(self.TOOLS) <= names, (used, names)


class TestNoPlaceholderSurvives:
    @pytest.mark.parametrize("placeholder", ["<project_slug>", "<slug>"])
    def test_the_package_name_is_always_rendered(
        self, scaffold: Scaffold, placeholder: str
    ) -> None:
        # ``<query>`` and ``<query_name>`` are meant to stay: they stand for a value the
        # reader chooses. The package name is known when the file is written.
        offenders = sorted(path for path, text in scaffold.files.items() if placeholder in text)
        assert offenders == []

    def test_the_package_name_reaches_the_commented_imports(self, scaffold: Scaffold) -> None:
        text = scaffold.files["analysis/05_initial_models.qmd"]
        assert f"# from {scaffold.slug}.models import train, predict" in text
        assert f"# from {scaffold.slug}.evaluation import evaluate" in text


@pytest.fixture(scope="module")
def tier1() -> Iterator[dict[str, str]]:
    _, files = _generate(VARIANTS[1])
    yield files


class TestTheFairnessPackage:
    def test_its_init_carries_no_noqa(self, tier1: dict[str, str]) -> None:
        # ``subgroup_metrics`` is already in ``__all__``, so the ``noqa: F401`` that used to
        # follow its import silenced nothing. ruff 0.17 reports an unused directive (RUF100),
        # which made the generated lint job fail for every project using protected attributes.
        package = next(p for p in tier1 if p.endswith("/fairness/__init__.py"))
        assert "noqa" not in tier1[package]
