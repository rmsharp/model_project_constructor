"""Enforce §7 of architecture-plan.md: the Data Agent knows nothing about IntakeReport.

AST-walks every module under the standalone package
``packages/data-agent/src/model_project_constructor_data_agent/`` and fails
the build if any ``import`` or ``from ... import ...`` statement references
the intake schema. This is the structural guarantee that lets the Data Agent
be reused standalone (constraint C4) and that lets its standalone wheel be
distributed without pulling in the orchestrator.

The main ``model_project_constructor.agents.data.*`` modules are thin
re-export shims and are also walked here as defense in depth — a shim that
accidentally started importing ``IntakeReport`` would defeat the guarantee.
"""

from __future__ import annotations

import ast
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
STANDALONE_DIR = (
    REPO_ROOT / "packages" / "data-agent" / "src" / "model_project_constructor_data_agent"
)
SHIM_DIR = REPO_ROOT / "src" / "model_project_constructor" / "agents" / "data"

FORBIDDEN_SUBSTRINGS = (
    "IntakeReport",
    "schemas.v1.intake",
    "intake_report",
)


def _walk_imports(root: pathlib.Path) -> list[str]:
    files = sorted(root.rglob("*.py"))
    assert files, f"expected python files under {root}"

    offenders: list[str] = []
    for path in files:
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imported = ast.unparse(node)
                for forbidden in FORBIDDEN_SUBSTRINGS:
                    if forbidden in imported:
                        offenders.append(
                            f"{path.relative_to(REPO_ROOT)}: {imported!r} "
                            f"contains forbidden token {forbidden!r}"
                        )
    return offenders


def test_standalone_package_does_not_import_intake_report() -> None:
    offenders = _walk_imports(STANDALONE_DIR)
    assert not offenders, (
        "Standalone Data Agent decoupling violation — the following imports "
        "reference the intake schema, breaking §7 of architecture-plan.md:\n  - "
        + "\n  - ".join(offenders)
    )


def test_main_package_data_agent_shim_does_not_import_intake_report() -> None:
    offenders = _walk_imports(SHIM_DIR)
    assert not offenders, (
        "Main-package Data Agent shim decoupling violation — the following "
        "imports reference the intake schema, breaking §7 of architecture-plan.md:\n  - "
        + "\n  - ".join(offenders)
    )


def _imports_of_the_main_package(root: pathlib.Path) -> list[str]:
    """Every import under ``root`` of ``model_project_constructor`` or one of its submodules.

    The package's own name, ``model_project_constructor_data_agent``, is a different top-level
    module and is not one. Relative imports stay inside the package they are written in.
    """
    offenders: list[str] = []
    for path in sorted(root.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules = [node.module]
            else:
                continue
            for module in modules:
                if module == "model_project_constructor" or module.startswith(
                    "model_project_constructor."
                ):
                    offenders.append(f"{path.relative_to(root)}: {ast.unparse(node)!r}")
    return offenders


def test_standalone_package_does_not_import_the_main_package() -> None:
    """Session 279. The standalone wheel's ``pyproject.toml`` does not depend on the main
    distribution, so an import of it would raise on an install of the wheel alone, and every
    other test here runs with both installed. ``db.safe_class_name`` is a copy of
    ``orchestrator.logging._class_name`` for this reason; this is what keeps the next copy from
    being an import."""
    offenders = _imports_of_the_main_package(STANDALONE_DIR)
    assert not offenders, (
        "The standalone Data Agent imports the main package, which its wheel does not "
        "depend on:\n  - " + "\n  - ".join(offenders)
    )


def test_the_main_package_import_check_can_fail(tmp_path: pathlib.Path) -> None:
    """The arm above passes today; this holds that it could not pass for the wrong reason."""
    (tmp_path / "bad.py").write_text(
        "from model_project_constructor.orchestrator.logging import _class_name\n"
        "import model_project_constructor.schemas\n"
        "import model_project_constructor\n"
    )
    (tmp_path / "fine.py").write_text(
        "from model_project_constructor_data_agent.db import safe_message\n"
        "import model_project_constructor_data_agent\n"
        "from . import db\n"
        "import sqlalchemy\n"
    )
    assert _imports_of_the_main_package(tmp_path) == [
        "bad.py: 'from model_project_constructor.orchestrator.logging import _class_name'",
        "bad.py: 'import model_project_constructor.schemas'",
        "bad.py: 'import model_project_constructor'",
    ]
