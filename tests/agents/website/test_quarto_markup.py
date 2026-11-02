"""Report text must not act on the notebook Quarto renders.

``BACKLOG.md`` item "What the scaffold still gets wrong after Larkspur point (2)", part (7)(b).
The intake and data reports hold text a language model wrote from a stakeholder's words and a
database, and the website agent writes it into ``analysis/01``, ``02``, ``05`` and ``06``
``.qmd`` files as prose. Quarto reads those files for more than prose, and Session 295's scouts
ran each of these with Quarto 1.7.33: a line of three backticks and ``{python}`` is a cell that
runs (even in a notebook with no cell of its own), `` `{python} expr` `` runs once any cell has
switched the engine on, ``{{< env NAME >}}`` expands anywhere and ``{{< include path >}}``
splices a file in when it is a whole line, and a second ``---`` block in the body is read as
metadata (a ``filters`` entry in it ran). The backlog proposed neutralising the opening of an
inline chunk; the scouts' critic showed that leaves all of the others open.

What is tested here:

* the model of Quarto in ``quarto_constructs.py`` sees every one of those spellings (otherwise
  every test below could pass by being blind);
* ``neutralise_quarto_markup`` leaves ordinary text byte for byte alone, and after it no spelling
  is left, in any of the places a template puts a field, over a seeded fuzz as well as a table;
* it only ever inserts one invisible character, so nothing a reader sees changes;
* it runs in linear time, because it is applied to text a model wrote;
* the four ``.qmd`` renderers apply it to every field they take, including a field no one has
  thought of yet (a payload goes into every string of both reports, which is the test that a new
  interpolation cannot slip past), and it is applied nowhere else.

``test_quarto_render.py`` renders the same text with the real tool where one is installed.
"""

from __future__ import annotations

import random
import re
import time
import unicodedata
from collections import Counter
from collections.abc import Callable
from typing import Any

import pytest

from model_project_constructor.agents.website import templates
from model_project_constructor.agents.website._quarto_markup import (
    ZERO_WIDTH_SPACE,
    neutralise_quarto_markup,
    neutralise_report,
)
from model_project_constructor.agents.website.templates import (
    build_base_files,
    render_qmd_business_understanding,
    render_qmd_data,
    render_qmd_implementation_plan,
    render_qmd_initial_models,
    render_reports_intake_md,
)
from model_project_constructor.schemas.v1.data import DataReport
from model_project_constructor.schemas.v1.intake import IntakeReport
from tests.agents.website.quarto_constructs import JS_SPACE, constructs

Z = ZERO_WIDTH_SPACE

# The places a template puts a field. A field can be the whole document, a paragraph, a list
# item, a heading, or the inside of a code span the template itself opened (06 does that for
# the baseline metric's name).
CONTEXTS: dict[str, Callable[[str], str]] = {
    "alone": lambda s: s,
    "paragraph": lambda s: f"Intro.\n\n{s}\n\nOutro.\n",
    "list_item": lambda s: f"- {s}\n- next\n",
    "heading": lambda s: f"### {s}\n\nbody\n",
    "code_span": lambda s: f"- **Metric:** `{s}`\n",
}

# (id, text, kind of construct the text holds). Every one is something Quarto 1.7.33 acted on
# when Session 295's scouts or critic rendered it, or is a spelling the source accepts.
HOSTILE: list[tuple[str, str, str]] = [
    ("fence", "```{python}\nopen('ran', 'w')\n```", "fence"),
    ("fence_the_opening_line_only", "```{python}", "fence"),
    ("fence_space_before_brace", "``` {python}\nx\n```", "fence"),
    ("fence_tab_before_brace", "```\t{python}\nx\n```", "fence"),
    ("fence_four_ticks", "````{python}\nx\n````", "fence"),
    ("fence_four_ticks_and_a_space", "```` {python}\nx\n````", "fence"),
    ("fence_with_options", "```{python, echo=false}\nx\n```", "fence"),
    ("fence_with_a_space_and_options", "``` {python, echo=false}\nx\n```", "fence"),
    ("fence_other_language", "```{bash}\nx\n```", "fence"),
    ("fence_indented_two", "  ```{python}\nx\n  ```", "fence"),
    ("fence_indented_four", "    ```{python}\nx\n```", "fence"),
    ("fence_no_break_space_before", "\u00a0```{python}\nx\n```", "fence"),
    ("fence_no_break_space_before_brace", "```\u00a0{python}\nx", "fence"),
    ("fence_byte_order_mark_before_brace", "```\ufeff{python}\nx", "fence"),
    ("fence_ideographic_space_before_brace", "```\u3000{python}\nx", "fence"),
    ("fence_in_a_blockquote", "> ```{python}\nx\n> ```", "fence"),
    ("fence_after_a_carriage_return", "a\r```{python}\nx", "fence"),
    ("fence_after_a_line_separator", "a\u2028```{python}\nx", "fence"),
    ("fence_after_a_paragraph_separator", "a\u2029``` {python}\nx", "fence"),
    ("fence_in_a_list_item_continuation", "item\n```{python}\nx\n```", "fence"),
    ("inline", "`{python} 1+1`", "inline_chunk"),
    ("inline_two_spaces", "`{python}  1+1`", "inline_chunk"),
    ("inline_tab", "`{python}\t1+1`", "inline_chunk"),
    ("inline_after_a_backslash", "\\`{python} 1+1`", "inline_chunk"),
    ("inline_other_language", "`{r} 1+1`", "inline_chunk"),
    ("inline_in_a_sentence", "Loss is `{python} open('ran', 'w')` here.", "inline_chunk"),
    ("inline_the_template_opened_the_span", "{python} open('ran', 'w')", "inline_chunk"),
    ("shortcode_env", "{{< env HOME >}}", "shortcode"),
    ("shortcode_without_spaces", "{{<env HOME>}}", "shortcode"),
    ("shortcode_include_a_line", "{{< include ../secret.txt >}}", "shortcode"),
    ("shortcode_meta", "{{< meta title >}}", "shortcode"),
    ("shortcode_in_a_sentence", "Home is {{< env HOME >}} here.", "shortcode"),
    ("metadata_filters", "x\n\n---\nfilters:\n  - f.lua\n---\n\ny", "metadata_block"),
    (
        "metadata_include_in_header",
        "---\ninclude-in-header:\n  - /etc/hosts\n...\n",
        "metadata_block",
    ),
    ("metadata_trailing_spaces", "---  \nfilters: [f]\n---  \n", "metadata_block"),
    ("metadata_carriage_returns", "---\r\nfilters: [f]\r\n---\r\n", "metadata_block"),
    ("metadata_line_separators", "---\u2028filters: [f]\u2028---\u2028", "metadata_block"),
    ("metadata_dots_to_close", "---\nfilters: [f]\n...", "metadata_block"),
]

HOSTILE_IDS = [name for name, _, _ in HOSTILE]

# Text that must come back byte for byte. The first group is what a model writes about a claims
# problem; the second is markup that looks near but is not something Quarto acts on.
BENIGN: list[tuple[str, str]] = [
    ("empty", ""),
    ("sentence", "Subrogation recovery dropped 12% after the new claims system went live."),
    ("code_span", "Join on `claim_id` and `policy_no`, then drop `__dupe`."),
    ("code_span_with_a_space", "Run `uv sync` first."),
    ("double_tick_code", "The value ``a`b`` is a literal."),
    ("money_and_comparison", "Cost is $1,200 < $2,000 and lift is > 2pp."),
    ("snake_case", "claim_cycle_time_days and policy_effective_date"),
    ("em_dash_and_accent", "Précision — recall trade-off, 🙂."),
    (
        "braces_in_a_sentence",
        "Use {braces} and {{double}} sometimes, or {{ name }} like a template.",
    ),
    ("lone_open_brace_mid_text", "the set { a, b } of claims"),
    ("brace_at_a_later_line_start", "First line.\n{second} line.\n"),
    ("brace_after_a_space", "a ` {python} b`"),
    ("dashes_inside_a_line", "Two -- or three --- dashes in a line, and a trailing dash -"),
    ("four_dashes", "----"),
    ("spaced_dashes", "- - -"),
    ("two_dashes_alone", "--"),
    ("dashes_with_text", "--- not a rule"),
    ("a_list", "- first\n- second\n  - nested"),
    ("a_heading", "# Heading\n\nbody"),
    ("a_link_and_image", "[docs](https://example.com/a) and ![alt](x.png)"),
    ("html", "<b>bold</b> and <br> and <!-- comment -->"),
    ("a_blockquote", "> quoted\n> more"),
    ("a_fence_that_is_not_a_cell", "```python\nSELECT 1\n```"),
    ("a_sql_fence", "```sql\nSELECT 1\n```"),
    ("a_bare_fence", "```\nplain\n```"),
    ("a_tilde_fence", "~~~{python}\nx\n~~~"),
    ("two_paragraphs", "First paragraph.\n\nSecond paragraph with `code`.\n"),
    ("windows_line_ends", "First\r\n\r\nSecond\r\n"),
    ("a_dot_dot_dot", "...\nand so on..."),
    ("a_python_name_in_prose", "The python and r engines; {python} alone is just a word."),
    ("a_zero_width_space_already", "a\u200bb"),
]

BENIGN_IDS = [name for name, _ in BENIGN]


def _kinds(text: str) -> Counter[str]:
    return Counter(c.kind for c in constructs(text))


class TestTheModelOfQuartoSeesWhatQuartoActsOn:
    """If the model were blind, every test that asks it for a clean bill would pass for nothing."""

    @pytest.mark.parametrize(("text", "kind"), [(t, k) for _, t, k in HOSTILE], ids=HOSTILE_IDS)
    def test_each_hostile_spelling_is_seen_in_some_place_a_field_lands(
        self, text: str, kind: str
    ) -> None:
        seen = set()
        for place in CONTEXTS.values():
            seen |= set(_kinds(place(text)))
        assert kind in seen

    @pytest.mark.parametrize(("text",), [(t,) for _, t in BENIGN], ids=BENIGN_IDS)
    def test_ordinary_text_is_not_seen_as_anything(self, text: str) -> None:
        for place in CONTEXTS.values():
            assert not constructs(place(text)), place(text)

    def test_the_documents_own_front_matter_is_one_block(self) -> None:
        header = '---\ntitle: "t"\nformat: html\n---\n\nbody\n'
        assert _kinds(header) == Counter({"metadata_block": 1})

    @pytest.mark.parametrize(
        "text",
        [
            "`{python}1+1`",  # no separator: Quarto 1.7.33 left it as text
            "`{ python} 1+1`",
            "`{python 1+1}`",
            "` {python} 1+1`",
            "{python} 1+1",
        ],
    )
    def test_an_inline_chunk_needs_its_separator_and_a_backtick_before_the_brace(
        self, text: str
    ) -> None:
        assert not [c for c in constructs(text) if c.kind == "inline_chunk"]

    def test_the_escaped_spellings_quarto_offers_are_not_shortcodes(self) -> None:
        assert not constructs("{{{< env HOME >}}} and {{</* env HOME */>}}")


class TestTheInsertedCharacter:
    """The one character this module writes into a notebook has to be the right one."""

    def test_it_is_a_zero_width_space(self) -> None:
        assert Z == "\u200b"

    def test_neither_quartos_patterns_nor_pythons_count_it_as_whitespace(self) -> None:
        """If either did, ``` {python}`` with it in front of the brace would still be a fence."""

        assert not Z.isspace()
        assert not re.fullmatch(r"\s", Z)
        assert not re.fullmatch(rf"[{JS_SPACE}]", Z)

    def test_a_joiner_would_be_the_wrong_choice(self) -> None:
        """U+200D is not whitespace either, but it joins the character before it to the one after
        (an emoji sequence), which a space does not."""

        assert Z != "\u200d"
        assert unicodedata.category(Z) == "Cf"
        assert unicodedata.combining(Z) == 0


class TestOrdinaryTextIsNotChanged:
    @pytest.mark.parametrize(("text",), [(t,) for _, t in BENIGN], ids=BENIGN_IDS)
    def test_comes_back_byte_for_byte(self, text: str) -> None:
        assert neutralise_quarto_markup(text) == text

    def test_the_characters_that_change_are_only_the_ones_that_can_act(self) -> None:
        """Documented, not accidental: a brace at the very start, and one right after a backtick."""

        assert neutralise_quarto_markup("{3 claims}") == Z + "{3 claims}"
        assert neutralise_quarto_markup("the `{` character") == "the `" + Z + "{` character"
        # A horizontal rule typed as three dashes alone on a line is a metadata marker to Pandoc.
        assert neutralise_quarto_markup("a\n\n---\n\nb") == "a\n\n-" + Z + "--\n\nb"


class TestEverySpellingIsBrokenInEveryPlace:
    @pytest.mark.parametrize(("text",), [(t,) for _, t, _ in HOSTILE], ids=HOSTILE_IDS)
    @pytest.mark.parametrize("place", list(CONTEXTS))
    def test_nothing_is_left_for_quarto_to_act_on(self, text: str, place: str) -> None:
        out = CONTEXTS[place](neutralise_quarto_markup(text))
        assert constructs(out) == []

    @pytest.mark.parametrize(("text",), [(t,) for _, t, _ in HOSTILE], ids=HOSTILE_IDS)
    def test_only_the_invisible_character_was_added(self, text: str) -> None:
        out = neutralise_quarto_markup(text)
        assert out != text
        assert out.replace(Z, "") == text.replace(Z, "")

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("`{python} 1`", "`" + Z + "{python} 1`"),
            ("```{python}", "```" + Z + "{python}"),
            ("``` {python}", "``` " + Z + "{python}"),
            ("```\t \u00a0{python, echo=false}", "```\t \u00a0" + Z + "{python, echo=false}"),
            ("> ```{r}", "> ```" + Z + "{r}"),
            ("x {{< env HOME >}}", "x {{" + Z + "< env HOME >}}"),
            ("x {{<env HOME>}}", "x {{" + Z + "<env HOME>}}"),
            ("x {{{< env HOME >}}}", "x {{{" + Z + "< env HOME >}}}"),
            # A string that starts with a brace gets one in front of it (a template may have
            # opened a code span just before the field), and the shortcode rule adds its own.
            ("{python} 1", Z + "{python} 1"),
            ("{{< env HOME >}}", Z + "{{" + Z + "< env HOME >}}"),
            ("a\n---\nb", "a\n-" + Z + "--\nb"),
            ("---", "-" + Z + "--"),
            ("---  \r\nx", "-" + Z + "--  \r\nx"),
            ("a\u2028---\u2028b", "a\u2028-" + Z + "--\u2028b"),
            ("a---", "a---"),
            ("---a", "---a"),
        ],
    )
    def test_where_the_character_goes(self, text: str, expected: str) -> None:
        assert neutralise_quarto_markup(text) == expected

    def test_running_it_twice_changes_nothing(self) -> None:
        for _, text, _ in HOSTILE:
            once = neutralise_quarto_markup(text)
            assert neutralise_quarto_markup(once) == once


class TestSeededFuzz:
    """Strings made of the pieces Quarto's patterns are built from, in every order the dice give.

    Half are random pieces; half are one dangerous construct built from its parts with a
    variation at each joint (what stands between the ticks and the brace, what stands before
    the ticks, which line end, how it closes), so the strings that matter are not left to chance.
    """

    PIECES = [
        "`", "``", "```", "````", "{", "}", "{{", "}}", "<", ">", "/*", "*/", "---", "...", "-",
        " ", "  ", "\t", "\n", "\n\n", "\r", "\r\n", "\u2028", "\u2029", "\ufeff", "\u00a0",
        "\u3000", "python", "r", "env", "x", "=", ",", "~~~", ":::", "#", "|",
    ]  # fmt: skip
    TICKS = ["```", "````", "`````", "`", "``"]
    BETWEEN = ["", "", " ", "  ", "\t", " \t", "\u00a0", "\ufeff", "\u3000", "\u2003", "\u200b",
               "\n", "\u2028"]  # fmt: skip
    BEFORE = ["", "", "  ", "    ", "\t", "> ", ">", "\u00a0", "- ", "a\r", "a\n", "a\u2028",
              "a\u2029", "a\r\n", "text "]  # fmt: skip
    LANGUAGES = ["python", "r", "bash", "julia", "ojs", "Python", "py thon", ".python", "=html", ""]
    OPTIONS = ["", "", ", echo=false", " echo=false", ",", " ", "  x", "}"]
    AFTER = ["", "\nx\n```", " 1+1`", "`", "\n", "\r\nx", "\u2028x"]
    LINE_ENDS = ["\n", "\r\n", "\r", "\u2028", "\u2029", "\n\n", " \n", "\t\n"]
    CLOSERS = ["---", "...", "----", "-- -", "---  "]

    @staticmethod
    def _built(dice: random.Random) -> str:
        cls = TestSeededFuzz
        kind = dice.choice(["fence", "fence", "inline", "shortcode", "metadata"])
        if kind == "fence":
            return (
                dice.choice(cls.BEFORE)
                + dice.choice(cls.TICKS)
                + dice.choice(cls.BETWEEN)
                + "{"
                + dice.choice(cls.LANGUAGES)
                + dice.choice(cls.OPTIONS)
                + "}"
                + dice.choice(cls.AFTER)
            )
        if kind == "inline":
            return (
                dice.choice(cls.BEFORE)
                + dice.choice(["", "\\", "`"])
                + dice.choice(cls.TICKS[3:])
                + dice.choice(cls.BETWEEN[:3])
                + "{"
                + dice.choice(cls.LANGUAGES)
                + "}"
                + dice.choice([" ", "\t", "  ", "", "\n"])
                + "1+1"
                + dice.choice(["`", "", "``"])
            )
        if kind == "shortcode":
            return (
                dice.choice(cls.BEFORE)
                + dice.choice(["{{", "{{{", "{{{{", "{ {", "{\u200b{"])
                + dice.choice(["<", "<", "&lt;", "</*"])
                + dice.choice([" ", "", "  "])
                + "env HOME"
                + dice.choice([" ", ""])
                + dice.choice([">}}", "*/>}}", ">}}}"])
            )
        ends = cls.LINE_ENDS
        return (
            dice.choice(cls.BEFORE)
            + dice.choice(ends)
            + "---"
            + dice.choice(["", " ", "\t", "  "])
            + dice.choice(ends)
            + "filters: [f]"
            + dice.choice(ends)
            + dice.choice(cls.CLOSERS)
            + dice.choice(ends)
        )

    @staticmethod
    def _strings(count: int, seed: int) -> list[str]:
        dice = random.Random(seed)
        out = []
        for _ in range(count):
            if dice.random() < 0.5:
                out.append(
                    "".join(dice.choice(TestSeededFuzz.PIECES) for _ in range(dice.randint(1, 14)))
                )
            else:
                parts = [TestSeededFuzz._built(dice) for _ in range(dice.randint(1, 3))]
                out.append(dice.choice(["", "\n", " ", "\n\n"]).join(parts))
        return out

    def test_nothing_is_left_to_act_on_and_only_the_character_was_added(self) -> None:
        flagged_raw = 0
        for text in self._strings(30_000, seed=295):
            out = neutralise_quarto_markup(text)
            assert out.replace(Z, "") == text.replace(Z, ""), repr(text)
            assert neutralise_quarto_markup(out) == out, repr(text)
            for place in CONTEXTS.values():
                assert constructs(place(out)) == [], (repr(text), place("."))
            if any(constructs(place(text)) for place in CONTEXTS.values()):
                flagged_raw += 1
        # The dice must actually produce the dangerous strings, or the loop above proves nothing.
        assert flagged_raw > 4_000


class TestItIsFastOnTextAModelWrote:
    """The patterns are built to be linear: a long run of the pieces they look for is the input
    that makes an ordinary pattern quadratic.

    The patterns take about ten milliseconds for 100,000 characters. A quadratic pattern needs
    tens of seconds for the same input (the pattern did, in a scratch copy with the guard against
    restarting inside a run of ticks removed), so a bound of two seconds separates them with room
    on a slow machine, and a failure arrives in well under a minute rather than after a hang.
    """

    N = 100_000

    @pytest.mark.parametrize(
        "text",
        [
            "`" * N,
            "```" + " " * N + "x",
            "```" + " " * N + "{",
            ("``` " * (N // 4)) + "x",
            "`{" * (N // 2),
            "{{" * (N // 2),
            "{{<" * (N // 3),
            "\n---" * (N // 4),
            ("--- " * (N // 4)) + "x",
            "---" + " " * N + "x",
            "-" * N,
            "\n" * N,
            "{" * N,
        ],
        ids=[
            "backticks", "fence_then_spaces", "fence_then_spaces_then_brace", "many_fences",
            "tick_brace", "double_braces", "shortcode_openers", "dashes_at_line_starts",
            "dashes_and_spaces", "dashes_then_spaces", "dashes", "newlines", "braces",
        ],
    )  # fmt: skip
    def test_a_long_run_takes_seconds_not_minutes(self, text: str) -> None:
        start = time.perf_counter()
        neutralise_quarto_markup(text)
        assert time.perf_counter() - start < 2


class TestReports:
    """``neutralise_report`` walks a report as ``model_dump`` returns it."""

    def test_every_string_at_every_depth_is_neutralised(self) -> None:
        report = {
            "a": "{{< env HOME >}}",
            "b": ["---", {"c": "`{python} 1`", "d": ("```{r}", 7)}],
            "e": {"f": {"g": ["x", "{{<"]}},
        }
        assert neutralise_report(report) == {
            "a": Z + "{{" + Z + "< env HOME >}}",
            "b": ["-" + Z + "--", {"c": "`" + Z + "{python} 1`", "d": ("```" + Z + "{r}", 7)}],
            "e": {"f": {"g": ["x", Z + "{{" + Z + "<"]}},
        }

    def test_what_is_not_a_string_is_left_alone(self) -> None:
        value: dict[str, Any] = {"n": 3, "x": 2.5, "t": True, "none": None, "keys{{<": "v"}
        assert neutralise_report(value) == value

    def test_the_input_is_not_changed_and_the_result_is_a_new_object(self) -> None:
        source = {"a": ["{{< env HOME >}}"]}
        out = neutralise_report(source)
        assert source == {"a": ["{{< env HOME >}}"]}
        assert out is not source
        assert out["a"] is not source["a"]

    def test_types_are_kept(self) -> None:
        out = neutralise_report({"l": ["a"], "t": ("a",), "s": "a"})
        assert isinstance(out["l"], list)
        assert isinstance(out["t"], tuple)
        assert isinstance(out["s"], str)


# --- The renderers -----------------------------------------------------------------------

PAYLOADS = {
    # Every construct, with a marker so a reader of a failure can see which field it came from.
    "everything": (
        "MARK\n\n```{python}\nopen('ran', 'w')\n```\n\n``` {python}\nx\n```\n\n"
        "`{python} 1+1`\n\n{{< env HOME >}}\n\n{{< include ../secret.txt >}}\n\n"
        "---\nfilters:\n  - f.lua\n---\n\nend MARK"
    ),
    # Single-line fields: no newline in them, and still enough in the right two neighbours.
    "an_opening_fence_alone": "```{python}",
    "an_include_alone": "{{< include ../secret.txt >}}",
    "an_env_alone": "{{< env HOME >}}",
    "an_expression_that_starts_with_a_brace": "{python} open('ran', 'w')",
    "an_inline_chunk_alone": "`{python} open('ran', 'w')`",
    "a_rule_alone": "---",
}

QMD_FILES = [
    "analysis/01_business_understanding.qmd",
    "analysis/02_data.qmd",
    "analysis/03_eda.qmd",
    "analysis/04_feature_engineering.qmd",
    "analysis/05_initial_models.qmd",
    "analysis/06_implementation_plan.qmd",
    "analysis/99_extensions.qmd",
]


def _plant(value: Any, make: Callable[[int], str], counter: list[int]) -> Any:
    """``value`` with every string, at every depth, replaced by ``make(n)`` for a fresh n."""

    if isinstance(value, str):
        counter[0] += 1
        return make(counter[0])
    if isinstance(value, dict):
        return {k: _plant(v, make, counter) for k, v in value.items()}
    if isinstance(value, list):
        return [_plant(v, make, counter) for v in value]
    return value


def _reports(
    intake_report: IntakeReport, data_report: DataReport
) -> tuple[dict[str, Any], dict[str, Any]]:
    return intake_report.model_dump(mode="json"), data_report.model_dump(mode="json")


def _build(intake: dict[str, Any], data: dict[str, Any]) -> dict[str, str]:
    return build_base_files(
        intake=intake,
        data=data,
        project_name="subrogation-model",
        project_slug="subrogation_model",
    )


def _planted_build(
    intake_report: IntakeReport, data_report: DataReport, payload: str
) -> dict[str, str]:
    intake, data = _reports(intake_report, data_report)
    counter = [0]

    def make(n: int) -> str:
        return payload.replace("MARK", f"ZZ{n}ZZ")

    return _build(_plant(intake, make, counter), _plant(data, make, counter))


class TestTheRenderersNeutraliseEveryFieldTheyTake:
    def test_the_payload_reaches_the_four_notebooks_that_take_report_text(
        self, intake_report: IntakeReport, data_report: DataReport
    ) -> None:
        """Without this, a clean result below could mean the text never arrived."""

        files = _planted_build(intake_report, data_report, "MARK")
        reaching = {
            path: {n for n in range(1, 200) if f"ZZ{n}ZZ" in files[path]} for path in QMD_FILES
        }
        assert reaching["analysis/01_business_understanding.qmd"]
        assert reaching["analysis/02_data.qmd"]
        assert reaching["analysis/05_initial_models.qmd"]
        assert reaching["analysis/06_implementation_plan.qmd"]
        assert not reaching["analysis/03_eda.qmd"]
        assert not reaching["analysis/04_feature_engineering.qmd"]
        assert not reaching["analysis/99_extensions.qmd"]
        assert len(set().union(*reaching.values())) >= 30

    @pytest.mark.parametrize("shape", list(PAYLOADS))
    def test_a_payload_in_every_string_adds_nothing_quarto_acts_on(
        self, intake_report: IntakeReport, data_report: DataReport, shape: str
    ) -> None:
        intake, data = _reports(intake_report, data_report)
        baseline = _build(intake, data)
        planted = _planted_build(intake_report, data_report, PAYLOADS[shape])
        for path in QMD_FILES:
            assert _kinds(planted[path]) == _kinds(baseline[path]), (
                path,
                constructs(planted[path])[:6],
            )

    def test_the_check_above_can_fail(
        self,
        intake_report: IntakeReport,
        data_report: DataReport,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """With the neutraliser switched off, the same payload does add constructs to each of
        the four notebooks that take report text. A test that cannot fail proves nothing."""

        intake, data = _reports(intake_report, data_report)
        baseline = _build(intake, data)
        monkeypatch.setattr(templates, "neutralise_report", lambda value: value)
        planted = _planted_build(intake_report, data_report, PAYLOADS["everything"])
        for path in (
            "analysis/01_business_understanding.qmd",
            "analysis/02_data.qmd",
            "analysis/05_initial_models.qmd",
            "analysis/06_implementation_plan.qmd",
        ):
            assert _kinds(planted[path]) != _kinds(baseline[path]), path

    @pytest.mark.parametrize(
        "render",
        [
            lambda i, d: render_qmd_business_understanding(intake=i),
            lambda i, d: render_qmd_data(data=d, project_slug="subrogation_model"),
            lambda i, d: render_qmd_initial_models(intake=i, project_slug="subrogation_model"),
            lambda i, d: render_qmd_implementation_plan(intake=i, data=d),
        ],
        ids=["01", "02", "05", "06"],
    )
    def test_each_renderer_does_it_itself(
        self,
        intake_report: IntakeReport,
        data_report: DataReport,
        render: Callable[[dict[str, Any], dict[str, Any]], str],
    ) -> None:
        """The renderers are public functions and tests and callers use them directly."""

        intake, data = _reports(intake_report, data_report)
        baseline = _kinds(render(intake, data))
        counter = [0]

        def make(n: int) -> str:
            return PAYLOADS["everything"].replace("MARK", f"ZZ{n}ZZ")

        out = render(_plant(intake, make, counter), _plant(data, make, counter))
        assert _kinds(out) == baseline

    def test_ordinary_reports_produce_the_same_files_as_before(
        self,
        intake_report: IntakeReport,
        data_report: DataReport,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        intake, data = _reports(intake_report, data_report)
        with_it = _build(intake, data)
        monkeypatch.setattr(templates, "neutralise_report", lambda value: value)
        without_it = _build(intake, data)
        assert with_it == without_it

    def test_only_the_notebooks_are_changed_and_the_markdown_mirrors_are_not(
        self,
        intake_report: IntakeReport,
        data_report: DataReport,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Quarto renders ``.qmd`` files. ``reports/intake_report.md`` shares its business-case
        block with notebook 01, and neither it nor any other file is rewritten."""

        with_it = _planted_build(intake_report, data_report, PAYLOADS["everything"])
        monkeypatch.setattr(templates, "neutralise_report", lambda value: value)
        without_it = _planted_build(intake_report, data_report, PAYLOADS["everything"])
        changed = {path for path in with_it if with_it[path] != without_it[path]}
        assert changed == {
            "analysis/01_business_understanding.qmd",
            "analysis/02_data.qmd",
            "analysis/05_initial_models.qmd",
            "analysis/06_implementation_plan.qmd",
        }
        intake, _ = _reports(intake_report, data_report)
        hostile_intake = _plant(intake, lambda n: PAYLOADS["everything"], [0])
        assert Z not in render_reports_intake_md(intake=hostile_intake)
