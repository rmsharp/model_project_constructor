"""A model of what Quarto acts on while it renders a ``.qmd`` file.

The generated notebooks are Quarto documents, and Quarto does more than format them: it runs
code, reads files and reads the environment. Session 295's scouts found which pieces of text do
that in Quarto 1.7.33 (by rendering each one with the real tool, then reading the patterns out
of the shipped source). This module is those patterns, written once, so a test can ask "does
this text hold anything Quarto would act on?" without starting Quarto.

It is deliberately **not** the neutraliser's own logic run backwards. The neutraliser
(``_quarto_markup.py``) is conservative on purpose: it breaks anything that is near enough to
matter. This model is as exact as the source allows, and it follows JavaScript's rules for
``\\s`` and for line ends (Quarto's patterns are JavaScript), which differ from Python's. A
neutraliser that misses a spelling Quarto accepts fails a test here; one that merely over-breaks
does not. Whether this model matches Quarto is itself checked against the real tool, in
``test_quarto_render.py`` (skipped where Quarto or a Jupyter kernel is missing).

Where the model and the tool differ, the model errs towards "Quarto acts": a fence that follows a
lone carriage return or U+2028 is reported, and Quarto 1.7.33 did not run one when Session 295
rendered it (the source's patterns are JavaScript, whose ``^`` counts those as line starts; the
path a notebook takes to the engine does not). A fence in a blockquote is reported for the
opposite reason: it selects the engine without becoming a cell, and the engine is what makes an
inline chunk run.

The four kinds, each with the observation behind it:

``fence``
    A line that opens an executable cell: three or more backticks, optional whitespace, then
    ``{language}`` or ``{language, options}`` to the end of the line. The cell runs, and the
    line alone also makes Quarto start that language's engine, so it works in a notebook that
    holds no cell of its own. Indentation of any size, a list item's, four backticks and a
    space before the brace are all accepted; a blockquote marker, a tilde fence and a bare
    ```` ```python ```` are not executed (the engine pattern accepts ``>``, the cell pattern
    does not; this model reports the union).
``inline_chunk``
    A backtick, ``{language}``, a space or tab, an expression, a closing backtick. It runs only
    once the document's engine is that language (a document with a cell, or one a fence
    switched on), and a backslash before the first backtick does not stop it.
``shortcode``
    ``{{<`` (with or without the space after it). ``env`` and ``meta`` expand anywhere in the
    text; ``include`` splices a file in when the shortcode is the whole line. Three braces
    (``{{{<``) and the ``{{</* ... */>}}`` spelling are Quarto's own ways to write one literally.
``metadata_block``
    A second YAML block in the body: a ``---`` line, lines of YAML, a ``---`` or ``...`` line.
    A ``filters`` entry in it ran, and ``include-in-header`` read a file. The document's own
    front matter is such a block too, so a caller compares counts against a render of benign
    text instead of expecting none.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# JavaScript's ``\s`` (ECMAScript WhiteSpace and LineTerminator). Python's ``\s`` is wider by a
# few controls and narrower by U+FEFF, which is why this is written out.
JS_SPACE = "\t\n\v\f\r \u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"

_LINE_BREAK = re.compile(r"\r\n|[\r\u2028\u2029]")

_FENCE = re.compile(
    rf"[{JS_SPACE}>]*`{{3,}}[{JS_SPACE}]*\{{[A-Za-z0-9_]+( *[ ,].*)?\}}[{JS_SPACE}]*"
)
_INLINE = re.compile(r"(^|[^`])`\{[A-Za-z0-9_]+\}[ \t][^`]+`", re.MULTILINE)
_SHORTCODE = re.compile(r"(?<!\{)\{\{<(?!/\*)")
_METADATA = re.compile(
    r"^---[ \t]*[\r\n]+(?![ \t]*[\r\n]+)[\s\S]*?[\r\n]+(?:---|\.\.\.)[ \t]*$", re.MULTILINE
)


@dataclass(frozen=True)
class Construct:
    """One piece of text Quarto would act on: its kind, 1-based line and the matched text."""

    kind: str
    line: int
    text: str


def constructs(text: str) -> list[Construct]:
    """Everything in ``text`` that Quarto 1.7.33 would act on, in order of appearance."""

    # JavaScript treats \r, U+2028 and U+2029 as line ends where Python's re does not.
    normal = _LINE_BREAK.sub("\n", text)
    found: list[Construct] = []

    for number, line in enumerate(normal.split("\n"), start=1):
        if _FENCE.fullmatch(line):
            found.append(Construct("fence", number, line))

    for kind, pattern in (
        ("inline_chunk", _INLINE),
        ("shortcode", _SHORTCODE),
        ("metadata_block", _METADATA),
    ):
        for match in pattern.finditer(normal):
            number = normal.count("\n", 0, match.start()) + 1
            found.append(Construct(kind, number, match.group(0)))

    return sorted(found, key=lambda c: (c.line, c.kind))
