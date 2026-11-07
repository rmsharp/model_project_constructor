"""Stop report text from acting on the notebook that Quarto renders.

The website agent writes the intake and data reports into ``analysis/*.qmd`` as prose, and
quotes their fields in the generated ``.md`` files (the READMEs, ``reports/*.md``, the governance
documents and the datasheets). The reports hold text a language model wrote from a stakeholder's
words and from a database, and the schemas constrain none of it. Quarto reads a ``.qmd`` for more
than prose: it runs code, reads files and reads the environment. It reads a ``.md`` it is asked
to render the same way, except that a ``.md`` runs no code (a ``{python}`` fence aborts the render
and an inline chunk stays literal): ``{{< env >}}`` and ``{{< include >}}`` and a second ``---``
block act in both. Session 295's scouts rendered each of these with Quarto 1.7.33
(``BACKLOG.md``, "What the scaffold still gets wrong after Larkspur point (2)", part (7)(b)):

* a line of three or more backticks and ``{python}`` opens a cell that runs, and it does so in a
  notebook that holds no cell of its own. The fence needs its closing line as well, but that line
  can come from another field or from the template: three single-line fields (the opener, a line
  of code, a closing fence) ran in notebook 01, and in 02 the template's own closing fence closes
  a field's opener;
* `` `{python} expr` `` runs once any cell has switched the engine on (notebooks 02 and 05 hold
  one), and a backslash before the first backtick does not stop it;
* ``{{< env NAME >}}`` expands wherever it stands, ``{{<env NAME>}}`` too, and
  ``{{< include path >}}`` splices a file in when it is the whole line;
* a second ``---`` block in the body is read as metadata: a ``filters`` entry in it ran. Quarto
  removes ``<!-- ... -->`` comments before it looks for the block, so a comment next to or inside
  the ``---`` does not hide it.

The fix proposed in the backlog, to neutralise the opening of an inline chunk, leaves the other
three open. So does a zero-width space put only between a backtick and a brace: a fence with a
space, a tab or four ticks before its brace still ran after that.

What this does, and the only thing it does: put one zero-width space (U+200B) in front of the
text Quarto's patterns need to see. It is not whitespace to the JavaScript or the Python
patterns Quarto uses, so the construct no longer matches. A reader sees the same text, with
three exceptions that are costs and are listed below. The rules, each of which Session 295 broke
and re-rendered:

``{{<``
    a shortcode opener: the character goes between ``{{`` and ``<``.
a brace right after a backtick
    an inline chunk, and a fence whose brace follows its ticks at once.
a brace right after three or more backticks and whitespace
    a fence: ``` {python}``, a tab, four ticks, options. The whitespace is Python's ``\\s`` plus
    U+FEFF, which JavaScript's ``\\s`` counts and Python's does not, and it may include line
    ends, because Quarto's pattern spans them. Two backticks at the very start of the text count
    too: 06 puts a backtick in front of the review cadence, and with it they make a fence.
a brace at the very start of the text
    the template may have opened a code span just before the field (06 does, for the baseline
    metric's name), and then the field's first brace follows a backtick it cannot see.
``<!--``
    a comment opener: the character goes between ``<!`` and ``--``. Quarto deletes comments
    before it looks for a metadata block, which turns ``---<!---->`` and ``-<!-- c -->--`` into
    a ``---`` line.
``---`` alone on a line
    a metadata block marker, as Pandoc and Quarto read it. Lines end at ``\\n``, ``\\r``, U+2028
    and U+2029, which is what JavaScript's ``^`` and ``$`` count; Python's ``splitlines`` adds
    ``\\x0b``, ``\\x0c``, ``\\x1c``-``\\x1e`` and ``\\x85``, which are broken too because it costs
    nothing. The renderers ``.strip()`` most fields after this runs, so whitespace before a
    ``---`` at the start of the text, or after one at its end, counts as nothing: `` ---`` would
    otherwise reach the notebook as a ``---`` at the start of a line.

Backslash-escaping is not a way out: Quarto's inline pattern ignores it. An HTML entity does
stop the construct but shows the reader the entity, and inside a code span shows it literally.

Properties the tests hold it to: text with none of these is returned unchanged; removing the
zero-width spaces from the result gives the input back (so nothing was removed or reordered);
applying it twice changes nothing; and the time is linear, because every pattern starts at a
run of ticks or at a line start and cannot be restarted from inside one.

What a reader sees that differs, which are the costs: a field that starts with a brace, or a code
span that opens with one, carries an invisible character; so does a line that starts with a brace
and follows a bare ``` fence (the fence rule's whitespace crosses line ends, as Quarto's does); a
``<!--`` comment is shown as the text it is instead of being hidden; and a ``---`` alone on its
line is no longer a horizontal rule (it renders as a hyphen and an en dash) and no longer
underlines a heading above it.

What it does not do: it does not make a field safe as Markdown (a heading, a link, a raw HTML tag
or a ``![](url)`` image is still whatever the model wrote), it does not touch the names used as
file paths (part (7)(a)), and it does not stop raw TeX (``\\input{file}`` reads a file into a PDF)
or raw HTML, in a notebook or a ``.md`` alike.

Every renderer that puts a report field into a ``.qmd`` or a ``.md`` calls it itself, on the
report it was given and before it reads a field (``templates.py`` and ``governance_templates.py``);
the two that also use a field as a path or a dict key (the query names, the framework names) take
the path from the report as it came and neutralise only the text that is shown.
"""

from __future__ import annotations

import re
from typing import Any

ZERO_WIDTH_SPACE = "\u200b"

# What ends a line. JavaScript's ``^`` and ``$`` count ``\n``, ``\r``, U+2028 and U+2029;
# Python's ``str.splitlines`` adds ``\x0b``, ``\x0c``, ``\x1c``-``\x1e`` and ``\x85``, which
# Quarto does not count. Over-breaking a rule costs one invisible character; missing a line end
# that Quarto honours leaves the construct working.
_LINE_ENDS = "\n\r\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029"

# A shortcode opener. ``{{{<`` (Quarto's own escape for writing one literally) holds ``{{<`` and
# is broken too; that is harmless, the text is only ever shown.
_SHORTCODE = re.compile(r"\{\{(?=<)")

# A comment opener. Quarto deletes ``<!-- ... -->`` before it reads a body metadata block.
_COMMENT_OPEN = re.compile(r"<!(?=--)")

# An inline chunk, and a fence whose brace follows its ticks with nothing between.
_BRACE_AFTER_A_TICK = re.compile(r"(?<=`)\{")

# A fence with whitespace between its ticks and its brace. ``(?<!`)`{3,}`` starts a match only at
# the start of a run of ticks, so a long run is scanned once rather than from every position.
# The second form is two ticks at the start of the text: 06 writes a backtick before the review
# cadence, and a line of three ticks is a fence.
_BRACE_AFTER_A_FENCE = re.compile(r"(?:(?<!`)`{3,}|\A\s*``)[\s\ufeff]+(?=\{)")

# The template may have opened a code span immediately before a field, and the renderers strip
# a field, so a brace behind leading whitespace is at the start too.
_BRACE_AT_THE_START = re.compile(r"\A(\s*)\{")

# ``---`` and nothing but spaces or tabs until the end of the line. The renderers ``.strip()``
# after this runs: whitespace in front of a ``---`` that starts the text, or behind one that
# ends it, is removed, which leaves the marker alone on its line.
_METADATA_MARKER = re.compile(
    rf"(?:(?<=[{_LINE_ENDS}])|\A(?P<lead>\s*))---(?=[ \t]*[{_LINE_ENDS}]|\s*\Z)"
)


def neutralise_quarto_markup(text: str) -> str:
    """``text`` with one zero-width space in front of anything Quarto would act on."""

    text = _SHORTCODE.sub("{{" + ZERO_WIDTH_SPACE, text)
    text = _COMMENT_OPEN.sub("<!" + ZERO_WIDTH_SPACE, text)
    text = _BRACE_AFTER_A_TICK.sub(ZERO_WIDTH_SPACE + "{", text)
    text = _BRACE_AFTER_A_FENCE.sub(lambda match: match.group(0) + ZERO_WIDTH_SPACE, text)
    text = _BRACE_AT_THE_START.sub(lambda match: match.group(1) + ZERO_WIDTH_SPACE + "{", text)
    return _METADATA_MARKER.sub(
        lambda match: (match.group("lead") or "") + "-" + ZERO_WIDTH_SPACE + "--", text
    )


def neutralise_report(value: Any) -> Any:
    """``value`` (a report as ``model_dump`` returns it) with every string neutralised.

    Strings are neutralised wherever they stand, in lists, tuples and dict values, so a field
    nobody has thought of yet is covered the day it is added. Dict keys are field names and are
    not rendered, so they are left alone; anything that is not a string is returned as it was.
    The input is not changed.
    """

    if isinstance(value, str):
        return neutralise_quarto_markup(value)
    if isinstance(value, dict):
        return {key: neutralise_report(item) for key, item in value.items()}
    if isinstance(value, list):
        return [neutralise_report(item) for item in value]
    if isinstance(value, tuple):
        return tuple(neutralise_report(item) for item in value)
    return value
