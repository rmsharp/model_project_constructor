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

Session 302 measured what is left (``BACKLOG.md`` item (7)(g)), with Quarto 1.7.33, Pandoc 3.6.3
and XeTeX. In a page rendered as HTML (the notebooks declare ``format: html`` and Quarto renders a
``.md`` to HTML by default) raw HTML in the text reaches the page unescaped: a ``script`` element,
an ``img`` with ``onerror``, an ``iframe``, a stylesheet ``link``, an ``object``, an ``embed``, a
``javascript:`` link and ``{onclick=...}`` or ``{style=...}`` on a heading, a span or a div. With
``embed-resources: true`` the page inlines the file a link, an import, an iframe, an embed or a
relative image names. A PDF render hands raw TeX to the engine, which reads files and runs
``kpsewhich``: ``\\input{/path}``, ``\\input{|"kpsewhich --var-value=NAME"}`` (an environment
value), TeX in ``$...$`` math, a raw block fenced with tildes and ``^^5c`` (TeX's spelling of a
backslash).
A first version of this
fix listed spellings, and its adversary got past it with Pandoc's special attribute
(``## H {- onclick="..."}``), a character the writer put in front of a brace, a reference
definition that is not at the very start of a line, and white space or control characters in a link
destination. A second version put the rules below in place of the lists, and its adversary found
that a metadata block does not have to start a line: Pandoc reads ``---``, YAML and ``---`` inside
a block quote, a list item (a bullet's second paragraph, ``1. ---``, ``+ ---``), a definition, a
footnote and a grid table cell, and Quarto passes the keys on (measured with Quarto 1.7.33:
``css: /outside/x.css`` was inlined into a page rendered with ``embed-resources: true``, from a
``.qmd`` and from a ``.md``; ``header-includes`` put raw HTML in the page; a ``title`` took effect
in a ``.qmd`` and not in a ``.md``; ``filters``, ``include-in-header`` and ``bibliography`` did not
act from there). The marker rule below no longer asks what stands in front of the dashes. The rules
do not list spellings.

What this does, and the only thing it does: put one zero-width space (U+200B) at a place in the
text where Quarto, Pandoc or TeX need two characters to touch. It is not whitespace to the
JavaScript or the Python patterns Quarto uses, nor to Pandoc's attribute and link parsers; to TeX
it is an ordinary character, so a backslash followed by it is a control symbol that reads nothing.
The construct no longer matches. A reader sees the same text, with exceptions that are costs and
are listed below. The rules (Session 295 found the brace, comment and metadata-marker cases and
re-rendered each; Session 302 the rest):

a brace (``{``)
    the character goes after it, unless it is there already. Every construct that carries code, an
    expression, a file name, an attribute or a raw format opens with one: a cell (``{python}`` with
    any tick count, white space, quote marker or option), an inline chunk, a shortcode
    (``{{< env >}}``), and the attribute lists on a heading, a span, a div, a link, a code span or
    a fenced block (``{#id}``, ``{.class}``, ``{key=value}``, Pandoc's special ``{-}``, the raw
    format ``{=html}``). The rule lists no spelling, and it does not look at what stands in front of
    the brace, so a character the writer puts there changes nothing. Two braces in a row each get
    one, so ``{{<`` never touches.
``<`` and then a letter, ``/``, ``?`` or ``!``
    raw HTML (a tag, a closing tag, a doctype, an instruction, CDATA), an autolink and a comment
    opener. Quarto deletes ``<!-- ... -->`` comments before it looks for a metadata block, which
    turns ``---<!---->`` and ``-<!-- c -->--`` into a ``---`` line.
a backslash and then a letter
    a TeX command, in text or in math. A control word is a backslash and letters, so a backslash
    before the character is a control symbol.
``^`` and then ``^``
    TeX's spelling of a character code (``^^5c`` is a backslash, and ``\\^^69nput`` is ``\\input``),
    which math passes through.
``!`` and then ``[``
    an image, which a file or an address fills in. What is left is a link text. The next rule
    already breaks every form that gives an image its destination, so this one is defence in depth
    and costs one more invisible character.
``]`` and then ``(``, ``[`` or ``:``
    an inline link, a full or a collapsed reference link and a reference definition: the only places
    a destination is read. The destination is never looked at, so no spelling of it
    (``javascript:``, an entity, a blank or a control character in front) can matter, and neither
    can the shape of the label or where the definition stands (a line start, a quote, a list
    item, a table).
``+`` and then ``-`` or ``:``
    the top border of a grid table (``+---+---+``). A cell of a grid table holds blocks, so it can
    hold a metadata block whose ``---`` lines end in the cell's padding and its ``|``, where the
    next rule does not look. Without a border there is no table, and its text is a paragraph.
a carriage return that no line feed follows
    Pandoc deletes every carriage return before it reads a character. The line feed of a CRLF
    stays and still stands between what is on either side of it, so only a carriage return that no
    line feed follows can join a pair again: ``<`` and ``img``, a backslash and ``input``, ``]``
    and ``(``, ``^`` and ``^``, ``-`` and ``--`` with a bare carriage return between them touch
    again once Pandoc has read them, and every rule above looks at the text as it stands. The
    character goes after the carriage return; Pandoc deletes the carriage return and the
    character stands between the two. It is the only character that does this: a census of all
    1,112,064 code points between two letters, and a sweep of every code point of the Basic
    Multilingual Plane at the gap of each pair, found no other that Pandoc 3.6.3 removes (a tab
    becomes a space, which does not join a pair). Found in Session 302 in the attack on the third
    version, in a fuzz hit the attacker left unresolved that read as a backslash, a carriage
    return and a letter.
``---`` at the end of a line
    a metadata block marker, wherever the line begins: Pandoc opens a block on ``---`` and a blank
    line after the container's own prefix (``> ``, ``- ``, ``1. ``, an indent, ``::: `` on the
    line before), and the prefix is not looked at. A dash in front or behind makes it a longer
    run, which is a horizontal rule or text and no marker. Trailing blanks, tabs, any other
    white space and U+FEFF count as nothing, and so does the end of the text (the renderers
    ``.strip()`` most fields after this runs, so a ``---`` followed by a blank at the end of a
    field would reach the notebook alone on its line). Lines end at ``\\n``, ``\\r``, U+2028 and
    U+2029, which is what JavaScript's ``^`` and ``$`` count; Python's ``splitlines`` adds
    ``\\x0b``, ``\\x0c``, ``\\x1c``-``\\x1e`` and ``\\x85``, which are broken too because it costs
    nothing. This is the one rule that names a line end instead of a pair.

Backslash-escaping is not a way out: Quarto's inline pattern ignores it. An HTML entity does
stop the construct but shows the reader the entity, and inside a code span shows it literally.

Properties the tests hold it to: text with none of these is returned unchanged; removing the
zero-width spaces from the result gives the input back (so nothing was removed or reordered);
applying it twice changes nothing; the rules give the same result in any order (each looks at one
pair and each inserted character separates the pair its rule looked at); and the time is linear,
because every rule is one or three characters and a run of blanks to look at. (That is the
neutraliser's time. Pandoc's, on the text it returns, is not: see the last of the costs.)

What a reader sees that differs, which are the costs. The operator accepted (Session 302): an
invisible character in what the reader sees, a literal tag or autolink shown as text, an image
shown as a link text, and a PDF whose math carries a TeX command failing to build instead of
leaking. Each item below says what was not put to the operator, either because it was not said
plainly (the backslash) or because it was found afterwards (marked *new*):

* every brace is followed by an invisible character, and so is a ``]`` before ``(``, ``[`` or
  ``:``, a ``+`` before ``-`` or ``:`` and the first dash of a ``---`` that ends its line (*new*:
  the last two, and a ``---`` at the end of a line of prose, which is a hyphen and an en dash
  now). They stay in code spans and fenced code: a reader who copies a JSON example copies the
  character. *New*: ``pdflatex`` cannot typeset it there and **fails to build** a PDF whose report
  text holds a fenced code block with anything a rule touches in it (a brace, ``\\d+``, ``x<y``,
  ``<policy_number>``; ``Unicode character U+200B not set up for use with LaTeX``; the same PDF
  builds without the character), where XeLaTeX, Quarto's default, and LuaLaTeX build it and XeLaTeX
  warns of a missing character. A code span and prose build;
* a literal tag the analyst wrote on purpose (``<b>``, ``<policy_number>``) and an autolink
  (``<https://x>``) are shown as the text they are;
* no link, reference link or definition works: ``[text](https://x)`` shows its brackets and its
  address, ``![alt](path)`` is a link text with no image, a footnote definition is a paragraph and
  (*new*) so is a grid table. A label such as ``{#sec-x}`` stops being one;
* a backslash before a letter shows without the backslash in the page: ``C:\\Users`` shows as
  ``C:Users``, ``\\d+`` as ``d+`` and a literal ``\\n`` as ``n`` (a saved report holds a model's
  error message with ``\\n`` in it: ``json\\n[`` shows as ``jsonn[``), because Pandoc reads a
  backslash and the character as an escape. (The operator was not told this one plainly when the
  rules were chosen.) At HEAD the same text was swallowed as raw TeX instead (``C:\\Data\\x.csv``
  showed as ``C:.csv``). In a code span the backslash stays and the character is in the code.
  *New*: ``^^`` in prose shows as nothing: Pandoc reads a caret, the character and a caret as a
  superscript, so ``x^^2`` shows as ``x2``;
* a PDF whose report text holds math with a TeX command fails to build (TeX stops on the undefined
  control sequence) instead of reading the file, and a raw block fenced with tildes becomes a
  strikeout, which fails the same way (below). *New*: in an HTML page the same math reaches MathJax
  as ``\\<U+200B>frac{<U+200B>a}``, an undefined control sequence (no page was rendered with
  MathJax here, so what the reader sees is not measured). A build that fails reads nothing;
* a ``<!--`` comment is shown as the text it is instead of being hidden, and a ``---`` alone on
  its line is no longer a horizontal rule (it renders as a hyphen and an en dash) and no longer
  underlines a heading above it. *New*: the same goes for a ``---`` that ends any line, so a pipe
  table written without a closing pipe (``a | b`` over ``--- | ---``), a simple table with
  ``---`` underlines and a ``---`` in a quote or a list item stop being what they were: the two
  tables are paragraphs. A table with its outer pipes (``| a | b |`` over ``|---|---|``) is not
  touched;
* *new*: every bare carriage return (text pasted with old Mac or mixed line ends) is followed by an
  invisible character, one per line end, in prose and in fenced code alike. Pandoc ran such lines
  together without the rule, so no line break is lost;
* **not accepted yet**: a PDF whose report text holds a strikeout (``~~...~~``) with a neutralised
  character inside it fails to build with XeLaTeX, because the ``soul`` package that Pandoc uses
  for strikeout cannot typeset the character (measured for a brace, a tag, ``]:`` and ``][``; a
  strikeout of plain words builds). No rule can avoid this: a character between the two tildes
  makes Pandoc read a subscript of that character, which would drop the tildes and the meaning of
  the text without a word. A build that fails was judged better than text that lies;
* *new*: Pandoc's time to read the text this returns grows with the square of the number of ``<``
  signs that are followed by a letter, ``/``, ``?`` or ``!``, because it looks at the rest of the
  text at each one (measured on a busy machine, so the seconds are rough: 800 paragraphs that each
  hold a tag take 0.1 s raw and 9 to 16 s here, about four times as long for each doubling, and
  3,200 take minutes). A ``<`` before a space or a digit costs about half as much at HEAD, so this
  widens a property of Pandoc; a report with thousands of tags would take minutes to render. No
  report in the saved corpus holds one.

"Letter" in the rules for ``<`` and a backslash is an ASCII letter or any character above U+007F
that is not white space and is not the inserted character. It does not use Python's table of
letters, which depends on the version: a first version did, and Python 3.11 (Unicode 14) and 3.12
(Unicode 15.0) leave 4,970 and 622 letters that Pandoc 3.6.3 reads after ``<`` or a backslash as a
tag or a command (measured: Quarto shows the tag as text and a PDF build stops with an undefined
control sequence, so nothing was read, but only this class makes the answer the same on every
Python). It over-breaks: ``<`` or a backslash before a symbol, a currency sign or an emoji costs
one invisible character.

What this claims, and what it does not. It stops the constructs listed above, each of which the
real-Quarto tests render with the neutraliser off and on (the image rule is defence in depth and
no render tells it from the link rule). It does not make the text safe, and it is measured against
one Quarto, one Pandoc and one TeX engine, on one platform. Left open, on purpose or because
nothing here reaches them: a heading, emphasis, a list or a table is still whatever the model
wrote, and so is a fenced div's class (``::: name`` is a class to Pandoc, and Quarto gives some
classes meaning, and a bare ``::: panel-tabset`` stops ``quarto render`` with a Lua error, as it
does without this module); a title block (``% title`` is read as the document's title when it is
the first line of a file, which no generated file begins with report text for); the keys inside a
metadata block, which are not looked at because the block is
broken where it opens; a ``from:`` in a
``_quarto.yml`` that adds extensions (for instance ``autolink_bare_uris``, which Quarto 1.7.33
does not turn on, so a bare ``javascript:`` is text) or a different Quarto or Pandoc version; a
TeX engine or a template that reads text another way; a page that is published, where a person's
browser meets whatever text the model wrote; the names used as file paths (part (7)(a)); and any
construct nobody has tried. The text of a report should be read before a PDF is rendered or a
page is published: ``render_readme`` says so.

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

# Every rule below but the marker rule puts the character between two characters that must touch
# for the construct to exist, and decides from the character on the right alone. That is what
# makes them structural: no rule lists a spelling (a tag name, an attribute name, a URL scheme, a
# kind of white space), so a spelling nobody has tried is broken the same way. It is also why the
# rules can run in any order and why a second pass finds nothing: each inserted character
# separates the pair that its rule looked at, and no rule looks at a pair that has the character
# in it.

# What counts as a letter after ``<`` and after a backslash: an ASCII letter, or any character
# above U+007F that is not white space and is not the character itself. Python's own table of
# letters (``[^\W\d_]``) depends on the version of Python: 3.11 knows Unicode 14 and 3.12 Unicode
# 15.0, and Pandoc 3.6.3 reads a newer letter after ``<`` as a tag and after a backslash as a
# command (4,970 and 622 code points were measured), so a rule that asked Python which characters
# are letters would be open on those versions. Nothing above U+007F is a tag or a command start for
# any other reason, so asking only what is not ASCII over-breaks (a symbol, a currency sign, an
# emoji) and never misses. The character is left out so that a second pass finds nothing to do.
_LETTER = r"(?:[A-Za-z]|[^\x00-\x7f\s\u200b])"

# An opening brace, whatever follows it, unless the character follows already. Quarto and Pandoc
# open every construct that carries code, an expression, a file name, an attribute or a raw
# format with a brace: a cell (``{python}``, behind ticks, white space, a quote marker or
# anything else the fence pattern allows), an inline chunk, a shortcode (``{{<``), an attribute
# list (``{#id}``, ``{.class}``, ``{key=value}``, ``{-}``, ``{=html}``) on a heading, a span, a
# div, a link, a code span or a fenced block. Every one of those patterns needs a word
# character, a dot, a hash, an equals sign, a dash or a ``<`` right after the brace, and the
# character is none of them, so a brace nothing may follow cannot open any. A brace that the
# writer already put the character behind needs nothing; one that has it in front, as in
# ``<U+200B>{onclick=...}``, is broken all the same, because the rule looks at what follows.
# A brace at the very end of the text is broken too, so whatever a template writes next cannot
# join it.
_OPEN_BRACE = re.compile(r"\{(?!\u200b)")

# ``<`` and a letter, ``/``, ``?`` or ``!``: a tag, a closing tag, a processing instruction, a
# doctype, CDATA, a comment (``<!--``, which Quarto deletes before it looks for a metadata block)
# and an autolink (``<https://x>``). Raw HTML cannot begin with anything else, so a ``<`` before an
# ASCII digit, a space or the end of the text (``< 5``, ``<=``) is left alone.
_RAW_HTML = re.compile(rf"<(?={_LETTER}|[/?!])")

# A backslash and a letter: a TeX command, in text or in math, ``\input{file}`` among them. A
# control word is a backslash and letters, so a backslash and anything else (a symbol, a digit,
# the character) is a control symbol and reads nothing. The backslash itself is kept.
_TEX_COMMAND = re.compile(rf"\\(?={_LETTER})")

# TeX's own spelling of a character code, ``^^5c`` for a backslash and ``^^69`` for ``i``, so
# ``\^^69nput`` is ``\input``. Math passes it through. TeX needs the two carets to touch.
_TEX_CARET_NOTATION = re.compile(r"\^(?=\^)")

# ``![``: an image, which a file or an address can fill in. Without the ``!`` the rest is a link.
# The link rule below breaks every form that supplies a destination, so this is defence in depth.
_IMAGE = re.compile(r"!(?=\[)")

# ``](``, ``][`` and ``]:``: the three ways a bracketed label becomes a link. An inline link
# (``[x](dest)``), a full or a collapsed reference link (``[x][ref]``, ``[x][]``, with or without
# white space between) and a reference definition (``[ref]: dest``, at the start of a line or
# inside a quote, a list item or a table, with a label of any shape) are the only places a
# destination is read, and each has ``]`` right before a ``(``, a ``[`` or a ``:``. Whatever
# the destination or its spelling, and whatever white space or control character stands in it,
# nothing reads it. A ``]`` followed by ``{`` is the attribute rule's.
_LINK_JOINT = re.compile(r"\](?=[(\[:])")

# ``---`` that ends its line, whatever stands in front of it. Pandoc opens a metadata block on
# ``---`` and a blank line, and does so inside a block quote, a list item, a definition, a
# footnote and a fenced div, after the container's own prefix (``> ``, ``- ``, ``1. ``, an indent):
# a rule that asked for a line start would have to list those prefixes, so this one asks only that
# the run be exactly three dashes (a longer run is a horizontal rule, and no marker) and that the
# rest of the line be blank. Python's ``\s`` is wider than Pandoc's blank (a space or a tab) and
# differs from JavaScript's in both directions (it lacks U+FEFF, and counts ``\x1c``-``\x1f`` and
# ``\x85``, which JavaScript's does not); the class below is the union of the two, with the line
# ends excluded because the next group names them. The end of the text counts as a line end,
# because the renderers ``.strip()`` after this runs.
_METADATA_MARKER = re.compile(rf"(?<!-)---(?=(?:[^\S\r\n]|\ufeff)*(?:[{_LINE_ENDS}]|\Z))")

# ``+`` and then ``-`` or ``:``: the top border of a grid table (``+---+---+``, or
# ``+:---+`` when it sets an alignment). A cell of a grid table holds blocks, so it can hold the
# ``---`` YAML ``---`` of a metadata block with the cell's padding and a ``|`` after each marker,
# where the rule above does not look. A grid table starts with this border, so without it there is
# no table; the cell text is a paragraph. ``+=`` is not matched: it is a header separator, never
# the first line, and ``x += 1`` is code.
_GRID_TABLE = re.compile(r"\+(?=[-:])")

# A carriage return that is not the first half of a CRLF. Pandoc deletes it before it reads a
# character, so the two characters on either side of it touch for Pandoc though they do not in
# the text, and the pairs above are whole again (``<\rimg`` is ``<img``, ``\\\rinput`` is
# ``\input``). The character goes after it: Pandoc deletes the carriage return and the character
# stands between the two. A carriage return that has the character after it already needs nothing.
# (The ``\n`` it must not be followed by is a CRLF, which Pandoc reads as a line end.)
_LONE_CARRIAGE_RETURN = re.compile(r"\r(?![\n\u200b])")

# Every rule as (name, pattern, replacement). Each replacement keeps the matched characters and
# adds the one character, so a rule never removes or reorders text; each pattern looks at what
# follows (or, for the marker, what surrounds) a pair and nothing a rule inserts is in a pair
# another rule looks at, so the order here is not a requirement. The tests apply them in other
# orders.
_RULES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("a brace", _OPEN_BRACE, "{" + ZERO_WIDTH_SPACE),
    ("a tag, a doctype, an instruction or a comment opener", _RAW_HTML, "<" + ZERO_WIDTH_SPACE),
    ("a TeX command", _TEX_COMMAND, "\\" + ZERO_WIDTH_SPACE),
    ("a character code", _TEX_CARET_NOTATION, "^" + ZERO_WIDTH_SPACE),
    ("an image", _IMAGE, "!" + ZERO_WIDTH_SPACE),
    ("a link, a reference link or a definition", _LINK_JOINT, "]" + ZERO_WIDTH_SPACE),
    ("the top border of a grid table", _GRID_TABLE, "+" + ZERO_WIDTH_SPACE),
    ("a carriage return that Pandoc deletes", _LONE_CARRIAGE_RETURN, "\r" + ZERO_WIDTH_SPACE),
    ("a metadata block marker", _METADATA_MARKER, "-" + ZERO_WIDTH_SPACE + "--"),
)


def neutralise_quarto_markup(text: str) -> str:
    """``text`` with one zero-width space in front of anything Quarto would act on."""

    for _, pattern, replacement in _RULES:
        text = pattern.sub(replacement, text)
    return text


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
