"""The file name a report name becomes.

``PrimaryQuery.name`` and ``QualityCheck.check_name`` are bare strings, and the Data Agent's
language model chooses them. The website agent writes them into the generated project as file
names: ``queries/primary/<name>.sql``, ``data/datasheet_<name>.md`` and
``queries/quality/<name>/<check>.sql``. Session 296's scouts ran what that did with the name it
was given (``BACKLOG.md``, "What the scaffold still gets wrong after Larkspur point (2)", part
(7)(a)):

* ``x/../../governance/model_card`` made the datasheet path ``governance/model_card.md``. Written
  in the order the files were generated (the in-memory client, the Larkspur example script) the
  datasheet replaced the model card, and the generated project's own check and tests still
  passed. A check name of ``../../primary/beta`` did the same to a primary query. Git refuses a
  tree with ``..`` in a path, so on a host that behaves like git the commit fails after the
  project exists, and what the real GitLab and GitHub do was not measured;
* two queries (or two checks) with one name wrote one file, the second replacing the first, and
  ``Foo`` and ``foo`` were two entries in the commit and one file on macOS or Windows;
* a ``/`` made a directory the generated governance check does not look in, an empty name made
  ``queries/primary/.sql``, ``CON`` is a file name Windows cannot check out, and a name of 243
  characters or more made the generated check crash on a file name past 255 bytes.

The schemas constrain none of it, and the repository's rule for text an agent writes is to fix it
where it is used (``_py_str_literal``, ``_quarto_markup``), because a fix in the schema does not
reach a report that was built by hand or saved earlier. So this module is the one place that
turns a name into a file stem, and every site that writes a path from a report name asks it.

What a stem is, and the only things the module does:

* lower-case ASCII letters, digits and underscores, no more than ``MAX_STEM_LENGTH`` of them, and
  at least one letter or digit. A separator, a dot, a space, a control character or any other
  character becomes an underscore (a run of them becomes one), and an accent is dropped (a name
  spelled with an accented e gives a plain e). The compatibility forms fold first, so a fullwidth
  slash is a separator and a fullwidth letter is a letter;
* a name with nothing left (``""``, ``..``, ``/``, a name of another script) is ``unnamed``, and
  a check with nothing left is ``unnamed_check``;
* a stem that is a Windows device name (``con``, ``nul``, ``com1`` ...) takes ``_file`` after it;
* **a name that is already a stem is its own stem**, so every report that was fine is
  byte-for-byte what it was. Every real name seen is such a name (6 query names and 40 check
  names in 20 saved reports, all ``snake_case``, the longest 47 characters);
* the stems of one list are different from one another. The first name that is already a stem
  keeps it wherever it stands, then the others take the stem they fold to if it is free, and
  otherwise the stem with ``_2``, ``_3`` ... after it. A number never takes a stem another name
  has as its own, and the order of the list decides the numbering, so the same report always
  gives the same files.

Costs a reader sees:

* the file can have a different name from the report's: ``claims/auto_total_loss`` is
  ``claims_auto_total_loss.sql``. The readable name stays in headings, in the datasheet's title
  and in ``reports/data_report.json``, and the paths that the project prints are the real ones;
* nobody is told that the model broke the ``snake_case`` the Data Agent's prompt asks for;
* two names that fold together make the second ``<stem>_2``, which a reader has to match to the
  query by its place in the report.

Not covered, on purpose: a name that only a person reading it would call hostile (a Markdown or
Quarto construct in a heading is part (7)(e) and the notebooks' own neutraliser); the generated
``check_governance.py``, which reads the files on disk and needs no change while the files are
flat; and whether a real host accepts a path with ``..`` in it, which these stems make moot.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any, Final

# PostgreSQL's limit for an identifier is 63 bytes, and the longest real name is 47 characters.
# With ``datasheet_`` in front and ``.md`` after, a stem of this length is 77 bytes of a 255-byte
# file name, and ``queries/quality/<stem>/<stem>.sql`` is well inside any path limit.
MAX_STEM_LENGTH: Final[int] = 64

UNNAMED: Final[str] = "unnamed"
UNNAMED_CHECK: Final[str] = "unnamed_check"

# The file names Windows reserves, whatever follows them (``CON.sql`` is as reserved as ``CON``).
WINDOWS_DEVICE_NAMES: Final[frozenset[str]] = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{number}" for number in range(1, 10)}
    | {f"lpt{number}" for number in range(1, 10)}
)
DEVICE_SUFFIX: Final[str] = "_file"

_NOT_A_STEM_CHARACTER = re.compile(r"[^a-z0-9_]+")
_A_LETTER_OR_DIGIT = re.compile(r"[a-z0-9]")


def file_stem(name: object, *, fallback: str = UNNAMED) -> str:
    """The stem one name becomes on its own, without regard to the other names of its list.

    ``derive_file_stems`` is what the generator calls, because two names can fold to one stem.
    """

    if name is None:
        return fallback
    text = unicodedata.normalize("NFKD", str(name)).casefold()
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = _NOT_A_STEM_CHARACTER.sub("_", text)[:MAX_STEM_LENGTH]
    if not _A_LETTER_OR_DIGIT.search(text):
        return fallback
    if text in WINDOWS_DEVICE_NAMES:
        return text + DEVICE_SUFFIX
    return text


def derive_file_stems(names: Sequence[object], *, fallback: str = UNNAMED) -> list[str]:
    """The stems of one list of names: safe as a file name, and different from one another."""

    folded = [file_stem(name, fallback=fallback) for name in names]
    stems: dict[int, str] = {}
    taken: set[str] = set()
    for index, (name, stem) in enumerate(zip(names, folded, strict=True)):
        if isinstance(name, str) and name == stem and stem not in taken:
            stems[index] = stem
            taken.add(stem)
    # A number may not take the stem that some other name would take as its own.
    claimed = set(folded) | taken
    for index, stem in enumerate(folded):
        if index in stems:
            continue
        if stem in taken:
            number = 2
            while True:
                tail = f"_{number}"
                stem = folded[index][: MAX_STEM_LENGTH - len(tail)] + tail
                if stem not in claimed:
                    break
                number += 1
        stems[index] = stem
        taken.add(stem)
        claimed.add(stem)
    return [stems[index] for index in range(len(names))]


def primary_query_stems(data: Mapping[str, Any]) -> list[str]:
    """One stem for each primary query of a data report (a dumped ``DataReport``)."""

    return derive_file_stems([query.get("name") for query in data.get("primary_queries") or []])


def quality_check_stems(query: Mapping[str, Any]) -> list[str]:
    """One stem for each quality check of one primary query, unique within that query."""

    return derive_file_stems(
        [check.get("check_name") for check in query.get("quality_checks") or []],
        fallback=UNNAMED_CHECK,
    )
