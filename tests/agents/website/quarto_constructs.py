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
does not. The model is checked against the real tool only where ``test_quarto_render.py`` does
it (skipped where Quarto or a Jupyter kernel is missing): it must report every construct in that
file's payload, one or two spellings of each kind. Every other spelling here is what the scouts
rendered once, or what the source's patterns accept.

Where the model and the tool differ, the model errs towards "Quarto acts". A fence that follows a
lone carriage return or U+2028 is reported, and Quarto 1.7.33 did not run one when Session 295
rendered it (the source's patterns are JavaScript, whose ``^`` counts those as line starts; the
path a notebook takes to the engine does not). An opening fence that nothing closes is reported,
and on its own it started no engine. A fence in a blockquote is reported for the opposite reason:
it selects the engine without becoming a cell, and the engine is what makes an inline chunk run.
A metadata block whose lines end in U+2028 is reported although the tool read it differently.
The model does not remove closed fenced code before it looks for a metadata block, as the source
does, which reports more, not less.

The four kinds, each with the observation behind it:

``fence``
    A line that opens an executable cell: three or more backticks, optional whitespace (which
    may include line ends, as the source's pattern does), then ``{language}`` or
    ``{language, options}`` to the end of the line. A closed fence is a cell that runs, and it
    does in a notebook that holds no cell of its own; the closing line can come from another
    field or from the template. Indentation of any size, a list item's, four backticks and a
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
    A ``filters`` entry in it ran, and ``include-in-header`` read a file. Quarto deletes
    ``<!-- ... -->`` comments before it looks, so the model does too: ``---<!---->`` is a
    ``---`` line. The document's own
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

# The same without the characters that end a line: what may stand before a fence's ticks on
# their line. (A fence that starts after blank lines is found from its own line start.)
_INDENT = JS_SPACE.translate({ord(c): None for c in "\n\r\u2028\u2029"})

# The whitespace between the ticks and the brace is JavaScript's ``\s`` and so includes line
# ends: Quarto's pattern is applied to the whole text, not to one line at a time.
_FENCE = re.compile(
    rf"^[{_INDENT}>]*(?P<ticks>`{{3,}})[{JS_SPACE}]*"
    rf"\{{[A-Za-z0-9_]+( *[ ,][^\n]*)?\}}[{JS_SPACE}]*$",
    re.MULTILINE,
)
_COMMENT = re.compile(r"<!--[\s\S]*?-->")
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

    for fence in _FENCE.finditer(normal):
        number = normal.count("\n", 0, fence.start("ticks")) + 1
        found.append(Construct("fence", number, fence.group(0).strip()))

    # Quarto deletes comments before it reads a body metadata block, so the block is looked for
    # in the text without them (its line numbers count the lines that are left).
    uncommented = _COMMENT.sub("", normal)
    for kind, pattern, source in (
        ("inline_chunk", _INLINE, normal),
        ("shortcode", _SHORTCODE, normal),
        ("metadata_block", _METADATA, uncommented),
    ):
        for match in pattern.finditer(source):
            number = source.count("\n", 0, match.start()) + 1
            found.append(Construct(kind, number, match.group(0)))

    return sorted(found, key=lambda c: (c.line, c.kind))
