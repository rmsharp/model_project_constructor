"""The notebooks the website agent writes, rendered by the real Quarto.

``test_quarto_markup.py`` holds the neutraliser to a model of what Quarto acts on. This file
checks the model against the tool: the same text goes through the real renderers, then through
``quarto render``, and the evidence is a side effect (a file the payload writes, an environment
value or a file's content turning up in the page), not a pattern match.

It needs Quarto and a Python that can start its Jupyter engine (``ipykernel``, ``nbclient``,
``nbformat`` and ``pyyaml``), so it is skipped where there is none. CI has neither, and this
repository's own environment does not install them: point ``QUARTO_PYTHON`` at an interpreter
that has them. The tool is the only judge of what Quarto does, so a machine that has it should
run this before changing the neutraliser; a render takes a few seconds, and the module renders
six notebooks. It is three tests on purpose: each skip is counted, and nine parametrised ones
would move the suite's standing skip count for no gain.
"""

from __future__ import annotations

import html
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from model_project_constructor.agents.website import templates
from model_project_constructor.agents.website._quarto_markup import ZERO_WIDTH_SPACE
from model_project_constructor.schemas.v1.data import DataReport
from model_project_constructor.schemas.v1.intake import IntakeReport

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"

# Every construct that ran when Session 295 rendered it, each with an effect that cannot happen
# by accident. ``QPROBE`` is set in the child's environment; ``secret.txt`` and ``f.lua`` are
# written beside the notebook.
PAYLOAD = (
    "Visible start.\n\n"
    "```{python}\nopen('ran_cell.txt', 'w').write('x')\n```\n\n"
    "``` {python}\nopen('ran_spaced_cell.txt', 'w').write('x')\n```\n\n"
    "Inline `{python} open('ran_inline.txt', 'w').write('x')` here.\n\n"
    "Env {{< env QPROBE >}} here.\n\n"
    "{{< include secret.txt >}}\n\n"
    "---\nfilters:\n  - f.lua\n---\n\n"
    "Visible end."
)

RENDERERS: dict[str, Callable[[dict[str, Any], dict[str, Any]], str]] = {
    "01": lambda i, d: templates.render_qmd_business_understanding(intake=i),
    "02": lambda i, d: templates.render_qmd_data(data=d, project_slug="subrogation_model"),
    "05": lambda i, d: templates.render_qmd_initial_models(
        intake=i, project_slug="subrogation_model"
    ),
    "06": lambda i, d: templates.render_qmd_implementation_plan(intake=i, data=d),
}


def _can_start_jupyter(python: str) -> bool:
    probe = "import ipykernel, nbclient, nbformat, yaml"
    try:
        done = subprocess.run(
            [python, "-I", "-c", probe], capture_output=True, timeout=60, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0


@pytest.fixture(scope="module")
def quarto() -> dict[str, str]:
    exe = shutil.which("quarto")
    if exe is None:
        pytest.skip("quarto is not installed")
    candidates = [
        os.environ.get("QUARTO_PYTHON"),
        sys.executable,
        shutil.which("python3"),
        shutil.which("python"),
    ]
    for python in candidates:
        if python and _can_start_jupyter(python):
            return {"exe": exe, "python": python}
    pytest.skip(
        "no Python with ipykernel, nbclient, nbformat and pyyaml to start Quarto's Jupyter "
        "engine (set QUARTO_PYTHON to one)"
    )


def _planted() -> tuple[dict[str, Any], dict[str, Any]]:
    def plant(value: Any) -> Any:
        if isinstance(value, str):
            return PAYLOAD
        if isinstance(value, dict):
            return {k: plant(v) for k, v in value.items()}
        if isinstance(value, list):
            return [plant(v) for v in value]
        return value

    intake = IntakeReport.model_validate_json(
        (FIXTURES_DIR / "subrogation_intake.json").read_text()
    ).model_dump(mode="json")
    data = DataReport.model_validate_json(
        (FIXTURES_DIR / "sample_datareport.json").read_text()
    ).model_dump(mode="json")
    return plant(intake), plant(data)


def _render(quarto: dict[str, str], directory: Path, qmd: str) -> tuple[str, set[str]]:
    """Render ``qmd`` in ``directory``; return the page text and which effects happened."""

    directory.mkdir(parents=True)
    (directory / "secret.txt").write_text("SECRET456\n")
    (directory / "f.lua").write_text("io.open('ran_filter.txt', 'w'):write('x')\nreturn {}\n")
    (directory / "doc.qmd").write_text(qmd, encoding="utf-8")
    env = {**os.environ, "QUARTO_PYTHON": quarto["python"], "QPROBE": "SECRET123"}
    done = subprocess.run(
        [quarto["exe"], "render", "doc.qmd", "--to", "html"],
        cwd=directory,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert done.returncode == 0, done.stderr[-2000:]
    page = (directory / "doc.html").read_text(encoding="utf-8")
    effects = {path.name for path in directory.glob("ran_*.txt")}
    if "SECRET123" in page:
        effects.add("env")
    if "SECRET456" in page:
        effects.add("include")
    return page, effects


@pytest.fixture(scope="module")
def neutralised(quarto: dict[str, str], tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    intake, data = _planted()
    root = tmp_path_factory.mktemp("neutralised")
    return {
        name: _render(quarto, root / name, render(intake, data))
        for name, render in RENDERERS.items()
    }


class TestTheRealQuartoRunsNothingFromReportText:
    def test_no_effect_in_any_notebook(self, neutralised: dict[str, Any]) -> None:
        assert {name: effects for name, (_, effects) in neutralised.items()} == {
            name: set() for name in RENDERERS
        }

    def test_the_reader_still_sees_the_text_that_was_written(
        self, neutralised: dict[str, Any]
    ) -> None:
        for name, (page, _) in neutralised.items():
            text = html.unescape(page).replace(ZERO_WIDTH_SPACE, "")
            assert "Visible start." in text, name
            assert "Visible end." in text, name
            # The inline chunk is shown as the code it was, not run and not dropped.
            assert "{python} open('ran_inline.txt', 'w').write('x')" in text, name
            assert "{{< env QPROBE >}}" in text, name

    def test_the_same_text_does_act_when_the_fix_is_switched_off(
        self,
        quarto: dict[str, str],
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The control: without it the payload runs in the notebook with no cell of its own
        (01) and in the one that has one (02). If this ever stops holding, the checks above can
        no longer fail and prove nothing."""

        monkeypatch.setattr(templates, "neutralise_report", lambda value: value)
        intake, data = _planted()
        _, effects_01 = _render(quarto, tmp_path / "01", RENDERERS["01"](intake, data))
        _, effects_02 = _render(quarto, tmp_path / "02", RENDERERS["02"](intake, data))
        everything = {
            "ran_cell.txt",
            "ran_spaced_cell.txt",
            "ran_inline.txt",
            "ran_filter.txt",
            "env",
            "include",
        }
        assert effects_01 == everything
        assert effects_02 == everything
