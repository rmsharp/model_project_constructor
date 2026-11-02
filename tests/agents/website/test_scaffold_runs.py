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

import json
import os
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import pytest
import yaml

from model_project_constructor.agents.website.agent import WebsiteAgent
from model_project_constructor.agents.website.fake_client import FakeRepoClient
from model_project_constructor.agents.website.governance_templates import (
    render_fairness_test_stub,
)
from model_project_constructor.agents.website.templates import (
    _STUB_CALLS,
    derive_project_name,
    derive_project_slug,
    render_test_stub,
)
from model_project_constructor.schemas.v1.data import DataReport
from model_project_constructor.schemas.v1.intake import IntakeReport
from model_project_constructor.schemas.v1.repo import RepoTarget

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"

# A project name is a free-form hint and nothing caps its length, so the slug can be long.
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
    # A report may validly list no evaluation metrics and no primary queries.
    empty_lists: bool = False


VARIANTS = [
    Variant("tier3-gitlab", "subrogation_intake.json", "gitlab", "Subrogation Model", False),
    Variant("tier1-github", "tier1_intake.json", "github", "Renewal Pricing Model", True),
    Variant("tier1-long-slug", "tier1_intake.json", "gitlab", LONG_NAME_HINT, True),
    Variant(
        "tier3-empty-lists",
        "subrogation_intake.json",
        "gitlab",
        "Segment Discovery",
        False,
        empty_lists=True,
    ),
    # A project name that is a Python module's name. Each fails differently without the rename:
    # ``tests`` under pytest (its own ``tests`` package wins), ``statistics`` only when the
    # package is imported with ``src`` after the standard library (pytest hides it), and
    # ``class`` as a SyntaxError in every generated test file.
    Variant("reserved-tests", "tier1_intake.json", "github", "Tests", True),
    Variant("reserved-statistics", "subrogation_intake.json", "gitlab", "Statistics", False),
    Variant("reserved-keyword", "subrogation_intake.json", "gitlab", "Class", False),
]
TIER1_GITHUB = VARIANTS[1]


@dataclass(frozen=True)
class Scaffold:
    variant: Variant
    slug: str
    files: dict[str, str]
    root: Path


def _generate(variant: Variant) -> tuple[str, dict[str, str]]:
    intake_json = json.loads((FIXTURES_DIR / variant.intake_fixture).read_text())
    data_json = json.loads((FIXTURES_DIR / "sample_datareport.json").read_text())
    if variant.empty_lists:
        intake_json["model_solution"]["evaluation_metrics"] = []
        data_json["primary_queries"] = []
    target = RepoTarget(
        host_url="https://gitlab.example.com",
        namespace="data-science/model-drafts",
        project_name_hint=variant.name_hint,
        visibility="private",
    )
    client = FakeRepoClient()
    result = WebsiteAgent(client, ci_platform=variant.ci_platform).run(
        IntakeReport.model_validate(intake_json), DataReport.model_validate(data_json), target
    )
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

    ``PYTEST_ADDOPTS`` or ``PYTHONPATH`` would leak this repository's settings and source into a
    project that must stand on its own; ``pytest-cov`` before version 7 exports ``COV_CORE_*``,
    which would start coverage inside the child; ``RUFF_*`` would configure the child's ruff;
    and ``FORCE_COLOR`` or ``PY_COLORS`` put escape codes into the output that is read below.
    """
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(
            ("PYTEST_", "COV_CORE", "COVERAGE", "PYTHON", "RUFF_", "FORCE_COLOR", "PY_COLORS")
        )
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


def _ruff(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    # ``--isolated`` ignores every ruff config file: the generated project declares none, so a
    # config in the developer's home or in a parent of the temporary directory must not apply.
    return _run(project, "-m", "ruff", *args, "--isolated", "--no-cache", ".")


def _report(done: subprocess.CompletedProcess[str]) -> str:
    return f"exit {done.returncode}\n--- stdout ---\n{done.stdout}\n--- stderr ---\n{done.stderr}"


class TestTheGeneratedProjectChecksItself:
    def test_its_own_tests_pass(self, scaffold: Scaffold) -> None:
        done = _run(scaffold.root, "-m", "pytest", "-q", "--color=no", "-p", "no:cacheprovider")
        assert done.returncode == 0, _report(done)
        # Four stub modules, two tests each; the fairness test is a ninth.
        expected = 8 + (1 if scaffold.variant.protected_attributes else 0)
        assert re.search(rf"\b{expected} passed\b", done.stdout), _report(done)
        assert "skipped" not in done.stdout and "xfail" not in done.stdout, _report(done)

    def test_ruff_check_passes(self, scaffold: Scaffold) -> None:
        done = _ruff(scaffold.root, "check")
        assert done.returncode == 0, _report(done)

    def test_ruff_format_would_change_nothing(self, scaffold: Scaffold) -> None:
        # The generated pre-commit config runs ``ruff-format``; a file it rewrites makes the
        # first commit fail.
        done = _ruff(scaffold.root, "format", "--check")
        assert done.returncode == 0, _report(done)


class TestTheNotebooksCanBeRendered:
    """The analysis notebooks are Quarto files whose Python cells Quarto runs through Jupyter.

    Nothing in the scaffold declared Jupyter, said Quarto is needed, or said how to render a
    notebook, and ``quarto render analysis`` (the directory) fails without a ``_quarto.yml``.
    It went unseen on any machine whose ``PATH`` python already had Jupyter. The packages are a
    separate ``notebooks`` extra, not ``dev``: no CI job opens a notebook, and ``dev`` is what
    every job installs.
    """

    NEEDED = {"ipykernel", "nbclient", "nbformat", "pyyaml"}

    @staticmethod
    def _extras(scaffold: Scaffold) -> dict[str, set[str]]:
        extras = tomllib.loads(scaffold.files["pyproject.toml"])["project"]["optional-dependencies"]
        return {
            name: {re.split(r"[<>=!~\[ ]", requirement)[0] for requirement in requirements}
            for name, requirements in extras.items()
        }

    @staticmethod
    def _python_notebooks(scaffold: Scaffold) -> list[str]:
        return sorted(
            path
            for path, text in scaffold.files.items()
            if path.startswith("analysis/") and path.endswith(".qmd") and "```{python}" in text
        )

    def test_there_are_notebooks_with_python_cells(self, scaffold: Scaffold) -> None:
        notebooks = self._python_notebooks(scaffold)
        assert {f"analysis/0{n}_" for n in (2, 3, 4, 5)} <= {nb[:12] for nb in notebooks}
        # The fairness audit has a Python cell too and needs the same packages.
        assert ("analysis/fairness_audit.qmd" in notebooks) == scaffold.variant.protected_attributes

    def test_the_notebooks_extra_declares_what_quarto_needs_to_run_them(
        self, scaffold: Scaffold
    ) -> None:
        extras = self._extras(scaffold)
        assert sorted(self.NEEDED - extras.get("notebooks", set())) == [], extras

    def test_the_dev_extra_stays_what_every_ci_job_installs(self, scaffold: Scaffold) -> None:
        assert self._extras(scaffold)["dev"] == {"pytest", "pytest-cov", "ruff"}

    def test_the_readme_names_quarto_and_the_command_that_renders_one_notebook(
        self, scaffold: Scaffold
    ) -> None:
        readme = scaffold.files["README.md"]
        assert "https://quarto.org/docs/get-started/" in readme
        assert "uv run --extra notebooks quarto render analysis/03_eda.qmd" in readme

    def test_every_extra_a_document_asks_for_is_declared(self, scaffold: Scaffold) -> None:
        # ``uv run --extra X`` is invisible to the ``uv run (\w+)`` check above, so a README
        # naming an extra that was later renamed would otherwise pass.
        declared = self._extras(scaffold)
        ci_file = TestTheCommandsInstallWhatTheyRun._ci_file(scaffold)
        documents = (scaffold.files["README.md"], scaffold.files[ci_file])
        asked = {name for text in documents for name in re.findall(r"--extra (\w+)", text)}
        assert asked and asked <= set(declared), (asked, declared)


class TestTheRuffVersionIsDeclaredOnce:
    """The ``pyproject.toml`` floor and the pre-commit pin come from one number.

    They were two hand-typed literals, ``ruff>=0.5`` and ``rev: v0.5.0``: the same June-2024
    release written two ways, so a fresh ``uv sync`` resolved ruff 0.17 while the hook ran 0.5.0
    (the two formatters disagree about ordinary code from 0.9 on). The comparison below is on the
    text, not on ``packaging.version``, because ``Version("0.5") == Version("0.5.0")`` is how the
    drift went unseen.
    """

    @staticmethod
    def _floor(scaffold: Scaffold) -> str:
        dev = tomllib.loads(scaffold.files["pyproject.toml"])["project"]["optional-dependencies"][
            "dev"
        ]
        (requirement,) = [r for r in dev if r.startswith("ruff")]
        match = re.fullmatch(r"ruff>=(\d+\.\d+\.\d+)", requirement)
        assert match, requirement
        return match.group(1)

    @staticmethod
    def _rev(scaffold: Scaffold) -> str:
        config = yaml.safe_load(scaffold.files[".pre-commit-config.yaml"])
        (repo,) = [r for r in config["repos"] if "ruff" in r["repo"]]
        return str(repo["rev"])

    def test_the_hook_pins_exactly_the_version_the_project_asks_for(
        self, scaffold: Scaffold
    ) -> None:
        assert self._rev(scaffold) == f"v{self._floor(scaffold)}"

    def test_both_come_from_the_one_constant(self, scaffold: Scaffold) -> None:
        from model_project_constructor.agents.website.templates import RUFF_VERSION

        assert self._floor(scaffold) == RUFF_VERSION
        assert re.fullmatch(r"\d+\.\d+\.\d+", RUFF_VERSION)

    def test_the_pin_is_not_newer_than_the_ruff_these_tests_format_with(
        self, scaffold: Scaffold
    ) -> None:
        # ``test_ruff_format_would_change_nothing`` runs this repository's locked ruff. A pin
        # above it would let the hook run a formatter no test here has seen: raise the constant
        # together with ``uv lock --upgrade-package ruff``, never ahead of it.
        from packaging.version import Version

        from model_project_constructor.agents.website.templates import RUFF_VERSION

        done = _run(scaffold.root, "-m", "ruff", "--version")
        installed = done.stdout.split()[-1]
        assert Version(installed) >= Version(RUFF_VERSION), (installed, RUFF_VERSION)


class TestTheGeneratedPackageCanBeImported:
    """The tests above run under pytest, which adds the project's own directories to the path.

    A package installed the way ``uv sync`` installs it (editable, ``src`` appended after the
    standard library) is found differently: a package named like a standard-library module
    (``statistics``) passes pytest and cannot be imported at all. This child process appends
    ``src`` last, as that install does, and imports every module the scaffold wrote.
    """

    @staticmethod
    def _modules(scaffold: Scaffold) -> list[str]:
        prefix = f"src/{scaffold.slug}/"
        names = []
        for path in scaffold.files:
            if path.startswith(prefix) and path.endswith(".py"):
                name = path.removeprefix("src/").removesuffix(".py").replace("/", ".")
                names.append(name.removesuffix(".__init__"))
        return sorted(names)

    def test_every_module_imports_with_src_after_the_standard_library(
        self, scaffold: Scaffold
    ) -> None:
        modules = self._modules(scaffold)
        assert scaffold.slug in modules and len(modules) >= 5, modules
        code = (
            "import importlib, sys\n"
            "sys.path.append('src')\n"
            f"for name in {modules!r}:\n"
            "    importlib.import_module(name)\n"
            "print('imported', len(sys.modules))\n"
        )
        done = _run(scaffold.root, "-I", "-c", code)
        assert done.returncode == 0, _report(done)

    def test_a_package_named_like_a_python_module_is_renamed_everywhere(
        self, scaffold: Scaffold
    ) -> None:
        bare = derive_project_name(scaffold.variant.name_hint).replace("-", "_")
        if not scaffold.variant.id.startswith("reserved-"):
            assert scaffold.slug == bare
            return
        assert scaffold.slug == f"{bare}_model"
        offenders = sorted(
            path
            for path, text in scaffold.files.items()
            if path.startswith(f"src/{bare}/")
            or re.search(rf"^\s*(?:from|import) {bare}[. ]", text, flags=re.MULTILINE)
        )
        assert offenders == []


class TestFormatStabilityAtEverySlugLength:
    def test_the_generated_tests_are_formatted_for_slugs_of_1_to_130_characters(
        self, tmp_path: Path
    ) -> None:
        # A string constant holding the slug was wrapped by ``ruff format`` for slugs of 77 to
        # 82 characters only, a window no hand-picked slug lands in, so sweep every length.
        for length in range(1, 131):
            slug = "m" * length
            texts = {module: render_test_stub(module, slug) for module in _STUB_CALLS}
            texts["fairness"] = render_fairness_test_stub(project_slug=slug)
            for name, text in texts.items():
                (tmp_path / f"test_{name}_{length}.py").write_text(text, encoding="utf-8")
        done = _ruff(tmp_path, "format", "--check")
        assert done.returncode == 0, _report(done)


class TestTheCommandsInstallWhatTheyRun:
    """The README, the CI file and the pre-commit hook run tools that must be installed first.

    ``pytest`` and ``ruff`` are declared under ``[project.optional-dependencies] dev``, which a
    bare ``uv sync`` does not install, so ``uv run pytest`` failed with "Failed to spawn" on any
    machine without a global ``pytest`` (it appeared to work on the Mac where Session 286 ran it
    only because a ``pytest`` from another environment was on ``PATH``). Installing needs the
    network, so what is checked here is the link between the three: every ``uv sync`` asks for
    the extra, every job installs before it runs a tool, and the extra declares every tool a
    ``uv run`` names.
    """

    SYNC = "uv sync --extra dev"

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
            assert all(line.endswith(self.SYNC) for line in syncs), (name, syncs)

    def test_the_readme_installs_before_it_runs_pytest(self, scaffold: Scaffold) -> None:
        readme = scaffold.files["README.md"]
        assert readme.index(self.SYNC) < readme.index("uv run pytest")

    def test_every_ci_job_installs_before_it_runs_a_tool(self, scaffold: Scaffold) -> None:
        document: dict[str, Any] = yaml.safe_load(scaffold.files[self._ci_file(scaffold)])
        if scaffold.variant.ci_platform == "gitlab":
            # One install in ``default.before_script`` serves every job, unless a job sets a
            # ``before_script`` of its own, which replaces it.
            before = document["default"]["before_script"]
            assert before.index(self.SYNC) > before.index("pip install uv")
            jobs = {k: v for k, v in document.items() if isinstance(v, dict) and "script" in v}
            assert set(jobs) == {"lint", "unit-tests", "model-registry-schema"}
            for name, job in jobs.items():
                assert "before_script" not in job, name
                assert any("uv run" in command for command in job["script"]), name
        else:
            jobs = document["jobs"]
            assert set(jobs) == {"lint", "test", "governance"}
            for name, job in jobs.items():
                commands = [step.get("run", "") for step in job["steps"]]
                assert self.SYNC in commands, name
                first_tool = next(i for i, c in enumerate(commands) if "uv run" in c)
                assert commands.index(self.SYNC) < first_tool, name

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
        # ``uv run python`` is the interpreter of the project's environment, not a package.
        assert {"pytest", "ruff"} <= used, used
        assert used - {"python"} <= names, (used, names)


class TestNoPlaceholderSurvives:
    @pytest.mark.parametrize("placeholder", ["<project_slug>", "<slug>"])
    def test_the_package_name_is_always_rendered(
        self, scaffold: Scaffold, placeholder: str
    ) -> None:
        # ``<query>`` and ``<query_name>`` are meant to stay: they stand for a value the
        # reader chooses. The package name is known when the file is written.
        offenders = sorted(path for path, text in scaffold.files.items() if placeholder in text)
        assert offenders == []

    def test_the_package_name_reaches_the_narratives(self, scaffold: Scaffold) -> None:
        slug = scaffold.slug
        expected = {
            "analysis/02_data.qmd": [f"# from {slug}.data_loading import load_primary"],
            "analysis/04_feature_engineering.qmd": [
                f"``src/{slug}/features.py``",
                f"# from {slug}.features import build_feature_matrix",
            ],
            "analysis/05_initial_models.qmd": [
                f"# from {slug}.models import train, predict",
                f"# from {slug}.evaluation import evaluate",
            ],
        }
        if scaffold.variant.protected_attributes:
            expected["analysis/fairness_audit.qmd"] = [
                f"`src/{slug}/fairness/`",
                f"# from {slug}.fairness.audit import subgroup_metrics",
            ]
        for path, fragments in expected.items():
            for fragment in fragments:
                assert fragment in scaffold.files[path], (path, fragment)

    def test_the_generated_tests_import_the_package_by_its_name(self, scaffold: Scaffold) -> None:
        for module in _STUB_CALLS:
            text = scaffold.files[f"tests/test_{module}.py"]
            assert text.count(f"import {scaffold.slug}.{module} as module") == 2, module


class TestTheTextDescribesWhatWasGenerated:
    """What a generated file says is there has to be there, and what is there has to be said.

    Session 286 read the scaffold's prose against its files and found it describing a project
    that had not been written yet: the README called ``governance/`` and the datasheets "Phase
    4B" work although Phase 4B had run, and ``analysis/99_extensions.qmd`` pointed at a
    ``src/fairness/`` that no project has (the package is ``src/<slug>/fairness/``, and exists
    only when the intake report declares protected attributes). Nothing compared the prose with
    the file set, so no test noticed.
    """

    def test_no_file_speaks_of_a_phase_that_has_already_run(self, scaffold: Scaffold) -> None:
        offenders = {
            path: match.group(0)
            for path, text in scaffold.files.items()
            if (match := re.search(r"Phase 4[AB]\b", text))
        }
        assert offenders == {}

    def test_the_readme_layout_lists_exactly_the_directories_that_exist(
        self, scaffold: Scaffold
    ) -> None:
        listed = re.findall(r"^- `([a-z_]+/)`", scaffold.files["README.md"], flags=re.MULTILINE)
        assert {"src/", "analysis/", "tests/", "reports/", "data/", "governance/"} <= set(listed)
        for directory in listed:
            assert any(path.startswith(directory) for path in scaffold.files), directory
        # ``queries/`` holds the report's SQL, so a report with no primary queries has none.
        has_queries = any(path.startswith("queries/") for path in scaffold.files)
        assert ("queries/" in listed) == has_queries

    def test_datasheets_are_mentioned_exactly_where_they_exist(self, scaffold: Scaffold) -> None:
        sheets = sorted(path for path in scaffold.files if path.startswith("data/datasheet_"))
        for path in ("README.md", "data/README.md"):
            assert ("datasheet" in scaffold.files[path]) == bool(sheets), path
        for sheet in sheets:
            assert Path(sheet).name in scaffold.files["data/README.md"], sheet

    def test_the_extensions_notebook_points_at_the_fairness_package_only_if_it_exists(
        self, scaffold: Scaffold
    ) -> None:
        text = scaffold.files["analysis/99_extensions.qmd"]
        package = f"src/{scaffold.slug}/fairness/"
        exists = any(path.startswith(package) for path in scaffold.files)
        assert exists == scaffold.variant.protected_attributes
        assert "src/fairness/" not in text
        assert (package in text) == exists
        assert ("analysis/fairness_audit.qmd" in text) == (
            "analysis/fairness_audit.qmd" in scaffold.files
        )

    def test_every_path_the_extensions_notebook_names_exists(self, scaffold: Scaffold) -> None:
        text = scaffold.files["analysis/99_extensions.qmd"]
        for reference in re.findall(r"`((?:src|analysis)/[^`]+)`", text):
            assert any(path.startswith(reference) for path in scaffold.files), reference


@pytest.fixture(scope="module")
def tier1() -> dict[str, str]:
    return _generate(TIER1_GITHUB)[1]


class TestTheFairnessPackage:
    def test_its_init_carries_no_noqa(self, tier1: dict[str, str]) -> None:
        # ``subgroup_metrics`` is already in ``__all__``, so the ``noqa: F401`` that used to
        # follow its import silenced nothing. ruff 0.17 reports an unused directive (RUF100),
        # which made the generated lint job fail for every project using protected attributes.
        package = next(p for p in tier1 if p.endswith("/fairness/__init__.py"))
        assert "noqa" not in tier1[package]

    def test_its_test_calls_the_stub_and_expects_it_to_raise(self, tier1: dict[str, str]) -> None:
        text = tier1["tests/test_fairness.py"]
        assert (
            "    with pytest.raises(NotImplementedError):\n"
            '        module.subgroup_metrics(None, protected_attribute="x", metric="accuracy")\n'
        ) in text
        assert "pass" not in text
