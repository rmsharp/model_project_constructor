"""Keep every shipped Typer app from printing its parameters' values in a traceback.

Typer 0.16 to 0.22 render an uncaught exception with ``rich.traceback`` and, by default, a
*locals* box under every frame: ``db_url = 'postgresql://bob:<password>@...'`` in the data agent,
``private_token = 'glpat-...'`` in the website agent. ``typer>=0.16.0`` admits those releases.
0.23.0 turned the default off and every release since, through 0.27.2, keeps it off, and
``uv.lock`` pins 0.24.1, so CI and an ordinary install never see it: only an environment resolved
outside the lock does (found by Session 271's review, widened and measured by Session 272, which
also found that the website agent's ``--private-token`` leaks the same way).

Two arms, because neither can do the other's job.

* **Structural.** Every Typer app built under ``src/``, ``packages/`` and ``scripts/`` (the trees
  CI lints) must pass ``pretty_exceptions_show_locals=False`` as a literal. It fails on the
  unfixed code under ANY installed Typer, the lock's included, which is what holds the fix in CI.
  It sees an app built the ordinary way: ``Typer(...)`` or ``typer.Typer(...)``, either under an
  ``import ... as`` alias, a class that subclasses ``Typer``, and ``typer.run(...)``, which builds
  a default app. It does NOT see an alias made by assignment, ``functools.partial``, ``getattr``
  or ``app.pretty_exceptions_show_locals = True`` after construction (each reproduced by Session
  272's review), nor an app outside those trees, and a factory taking ``**kwargs`` fails closed.
  It guards against the accidental fourth app, not an adversary, and it fails if a known app is
  no longer found rather than passing for want of anything to check.
* **Behavioural.** Run each real app with ``python -m``, force an uncaught exception while the
  secret is still a local, and require no locals box and no secret in the output. Under the lock
  this passes with or without the fix, which is the finding: it can only fail where Typer older
  than 0.23.0 is installed. It requires the run to have reached the provoked statement, by the
  exception it names and the app's own ``run`` frame: a run that dies earlier, at an import or on
  a usage error, leaks nothing and would otherwise pass (reproduced on unfixed code under Typer
  0.22.0 with an import blocked, where all three arms passed).

The output is read with the terminal styling removed. Typer forces terminal output when
``GITHUB_ACTIONS``, ``FORCE_COLOR`` or ``PY_COLORS`` is set, which CI does, and a style code then
falls inside the traceback title and the box title (measured), so the arms fail there whenever
the file runs, alone or in the suite, unless it is stripped.
"""

from __future__ import annotations

import ast
import os
import pathlib
import re
import subprocess
import sys
from collections.abc import Callable

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE_ROOTS = [REPO_ROOT / "src", REPO_ROOT / "packages", REPO_ROOT / "scripts"]
SKIPPED_PARTS = {".venv", "venv", "node_modules", "build", "dist", "site-packages", "__pycache__"}

# The three apps that exist today, named so a search that stops finding one fails instead of
# passing for want of anything to check.
KNOWN_APP_FILES = {
    "packages/data-agent/src/model_project_constructor_data_agent/cli.py",
    "src/model_project_constructor/agents/intake/cli.py",
    "src/model_project_constructor/agents/website/cli.py",
}

KEYWORD = "pretty_exceptions_show_locals"
# The box title in rich's Unicode and ASCII renderings: a child whose stdout cannot encode
# U+2500 draws it with hyphens, which a Unicode-only pattern would miss.
LOCALS_BOX = re.compile(r"[─-]+ locals [─-]+")
ANSI_STYLE = re.compile(r"\x1b\[[0-9;]*m")
PASSWORD = "Zq7Lm9Xt"
TOKEN = "glpat-TOKENSECRET9f3k"


def _source_files() -> list[pathlib.Path]:
    return sorted(
        path
        for root in SOURCE_ROOTS
        for path in root.rglob("*.py")
        if path.is_file() and not SKIPPED_PARTS & set(path.relative_to(REPO_ROOT).parts)
    )


def _scan() -> tuple[set[str], list[str]]:
    """The files that build a Typer app, and one message per app that lacks the setting."""
    built_in: set[str] = set()
    problems: list[str] = []
    for path in _source_files():
        label = str(path.relative_to(REPO_ROOT))
        tree = ast.parse(path.read_bytes(), filename=str(path))

        constructors = {"Typer"}  # names that call the class: ``Typer``, or ``... as T``
        modules = {"typer"}  # names that hold the module: ``typer``, or ``import typer as t``
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "typer":
                constructors |= {a.asname or a.name for a in node.names if a.name == "Typer"}
            elif isinstance(node, ast.Import):
                modules |= {a.asname for a in node.names if a.name == "typer" and a.asname}

        def names_the_class(expr: ast.expr, constructors: set[str] = constructors) -> bool:
            return (isinstance(expr, ast.Attribute) and expr.attr == "Typer") or (
                isinstance(expr, ast.Name) and expr.id in constructors
            )

        for node in ast.walk(tree):
            where = f"{label}:{getattr(node, 'lineno', 0)}"
            if isinstance(node, ast.ClassDef) and any(names_the_class(b) for b in node.bases):
                built_in.add(label)
                problems.append(f"{where} subclasses Typer: its construction is not seen")
            elif isinstance(node, ast.Call) and names_the_class(node.func):
                built_in.add(label)
                if not any(
                    kw.arg == KEYWORD
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value is False
                    for kw in node.keywords
                ):
                    problems.append(f"{where} Typer(...) without {KEYWORD}=False")
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "run"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in modules
            ):
                built_in.add(label)
                problems.append(f"{where} typer.run(...) builds a default app: use a Typer app")
    return built_in, problems


def test_every_known_app_is_found() -> None:
    built_in, _ = _scan()
    assert built_in >= KNOWN_APP_FILES


def test_every_typer_app_hides_locals_in_a_traceback() -> None:
    _, problems = _scan()
    assert not problems, (
        f"{problems}: Typer 0.16 to 0.22 print every parameter's value (an address with its "
        "password, a token) in an uncaught exception's traceback unless "
        f"{KEYWORD}=False"
    )


def _environment() -> dict[str, str]:
    """The ambient environment with the switches that change the rendering pinned.

    ``TYPER_STANDARD_TRACEBACK`` turns the rich traceback off, so a run would pass for a reason
    that has nothing to do with the app's configuration. ``TERMINAL_WIDTH`` overrides ``COLUMNS``
    and a narrow one cuts the traceback title in two. The child's streams are forced to UTF-8
    because rich draws the box with hyphens where it cannot encode U+2500.
    """
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in {"TYPER_STANDARD_TRACEBACK", "_TYPER_STANDARD_TRACEBACK", "TERMINAL_WIDTH"}
    }
    env["COLUMNS"] = "250"  # a wide box never wraps a secret across two lines
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def _run(argv: list[str], *, raises: list[str]) -> str:
    """Run one app; return what it printed, styling removed, once it is shown to have failed
    where it was meant to: the named exception, raised from the app's own ``run`` frame."""
    result = subprocess.run(
        [sys.executable, "-m", *argv],
        capture_output=True,
        encoding="utf-8",  # the child is forced to UTF-8 below; the parent's locale may not be
        errors="replace",
        check=False,
        env=_environment(),
        stdin=subprocess.DEVNULL,
        timeout=120,
    )
    output = ANSI_STYLE.sub("", result.stdout + result.stderr)
    assert result.returncode == 1, output
    assert "Traceback (most recent call last)" in output, output
    assert re.search(r"cli\.py:\d+ in run\b", output), output
    for expected in raises:
        assert expected in output, output
    return output


def _data_agent(files: dict[str, pathlib.Path]) -> list[str]:
    return [
        "model_project_constructor_data_agent",
        "run",
        "-r",
        str(files["json"]),
        "-o",
        str(files["out"]),
        "--fake-llm",
        "--db-url",
        f"postgresql://bob:{PASSWORD}@db.internal/claims",
    ]


def _website(files: dict[str, pathlib.Path]) -> list[str]:
    return [
        "model_project_constructor.agents.website",
        "--intake",
        str(files["json"]),
        "--data",
        str(files["json"]),
        "--private-token",
        TOKEN,
    ]


def _intake(files: dict[str, pathlib.Path]) -> list[str]:
    return ["model_project_constructor.agents.intake", "--fixture", str(files["yaml"])]


@pytest.fixture
def malformed(tmp_path: pathlib.Path) -> dict[str, pathlib.Path]:
    json_file = tmp_path / "malformed.json"
    json_file.write_text("{ not json")
    yaml_file = tmp_path / "malformed.yaml"
    yaml_file.write_text(": : not yaml [")
    return {"json": json_file, "yaml": yaml_file, "out": tmp_path / "out.json"}


# An intake run takes no secret, so for it the absence of the box is the whole check.
@pytest.mark.parametrize(
    ("build", "raises", "secret"),
    [
        pytest.param(_data_agent, ["JSONDecodeError"], PASSWORD, id="data-agent-db-url"),
        pytest.param(_website, ["ValidationError", "json_invalid"], TOKEN, id="website-token"),
        pytest.param(_intake, ["ParserError"], None, id="intake-no-secret"),
    ],
)
def test_an_uncaught_error_prints_no_secret_and_no_locals_box(
    malformed: dict[str, pathlib.Path],
    build: Callable[[dict[str, pathlib.Path]], list[str]],
    raises: list[str],
    secret: str | None,
) -> None:
    output = _run(build(malformed), raises=raises)
    if secret is not None:
        assert secret not in output
    assert not LOCALS_BOX.search(output)
