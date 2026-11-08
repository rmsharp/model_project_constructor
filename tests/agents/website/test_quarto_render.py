"""The notebooks and the Markdown files the website agent writes, rendered by the real Quarto.

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
neutraliser; a render takes a few seconds, and the module renders fourteen notebooks and then the
Markdown files twice. It is six tests on purpose: each skip is counted, and nine parametrised
ones would move the suite's standing skip count for no gain, so a new group of payloads goes into
one of these and not into a test of its own. The last two (raw HTML, links, attributes and
metadata blocks nested in a container in the page; raw TeX and a fenced code block in a PDF) are
the checks of ``BACKLOG.md`` item (7)(g) and are described where they stand. The PDF test also
needs ``xelatex`` on ``PATH`` and is skipped without it.

The Markdown test needs Quarto and nothing else (a ``.md`` runs no code, so no Jupyter engine
starts). Quarto renders a ``.md`` as it does a ``.qmd`` for ``{{< env >}}``, ``{{< include >}}``
and a second ``---`` block, and nothing in a generated project stops a person asking it to:
``quarto render reports/intake_report.md`` works today, and so does a render of the directory
once anyone adds a ``_quarto.yml`` (the operator's ruling of Session 301, ``BACKLOG.md`` item
(7)(e), is to neutralise the ``.md`` files too). A ``{python}`` fence aborts the
render of a ``.md`` ("You must use the .qmd extension for documents with executable code"), so
the control below plants a payload without one.

A regression shows up as a side effect, or as Quarto refusing the notebook: payloads planted in
every field do not always make one valid YAML document once they act (a stray ``---`` opens a
block that swallows the text after it), and the tests that use the fixture then error. Either is
a red test; the control below is where each construct is shown to act, one at a time.
"""

from __future__ import annotations

import base64
import html
import os
import re
import shutil
import struct
import subprocess
import sys
import zlib
from collections.abc import Callable
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pytest

from model_project_constructor.agents.website import governance_templates, templates
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


# --- The Markdown files -----------------------------------------------------------------------

# ``PAYLOAD`` without the two fences, which abort the render of a ``.md`` (a control that fails to
# render shows nothing). The inline chunk stays as it is: it is literal in a ``.md``.
PAYLOAD_MARKDOWN = (
    "Visible start.\n\n"
    "Inline `{python} open('ran_inline.txt', 'w').write('x')` here.\n\n"
    "Env {{< env QPROBE >}} here.\n\n"
    "{{< include secret.txt >}}\n\n"
    "---\nfilters:\n  - f.lua\n---\n\n"
    "---<!---->\ninclude-in-header: header.html\n---\n\n"
    "-<!-- c -->--\ninclude-after-body: after.html\n---\n\n"
    "Visible end."
)

# What the control must see act, and the files in which at least one of them must.
EVERY_EFFECT = {"ran_filter.txt", "env", "include", "header", "after"}


def _markdown_files(payload: str) -> dict[str, str]:
    """Every ``.md`` the agent writes for a tier 1 model that touches consumers, with ``payload``
    in every string of both reports (the tier itself is kept valid, or half the files would not
    be written)."""

    intake, data = _plant_everywhere(payload)
    intake["governance"] = {
        **intake["governance"],
        "risk_tier": "tier_1_critical",
        "affects_consumers": True,
        "uses_protected_attributes": True,
    }
    files = {
        **templates.build_base_files(
            intake=intake, data=data, project_name="subrogation-model", project_slug="subrogation"
        ),
        **governance_templates.build_governance_files(
            intake=intake, data=data, project_name="subrogation-model", project_slug="subrogation"
        ),
    }
    return {path: text for path, text in files.items() if path.endswith(".md")}


def _render_markdown(
    exe: str, root: Path, files: dict[str, str]
) -> tuple[dict[str, str], set[str]]:
    """Write ``files`` under ``root`` and ask Quarto to render them the two ways a person can:
    the project (a bare ``_quarto.yml``, which a team adds the day it wants ``quarto render`` to
    work on the directory) and each file by name (the one way that works with no ``_quarto.yml``,
    and the only one that reaches the READMEs). Returns each page by its source path and the
    effects that happened."""

    root.mkdir(parents=True)
    (root / "_quarto.yml").write_text("project:\n  type: default\n")
    for path, text in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    for directory in {(root / path).parent for path in files}:
        (directory / "secret.txt").write_text("SECRET456\n")
        (directory / "header.html").write_text("<p>HDRMARK789</p>\n")
        (directory / "after.html").write_text("<p>AFTERMARK789</p>\n")
        (directory / "f.lua").write_text("io.open('ran_filter.txt', 'w'):write('x')\nreturn {}\n")
    env = {**os.environ, "QPROBE": "SECRET123"}
    # The READMEs are not part of a project render; the others are rendered by it and then once
    # more by name, which is what a person who opens one file does.
    runs = [[exe, "render", "--to", "html"]] + [
        [exe, "render", path, "--to", "html"] for path in files if path.endswith("README.md")
    ]
    for command in runs:
        done = subprocess.run(
            command, cwd=root, env=env, capture_output=True, text=True, timeout=300, check=False
        )
        assert done.returncode == 0, (command, done.stderr[-2000:])
    pages = {
        path: (root / path).with_suffix(".html").read_text(encoding="utf-8")
        for path in files
        if (root / path).with_suffix(".html").exists()
    }
    effects = {path.name for path in root.rglob("ran_*.txt")}
    for page in pages.values():
        for marker, name in (
            ("SECRET123", "env"),
            ("SECRET456", "include"),
            ("HDRMARK789", "header"),
            ("AFTERMARK789", "after"),
        ):
            if marker in page:
                effects.add(name)
    return pages, effects


def test_a_markdown_file_quarto_is_asked_to_render_runs_and_reads_nothing_from_report_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every ``.md`` the agent writes, rendered by the real tool: with the neutraliser in place
    no effect happens and the reader still sees the text that was written; with it switched off
    the same payload acts (the control, without which a clean result proves nothing)."""

    exe = shutil.which("quarto")
    if exe is None:
        pytest.skip("quarto is not installed")

    pages, effects = _render_markdown(exe, tmp_path / "neutralised", _markdown_files(PAYLOAD))
    assert effects == set()
    assert len(pages) >= 14, sorted(pages)
    for path, page in pages.items():
        text = html.unescape(page).replace(ZERO_WIDTH_SPACE, "")
        if "Visible start." in text:
            assert "{{< env QPROBE >}}" in text, path
    assert sum("Visible start." in html.unescape(page) for page in pages.values()) >= 9

    monkeypatch.setattr(templates, "neutralise_report", lambda value: value)
    monkeypatch.setattr(governance_templates, "neutralise_report", lambda value: value)
    monkeypatch.setattr(governance_templates, "neutralise_quarto_markup", lambda text: text)
    _, control = _render_markdown(exe, tmp_path / "raw", _markdown_files(PAYLOAD_MARKDOWN))
    assert control == EVERY_EFFECT


# --- Raw HTML, links, attributes and raw TeX (BACKLOG.md item (7)(g)) --------------------------

# Quarto passes more than its own constructs on. A page it renders as HTML carries raw HTML from
# the text (a script, an event handler, an iframe, a stylesheet link, a ``javascript:`` link), and
# the attributes Pandoc reads after a brace; ``embed-resources: true`` inlines the files a link, an
# import, an iframe, an embed or an image points at; and a PDF render hands raw TeX to the TeX
# engine, which reads files and runs ``kpsewhich`` (``\input{|"kpsewhich --var-value=NAME"}`` prints
# an environment value). Session 302 measured each of these with Quarto 1.7.33 and MacTeX.
#
# The evidence is parsed elements and attribute values (an escaped tag does not count), content
# that turns up in the page, and the TeX log, which names every file TeX opens and every command it
# runs. Each group is also run with the neutraliser switched off, where it must act: without that a
# clean result proves nothing.

CSS_MARK = "OUTSIDECSS314"
CSS_IMPORT_MARK = "OUTSIDEIMPORT314"
SECRET_MARK = "OUTSIDESECRET314"
NESTED_MARK = "OUTSIDENESTED314"
ENV_VALUE = "ENVPROBE777"


def _png() -> bytes:
    """A valid one-pixel PNG, built here so that its bytes are known."""

    def chunk(kind: bytes, body: bytes) -> bytes:
        checksum = zlib.crc32(kind + body)
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", checksum)

    header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(b"\x00\x10\x20\x30"))
        + chunk(b"IEND", b"")
    )


def _write_assets(directory: Path) -> None:
    """Files that are no part of a generated project: what a page would show if report text could
    point at them."""

    directory.mkdir(parents=True, exist_ok=True)
    (directory / "x.css").write_text(f".m {{ content: '{CSS_MARK}'; }}\n")
    (directory / "x2.css").write_text(f".m2 {{ content: '{CSS_IMPORT_MARK}'; }}\n")
    (directory / "nested.css").write_text(f".m3 {{ content: '{NESTED_MARK}'; }}\n")
    (directory / "secret.txt").write_text(f"{SECRET_MARK}\n")
    (directory / "pixel.png").write_bytes(_png())


# One construct to a paragraph, so that a construct which fails to act cannot hide the next. A
# mark names the construct that carried it; ``ZZMARK`` + capitals is in no page Quarto makes.
PAYLOAD_HTML = (
    "Visible start.\n\n"
    '<script>document.title="ZZMARKSCRIPT";</script>\n\n'
    '<img src="@OUT@/pixel.png" onerror="document.title=\'ZZMARKIMAGE\'">\n\n'
    '<iframe src="@OUT@/secret.txt"></iframe>\n\n'
    '<link rel="stylesheet" href="@OUT@/x.css">\n\n'
    '<style>@import url("@OUT@/x2.css");</style>\n\n'
    '<object data="@OUT@/secret.txt"></object>\n\n'
    '<embed src="@OUT@/secret.txt">\n\n'
    '<a href="javascript:ZZMARKRAWLINK">a link</a>\n\n'
    "[an inline link](javascript:ZZMARKINLINE)\n\n"
    "[a reference link][r]\n\n"
    "> [r]: javascript:ZZMARKREFERENCE\n\n"
    '## A heading {onclick="ZZMARKHEADING"}\n\n'
    '## A special one {- onclick="ZZMARKSPECIAL"}\n\n'
    '## A writer\'s character in front of the brace \u200b{onclick="ZZMARKWRITER"}\n\n'
    '[a span]{onclick="ZZMARKSPAN"}\n\n'
    '[a special span]{- onclick="ZZMARKSPANSPECIAL"}\n\n'
    "[a link with a blank](\u00a0javascript:ZZMARKBLANK)\n\n"
    "[a link with a control character](\x1fjavascript:ZZMARKCONTROL)\n\n"
    "- [r2]: javascript:ZZMARKLISTITEM\n\n"
    "[a list reference][r2]\n\n"
    "[a [nested] label]: javascript:ZZMARKNESTED\n\n"
    "[a [nested] label]\n\n"
    '::: {onclick="ZZMARKDIV"}\na div\n:::\n\n'
    '[a span]{style="background-image:url(@OUT@/x.css);--m:ZZMARKSTYLE"}\n\n'
    "~~~{=html}\n<b>ZZMARKRAWBLOCK</b>\n~~~\n\n"
    # A metadata block behind a container's prefix. Pandoc opens one there, and in a ``.qmd``
    # Quarto passes its keys on: ``css`` links (or, with ``embed-resources``, inlines) a file and
    # ``header-includes`` puts raw HTML in the page (measured with 1.7.33, in a ``.qmd`` and, for
    # ``css``, in a ``.md``).
    "> ---\n> css: @OUT@/nested.css\n> ---\n\n"
    "- a bullet\n\n  ---\n  css: @OUT@/nested.css\n  ---\n\n"
    "A note.[^n]\n\n[^n]: A footnote.\n\n    ---\n    css: @OUT@/nested.css\n    ---\n\n"
    "> ---\n> header-includes: <script>document.title='ZZMARKNESTEDHEAD'</script>\n> ---\n\n"
    # ... and in the cell of a grid table, where the markers end in the cell's padding and a ``|``.
    "+------------------------+\n| ---                    |\n| css: nested.css        |\n"
    "| ---                    |\n+------------------------+\n\n"
    "![an image](@OUT@/pixel.png)\n\n"
    "![a relative image](pixel.png)\n\n"
    # A bare carriage return, which Pandoc deletes before it reads a character: a pair with one
    # between its halves is whole again. The rules found it only after the last attack round.
    '<\rimg src="@OUT@/pixel.png" onerror="document.title=\'ZZMARKCRIMAGE\'">\n\n'
    "[a link with a carriage return]\r(javascript:ZZMARKCRLINK)\n\n"
    "-\r--\ntitle: ZZMARKCRTITLE\n---\n\n"
    "Visible end."
)

# What the unneutralised payload does in a page, per route, as the controls below must see it.
HTML_EFFECTS = {
    "<img>",
    "<iframe>",
    "<object>",
    "<embed>",
    "<link x.css>",
    "<link nested.css>",
    "<style @import>",
    "ZZMARKNESTEDHEAD",
    "ZZMARKSCRIPT",
    "ZZMARKIMAGE",
    "ZZMARKRAWLINK",
    "ZZMARKINLINE",
    "ZZMARKREFERENCE",
    "ZZMARKHEADING",
    "ZZMARKSPECIAL",
    "ZZMARKWRITER",
    "ZZMARKSPAN",
    "ZZMARKSPANSPECIAL",
    "ZZMARKBLANK",
    "ZZMARKCONTROL",
    "ZZMARKLISTITEM",
    "ZZMARKNESTED",
    "ZZMARKDIV",
    "ZZMARKSTYLE",
    "ZZMARKRAWBLOCK",
    "ZZMARKCRIMAGE",
    "ZZMARKCRLINK",
    "ZZMARKCRTITLE",
}
# With ``embed-resources`` the stylesheet link and the import become text in the page, so the
# elements are gone and their content is what shows.
EMBED_EFFECTS = (HTML_EFFECTS - {"<link x.css>", "<link nested.css>", "<style @import>"}) | {
    "inlined:css",
    "inlined:nested",
    "inlined:import",
    "inlined:secret",
    "inlined:png",
}

_MARK = re.compile(r"ZZMARK[A-Z]+")
_BLANKS = re.compile(r"[\x00-\x20\u00a0\u2000-\u200b\u3000]")


class _PageEffects(HTMLParser):
    """The elements and attributes of a rendered page that act, from the parsed page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found: set[str] = set()
        self._open: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._open.append(tag)
        if tag in ("img", "iframe", "object", "embed"):
            self.found.add(f"<{tag}>")
        for name, value in attrs:
            value = value or ""
            blank_free = _BLANKS.sub("", value).lower()
            if tag == "link" and name == "href" and "x.css" in value:
                self.found.add("<link x.css>")
            if tag == "link" and name == "href" and "nested.css" in value:
                self.found.add("<link nested.css>")
            if (
                name.startswith("on")
                or blank_free.startswith(("javascript:", "vbscript:"))
                or (name == "style" and "url(" in blank_free)
            ):
                self.found.update(_MARK.findall(value))
                self.found.add(f"{tag}@{name}")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._open:
            while self._open.pop() != tag:
                pass

    def handle_data(self, data: str) -> None:
        if not self._open:
            return
        tag = self._open[-1]
        if tag == "style" and "x2.css" in data:
            self.found.add("<style @import>")
        if tag in ("script", "b", "title"):
            self.found.update(_MARK.findall(data))


class _ShownText(HTMLParser):
    """The text a reader sees: the text nodes of the page, without scripts and styles."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style"):
            self._hidden += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self._hidden:
            self._hidden -= 1

    def handle_data(self, data: str) -> None:
        if not self._hidden:
            self.parts.append(data)


def _shown_text(page: str) -> str:
    parser = _ShownText()
    parser.feed(page)
    parser.close()
    return "".join(parser.parts).replace(ZERO_WIDTH_SPACE, "")


def _page_effects(page: str) -> set[str]:
    parser = _PageEffects()
    parser.feed(page)
    parser.close()
    # Quarto's own scripts, links and elements are no effect; the marks are what is ours.
    found = {name for name in parser.found if name.startswith(("<", "ZZMARK"))}
    # ``embed-resources`` turns a file into inline text or a data URI: look in both.
    texts = [page]
    for body in re.findall(r"data:[^\"')\s]*?;base64,([A-Za-z0-9+/=]+)", page):
        try:
            texts.append(base64.b64decode(body).decode("latin-1"))
        except ValueError:
            continue
    for label, mark in (
        ("css", CSS_MARK),
        ("nested", NESTED_MARK),
        ("import", CSS_IMPORT_MARK),
        ("secret", SECRET_MARK),
    ):
        if any(mark in text for text in texts):
            found.add(f"inlined:{label}")
    if base64.b64encode(_png()).decode() in page:
        found.add("inlined:png")
    return found


def _planted_reports(text: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Both fixture reports with ``text`` in every string, at tier 1 for a consumer-facing model
    (so every governance ``.md`` is written)."""

    intake, data = _plant_everywhere(text)
    intake["governance"] = {
        **intake["governance"],
        "risk_tier": "tier_1_critical",
        "affects_consumers": True,
        "uses_protected_attributes": True,
    }
    return intake, data


# The files rendered: four of the ``.md`` files that quote a report (the README, both reports and
# the model card) and two notebooks, 01 (no cell of its own) and 06.
HTML_FILES = [
    "README.md",
    "reports/intake_report.md",
    "reports/data_report.md",
    "governance/model_card.md",
    "analysis/01_business_understanding.qmd",
    "analysis/06_implementation_plan.qmd",
]
# The routes with ``embed-resources`` cost a second render of each; two files stand for them.
EMBED_FILES = ["README.md", "analysis/01_business_understanding.qmd"]


def _project_files(text: str, names: list[str]) -> dict[str, str]:
    intake, data = _planted_reports(text)
    files = {
        **templates.build_base_files(
            intake=intake, data=data, project_name="subrogation-model", project_slug="subrogation"
        ),
        **governance_templates.build_governance_files(
            intake=intake, data=data, project_name="subrogation-model", project_slug="subrogation"
        ),
    }
    return {name: files[name] for name in names}


def _run_quarto(
    quarto: dict[str, str], root: Path, command: list[str], timeout: int = 300
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "QUARTO_PYTHON": quarto["python"], "QPROBE": ENV_VALUE}
    return subprocess.run(
        [quarto["exe"], *command],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _render_pages(
    quarto: dict[str, str], root: Path, payload: str, names: list[str], extra: list[str]
) -> tuple[dict[str, str], set[str]]:
    """Write the named files of a project whose reports hold ``payload`` under ``root`` and render
    each one by name (the way the README tells a person to), to HTML. Returns each page and the
    effects found in all of them. Assets sit in ``root/../outside`` (the payload names that
    directory) and beside every rendered file (the payload also names one by a relative path)."""

    outside = root.parent / f"{root.name}_outside"
    _write_assets(outside)
    files = _project_files(payload.replace("@OUT@", str(outside)), names)
    pages: dict[str, str] = {}
    effects: set[str] = set()
    for name, text in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        _write_assets(target.parent)
        done = _run_quarto(quarto, root, ["render", name, "--to", "html", *extra])
        assert done.returncode == 0, (name, extra, done.stderr[-2000:])
        page = target.with_suffix(".html").read_text(encoding="utf-8")
        pages[name] = page
        effects |= _page_effects(page)
    return pages, effects


def _switch_the_neutralisers_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(templates, "neutralise_report", lambda value: value)
    monkeypatch.setattr(governance_templates, "neutralise_report", lambda value: value)
    monkeypatch.setattr(governance_templates, "neutralise_quarto_markup", lambda text: text)


def test_a_page_quarto_renders_carries_no_markup_the_report_text_wrote(
    quarto: dict[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """HTML, as the generated files declare it (``format: html``, or a ``.md`` rendered by name),
    and with ``embed-resources: true``: no script, event handler, ``javascript:`` link, iframe,
    object, embed, stylesheet link or import, image or attribute comes out of report text, and no
    file it names is inlined; the reader still sees the text that was written. With the
    neutraliser switched off every one of them is in the page (the control)."""

    # The page of an ordinary report has none of these, or the checks below could not tell.
    _, plain_effects = _render_pages(
        quarto, tmp_path / "plain", "Plain.", EMBED_FILES, ["-M", "embed-resources:true"]
    )
    assert plain_effects == set()

    pages, effects = _render_pages(quarto, tmp_path / "html", PAYLOAD_HTML, HTML_FILES, [])
    assert effects == set()
    _, embed_effects = _render_pages(
        quarto, tmp_path / "embed", PAYLOAD_HTML, EMBED_FILES, ["-M", "embed-resources:true"]
    )
    assert embed_effects == set()
    for name, page in pages.items():
        shown = _shown_text(page)
        assert "Visible start." in shown, name
        # Every construct is shown as the text it is, not run and not dropped. The div is the
        # one exception: Pandoc reads ``::: {...`` that is no attribute list as a div whose
        # class is that text, so its mark is in a class name, where it does nothing.
        assert set(_MARK.findall(PAYLOAD_HTML)) - {"ZZMARKDIV"} <= set(_MARK.findall(shown)), name
        assert "[an inline link](javascript:ZZMARKINLINE)" in shown, name

    _switch_the_neutralisers_off(monkeypatch)
    _, control = _render_pages(quarto, tmp_path / "raw_html", PAYLOAD_HTML, HTML_FILES, [])
    assert control == HTML_EFFECTS
    _, control_embed = _render_pages(
        quarto, tmp_path / "raw_embed", PAYLOAD_HTML, EMBED_FILES, ["-M", "embed-resources:true"]
    )
    assert control_embed == EMBED_EFFECTS


# A file TeX reads writes a file of its own, so that the effect does not depend on a PDF reader.
def _tex_reads(directory: Path, names: list[str]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name in names:
        (directory / f"read_{name}.tex").write_text(
            f"\\immediate\\openout3=ran_{name}.txt \\immediate\\write3{{x}}"
            f"\\immediate\\closeout3 OUTSIDETEX{name.upper()}\n"
        )


# Text-level TeX, which builds a PDF once it is text: a raw command, an environment read and a raw
# inline span. A fenced code block with a brace (JSON, an f-string, a SQL template) is here too: it
# holds the inserted character, and the build with Quarto's default engine, XeLaTeX, must still
# succeed. (``pdflatex`` fails on it, which the module's docstring lists as a cost; it is not
# tested because Quarto does not use it unless a person asks.)
PAYLOAD_TEX_TEXT = (
    "Visible start.\n\n"
    "\\input{@OUT@/read_a.tex}\n\n"
    '\\input{|"kpsewhich --var-value=QPROBE"}\n\n'
    "`\\input{@OUT@/read_b.tex}`{=latex}\n\n"
    # A bare carriage return between the backslash and the letters, which Pandoc deletes. The second
    # has no brace, so only the carriage return rule and the backslash rule stand between it and
    # the file (``readh.tex`` sits beside the file being rendered: Pandoc escapes an underscore in
    # the text that follows the command; and the text before it keeps the command inline, since a
    # command that starts a paragraph is a raw block and the rest of the line a paragraph of its
    # own).
    "\\\r" + "input{@OUT@/read_h.tex}\n\n"
    "Read \\\r" + "input readh.tex\n\n"
    '```json\n{"claims": [1, 2], "nested": {"a": true}}\n```\n\n'
    "Visible end."
)
# Math, which Pandoc hands to TeX untouched (a command, a display, a character code for a backslash
# and one for a letter), and a raw block fenced with tildes. A PDF that holds one of these fails to
# build once it is neutralised, which is a cost the module names (TeX stops on the undefined control
# sequence instead of reading the file; the tilde fence becomes a strikeout, and TeX's strikeout
# does not take the character): the build is not asserted, only that nothing was read.
#
# Each one is a document of its own. TeX stops at the first error, so in one document the first
# payload to fail would end the build before the next was reached and a clean result would show
# nothing about the rest (the first version of this test had exactly that flaw: the rule for two
# carets could be removed and it stayed green). The effect is the key; a key of one letter is a
# file with a path in the payload, the others name a file beside the one being built, with no brace,
# so that the rule under test is the only thing between the text and the file.
PAYLOAD_TEX_MATH = {
    "c": "$\\input{@OUT@/read_c.tex}$",
    "d": "$$\\input{@OUT@/read_d.tex}$$",
    "e": "$^^5cinput{@OUT@/read_e.tex}$",
    "f": "$\\^^69nput{@OUT@/read_f.tex}$",
    "g": "~~~{=latex}\n\\input{@OUT@/read_g.tex}\n~~~",
    "braceless": "$^^5cinput readh.tex$",
    "bracelesscr": "$^\r^5cinput readi.tex$",
}
TEX_TEXT_EFFECTS = {"a", "b", "env", "h", "braceless"}


def _render_pdfs(
    quarto: dict[str, str], root: Path, payload: str, names: list[str], reads: list[str]
) -> tuple[dict[str, int], set[str]]:
    """Render the named files to PDF with the TeX packages left alone (``latex-auto-install`` off)
    and the log kept. Returns each exit code and the effects: a file TeX read (it wrote the file
    ``ran_<name>.txt``) and an environment read (``kpsewhich`` ran, which the log shows)."""

    outside = root.parent / f"{root.name}_outside"
    _tex_reads(outside, reads)
    files = _project_files(payload.replace("@OUT@", str(outside)), names)
    codes: dict[str, int] = {}
    for name, text in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        # The files the braceless ``\input readh.tex`` and ``\input readi.tex`` name: TeX looks
        # beside the file it builds.
        for stem, marker in (("readh", "braceless"), ("readi", "bracelesscr")):
            (target.parent / f"{stem}.tex").write_text(
                f"\\immediate\\openout3=ran_{marker}.txt \\immediate\\write3{{x}}"
                "\\immediate\\closeout3\n"
            )
        done = _run_quarto(
            quarto,
            root,
            [
                "render",
                name,
                "--to",
                "pdf",
                "-M",
                "latex-auto-install:false",
                "-M",
                "latex-clean:false",
            ],  # fmt: skip
        )
        codes[name] = done.returncode
    effects = {path.stem.removeprefix("ran_") for path in root.rglob("ran_*.txt")}
    for log in root.rglob("*.log"):
        if "kpsewhich --var-value" in log.read_text(encoding="utf-8", errors="replace"):
            effects.add("env")
    return codes, effects


def _render_each_math_payload(quarto: dict[str, str], root: Path) -> dict[str, set[str]]:
    """Render ``README.md`` once per payload of ``PAYLOAD_TEX_MATH`` and return what each read."""

    found: dict[str, set[str]] = {}
    for key, text in PAYLOAD_TEX_MATH.items():
        payload = f"Visible start.\n\n{text}\n\nVisible end."
        reads = [key] if len(key) == 1 else []
        _, found[key] = _render_pdfs(quarto, root / key, payload, ["README.md"], reads)
    return found


def test_a_pdf_render_reads_no_file_and_runs_nothing_the_report_text_wrote(
    quarto: dict[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A PDF render reads no file and runs no command because of report text: not an absolute
    ``\\input``, not ``kpsewhich`` (which prints an environment value), not TeX in math, in a
    raw block or spelled with character codes. Skipped where there is no TeX. With the
    neutraliser switched off each of them acts."""

    if shutil.which("xelatex") is None:
        pytest.skip("xelatex is not installed (a PDF needs a TeX engine)")

    names = ["README.md", "analysis/01_business_understanding.qmd"]
    codes, effects = _render_pdfs(
        quarto, tmp_path / "text", PAYLOAD_TEX_TEXT, names, ["a", "b", "h"]
    )
    assert effects == set()
    # What was written is shown, and the PDF builds: nothing here is TeX any more.
    assert set(codes.values()) == {0}, codes
    math_effects = _render_each_math_payload(quarto, tmp_path / "math")
    assert math_effects == {key: set() for key in PAYLOAD_TEX_MATH}

    _switch_the_neutralisers_off(monkeypatch)
    _, control = _render_pdfs(
        quarto, tmp_path / "raw_text", PAYLOAD_TEX_TEXT, names, ["a", "b", "h"]
    )
    assert control == TEX_TEXT_EFFECTS
    control_math = _render_each_math_payload(quarto, tmp_path / "raw_math")
    assert control_math == {key: {key} for key in PAYLOAD_TEX_MATH}
