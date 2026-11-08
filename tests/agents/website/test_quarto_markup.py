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
* it only ever inserts one invisible character, so what a reader sees changes only in the cases
  its module lists as costs (a ``---`` that ends a line is no longer a rule, a ``<!--`` comment
  is shown, every brace carries the character, a tag or an autolink is shown as the text it is,
  an image or a link is text, a grid table is a paragraph, a backslash before a letter shows
  without the backslash);
* Session 302's rules (``BACKLOG.md`` item (7)(g)) look at one pair of characters each and decide
  from the character on the right alone, so ``TestTheStructuralRules`` holds them to that: the
  spellings the scouts and the adversaries used, a pair-by-pair contract that no output may
  break, a seeded fuzz, and the claim that the rules can run in any order. What the tool does
  with the result is ``test_quarto_render.py``'s to say;
* it runs in linear time, because it is applied to text a model wrote;
* the four ``.qmd`` renderers and the twelve ``.md`` renderers (the READMEs, ``reports/*.md``,
  the governance documents and the datasheets) apply it to every field they take, including a
  field no one has thought of yet (a payload goes into every string of both reports, which is
  the test that a new interpolation cannot slip past). Quarto renders a ``.md`` it is asked to
  render as it does a ``.qmd``, without running code; and it is applied to nothing else (the
  JSON files and the SQL are not rendered).

``test_quarto_render.py`` renders the same text with the real tool where one is installed.
"""

from __future__ import annotations

import contextlib
import random
import re
import signal
import threading
import time
import unicodedata
from collections import Counter
from collections.abc import Callable, Iterator
from typing import Any

import pytest

from model_project_constructor.agents.website import _quarto_markup as markup
from model_project_constructor.agents.website import governance_templates, templates
from model_project_constructor.agents.website._quarto_markup import (
    ZERO_WIDTH_SPACE,
    neutralise_quarto_markup,
    neutralise_report,
)
from model_project_constructor.agents.website.governance_templates import (
    build_analysis_files,
    build_governance_files,
    build_regulatory_mapping,
)
from model_project_constructor.agents.website.templates import (
    build_base_files,
    render_qmd_business_understanding,
    render_qmd_data,
    render_qmd_implementation_plan,
    render_qmd_initial_models,
)
from model_project_constructor.schemas.v1.data import DataReport
from model_project_constructor.schemas.v1.intake import IntakeReport
from tests.agents.website.quarto_constructs import JS_SPACE, constructs

Z = ZERO_WIDTH_SPACE

# The places a template puts a field. A field can be the whole document, a paragraph, a list
# item, a heading, or the inside of a code span the template itself opened (06 does that for
# the baseline metric's name). Most renderers ``.strip()`` a field after it was neutralised, and
# 06 writes the review cadence as a code span that opens at the start of its line.
CONTEXTS: dict[str, Callable[[str], str]] = {
    "alone": lambda s: s,
    "paragraph": lambda s: f"Intro.\n\n{s}\n\nOutro.\n",
    "stripped": lambda s: f"Intro.\n\n{s.strip()}\n\nOutro.\n",
    "list_item": lambda s: f"- {s}\n- next\n",
    "heading": lambda s: f"### {s}\n\nbody\n",
    "code_span": lambda s: f"- **Metric:** `{s}`\n",
    "line_start_code_span": lambda s: f"## Review Cadence\n\n`{s}`\n\n## Next\n",
    "stripped_line_start_code_span": lambda s: f"## Review Cadence\n\n`{s.strip()}`\n\n## Next\n",
}

# (id, text, kind of construct the text holds). Every one is something Quarto 1.7.33 acted on
# when Session 295's scouts, critic or reviewers rendered it, or is a spelling the source
# accepts, or is one the model reports on the safe side: a fence after a lone carriage return,
# after U+2028 or behind a no-break space, and a metadata block with U+2028 line ends did not
# run when rendered.
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
    ("fence_brace_on_the_next_line", "```\n{python}\nx\n```", "fence"),
    ("fence_split_by_a_carriage_return", "```\r{python}\nx", "fence"),
    ("fence_split_by_a_line_separator", "```\u2028{python}\nx", "fence"),
    ("fence_split_by_a_paragraph_separator", "```\u2029 {python}\nx", "fence"),
    ("fence_a_gap_of_forty_spaces", "```" + " " * 40 + "{python}\nx", "fence"),
    ("fence_two_ticks_behind_a_template_tick", "`` {python}\nx\n``", "fence"),
    ("fence_two_ticks_and_a_tab_behind_a_template_tick", "``\t{python}\nx\n``", "fence"),
    ("fence_two_ticks_behind_a_nbsp_and_a_template_tick", "\u00a0`` {python}\nx\n``", "fence"),
    ("fence_two_ticks_behind_blank_lines_and_a_tick", "\n\n`` {python}\nx\n``", "fence"),
    ("inline_chunk_behind_a_nbsp_after_a_tick", "\u00a0{python} 1+1", "inline_chunk"),
    ("inline_chunk_behind_blank_lines_after_a_tick", "\n\n{python} 1+1", "inline_chunk"),
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
    # The renderers strip a field after it was neutralised: whitespace in front of a ``---`` that
    # starts the text is gone by the time the notebook is written.
    ("metadata_behind_a_space", " ---\nfilters: [f]\n...", "metadata_block"),
    ("metadata_behind_a_tab", "\t---\nfilters: [f]\n...", "metadata_block"),
    ("metadata_behind_a_no_break_space", "\u00a0---\nfilters: [f]\n...", "metadata_block"),
    ("metadata_behind_an_ideographic_space", "\u3000---\nfilters: [f]\n...", "metadata_block"),
    ("metadata_behind_blank_lines", "\n \n  ---\nfilters: [f]\n...", "metadata_block"),
    # Quarto deletes comments before it looks for the block.
    ("metadata_comment_after_the_dashes", "x\n\n---<!---->\nfilters: [f]\n...", "metadata_block"),
    (
        "metadata_comment_before_the_dashes",
        "x\n\n<!-- c -->---\nfilters: [f]\n...",
        "metadata_block",
    ),
    ("metadata_comment_between_dashes", "x\n\n-<!-- c -->--\nfilters: [f]\n...", "metadata_block"),
    ("metadata_comment_over_two_lines", "x\n\n---<!--\n-->\nfilters: [f]\n...", "metadata_block"),
    ("metadata_comment_in_a_list_item", "- x\n---<!---->\nfilters: [f]\n...", "metadata_block"),
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
    ("dashes_inside_a_line", "Two -- or three --- dashes in a line, and a trailing dash -"),
    ("four_dashes", "----"),
    ("spaced_dashes", "- - -"),
    ("two_dashes_alone", "--"),
    ("dashes_with_text", "--- not a rule"),
    ("a_list", "- first\n- second\n  - nested"),
    ("a_heading", "# Heading\n\nbody"),
    ("indented_text", "  indented text, and a tab\tinside"),
    ("indented_dashes_with_text", " --- not a rule"),
    ("a_rule_in_the_middle_of_a_line", "before --- after"),
    ("a_blockquote", "> quoted\n> more"),
    ("a_fence_that_is_not_a_cell", "```python\nSELECT 1\n```"),
    ("a_sql_fence", "```sql\nSELECT 1\n```"),
    ("a_bare_fence", "```\nplain\n```"),
    ("two_paragraphs", "First paragraph.\n\nSecond paragraph with `code`.\n"),
    ("windows_line_ends", "First\r\n\r\nSecond\r\n"),
    ("a_dot_dot_dot", "...\nand so on..."),
    ("a_python_name_in_prose", "The python and r engines; python alone is just a word."),
    ("a_zero_width_space_already", "a\u200bb"),
    # Session 302: what the new rules leave alone, so that they stay narrow. A ``<`` before a digit,
    # a space, ``=`` or the end is a comparison; a backslash before a symbol is a control symbol;
    # one caret is an exponent; a ``!`` or a ``]`` that no ``[`` or ``(`` touches is punctuation.
    ("comparisons", "p < 0.05, n<5, a <= b, 3<4, and x <"),
    (
        "a_backslash_before_something_that_is_not_a_letter",
        "5\\%, \\_x, \\(, \\\\, C:\\1, a\\ b, x\\",
    ),
    ("one_caret", "x^2 and 2^10 and a^b^c"),
    ("a_bang_that_is_not_an_image", "Done! Really!? Yes! [spaced] and ! [ spaced ]"),
    (
        "brackets_in_prose",
        "see [1] and [note] (below) and a [list] [of] items, array[0], f(x)[1] and [a]b",
    ),
    ("a_colon_that_is_not_a_definition", "Note: [x] is a: b, and [x] : y"),
    ("a_closing_brace_alone", "a } b and }} and ]"),
]

# Text the model of Quarto reports as nothing and that the rules break anyway, with the output and
# why. These stood in BENIGN until Session 302: the brace rule looks at every brace (the old rules
# looked at the three places Session 295 had broken), and the rules for ``<``, ``]`` and ``!`` do
# not know whether an author meant a tag, a link or an image. Each is a cost the module lists.
BROKEN_ANYWAY: list[tuple[str, str, str]] = [
    (
        "braces_in_a_sentence",
        "Use {braces} and {{double}} sometimes, or {{ name }} like a template.",
        f"Use {{{Z}braces}} and {{{Z}{{{Z}double}}}} sometimes, "
        f"or {{{Z}{{{Z} name }}}} like a template.",
    ),
    ("lone_open_brace_mid_text", "the set { a, b } of claims", f"the set {{{Z} a, b }} of claims"),
    (
        "brace_at_a_later_line_start",
        "First line.\n{second} line.\n",
        f"First line.\n{{{Z}second}} line.\n",
    ),
    ("brace_after_a_space", "a ` {python} b`", f"a ` {{{Z}python}} b`"),
    ("a_tilde_fence", "~~~{python}\nx\n~~~", f"~~~{{{Z}python}}\nx\n~~~"),
    (
        "a_python_name_in_braces",
        "The python and r engines; {python} alone is just a word.",
        f"The python and r engines; {{{Z}python}} alone is just a word.",
    ),
    (
        "a_link_and_image",
        "[docs](https://example.com/a) and ![alt](x.png)",
        f"[docs]{Z}(https://example.com/a) and !{Z}[alt]{Z}(x.png)",
    ),
    (
        "html",
        "<b>bold</b> and <br> and <!DOCTYPE html> and <!- not a comment",
        f"<{Z}b>bold<{Z}/b> and <{Z}br> and <{Z}!DOCTYPE html> and <{Z}!- not a comment",
    ),
]

BENIGN_IDS = [name for name, _ in BENIGN]
BROKEN_ANYWAY_IDS = [name for name, _, _ in BROKEN_ANYWAY]

# Every character that JavaScript's ``\s`` or Python's ``str.isspace`` counts. All of them are
# below U+3100 except the byte order mark, which only JavaScript counts.
SPACE_CHARACTERS = [
    chr(code)
    for code in range(0x3100)
    if chr(code).isspace() or re.fullmatch(f"[{JS_SPACE}]", chr(code))
] + ["\ufeff"]


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

    @pytest.mark.parametrize(
        ("text",),
        [(t,) for _, t in BENIGN] + [(t,) for _, t, _ in BROKEN_ANYWAY],
        ids=BENIGN_IDS + BROKEN_ANYWAY_IDS,
    )
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

    def test_a_comment_ends_at_the_first_close_so_a_block_between_two_is_a_block(self) -> None:
        """Quarto's pattern is lazy: ``<!-- a -->`` and ``<!-- b -->`` do not swallow the text
        between them."""

        text = "<!-- a -->\n\n---\nfilters: [f]\n...\n\n<!-- b -->"
        assert _kinds(text) == Counter({"metadata_block": 1})

    def test_a_rule_followed_by_a_line_of_spaces_opens_no_block(self) -> None:
        """Quarto's pattern refuses a ``---`` whose next line holds only spaces or tabs (a
        horizontal rule, not metadata). An empty next line it lets through, because ``[\\r\\n]+``
        takes it, and the model follows: Quarto then drops that block for starting with a
        blank line, which the model does not, and over-reporting is the safe direction."""

        assert not constructs("x\n\n---\n \nfilters: [f]\n...\n")
        assert _kinds("x\n\n---\n\nfilters: [f]\n...\n") == Counter({"metadata_block": 1})

    def test_a_block_inside_a_comment_is_not_a_block(self) -> None:
        """Quarto deletes the comment, block and all, before it looks."""

        assert not constructs("a <!--\n---\nfilters: [f]\n...\n--> b")

    def test_a_fence_is_found_across_a_line_end_and_a_line_break_is_any_of_four(self) -> None:
        for gap in ("\n", "\r", "\u2028", "\u2029", "\r\n", " \n "):
            assert _kinds(f"```{gap}{{python}}\nx") == Counter({"fence": 1}), repr(gap)


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

    @pytest.mark.parametrize(
        ("text", "expected"), [(t, e) for _, t, e in BROKEN_ANYWAY], ids=BROKEN_ANYWAY_IDS
    )
    def test_the_text_the_rules_break_anyway_is_broken_where_the_module_says(
        self, text: str, expected: str
    ) -> None:
        assert neutralise_quarto_markup(text) == expected
        assert expected.replace(Z, "") == text

    def test_the_characters_that_change_are_only_the_ones_that_can_act(self) -> None:
        """Documented, not accidental: every opening brace, and a ``---`` that ends its line."""

        # Until Session 302 only a brace at the very start and one right after a backtick changed;
        # the brace rule looks at every brace now, and puts the character after it.
        assert neutralise_quarto_markup("{3 claims}") == "{" + Z + "3 claims}"
        assert neutralise_quarto_markup("the `{` character") == "the `{" + Z + "` character"
        assert neutralise_quarto_markup("the set {a} and {b}") == f"the set {{{Z}a}} and {{{Z}b}}"
        # A horizontal rule typed as three dashes alone on a line is a metadata marker to Pandoc.
        assert neutralise_quarto_markup("a\n\n---\n\nb") == "a\n\n-" + Z + "--\n\nb"

    def test_the_costs_are_the_ones_the_module_lists(self) -> None:
        """What a reader sees differs in these cases and no others: each is a rule the module
        lists, and each is pinned so that narrowing or widening it is a decision."""

        # A comment is shown as the text it is instead of being hidden.
        assert neutralise_quarto_markup("a <!-- c --> b") == "a <" + Z + "!-- c --> b"
        # Every brace carries the character, in code as well: JSON in a code block, a fence with a
        # language label and a code span all hold it, where a reader who copies the code copies
        # it, and ``pdflatex`` cannot typeset it there.
        assert neutralise_quarto_markup('```\n{"a": 1}\n```') == "```\n{" + Z + '"a": 1}\n```'
        json_fence = neutralise_quarto_markup('```json\n{"a": 1}\n```')
        assert json_fence == "```json\n{" + Z + '"a": 1}\n```'
        assert neutralise_quarto_markup("use `{x}`") == "use `{" + Z + "x}`"
        # A lone rule renders as a hyphen and an en dash, and underlines no heading.
        assert neutralise_quarto_markup("Cost\n---\nText") == "Cost\n-" + Z + "--\nText"
        # A literal tag or an autolink is shown as the text it is: ``<policy_number>`` in prose is
        # a placeholder to the reader and a tag to Pandoc.
        placeholder = neutralise_quarto_markup("fill <policy_number> in")
        assert placeholder == "fill <" + Z + "policy_number> in"
        assert neutralise_quarto_markup("<https://x.example>") == "<" + Z + "https://x.example>"
        # An image is a link to the path, and no link, reference link or definition works.
        assert neutralise_quarto_markup("![alt](p.png)") == "!" + Z + "[alt]" + Z + "(p.png)"
        assert (
            neutralise_quarto_markup("[a](https://x.example)") == "[a]" + Z + "(https://x.example)"
        )
        assert neutralise_quarto_markup("[a][b]") == "[a]" + Z + "[b]"
        assert (
            neutralise_quarto_markup("[b]: https://x.example") == "[b]" + Z + ": https://x.example"
        )
        # A backslash before a letter keeps its backslash in the text and the character after it;
        # Pandoc reads backslash and the character as an escape, so a notebook shows ``C:Users``
        # for ``C:\\Users``. In a code span the backslash stays.
        windows_path = neutralise_quarto_markup("C:\\Users and \\d+")
        assert windows_path == "C:\\" + Z + "Users and \\" + Z + "d+"
        # A character code for a backslash is TeX's spelling of one. In prose a caret, the
        # character and a caret are a superscript to Pandoc, which shows ``x^^2`` as ``x2``.
        assert neutralise_quarto_markup("^^5c") == "^" + Z + "^5c"
        assert neutralise_quarto_markup("x^^2") == "x^" + Z + "^2"
        # Math with a TeX command: TeX (a PDF) and MathJax (a page) meet a control sequence that
        # does not exist, and the build or the equation fails instead of reading a file.
        assert neutralise_quarto_markup("$\\frac{a}{b}$") == (
            "$\\" + Z + "frac{" + Z + "a}{" + Z + "b}$"
        )
        # A strikeout that holds a character that was inserted fails a XeLaTeX build (``soul``
        # cannot typeset it); the module lists it as a cost that has not been accepted. The
        # characters are inserted inside the tildes whatever the words, and the tildes are left.
        assert neutralise_quarto_markup("~~old {x}~~") == "~~old {" + Z + "x}~~"
        assert neutralise_quarto_markup("~~old words~~") == "~~old words~~"
        # A grid table is a paragraph; a ``---`` that ends a line is no rule, wherever it is.
        assert neutralise_quarto_markup("+---+\n| a |\n+---+") == (
            "+" + Z + "---+\n| a |\n+" + Z + "---+"
        )
        assert neutralise_quarto_markup("words ---") == "words -" + Z + "--"


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
            ("`{python} 1`", "`{" + Z + "python} 1`"),
            ("```{python}", "```{" + Z + "python}"),
            ("``` {python}", "``` {" + Z + "python}"),
            ("```\t \u00a0{python, echo=false}", "```\t \u00a0{" + Z + "python, echo=false}"),
            ("> ```{r}", "> ```{" + Z + "r}"),
            ("x {{< env HOME >}}", "x {" + Z + "{" + Z + "< env HOME >}}"),
            ("x {{<env HOME>}}", "x {" + Z + "{" + Z + "<" + Z + "env HOME>}}"),
            ("x {{{< env HOME >}}}", "x {" + Z + "{" + Z + "{" + Z + "< env HOME >}}}"),
            # Every brace gets the character after it, a field that starts with one included (a
            # template may have opened a code span just before the field). Two braces in a row
            # each get one, so ``{{<`` is never adjacent.
            ("{python} 1", "{" + Z + "python} 1"),
            ("{{< env HOME >}}", "{" + Z + "{" + Z + "< env HOME >}}"),
            ("a\n---\nb", "a\n-" + Z + "--\nb"),
            ("---", "-" + Z + "--"),
            # The renderers strip a field after this runs, so whitespace around the text counts
            # as nothing: a rule behind it is at the start of a line when the notebook is written.
            (" ---\nx", " -" + Z + "--\nx"),
            ("\u00a0---\nx", "\u00a0-" + Z + "--\nx"),
            ("\n ---\nx", "\n -" + Z + "--\nx"),
            ("x\n---\u00a0", "x\n-" + Z + "--\u00a0"),
            ("x\n---   ", "x\n-" + Z + "--   "),
            # Session 302, second round: the marker rule no longer asks for the start of a line,
            # because Pandoc opens a metadata block inside a block quote, a list item and a
            # footnote, behind that container's own prefix. A ``---`` that ends a line is broken
            # whatever stands in front of it (these two were left alone by the first version).
            ("x --- ", "x -" + Z + "-- "),
            ("x\n --- \ny", "x\n -" + Z + "-- \ny"),
            (" {python} 1", " {" + Z + "python} 1"),
            ("`` {python}", "`` {" + Z + "python}"),
            (" ``\t{python}", " ``\t{" + Z + "python}"),
            ("a `` {python}", "a `` {" + Z + "python}"),
            ("``` {python}", "``` {" + Z + "python}"),
            ("```\n{python}", "```\n{" + Z + "python}"),
            ("```\r{python}", "```\r" + Z + "{" + Z + "python}"),
            ("```\u2028{python}", "```\u2028{" + Z + "python}"),
            ("<!-- c -->", "<" + Z + "!-- c -->"),
            ("<!--", "<" + Z + "!--"),
            ("<!-", "<" + Z + "!-"),
            ("---<!---->", "---<" + Z + "!---->"),
            ("-<!-- c -->--", "-<" + Z + "!-- c -->--"),
            ("---  \r\nx", "-" + Z + "--  \r\nx"),
            ("a\u2028---\u2028b", "a\u2028-" + Z + "--\u2028b"),
            ("a---", "a-" + Z + "--"),
            ("---a", "---a"),
            ("a---b", "a---b"),
        ],
    )
    def test_where_the_character_goes(self, text: str, expected: str) -> None:
        assert neutralise_quarto_markup(text) == expected

    def test_running_it_twice_changes_nothing(self) -> None:
        for _, text, _ in HOSTILE:
            once = neutralise_quarto_markup(text)
            assert neutralise_quarto_markup(once) == once

    def test_every_whitespace_character_between_the_ticks_and_the_brace(self) -> None:
        """Quarto's pattern counts JavaScript's ``\\s`` there, Python's counts a different set, and
        the rule uses the union. Every code point either one counts is tried."""

        for char in SPACE_CHARACTERS:
            out = neutralise_quarto_markup(f"```{char}{{python}}\nx\n```")
            assert constructs(out) == [], repr(char)
            assert out.replace(Z, "") == f"```{char}{{python}}\nx\n```", repr(char)

    @pytest.mark.parametrize("width", [1, 2, 3, 4, 8, 9, 40, 500])
    def test_a_gap_of_any_width_between_the_ticks_and_the_brace(self, width: int) -> None:
        for char in (" ", "\t", "\u00a0"):
            text = "```" + char * width + "{python}\nx\n```"
            assert constructs(neutralise_quarto_markup(text)) == [], (width, char)

    def test_every_whitespace_character_the_renderers_strip(self) -> None:
        """A ``.strip()`` runs after this: the rule has to see through whatever it removes, at
        either end, because what is left is a ``---`` alone on its line."""

        for char in SPACE_CHARACTERS:
            opener = neutralise_quarto_markup(f"{char}---\nfilters: [f]\n...")
            assert constructs(f"Intro.\n\n{opener.strip()}\n\nOutro.\n") == [], repr(char)
            ender = neutralise_quarto_markup(f"x\n---{char}")
            assert ender.strip().split("\n")[-1] != "---", repr(char)

    def test_every_whitespace_character_in_front_of_what_a_template_tick_completes(self) -> None:
        """06 writes a tick before the review cadence and the baseline metric, and the renderers
        strip a field. A brace, or two ticks and a brace, behind any whitespace at the start of
        the field is then right behind that tick."""

        for char in SPACE_CHARACTERS:
            brace = neutralise_quarto_markup(f"{char}{{python}} 1+1")
            assert constructs(f"`{brace.strip()}`") == [], repr(char)
            ticks = neutralise_quarto_markup(f"{char}`` {{python}}\nx\n``")
            assert constructs(f"`{ticks.strip()}`") == [], repr(char)

    @pytest.mark.parametrize("char", ["\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x85"])
    def test_the_line_ends_python_adds_are_broken_too(self, char: str) -> None:
        """Quarto does not end a line there, and the rule breaks a rule beside one anyway: it
        costs an invisible character, and a missed line end that Quarto does honour would cost
        a live block. The module says so; this holds it to that."""

        assert neutralise_quarto_markup(f"x{char}---{char}y") == f"x{char}-{Z}--{char}y"


class TestSeededFuzz:
    """Strings made of the pieces Quarto's patterns are built from, in every order the dice give.

    Half are random pieces; half are one dangerous construct built from its parts with a
    variation at each joint (what stands between the ticks and the brace, what stands before
    the ticks, which line end, how it closes), so the strings that matter are not left to chance.
    """

    PIECES = [
        "`", "``", "```", "````", "{", "}", "{{", "}}", "<", ">", "/*", "*/", "---", "...", "-",
        " ", "  ", "\t", "\n", "\n\n", "\r", "\r\n", "\u2028", "\u2029", "\ufeff", "\u00a0",
        "\u3000", "python", "r", "env", "x", "=", ",", "~~~", ":::", "#", "|", "<!--", "-->", "<!",
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
    # A ``---`` the way Quarto reads it after it deletes comments, and whitespace a renderer's
    # ``.strip()`` would remove from in front of it.
    OPENERS = ["---", "---", "---<!---->", "-<!-- c -->--", "<!-- c -->---", "--<!---->-"]
    STRIPPED = ["", " ", "  ", "\t", "\u00a0", "\u3000", "\u2003", "\x1c", "\x85", "\n "]

    @staticmethod
    def _built(dice: random.Random) -> str:
        cls = TestSeededFuzz
        kind = dice.choice(["fence", "fence", "inline", "shortcode", "metadata", "stripped"])
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
        if kind == "stripped":
            return (
                dice.choice(cls.STRIPPED)
                + dice.choice(cls.OPENERS)
                + dice.choice(ends)
                + "filters: [f]"
                + dice.choice(ends)
                + dice.choice(cls.CLOSERS)
                + dice.choice(["", "\u00a0", " ", "\n"])
            )
        return (
            dice.choice(cls.BEFORE)
            + dice.choice(ends)
            + dice.choice(cls.OPENERS)
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


# --- Session 302: the structural rules (BACKLOG.md item (7)(g)) ---------------------------------


# What each rule looks at, written out again so that a test can ask any output "is a pair left that
# Quarto, Pandoc or TeX reads?" without calling the rules. A name is the pair; the pattern finds it
# as it stands in the text, and nothing may be found in what the neutraliser returns. (The real
# tool is the judge of what these pairs do: ``test_quarto_render.py``.)
def _found(pattern: str) -> Callable[[str], bool]:
    compiled = re.compile(pattern)
    return lambda text: compiled.search(text) is not None


def _marker_ends_a_line(text: str) -> bool:
    """A run of exactly three dashes that ends a line (blanks allowed after it), by a different
    method than the module's: split on the line ends, strip the line, look at its last four
    characters. Whatever stands in front of the dashes is not asked about."""

    for line in re.split("[\n\r\x0b\x0c\x1c-\x1e\x85\u2028\u2029]", text):
        line = re.sub("[\\s\ufeff]+$", "", line)
        if line.endswith("---") and not line.endswith("----"):
            return True
    return False


# The pairs no output may hold, by the name of the rule that breaks each. Written from what the
# renderers and the tool read, not from the module's patterns.
PAIRS: dict[str, Callable[[str], bool]] = {
    "a brace": _found(r"\{(?!\u200b)"),
    "a tag, a doctype, an instruction or a comment opener": _found(
        r"<(?=[A-Za-z]|[/?!]|[^\x00-\x7f\s\u200b])"
    ),
    "a TeX command": _found(r"\\(?=[A-Za-z]|[^\x00-\x7f\s\u200b])"),
    "a character code": _found(r"\^\^"),
    "an image": _found(r"!\["),
    "a link, a reference link or a definition": _found(r"\](?=[(\[:])"),
    "the top border of a grid table": _found(r"\+[-:]"),
    "a carriage return that Pandoc deletes": _found(r"\r(?![\n\u200b])"),
    "a metadata block marker": _marker_ends_a_line,
}
CARRIAGE_RETURN_RULE = "a carriage return that Pandoc deletes"


def _as_pandoc_reads_it(text: str) -> str:
    """The text with every bare carriage return gone. Pandoc 3.6.3 deletes one before it reads a
    character (a CRLF it reads as a line end), so the characters on either side of it touch for
    Pandoc though they do not in the text. Session 302's last attack round found the rules
    unbroken by it: the oracle used to look at the text only as it stood."""

    return re.sub(r"\r(?!\n)", "", text)


def _after_each_bare_carriage_return(expected: str) -> str:
    """``expected`` with the character put after every bare carriage return, which is what the
    carriage return rule does to text that holds one (a test of another rule that uses a bare
    carriage return as a blank or a line end expects it)."""

    return re.sub(r"\r(?![\n\u200b])", "\r" + Z, expected)


def _surviving(text: str) -> list[str]:
    """The names of the pairs left in ``text``, as it stands and as Pandoc reads it."""

    read = _as_pandoc_reads_it(text)
    return [name for name, found in PAIRS.items() if found(text) or found(read)]


BLANKS = [" ", "\t", "\n", "\r", "\u00a0", "\x0b", "\x0c", "\u2003", "\u3000", "\ufeff"] + [
    chr(code) for code in range(0x1C, 0x20)
]

# What the scouts and the adversaries of Session 302 tried, one spelling each. The first group
# acted when Quarto 1.7.33 rendered it; the second is what a hand re-check and an adversary found
# through the first version of these rules (Pandoc's special attribute ``{-``, a character the
# writer put in front of a brace, a definition anywhere but the start of a line, white space and
# control characters in a destination).
ATTACKS: list[tuple[str, str]] = [
    ("script", "<script>document.title='x'</script>"),
    ("script_upper_case", "<SCRIPT SRC=//x></SCRIPT>"),
    ("img_onerror", "<img src=x onerror=alert(1)>"),
    ("iframe", '<iframe src="/outside/secret.txt"></iframe>'),
    ("link_stylesheet", '<link rel="stylesheet" href="/outside/x.css">'),
    ("style_import", '<style>@import url("/outside/x.css");</style>'),
    ("object", '<object data="/outside/secret.txt"></object>'),
    ("embed", '<embed src="/outside/secret.txt">'),
    ("anchor_javascript", '<a href="javascript:alert(1)">x</a>'),
    ("svg_onload", "<svg onload=alert(1)>"),
    ("autolink", "<https://example.com/a>"),
    ("autolink_javascript", "<javascript:alert(1)>"),
    ("doctype", "<!DOCTYPE html>"),
    ("instruction", "<?php echo 1 ?>"),
    ("cdata", "<![CDATA[ x ]]>"),
    ("closing_tag", "</div></main><script>1</script>"),
    ("comment", "a <!-- hidden --> b"),
    ("tag_with_a_non_ascii_letter", "<\u00e9x>"),
    ("input", "\\input{/outside/secret.txt}"),
    ("input_pipe", '\\input{|"kpsewhich --var-value=NAME"}'),
    ("input_in_math", "$\\input{/outside/secret.txt}$"),
    ("input_in_display_math", "$$\\input{/outside/secret.txt}$$"),
    ("input_in_a_tilde_fence", "~~~{=latex}\n\\input{/outside/secret.txt}\n~~~"),
    ("input_in_a_raw_span", "`\\input{/outside/secret.txt}`{=latex}"),
    ("character_code_for_a_backslash", "^^5cinput{/outside/secret.txt}"),
    ("character_code_for_a_letter", "$\\^^69nput{/outside/secret.txt}$"),
    ("four_caret_character_code", "^^^^005cinput{/outside/secret.txt}"),
    ("control_word_by_name", "\\csname input\\endcsname{f}"),
    ("shell_escape", "\\immediate\\write18{id}"),
    ("environment", "\\begin{verbatim}"),
    ("command_with_a_non_ascii_letter", "\\\u00e9x"),
    ("image", "![x](outside/pixel.png)"),
    ("image_reference", "![x][r]\n\n[r]: outside/pixel.png"),
    ("image_shortcut", "![r]\n\n[r]: outside/pixel.png"),
    ("image_in_a_link", "[![x](p.png)](javascript:alert(1))"),
    ("inline_link_javascript", "[x](javascript:alert(1))"),
    ("inline_link_angle", "[x](<javascript:alert(1)>)"),
    ("inline_link_entity", "[x](&#106;avascript:alert(1))"),
    ("inline_link_upper_case", "[x](JaVaScRiPt:alert(1))"),
    ("inline_link_data", "[x](data:text/html,<b>hi</b>)"),
    ("inline_link_relative", "[x](outside/secret.txt)"),
    ("inline_link_with_a_title", '[x](javascript:alert(1) "t")'),
    ("reference_link_full", "[x][r]\n\n[r]: javascript:alert(1)"),
    ("reference_link_collapsed", "[r][]\n\n[r]: javascript:alert(1)"),
    ("reference_link_spaced", "[x] [r]\n\n[r]: javascript:alert(1)"),
    ("definition_title", '[r]: javascript:alert(1) "t"'),
    ("definition_angle", "[r]: <javascript:alert(1)>"),
    ("definition_destination_on_the_next_line", "[r]:\n  javascript:alert(1)"),
    ("definition_indented", "   [r]: javascript:alert(1)"),
    ("definition_in_a_block_quote", "> [r]: javascript:alert(1)"),
    ("definition_in_a_list_item", "- [r]: javascript:alert(1)"),
    ("definition_in_a_numbered_item", "1. [r]: javascript:alert(1)"),
    ("definition_in_a_table_cell", "| a |\n|---|\n| [r]: javascript:alert(1) |"),
    ("definition_after_text", "text [r]: javascript:alert(1)"),
    ("definition_with_a_nested_label", "[a [b] c]: javascript:alert(1)\n\n[a [b] c]"),
    ("definition_with_a_label_over_two_lines", "[a\nb]: javascript:alert(1)\n\n[a b]"),
    ("definition_with_an_escaped_bracket", "[a\\]b]: javascript:alert(1)\n\n[a\\]b]"),
    ("definition_with_the_writers_character_before_the_label", "\u200b[r]: javascript:alert(1)"),
    ("footnote_definition", "[^1]: javascript:alert(1)\n\nx[^1]"),
    ("heading_attribute", '## H {#i onclick="alert(1)"}'),
    ("heading_attribute_without_a_marker", '## H {onclick="alert(1)"}'),
    ("heading_special_attribute", '## H {- onclick="alert(1)"}'),
    ("heading_special_attribute_with_style", '## H {- style="background-image:url(x.css)"}'),
    ("heading_class", "## H {.a}"),
    ("heading_with_the_writers_character_before_the_brace", '## H \u200b{onclick="alert(1)"}'),
    ("heading_setext", 'H {onclick="alert(1)"}\n==='),
    ("span_attribute", '[x]{onclick="alert(1)"}'),
    ("span_special_attribute", '[x]{- onclick="alert(1)"}'),
    ("span_with_the_writers_character_before_the_brace", '[x]\u200b{onclick="alert(1)"}'),
    ("div_attribute", '::: {onclick="alert(1)"}\ntext\n:::'),
    ("div_special_attribute", '::: {- onclick="alert(1)"}\ntext\n:::'),
    ("link_special_attribute", "[x](u){- onclick}"),
    ("link_attribute", "[x](u){onclick=alert(1)}"),
    ("code_span_attribute", '`x`{onclick="alert(1)"}'),
    ("raw_span", "`<b>x</b>`{=html}"),
    ("raw_block_tilde", "~~~{=html}\n<script>1</script>\n~~~"),
    ("raw_block_tilde_with_a_space", "~~~ {=html}\n<script>1</script>\n~~~"),
    ("raw_block_tick", "```{=html}\n<script>1</script>\n```"),
    ("fence_attribute", '```{.js onclick="alert(1)"}\nx\n```'),
    ("image_attribute", "![x](p){onerror=1}"),
    ("shortcode", "{{< include secret.txt >}}"),
    ("shortcode_without_spaces", "{{<env HOME>}}"),
    ("cell", "```{python}\nopen('ran', 'w')\n```"),
    ("inline_chunk", "`{python} 1+1`"),
    # Session 302, second round: a metadata block does not have to start a line. Pandoc opens one
    # on ``---`` and a blank line behind the prefix of a container, and in a ``.qmd`` Quarto passes
    # its keys on (``css`` was inlined into a page, ``header-includes`` put raw HTML in it).
    ("metadata_in_a_block_quote", "> ---\n> css: /outside/x.css\n> ---"),
    ("metadata_in_a_nested_quote", "> > ---\n> > css: /outside/x.css\n> > ---"),
    ("metadata_in_a_quote_without_a_space", ">---\n>css: /outside/x.css\n>---"),
    ("metadata_in_a_second_paragraph_of_a_bullet", "- a\n\n  ---\n  css: /outside/x.css\n  ---"),
    ("metadata_in_a_plus_item", "+ ---\n  css: /outside/x.css\n  ---"),
    ("metadata_in_a_numbered_item", "1. ---\n   css: /outside/x.css\n   ---"),
    ("metadata_in_a_lettered_item", "(a) ---\n    css: /outside/x.css\n    ---"),
    ("metadata_in_a_footnote", "x[^1]\n\n[^1]: a\n\n    ---\n    css: /outside/x.css\n    ---"),
    ("metadata_in_a_definition", "Term\n:   ---\n    css: /outside/x.css\n    ---"),
    ("metadata_in_a_quoted_list", "> - a\n>\n>   ---\n>   css: /outside/x.css\n>   ---"),
    ("metadata_in_a_fenced_div", "::: x\n---\ncss: /outside/x.css\n---\n:::"),
    ("metadata_after_text_on_the_line", "text ---\ncss: /outside/x.css\n---"),
    ("metadata_with_carriage_returns_in_a_quote", "> ---\r\n> css: /outside/x.css\r\n> ---\r\n"),
    (
        "metadata_in_a_grid_table_cell",
        "+----------+\n| ---      |\n| css: /outside/x.css |\n| ---      |\n+----------+",
    ),
    ("grid_table_with_an_alignment", "+:---+\n| ---  |\n+------+"),
    (
        "metadata_key_that_puts_html_in_the_page",
        "> ---\n> header-includes: <script>1</script>\n> ---",
    ),
    # Session 302, after the last attack round: Pandoc deletes a bare carriage return before it
    # reads a character, so a pair with one between its halves is whole again (measured with
    # Quarto 1.7.33, in a ``.md`` and a ``.qmd`` as HTML: an ``img`` with ``onerror``, a
    # ``javascript:`` link; Pandoc: ``\\input`` as raw TeX, a metadata block, a character code).
    ("carriage_return_in_a_tag", "<\rimg src=x onerror=alert(1)>"),
    ("carriage_return_in_a_script", "<\rscript>alert(1)</script>"),
    ("carriage_return_in_a_closing_tag", "<\r/div>"),
    ("carriage_return_in_a_comment", "<!\r--hidden-->"),
    ("carriage_return_in_a_link", "[x]\r(javascript:alert(1))"),
    ("carriage_return_in_a_reference_link", "[x]\r[r]\n\n[r]\r: javascript:alert(1)"),
    ("carriage_return_in_an_image", "!\r[x](outside/pixel.png)"),
    ("carriage_return_in_a_tex_command", "\\\rinput /outside/secret.txt"),
    ("carriage_return_in_a_tex_command_with_braces", "\\\rinput{/outside/secret.txt}"),
    ("carriage_return_in_math", "$\\\rinput{/outside/secret.txt}$"),
    ("carriage_return_in_a_character_code", "$^\r^5cinput{/outside/secret.txt}$"),
    ("carriage_return_in_a_marker", "x\n\n-\r--\ncss: /outside/x.css\n...\n"),
    ("carriage_return_in_a_grid_table_border", "+\r---+\n| a |\n+---+"),
    ("two_carriage_returns_in_a_tag", "<\r\rimg src=x onerror=1>"),
    ("carriage_returns_around_a_crlf", "<\r\r\nimg>\r\r\n[x]\r(u)"),
]

# A character that stands where the second half of a pair would, put there by the writer. Each
# turns an ordinary spelling into one the first version of these rules skipped or Pandoc reads
# through.
WRITER_CHARACTER_ATTACKS: list[tuple[str, str]] = [
    ("before_a_brace", f'## H {Z}{{onclick="alert(1)"}}'),
    ("before_two_braces", f"{Z}{{{Z}{{< env HOME >}}"),
    ("after_a_brace_then_a_blank", f'## H {{{Z} onclick="alert(1)"}}'),
    ("between_a_bracket_and_a_paren", f"[x]{Z} (javascript:alert(1))"),
    ("before_a_bracket", f"{Z}[r]: javascript:alert(1)"),
    ("after_a_bang", f"!{Z}[x](p.png)"),
    ("after_a_lt", f"<{Z}b>x</b>"),
    ("in_a_comment", f"<!{Z}--\n---\nfilters: [f]\n...\n-->"),
]


class TestTheStructuralRules:
    """Six rules that each look at one pair of characters and decide from the right-hand one, one
    that looks at a bare carriage return (which Pandoc deletes), and one (the marker) that looks
    at the end of a line."""

    @pytest.mark.parametrize(("name", "text"), ATTACKS, ids=[n for n, _ in ATTACKS])
    def test_no_pair_is_left_in_any_attack(self, name: str, text: str) -> None:
        out = neutralise_quarto_markup(text)
        assert _surviving(out) == [], repr(out)
        assert out != text
        assert out.replace(Z, "") == text.replace(Z, "")
        assert neutralise_quarto_markup(out) == out

    @pytest.mark.parametrize(
        ("name", "text"), WRITER_CHARACTER_ATTACKS, ids=[n for n, _ in WRITER_CHARACTER_ATTACKS]
    )
    def test_a_character_the_writer_puts_in_the_way_changes_nothing(
        self, name: str, text: str
    ) -> None:
        """The first version skipped a brace that had the character on either side. The writer
        controls where it stands: a rule that looks at what is in front of a brace is a rule the
        writer can switch off, so these look at what follows."""

        out = neutralise_quarto_markup(text)
        assert _surviving(out) == [], repr(out)
        assert out.replace(Z, "") == text.replace(Z, "")
        assert neutralise_quarto_markup(out) == out

    @pytest.mark.parametrize("blank", BLANKS, ids=[repr(b) for b in BLANKS])
    def test_nothing_in_a_destination_can_save_a_link(self, blank: str) -> None:
        """Pandoc strips white space from a destination and a browser strips control characters
        from an address, so ``[x](<blank>javascript:...)`` is a ``javascript:`` link. The rule
        never reads the destination, so no blank changes the result."""

        for opener in ("[x](", "[x](<", "[r]: ", "> [r]: ", "- [r]: ", "[a [b] c]: ", "[x]["):
            text = f"{opener}{blank}javascript:alert(1)"
            out = neutralise_quarto_markup(text)
            assert _surviving(out) == [], (opener, blank, out)
            assert out.replace(Z, "") == text

    @pytest.mark.parametrize("blank", BLANKS, ids=[repr(b) for b in BLANKS])
    def test_nothing_after_a_brace_can_save_an_attribute(self, blank: str) -> None:
        """The attribute grammar skips blanks after the brace, and the first version listed what
        may follow one. A blank, a dash, a dot, a hash, an equals sign or a letter after the brace:
        the rule does not ask."""

        for after in (blank, "-", ".a", "#i", "=html", "k=v", f"{blank}-"):
            text = f'## H {{{after} onclick="x"}}'
            out = neutralise_quarto_markup(text)
            assert _surviving(out) == [], (after, out)
            expected = f'## H {{{Z}{after} onclick="x"}}'
            assert out == _after_each_bare_carriage_return(expected)

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            # The brace rule: the character goes after every brace that does not have one.
            ("## H {#sec-x}", "## H {" + Z + "#sec-x}"),
            ("[x]{.cls}", "[x]{" + Z + ".cls}"),
            ('[x]{onclick="a"}', "[x]{" + Z + 'onclick="a"}'),
            ('## H {- onclick="a"}', "## H {" + Z + '- onclick="a"}'),
            ("~~~{=html}", "~~~{" + Z + "=html}"),
            ("{ onclick=a}", "{" + Z + " onclick=a}"),
            ("{\tonclick=a}", "{" + Z + "\tonclick=a}"),
            ("{\nonclick=a}", "{" + Z + "\nonclick=a}"),
            ("{\u00a0onclick=a}", "{" + Z + "\u00a0onclick=a}"),
            ("x {", "x {" + Z),
            ("{", "{" + Z),
            ("{{", "{" + Z + "{" + Z),
            ("{{{", "{" + Z + "{" + Z + "{" + Z),
            ("}{", "}{" + Z),
            # ... and leaves a brace alone that has it behind it already, wherever else it stands.
            ("## H {" + Z + 'onclick="a"}', "## H {" + Z + 'onclick="a"}'),
            ("{" + Z + "{", "{" + Z + "{" + Z),
            (Z + "{" + Z, Z + "{" + Z),
            ("## H " + Z + '{onclick="a"}', "## H " + Z + "{" + Z + 'onclick="a"}'),
            # Raw HTML: ``<`` before a letter, ``/``, ``?`` or ``!``.
            ("<b>", "<" + Z + "b>"),
            ("</b>", "<" + Z + "/b>"),
            ("<?xml ?>", "<" + Z + "?xml ?>"),
            ("<!DOCTYPE html>", "<" + Z + "!DOCTYPE html>"),
            ("<!--", "<" + Z + "!--"),
            ("<![CDATA[x]]>", "<" + Z + "!" + Z + "[CDATA[x]]>"),
            ("<\u00e9x>", "<" + Z + "\u00e9x>"),
            ("<" + Z + "b>", "<" + Z + "b>"),
            ("a < b <5 <= <", "a < b <5 <= <"),
            # A backslash before a letter, and a character code for one.
            ("\\input{f}", "\\" + Z + "input{" + Z + "f}"),
            ("$\\frac{a}{b}$", "$\\" + Z + "frac{" + Z + "a}{" + Z + "b}$"),
            ("\\\u00e9", "\\" + Z + "\u00e9"),
            ("\\\\input", "\\\\" + Z + "input"),
            ("\\1 \\_ \\( \\ \\%", "\\1 \\_ \\( \\ \\%"),
            ("\\" + Z + "input", "\\" + Z + "input"),
            ("^^5c", "^" + Z + "^5c"),
            ("^^^", "^" + Z + "^" + Z + "^"),
            ("^^^^005c", "^" + Z + "^" + Z + "^" + Z + "^005c"),
            ("x^2^3", "x^2^3"),
            # An image, a link, a reference link and a definition.
            ("![a](b)", "!" + Z + "[a]" + Z + "(b)"),
            ("![a][b]", "!" + Z + "[a]" + Z + "[b]"),
            ("![a]", "!" + Z + "[a]"),
            ("[a](b)", "[a]" + Z + "(b)"),
            ("[a][b]", "[a]" + Z + "[b]"),
            ("[a][]", "[a]" + Z + "[]"),
            ("[a]: b", "[a]" + Z + ": b"),
            ("> [a]: b", "> [a]" + Z + ": b"),
            ("- [a]: b", "- [a]" + Z + ": b"),
            ("[a [b] c]: d", "[a [b] c]" + Z + ": d"),
            ("[a\nb]: d", "[a\nb]" + Z + ": d"),
            ("[a\\]b]: d", "[a\\]b]" + Z + ": d"),
            ("[a](b){- onclick}", "[a]" + Z + "(b){" + Z + "- onclick}"),
            ("[^1]: note", "[^1]" + Z + ": note"),
            (
                "[a] (b) and [c] [d] and [e] : f and [g]h",
                "[a] (b) and [c] [d] and [e] : f and [g]h",
            ),
            ("[a]" + Z + "(b)", "[a]" + Z + "(b)"),
            # A bare carriage return, which Pandoc deletes: the character goes after it.
            ("a\rb", "a\r" + Z + "b"),
            ("a\r", "a\r" + Z),
            ("\r\r", "\r" + Z + "\r" + Z),
            ("<\rb>", "<\r" + Z + "b>"),
            ("\\\rinput", "\\\r" + Z + "input"),
            ("a\r\nb", "a\r\nb"),
            ("a\r\r\nb", "a\r" + Z + "\r\nb"),
            ("a\r" + Z + "b", "a\r" + Z + "b"),
        ],
    )
    def test_where_the_character_goes(self, text: str, expected: str) -> None:
        assert neutralise_quarto_markup(text) == expected

    def test_every_rule_has_a_text_that_only_it_breaks(self) -> None:
        """A mutant per rule: with one rule removed the pairs it looks at survive, so no rule is
        redundant and none is untested. (The rules are applied here one by one, as the function
        does, from the module's own table.)"""

        rules = {name: (pattern, replacement) for name, pattern, replacement in markup._RULES}
        assert set(rules) == set(PAIRS)
        for omitted in rules:
            text = "".join(t for _, t in ATTACKS)
            for name, (pattern, replacement) in rules.items():
                if name != omitted:
                    text = pattern.sub(replacement, text)
            surviving = _surviving(text)
            if omitted == CARRIAGE_RETURN_RULE:
                # Without it the carriage returns stay, and Pandoc puts the other pairs together.
                assert omitted in surviving and len(surviving) > 1, surviving
            else:
                assert surviving == [omitted], omitted

    def test_the_rules_can_run_in_any_order(self) -> None:
        """Each rule inserts the character after the left half of its pair, and decides from the
        right half; no rule's inserted character stands where another looks, so the order
        cannot matter. The module says so, and relies on it for idempotence."""

        rules = [(pattern, replacement) for _, pattern, replacement in markup._RULES]
        dice = random.Random(302)
        samples = [t for _, t in ATTACKS] + TestStructuralFuzz.strings(2_000, seed=3020)
        for text in samples:
            expected = text
            for pattern, replacement in rules:
                expected = pattern.sub(replacement, expected)
            assert expected == neutralise_quarto_markup(text), repr(text)
            for _ in range(3):
                shuffled = dice.sample(rules, len(rules))
                out = text
                for pattern, replacement in shuffled:
                    out = pattern.sub(replacement, out)
                assert out == expected, repr(text)

    # What can stand in front of a metadata marker: the prefix of every container Pandoc opens a
    # block in, none of them listed by the rule. (Measured: a block quote, a bullet's and a numbered
    # item's second block, ``+ ``, a footnote, a definition and a grid table cell each opened a
    # block in Quarto 1.7.33's Pandoc; the rest are the same shapes with the prefixes combined.)
    PREFIXES = [
        "", " ", "  ", "    ", "\t", "> ", ">", "> > ", ">> ", "- ", "+ ", "* ", "1. ", "1) ",
        "(a) ",
        "a. ", "iv. ", "#. ", "(@) ", ":   ", ": ", "    ", "  - > ", "> - > ", "| ",
        "x", "word ", "a.b", "# ", "| a | ", "\u00a0", "\u3000", "\u200b",
    ]  # fmt: skip

    @pytest.mark.parametrize("prefix", PREFIXES, ids=[repr(x) for x in PREFIXES])
    @pytest.mark.parametrize("blank", ["", " ", "\t", "  \t "] + BLANKS, ids=repr)
    def test_a_marker_is_broken_behind_any_prefix_and_in_front_of_any_blank(
        self, prefix: str, blank: str
    ) -> None:
        """The marker rule asks what follows the dashes and whether they are a run of three. A
        prefix the writer controls cannot switch it off, and no blank (or none) behind the dashes
        makes a difference, up to the end of the line."""

        for line_end in ("\n", "\r\n", "\r", "\u2028", ""):
            tail = "css: /outside/x.css" if line_end else ""
            text = f"{prefix}---{blank}{line_end}{tail}"
            out = neutralise_quarto_markup(text)
            expected = f"{prefix}-{Z}--{blank}{line_end}{tail}"
            assert out == _after_each_bare_carriage_return(expected), repr(text)
            assert _surviving(out) == [], repr(out)

    @pytest.mark.parametrize(
        "text",
        [
            "----",
            "-----\n",
            "x----",
            "-- -",
            "---a",
            "--- a",
            "- - -",
            "-\u200b--",
            "---\u200b",
            "--",
        ],  # fmt: skip
    )
    def test_what_is_no_marker_is_left_alone(self, text: str) -> None:
        """A longer run is a horizontal rule or text, a dash with the character in it is already
        broken, and a run with text after it on the line is not a marker: none of them is changed,
        so the rule costs only the lines it names."""

        assert neutralise_quarto_markup(text) == text

    def test_a_letter_does_not_depend_on_the_pythons_table_of_letters(self) -> None:
        """After ``<`` and after a backslash, every code point is decided by a rule that does not
        ask Python which characters are letters: Python 3.11 (Unicode 14) and 3.12 (Unicode 15.0)
        miss letters that Pandoc 3.6.3 reads as a tag or a command (4,970 and 622 code points were
        measured), so a table-driven rule gave a different answer on each supported Python. The
        expected set is written out here: an ASCII letter, ``/``, ``?`` or ``!`` after ``<``, and
        an ASCII letter after a backslash, or any character above U+007F that is not white space
        and not the inserted character after either. Every code point, one per pair."""

        points = [c for c in range(0x110000) if not 0xD800 <= c <= 0xDFFF]
        non_ascii = {c for c in points if c > 0x7F and not chr(c).isspace() and c != 0x200B}
        letters = {ord(x) for x in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"}
        for opener, extra, rule in (
            ("<", set(map(ord, "/?!")), markup._RAW_HTML),
            ("\\", set(), markup._TEX_COMMAND),
        ):
            expected = letters | extra | non_ascii
            text = "".join(f"{opener}{chr(c)}x" for c in points)
            hit = {
                ord(m.group(0)[1])
                for m in re.finditer(re.escape(opener) + r"[\s\S]", text)
                if rule.match(text, m.start())
            }
            assert hit == expected, (opener, sorted(hit ^ expected)[:10])

    def test_a_grid_table_is_no_table_and_a_plus_is_otherwise_left_alone(self) -> None:
        assert neutralise_quarto_markup("+---+---+\n| a | b |\n+---+---+") == (
            "+" + Z + "---+" + Z + "---+\n| a | b |\n+" + Z + "---+" + Z + "---+"
        )
        assert neutralise_quarto_markup("+:---+") == "+" + Z + ":---+"
        for text in ("x += 1", "1 + 2", "+1", "a+b", "+=", "+ -", "+\n-"):
            assert neutralise_quarto_markup(text) == text, text


class TestStructuralFuzz:
    """Strings made of the characters the rules look at, in the orders the dice give."""

    PIECES = [
        "{", "}", "<", "</", "<a", "<!", "<?", "\\", "\\i", "\\1", "^", "^^", "!", "![", "[", "]",
        "](", "][", "]:", "(", ")", ":", " ", "\n", "\t", Z, "\u00a0", "\x0c", "\x1f", "\u3000",
        "javascript:", "x", "---", "`", "$", "-", "=", "#", ".", '"', "&#106;", "onclick", "~~~",
        "+", "+-", "> ", "- ", "1. ", "|", "----", "\r\n", "\r", "\r", "\r" + Z,
    ]  # fmt: skip

    @staticmethod
    def strings(count: int, seed: int) -> list[str]:
        dice = random.Random(seed)
        pieces = TestStructuralFuzz.PIECES
        return [
            "".join(dice.choice(pieces) for _ in range(dice.randint(1, 16))) for _ in range(count)
        ]

    def test_no_pair_is_left_and_only_the_character_was_added(self) -> None:
        flagged_raw = 0
        for text in self.strings(30_000, seed=302):
            out = neutralise_quarto_markup(text)
            assert out.replace(Z, "") == text.replace(Z, ""), repr(text)
            assert neutralise_quarto_markup(out) == out, repr(text)
            assert _surviving(out) == [], (repr(text), repr(out))
            for place in CONTEXTS.values():
                assert constructs(place(out)) == [], (repr(text), place("."))
            if _surviving(text):
                flagged_raw += 1
        # The dice must produce text the rules act on, or the loop above proves nothing.
        assert flagged_raw > 20_000

    def test_text_without_a_pair_comes_back_unchanged(self) -> None:
        clean = 0
        for text in self.strings(30_000, seed=3021):
            if not _surviving(text):
                assert neutralise_quarto_markup(text) == text, repr(text)
                clean += 1
        assert clean > 50


@contextlib.contextmanager
def _deadline(seconds: int) -> Iterator[None]:
    """Raise ``TimeoutError`` if the block takes longer (where signals allow it).

    Python's ``re`` looks for a pending signal while it matches, so this stops a pattern that
    backtracks without end; without it that failure is a hang, not a red test. Windows has no
    ``SIGALRM`` and a worker thread cannot take one, and there the block simply runs.
    """

    if not hasattr(signal, "SIGALRM") or threading.current_thread() is not threading.main_thread():
        yield
        return

    def stop(signum: int, frame: Any) -> None:
        raise TimeoutError(f"took longer than {seconds} seconds")

    previous = signal.signal(signal.SIGALRM, stop)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


@pytest.fixture(autouse=True)
def _no_test_may_hang() -> Iterator[None]:
    """Every test in this module runs under a deadline of a minute where the platform has one.

    The timing tests below carry a tighter one of their own, but a pattern that backtracks
    without end can also stall a test above them (a sweep, a fuzz round), and then the run hangs
    before it reaches a test that would have named the problem. This turns that hang into a
    failure in the test that hit it; no test here takes more than a few seconds."""

    with _deadline(60):
        yield


class TestItIsFastOnTextAModelWrote:
    """The patterns are built to be linear: a long run of the pieces they look for is the input
    that makes an ordinary pattern quadratic.

    The patterns take about ten milliseconds for 100,000 characters. A quadratic pattern needs
    tens of seconds for the same input (the pattern did, in a scratch copy with the guard against
    restarting inside a run of ticks removed), so a bound of two seconds separates them with room
    on a slow machine. A pattern that backtracks exponentially never returns, so each case also
    runs under a deadline of twenty seconds where the platform has one: that fails the test
    instead of hanging the run.
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
            "<" * N,
            "<a" * (N // 2),
            "\\a" * (N // 2),
            "^" * N,
            "![" * (N // 2),
            "]" * N,
            "](" * (N // 2),
            "][:" * (N // 3),
        ],
        ids=[
            "backticks", "fence_then_spaces", "fence_then_spaces_then_brace", "many_fences",
            "tick_brace", "double_braces", "shortcode_openers", "dashes_at_line_starts",
            "dashes_and_spaces", "dashes_then_spaces", "dashes", "newlines", "braces",
            "angle_brackets", "tags", "backslash_letters", "carets", "image_openers",
            "closing_brackets", "link_joints", "bracket_colons",
        ],
    )  # fmt: skip
    def test_a_long_run_takes_seconds_not_minutes(self, text: str) -> None:
        with _deadline(20):
            start = time.perf_counter()
            neutralise_quarto_markup(text)
            assert time.perf_counter() - start < 2

    def test_a_gap_that_backtracks_badly_cannot_hang_the_run(self) -> None:
        """The shape that makes a nested quantifier exponential: whitespace that can be split
        between two repeats, then something that fails."""

        with _deadline(20):
            neutralise_quarto_markup("```" + " " * 60 + "x")

    @pytest.mark.parametrize(
        ("hostile", "expected"),
        [
            ("{{< env HOME >}}", "{" + Z + "{" + Z + "< env HOME >}}"),
            ("`{python} 1`", "`{" + Z + "python} 1`"),
            ("<!-- c -->", "<" + Z + "!-- c -->"),
            ("<script>x</script>", "<" + Z + "script>x<" + Z + "/script>"),
            ("\\input{f}", "\\" + Z + "input{" + Z + "f}"),
            ("![x](y)", "!" + Z + "[x]" + Z + "(y)"),
        ],
    )
    def test_a_construct_after_a_long_text_is_still_broken(
        self, hostile: str, expected: str
    ) -> None:
        """The cost of the patterns must not come from skipping text: the construct is found
        at the end of a hundred thousand ordinary characters and of one very long line."""

        for filler in ("word " * 40_000, "a" * 200_000):
            assert neutralise_quarto_markup(filler + hostile) == filler + expected
            assert neutralise_quarto_markup(filler + "\n" + hostile) == filler + "\n" + expected

    def test_a_rule_after_a_long_text_is_still_broken(self) -> None:
        filler = "word " * 40_000
        assert neutralise_quarto_markup(filler + "\n---\nx") == filler + "\n-" + Z + "--\nx"


class TestReports:
    """``neutralise_report`` walks a report as ``model_dump`` returns it."""

    def test_every_string_at_every_depth_is_neutralised(self) -> None:
        report = {
            "a": "{{< env HOME >}}",
            "b": ["---", {"c": "`{python} 1`", "d": ("```{r}", 7)}],
            "e": {"f": {"g": ["x", "{{<"]}},
        }
        assert neutralise_report(report) == {
            "a": "{" + Z + "{" + Z + "< env HOME >}}",
            "b": ["-" + Z + "--", {"c": "`{" + Z + "python} 1`", "d": ("```{" + Z + "r}", 7)}],
            "e": {"f": {"g": ["x", "{" + Z + "{" + Z + "<"]}},
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
    # The renderers strip a field after neutralising it.
    "a_block_behind_a_space": " ---\nfilters:\n  - f.lua\n...",
    "a_block_behind_no_break_spaces": "\u00a0\u00a0---\nfilters:\n  - f.lua\n...",
    "a_block_behind_blank_lines": "\n\n  ---\nfilters:\n  - f.lua\n...",
    "a_rule_before_trailing_spaces": "x\n---\u00a0",
    # Quarto deletes comments before it looks for the block.
    "a_block_opened_through_a_comment": "x\n\n---<!---->\nfilters:\n  - f.lua\n...",
    "a_block_opened_between_dashes": "-<!-- c -->--\nfilters:\n  - f.lua\n...",
    # 06 writes a backtick in front of the review cadence.
    "two_ticks_a_space_and_a_brace": "`` {python}\nopen('ran', 'w')\n``",
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

    def test_no_notebook_the_agent_writes_carries_a_construct_it_was_not_given(
        self, intake_report: IntakeReport, data_report: DataReport
    ) -> None:
        """Every file that Quarto would treat as a notebook, wherever it is built, not a list of
        the seven this module knew about: ``analysis/fairness_audit.qmd`` comes from the
        governance templates and only when the intake uses protected attributes. A notebook
        that someone adds tomorrow is covered the day it appears."""

        def agent_files(planted: bool) -> dict[str, str]:
            intake, data = _reports(intake_report, data_report)
            counter = [0]
            if planted:
                intake = _plant(intake, lambda n: PAYLOADS["everything"], counter)
                data = _plant(data, lambda n: PAYLOADS["everything"], counter)
            intake["governance"] = {
                **(intake.get("governance") or {}),
                "uses_protected_attributes": True,
            }
            return {
                **_build(intake, data),
                **build_analysis_files(intake=intake, project_slug="subrogation_model"),
            }

        baseline, hostile = agent_files(False), agent_files(True)
        notebooks = sorted(p for p in hostile if p.endswith((".qmd", ".ipynb", ".Rmd", ".rmd")))
        assert "analysis/fairness_audit.qmd" in notebooks
        assert set(QMD_FILES) <= set(notebooks)
        for path in notebooks:
            assert _kinds(hostile[path]) == _kinds(baseline[path]), path

    @pytest.mark.parametrize(
        ("start", "end"),
        [
            ("2024-01-01", "abcdef\n---junk"),
            ("x\n---\nk: v", "2024-02-01"),
            ("x\n---\nk: v", "abcdef\n---junk"),
        ],
        ids=["end", "start", "both"],
    )
    def test_a_cut_date_cannot_leave_a_rule_alone_on_a_line(self, start: str, end: str) -> None:
        """The measurement window is a datetime in a validated report, so only a hand-built dict
        holds text there; ``[:10]`` of it can end in ``---``, and the template's newline follows;
        and a newline inside it puts a ``---`` on a line of its own wherever it falls."""

        def render(first: str, last: str) -> str:
            data = {
                "baseline_snapshot": {
                    "measurement_window_start": first,
                    "measurement_window_end": last,
                }
            }
            return render_qmd_implementation_plan(
                intake={"value_measurement_plan": {"decision_rights": "..."}}, data=data
            )

        def rules(text: str) -> list[str]:
            return [line for line in text.split("\n") if line.rstrip(" \t") == "---"]

        out, plain = render(start, end), render("2024-01-01", "2024-02-01")
        assert _kinds(out) == _kinds(plain) == Counter({"metadata_block": 1})  # the header
        assert len(rules(out)) == len(rules(plain))

    @pytest.mark.parametrize("lead", [" ", "\t", "\u00a0", "\n", " \n "])
    def test_a_field_the_renderer_strips_cannot_start_a_block(self, lead: str) -> None:
        text = lead + "---\nfilters:\n  - f.lua\n..."
        intake = {"business_problem": text, "proposed_solution": text}
        out = render_qmd_business_understanding(intake=intake)
        assert _kinds(out) == Counter({"metadata_block": 1})
        # 02 holds a cell of its own, so it is compared with the same notebook for plain text.
        data_out = render_qmd_data(data={"summary": text}, project_slug="subrogation_model")
        plain = render_qmd_data(data={"summary": "Plain."}, project_slug="subrogation_model")
        assert _kinds(data_out) == _kinds(plain)

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

    def test_the_markdown_files_are_changed_with_the_notebooks(
        self,
        intake_report: IntakeReport,
        data_report: DataReport,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The scope, pinned so that changing it is a decision. Quarto renders a ``.md`` it is
        asked to render as it does a ``.qmd`` (it runs no code in one, but ``{{< env >}}`` and
        ``{{< include >}}`` expand and a second ``---`` block is read), and nothing the generated
        project does stops someone asking: so the four base ``.md`` files that quote a report
        change with the four notebooks, and nothing else does (the JSON mirrors and the SQL are
        not rendered). The governance ``.md`` files are held in ``TestTheMarkdownRenderers``."""

        with_it = _planted_build(intake_report, data_report, PAYLOADS["everything"])
        monkeypatch.setattr(templates, "neutralise_report", lambda value: value)
        without_it = _planted_build(intake_report, data_report, PAYLOADS["everything"])
        changed = {path for path in with_it if with_it[path] != without_it[path]}
        assert changed == {
            "analysis/01_business_understanding.qmd",
            "analysis/02_data.qmd",
            "analysis/05_initial_models.qmd",
            "analysis/06_implementation_plan.qmd",
            "README.md",
            "data/README.md",
            "reports/intake_report.md",
            "reports/data_report.md",
        }


# --- The .md renderers --------------------------------------------------------------------

_NAME = "subrogation-model"


class TestTheReadmeTellsAReaderWhatRenderingCanDo:
    """The neutraliser stops the constructs it lists and claims no more, so the README says what
    is left: report text is a language model's, rendering to PDF or to a self-contained page can
    read files and environment variables, and a page can carry markup. Nothing else pins the
    paragraph, and the module's last sentence points a reader to it."""

    def _readme(self, intake_report: IntakeReport, data_report: DataReport) -> str:
        intake, data = _reports(intake_report, data_report)
        return templates.render_readme(intake=intake, project_name="p", data=data)

    def test_it_follows_the_render_command_and_comes_before_the_license(
        self, intake_report: IntakeReport, data_report: DataReport
    ) -> None:
        readme = self._readme(intake_report, data_report)
        command = "uv run --extra notebooks quarto render analysis/03_eda.qmd\n```\n"
        assert readme.count(command) == 1
        advice = readme.split(command)[1].split("## License")[0]
        assert advice.startswith("\n"), advice
        flat = " ".join(advice.split())
        for phrase in (
            "report text quoted in these files was written by a language model",
            "stakeholder's words and from database content",
            "Rendering to PDF or to a self-contained page",
            "(`embed-resources: true`)",
            "can read files and environment variables on the machine that renders",
            "an HTML page can carry markup that came from that text",
            "Read the text before you render to PDF or publish a rendered page.",
        ):
            assert phrase in flat, phrase
        assert "## License" in readme

    def test_it_claims_nothing_about_the_text_being_safe(
        self, intake_report: IntakeReport, data_report: DataReport
    ) -> None:
        readme = self._readme(intake_report, data_report)
        advice = readme.split("quarto render analysis/03_eda.qmd\n```\n")[1].split("## License")[0]
        assert 3 <= advice.count(". ") + advice.count(".\n") <= 4
        for word in ("safe", "sanitis", "sanitiz", "trusted", "clean", "secure", "protect"):
            assert word not in advice.lower(), word

    def test_it_is_the_same_paragraph_whatever_the_reports_hold(
        self, intake_report: IntakeReport, data_report: DataReport
    ) -> None:
        def advice(readme: str) -> str:
            after_command = readme.split("quarto render analysis/03_eda.qmd\n```\n")[1]
            return after_command.split("## License")[0]

        intake, data = _reports(intake_report, data_report)
        hostile = templates.render_readme(
            intake={**intake, "business_problem": PAYLOADS["everything"]},
            project_name="p",
            data=data,
        )
        assert advice(self._readme(intake_report, data_report)) == advice(hostile)


def _mapping_for(intake: dict[str, Any]) -> dict[str, list[str]]:
    frameworks = list((intake.get("governance") or {}).get("regulatory_frameworks") or [])
    return build_regulatory_mapping(frameworks=frameworks, emitted_paths=set())


# Every renderer that writes a ``.md`` and takes a report, each called the way a test or a caller
# would call it on its own.
MARKDOWN_RENDERERS: dict[str, Callable[[dict[str, Any], dict[str, Any]], str]] = {
    "README.md": lambda i, d: templates.render_readme(intake=i, project_name=_NAME, data=d),
    "data/README.md": lambda i, d: templates.render_data_readme(data=d),
    "reports/intake_report.md": lambda i, d: templates.render_reports_intake_md(intake=i),
    "reports/data_report.md": lambda i, d: templates.render_reports_data_md(data=d),
    "governance/model_card.md": lambda i, d: governance_templates.render_model_card(
        intake=i, project_name=_NAME
    ),
    "governance/change_log.md": lambda i, d: governance_templates.render_change_log(intake=i),
    "governance/three_pillar_validation.md": (
        lambda i, d: governance_templates.render_three_pillar_validation(intake=i)
    ),
    "governance/ongoing_monitoring.md": (
        lambda i, d: governance_templates.render_ongoing_monitoring(intake=i)
    ),
    "governance/impact_assessment.md": (
        lambda i, d: governance_templates.render_impact_assessment(intake=i)
    ),
    "governance/regulatory_mapping.md": lambda i, d: governance_templates.render_regulatory_mapping(
        intake=i, mapping=_mapping_for(i)
    ),
    "governance/eu_ai_act_compliance.md": (
        lambda i, d: governance_templates.render_eu_ai_act_compliance(intake=i)
    ),
    "data/datasheet_x.md": lambda i, d: governance_templates.render_datasheet(
        query=d["primary_queries"][0], stem="x"
    ),
}

# The three that take no report text: nothing to neutralise, so nothing in the table above.
MARKDOWN_WITHOUT_REPORT_TEXT = {
    "governance/deployment_gates.md",
    "governance/lcp_integration.md",
    "governance/audit_log/README.md",
}

# Those the planted build below puts text in. ``three_pillar_validation.md`` and
# ``eu_ai_act_compliance.md`` quote only an enum and two flags, which the build keeps valid so
# that every file is written; the renderer tests above plant a payload in those fields too.
MARKDOWN_THAT_QUOTE_TEXT = {
    "README.md",
    "data/README.md",
    "reports/intake_report.md",
    "reports/data_report.md",
    "governance/model_card.md",
    "governance/change_log.md",
    "governance/ongoing_monitoring.md",
    "governance/impact_assessment.md",
    "governance/regulatory_mapping.md",
}


def _every_file(intake: dict[str, Any], data: dict[str, Any]) -> dict[str, str]:
    """All the files the agent writes at tier 1 for a consumer-facing model that uses protected
    attributes, so every ``.md`` it can write is written. The tier is set last: a payload planted
    in it would be a tier that is none of the four, and half the files would not exist."""

    intake = {
        **intake,
        "governance": {
            **(intake.get("governance") or {}),
            "risk_tier": "tier_1_critical",
            "affects_consumers": True,
            "uses_protected_attributes": True,
        },
    }
    return {
        **_build(intake, data),
        **build_governance_files(
            intake=intake, data=data, project_name=_NAME, project_slug="subrogation_model"
        ),
        **build_analysis_files(intake=intake, project_slug="subrogation_model"),
    }


def _markdown(files: dict[str, str]) -> dict[str, str]:
    return {path: text for path, text in files.items() if path.endswith((".md", ".markdown"))}


def _hand_built(
    intake: dict[str, Any], data: dict[str, Any], make: Callable[[int], str]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Both reports with ``make(n)`` in every string, and in the two flags the governance block
    holds as booleans: the schema allows nothing else there, so only a hand-built dict has text
    in them, and two of the files quote nothing else."""

    counter = [0]
    planted = _plant(intake, make, counter)
    planted["governance"]["affects_consumers"] = make(0)
    planted["governance"]["uses_protected_attributes"] = make(0)
    return planted, _plant(data, make, counter)


def _same_constructs(hostile: dict[str, str], baseline: dict[str, str]) -> None:
    """Every file holds the constructs its template holds and no others. A datasheet is filed
    under the stem of its query's name, which the payload changes, so it has no entry in the
    baseline; the template's own datasheet holds none."""

    for path, text in hostile.items():
        expected = _kinds(baseline[path]) if path in baseline else Counter()
        assert _kinds(text) == expected, (path, constructs(text)[:6])


def _switch_everything_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(templates, "neutralise_report", lambda value: value)
    monkeypatch.setattr(governance_templates, "neutralise_report", lambda value: value)
    monkeypatch.setattr(governance_templates, "neutralise_quarto_markup", lambda text: text)


class TestTheMarkdownRenderers:
    """Quarto renders a ``.md`` it is asked to render; the notebooks' neutraliser is applied to
    the files that quote a report as well (``_quarto_markup.py``)."""

    def test_the_table_lists_every_markdown_file_the_agent_writes(
        self, intake_report: IntakeReport, data_report: DataReport
    ) -> None:
        intake, data = _reports(intake_report, data_report)
        written = set(_markdown(_every_file(intake, data)))
        listed = set(MARKDOWN_RENDERERS) | MARKDOWN_WITHOUT_REPORT_TEXT
        listed -= {"data/datasheet_x.md"}
        written = {path for path in written if not path.startswith("data/datasheet_")}
        assert written == listed

    def test_no_markdown_file_the_agent_writes_carries_a_construct_it_was_not_given(
        self, intake_report: IntakeReport, data_report: DataReport
    ) -> None:
        """Every ``.md`` wherever it is built, not a list: a renderer added tomorrow is covered
        the day it appears."""

        intake, data = _reports(intake_report, data_report)
        baseline = _markdown(_every_file(intake, data))
        counter = [0]
        hostile = _markdown(
            _every_file(
                _plant(intake, lambda n: PAYLOADS["everything"], counter),
                _plant(data, lambda n: PAYLOADS["everything"], counter),
            )
        )
        assert set(MARKDOWN_THAT_QUOTE_TEXT) <= set(hostile)
        assert any(path.startswith("data/datasheet_") for path in hostile)
        _same_constructs(hostile, baseline)

    @pytest.mark.parametrize("shape", list(PAYLOADS))
    def test_a_payload_in_every_string_adds_nothing_quarto_acts_on_to_any_markdown_file(
        self, intake_report: IntakeReport, data_report: DataReport, shape: str
    ) -> None:
        intake, data = _reports(intake_report, data_report)
        baseline = _markdown(_every_file(intake, data))
        counter = [0]

        def make(n: int) -> str:
            return PAYLOADS[shape].replace("MARK", f"ZZ{n}ZZ")

        hostile = _markdown(_every_file(_plant(intake, make, counter), _plant(data, make, counter)))
        _same_constructs(hostile, baseline)

    def test_the_payload_reaches_the_markdown_files_that_quote_a_report(
        self, intake_report: IntakeReport, data_report: DataReport
    ) -> None:
        """Without this, a clean result above could mean the text never arrived."""

        intake, data = _reports(intake_report, data_report)
        counter = [0]
        make = lambda n: f"ZZ{n}ZZ"  # noqa: E731 - a one-line table entry
        files = _markdown(_every_file(_plant(intake, make, counter), _plant(data, make, counter)))
        reached = {
            path
            for path, text in files.items()
            if "ZZ" in text and not path.startswith("data/datasheet_")
        }
        assert reached == MARKDOWN_THAT_QUOTE_TEXT
        assert any("ZZ" in text for path, text in files.items() if "datasheet_" in path)

    @pytest.mark.parametrize("path", sorted(MARKDOWN_RENDERERS))
    def test_each_markdown_renderer_does_it_itself(
        self, intake_report: IntakeReport, data_report: DataReport, path: str
    ) -> None:
        """The renderers are public functions and tests and callers use them directly. A payload
        in every string, an enum and a flag as well as the free text."""

        render = MARKDOWN_RENDERERS[path]
        intake, data = _reports(intake_report, data_report)
        baseline = _kinds(render(intake, data))

        def make(n: int) -> str:
            return PAYLOADS["everything"].replace("MARK", f"ZZ{n}ZZ")

        assert _kinds(render(*_hand_built(intake, data, make))) == baseline

    @pytest.mark.parametrize("path", sorted(MARKDOWN_RENDERERS))
    def test_the_check_above_can_fail(
        self,
        intake_report: IntakeReport,
        data_report: DataReport,
        monkeypatch: pytest.MonkeyPatch,
        path: str,
    ) -> None:
        """With every neutraliser switched off, the payload does add constructs to each of the
        renderers. A test that cannot fail proves nothing."""

        render = MARKDOWN_RENDERERS[path]
        intake, data = _reports(intake_report, data_report)
        baseline = _kinds(render(intake, data))
        _switch_everything_off(monkeypatch)

        def make(n: int) -> str:
            return PAYLOADS["everything"].replace("MARK", f"ZZ{n}ZZ")

        assert _kinds(render(*_hand_built(intake, data, make))) != baseline

    def test_a_framework_name_is_neutralised_where_it_is_a_heading(
        self, intake_report: IntakeReport, data_report: DataReport, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``neutralise_report`` leaves dict keys alone, and the regulatory mapping's keys are the
        framework names the report gave, written as ``### <name>`` headings. With only that one
        call switched off, the mapping carries the payload and nothing else does."""

        intake, data = _reports(intake_report, data_report)
        intake["governance"]["regulatory_frameworks"] = [PAYLOADS["everything"]]
        render = MARKDOWN_RENDERERS["governance/regulatory_mapping.md"]
        assert not constructs(render(intake, data))
        monkeypatch.setattr(governance_templates, "neutralise_quarto_markup", lambda text: text)
        assert {c.kind for c in constructs(render(intake, data))} == {
            "fence",
            "inline_chunk",
            "shortcode",
            "metadata_block",
        }

    def test_ordinary_reports_produce_the_same_markdown_as_before(
        self,
        intake_report: IntakeReport,
        data_report: DataReport,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        intake, data = _reports(intake_report, data_report)
        with_it = _every_file(intake, data)
        _switch_everything_off(monkeypatch)
        assert with_it == _every_file(intake, data)

    def test_a_name_is_neutralised_where_it_is_shown_and_not_where_it_is_a_path(self) -> None:
        """The datasheet a query is filed under, and the SQL file it names, come from the name as
        the report gave it, as they do for the notebook; only the text a reader sees changes."""

        names = ["{{< env HOME >}}", "---", "<!-- x -->", "`{python} 1`", "plain"]
        intake = {"governance": {"risk_tier": "tier_4_low"}}
        data = {
            "primary_queries": [
                {"name": name, "datasheet": {}, "expected_row_count_order": "thousands"}
                for name in names
            ]
        }
        files = {
            **build_governance_files(
                intake=intake, data=data, project_name=_NAME, project_slug="subrogation_model"
            ),
            "data/README.md": templates.render_data_readme(data=data),
        }
        sheets = sorted(path for path in files if path.startswith("data/datasheet_"))
        assert len(sheets) == len(names)
        for path in sheets:
            stem = path.removeprefix("data/datasheet_").removesuffix(".md")
            assert f"`queries/primary/{stem}.sql`" in files[path]
            assert f"`datasheet_{stem}.md`" in files["data/README.md"]
            assert not constructs(files[path])
        assert not constructs(files["data/README.md"])
