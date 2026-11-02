"""Stop report text from acting on the notebook that Quarto renders.

The website agent writes the intake and data reports into ``analysis/*.qmd`` as prose. The
reports hold text a language model wrote from a stakeholder's words and from a database, and the
schemas constrain none of it. Quarto reads a ``.qmd`` for more than prose: it runs code, reads
files and reads the environment. Session 295's scouts rendered each of these with Quarto 1.7.33
(``BACKLOG.md``, "What the scaffold still gets wrong after Larkspur point (2)", part (7)(b)):

* a line of three or more backticks and ``{python}`` opens a cell that runs, and the line alone
  makes Quarto start the engine, so it works in a notebook that holds no cell of its own. One
  field ending ```` ```{python} ```` and the next one holding a line of code is enough: neither
  needs a newline of its own, because the template puts each field at the start of a line;
* `` `{python} expr` `` runs once any cell has switched the engine on (notebooks 02 and 05 hold
  one), and a backslash before the first backtick does not stop it;
* ``{{< env NAME >}}`` expands wherever it stands, ``{{<env NAME>}}`` too, and
  ``{{< include path >}}`` splices a file in when it is the whole line;
* a second ``---`` block in the body is read as metadata: a ``filters`` entry in it ran.

The fix proposed in the backlog, to neutralise the opening of an inline chunk, leaves the other
three open. So does a zero-width space put only between a backtick and a brace: a fence with a
space, a tab or four ticks before its brace still ran after that.

What this does, and the only thing it does: put one zero-width space (U+200B) in front of the
text Quarto's patterns need to see. It is not whitespace to the JavaScript or the Python
patterns Quarto uses, so the construct no longer matches; the text a reader sees is the same
(U+200B has no width, and a code span still renders as a code span). The rules, each of which
Session 295 broke and re-rendered:

``{{<``
    a shortcode opener: the character goes between ``{{`` and ``<``.
a brace right after a backtick
    an inline chunk, and a fence whose brace follows its ticks at once.
a brace right after three or more backticks and whitespace
    a fence: ``` {python}``, a tab, four ticks, options. The whitespace is Python's ``\\s`` plus
    U+FEFF, which JavaScript's ``\\s`` counts and Python's does not.
a brace at the very start of the text
    the template may have opened a code span just before the field (06 does, for the baseline
    metric's name), and then the field's first brace follows a backtick it cannot see.
``---`` alone on a line
    a metadata block marker, as Pandoc and Quarto read it. Lines end at ``\\n``, ``\\r``, U+2028,
    U+2029 and the other separators, because JavaScript's ``^`` and ``$`` count all of them.

Backslash-escaping is not a way out: Quarto's inline pattern ignores it. An HTML entity does
stop the construct but shows the reader the entity, and inside a code span shows it literally.

Properties the tests hold it to: text with none of these is returned unchanged; removing the
zero-width spaces from the result gives the input back (so nothing visible changed); applying it
twice changes nothing; and the time is linear, because every pattern starts at a run of ticks
or at a line start and cannot be restarted from inside one.

What it does not do: it does not make a field safe as Markdown (a heading, a link, a raw HTML tag
or a ``![](url)`` image is still whatever the model wrote), it is not applied to ``.md`` files
(Quarto renders ``.qmd``; ``reports/intake_report.md`` shares its text with notebook 01 and is
left as it was), and it does not touch the names used as file paths (part (7)(a)).
"""

from __future__ import annotations

import re
from typing import Any

ZERO_WIDTH_SPACE = "\u200b"

# Everything JavaScript's ``^`` and ``$`` treat as a line end (``\n``, ``\r``, U+2028, U+2029),
# plus the separators Python's ``str.splitlines`` adds. Over-breaking a rule costs one invisible
# character; missing a line end that Quarto honours leaves the construct working.
_LINE_ENDS = "\n\r\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029"

# A shortcode opener. ``{{{<`` (Quarto's own escape for writing one literally) holds ``{{<`` and
# is broken too; that is harmless, the text is only ever shown.
_SHORTCODE = re.compile(r"\{\{(?=<)")

# An inline chunk, and a fence whose brace follows its ticks with nothing between.
_BRACE_AFTER_A_TICK = re.compile(r"(?<=`)\{")

# A fence with whitespace between its ticks and its brace. ``(?<!`)`{3,}`` starts a match only at
# the start of a run of ticks, so a long run is scanned once rather than from every position.
_BRACE_AFTER_A_FENCE = re.compile(r"(?<!`)`{3,}[\s\ufeff]+(?=\{)")

# The template may have opened a code span immediately before a field.
_BRACE_AT_THE_START = re.compile(r"\A\{")

# ``---`` and nothing but spaces or tabs until the end of the line.
_METADATA_MARKER = re.compile(
    rf"(?:(?<=[{_LINE_ENDS}])|\A)---(?=[ \t]*(?:[{_LINE_ENDS}]|\Z))"
)


def neutralise_quarto_markup(text: str) -> str:
    """``text`` with one zero-width space in front of anything Quarto would act on."""

    text = _SHORTCODE.sub("{{" + ZERO_WIDTH_SPACE, text)
    text = _BRACE_AFTER_A_TICK.sub(ZERO_WIDTH_SPACE + "{", text)
    text = _BRACE_AFTER_A_FENCE.sub(lambda match: match.group(0) + ZERO_WIDTH_SPACE, text)
    text = _BRACE_AT_THE_START.sub(ZERO_WIDTH_SPACE + "{", text)
    return _METADATA_MARKER.sub("-" + ZERO_WIDTH_SPACE + "--", text)


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
