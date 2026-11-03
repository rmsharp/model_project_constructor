"""The notebooks the website agent writes, rendered by the real Quarto.

``test_quarto_markup.py`` holds the neutraliser to a model of what Quarto acts on. This file
checks the neutraliser against the tool: the same text goes through the real renderers, then
through ``quarto render``, and the evidence is a side effect (a file the payload writes, an
environment value or a file's content turning up in the page), not a pattern match. It also
checks the model against the tool, for the constructs in the payloads below and no others: the
model must report every one of them in the unneutralised notebook, where the tool acts on it.

It needs Quarto and a Python that can start its Jupyter engine (``ipykernel``, ``nbclient``,
``nbformat`` and ``pyyaml``), so it is skipped where there is none. CI has neither. The fixture
tries ``QUARTO_PYTHON``, then the interpreter running pytest, then ``python3`` and ``python`` on
``PATH``; ``uv run pytest`` puts this repository's environment first on ``PATH``, which has none
of the four packages, so a plain run skips unless ``QUARTO_PYTHON`` names a Python that has
them, and a machine whose ``python3`` has them runs the tests whatever else is set. The tool is
the only judge of what Quarto does, so a machine that has it should run this before changing the
neutraliser; a render takes a few seconds, and the module renders fourteen. It is
three tests on purpose: each skip is counted, and nine parametrised ones would move the suite's
standing skip count for no gain.

A regression shows up as a side effect, or as Quarto refusing the notebook: payloads planted in
every field do not always make one valid YAML document once they act (a stray ``---`` opens a
block that swallows the text after it), and the tests that use the fixture then error. Either is
a red test; the control below is where each construct is shown to act, one at a time.
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
from tests.agents.website.quarto_constructs import constructs

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"

# Every construct that ran when Session 295 rendered it, each with an effect that cannot happen
# by accident. ``QPROBE`` is set in the child's environment; ``secret.txt``, ``f.lua``,
# ``header.html`` and ``after.html`` are written beside the notebook. Three metadata blocks, each
# with its own effect; the second and third are the ones a comment hides from a line-by-line
# reader. They close with ``---``, not ``...``: Quarto strips only a closing ``---`` before it
# joins the blocks of a document, so a ``...`` closer followed by another block makes the render
# fail with "expected a single document" (measured with 1.7.33), which would hide the effect. A
# ``...`` closer that ends the last block acts, and the control below plants one.
PAYLOAD = (
    "Visible start.\n\n"
    "```{python}\nopen('ran_cell.txt', 'w').write('x')\n```\n\n"
    "``` {python}\nopen('ran_spaced_cell.txt', 'w').write('x')\n```\n\n"
    "Inline `{python} open('ran_inline.txt', 'w').write('x')` here.\n\n"
    "Env {{< env QPROBE >}} here.\n\n"
    "{{< include secret.txt >}}\n\n"
    "---\nfilters:\n  - f.lua\n---\n\n"
    "---<!---->\ninclude-in-header: header.html\n---\n\n"
    "-<!-- c -->--\ninclude-after-body: after.html\n---\n\n"
    "Visible end."
)

# The renderers strip most fields after neutralising them, which moves a block that began behind
# whitespace to the start of a line; and 06 puts a backtick in front of the review cadence, which
# turns two ticks into a fence. Neither text can sit in the middle of a field, so each is its own
# payload. The first goes into every field with a ``---`` closer (a ``...`` closer on several
# blocks would make an unneutralised render fail instead of act, as above); the control plants it
# in a single field, once with each closer.
PAYLOAD_BEHIND_A_SPACE = " ---\nfilters:\n  - f.lua\n---"
PAYLOAD_TWO_TICKS = "`` {python}\nopen('ran_ticks.txt', 'w').write('x')\n``"
# 05 writes the model type as a code span, and it holds a cell of its own, so a brace right behind
# the template's tick is an inline chunk that runs. The schema makes the model type an enum, so
# only a hand-built dict gets this far.
PAYLOAD_BRACE = "{python} open('ran_brace.txt', 'w').write('x')"

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
    named = os.environ.get("QUARTO_PYTHON")
    candidates = [
        named,
        sys.executable,
        shutil.which("python3"),
        shutil.which("python"),
    ]
    for python in candidates:
        if python and _can_start_jupyter(python):
            return {"exe": exe, "python": python}
    pytest.skip(
        "no Python with ipykernel, nbclient, nbformat and pyyaml to start Quarto's Jupyter "
        f"engine (QUARTO_PYTHON={named!r}, pytest's {sys.executable!r}, and python3 and python "
        "on PATH were tried; set QUARTO_PYTHON to one that has them)"
    )


def _plant_everywhere(text: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Both fixture reports with ``text`` in every string at every depth."""

    def plant(value: Any) -> Any:
        if isinstance(value, str):
            return text
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


def _planted() -> tuple[dict[str, Any], dict[str, Any]]:
    return _plant_everywhere(PAYLOAD)


def _planted_behind_a_space_and_two_ticks() -> tuple[dict[str, Any], dict[str, Any]]:
    intake, data = _plant_everywhere(PAYLOAD_BEHIND_A_SPACE)
    # A hand-built dict: the schema allows four words here, and the renderer takes whatever it is
    # given. This is the one place a template backtick starts a line.
    intake["value_measurement_plan"]["review_cadence"] = PAYLOAD_TWO_TICKS
    intake["model_solution"]["model_type"] = PAYLOAD_BRACE
    return intake, data


def _render(quarto: dict[str, str], directory: Path, qmd: str) -> tuple[str, set[str]]:
    """Render ``qmd`` in ``directory``; return the page text and which effects happened."""

    directory.mkdir(parents=True)
    (directory / "secret.txt").write_text("SECRET456\n")
    (directory / "header.html").write_text("<p>HDRMARK789</p>\n")
    (directory / "after.html").write_text("<p>AFTERMARK789</p>\n")
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
    for marker, name in (
        ("SECRET123", "env"),
        ("SECRET456", "include"),
        ("HDRMARK789", "header"),
        ("AFTERMARK789", "after"),
    ):
        if marker in page:
            effects.add(name)
    return page, effects


@pytest.fixture(scope="module")
def neutralised(quarto: dict[str, str], tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """Each real renderer's output for each payload, rendered by the tool."""

    root = tmp_path_factory.mktemp("neutralised")
    out: dict[str, Any] = {}
    for label, (intake, data) in (
        ("everything", _planted()),
        ("behind_a_space", _planted_behind_a_space_and_two_ticks()),
    ):
        for name, render in RENDERERS.items():
            out[f"{label}/{name}"] = _render(quarto, root / label / name, render(intake, data))
    return out


class TestTheRealQuartoRunsNothingFromReportText:
    def test_no_effect_in_any_notebook(self, neutralised: dict[str, Any]) -> None:
        assert {name: effects for name, (_, effects) in neutralised.items()} == {
            name: set() for name in neutralised
        }

    def test_the_reader_still_sees_the_text_that_was_written(
        self, neutralised: dict[str, Any]
    ) -> None:
        for name, (page, _) in neutralised.items():
            if not name.startswith("everything/"):
                continue
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
        """The control: without it the payloads run in the notebook with no cell of its own
        (01), in the one that has one (02) and in 06. If this ever stops holding, the checks
        above can no longer fail and prove nothing. The model of Quarto must also report every
        construct that acted, so a blind model cannot make the other tests pass."""

        monkeypatch.setattr(templates, "neutralise_report", lambda value: value)
        intake, data = _planted()
        raw_01 = RENDERERS["01"](intake, data)
        raw_02 = RENDERERS["02"](intake, data)
        _, effects_01 = _render(quarto, tmp_path / "01", raw_01)
        _, effects_02 = _render(quarto, tmp_path / "02", raw_02)
        everything = {
            "ran_cell.txt",
            "ran_spaced_cell.txt",
            "ran_inline.txt",
            "ran_filter.txt",
            "env",
            "include",
            "header",
            "after",
        }
        assert effects_01 == everything
        assert effects_02 == everything
        for raw in (raw_01, raw_02):
            kinds = {found.kind for found in constructs(raw)}
            assert kinds == {"fence", "inline_chunk", "shortcode", "metadata_block"}

        # One field behind a space, so the block starts a line once the renderer strips it; the
        # closer may be either, because it is the last block in the document.
        for closer in ("---", "..."):
            behind_a_space, data = _plant_everywhere("Plain.")
            behind_a_space["business_problem"] = PAYLOAD_BEHIND_A_SPACE[:-3] + closer
            raw_space = RENDERERS["01"](behind_a_space, data)
            _, effects_space = _render(quarto, tmp_path / f"space{closer[0]}", raw_space)
            assert effects_space == {"ran_filter.txt"}, closer
            assert [c.kind for c in constructs(raw_space)] == ["metadata_block"] * 2, closer

        # The review cadence behind the template's backtick.
        ticks, data = _plant_everywhere("Plain.")
        ticks["value_measurement_plan"]["review_cadence"] = PAYLOAD_TWO_TICKS
        raw_ticks = RENDERERS["06"](ticks, data)
        _, effects_ticks = _render(quarto, tmp_path / "ticks", raw_ticks)
        assert effects_ticks == {"ran_ticks.txt"}
        assert "fence" in {c.kind for c in constructs(raw_ticks)}

        # A brace right behind the template's tick, in the notebook that has the engine on.
        brace, data = _plant_everywhere("Plain.")
        brace["model_solution"]["model_type"] = PAYLOAD_BRACE
        raw_brace = RENDERERS["05"](brace, data)
        _, effects_brace = _render(quarto, tmp_path / "brace", raw_brace)
        assert effects_brace == {"ran_brace.txt"}
        assert "inline_chunk" in {c.kind for c in constructs(raw_brace)}
