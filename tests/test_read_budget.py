"""Hold the four mandated-read files to their read budgets, on every CI run.

WHY THIS EXISTS (Session 255 -- Option D of docs/planning/ledger-budgets-review.md,
widened; operator ruling 2026-09-10, recorded in docs/methodology/PROJECT_CONVENTIONS.md
§5, which carries every measured figure this module relies on). A session learns the state
of this project by reading files from the top. One default ``Read`` returns the whole file,
an announced PARTIAL view, or -- past a byte ceiling -- nothing at all.

* **The ceiling.** A file larger than ``READ_REFUSE_BYTES`` is refused outright. No
  mandated-read file may exceed it, except the ones in ``KNOWN_REFUSED`` -- and each of
  those must STILL be over it, so the exemption cannot outlive its reason.
* **The page.** Past the cap a partial view delivers ``floor(PAGE_TOKENS x L / T)`` lines
  (L lines, T tokens), or ``REGIME_FACTOR`` of that when the whole file's tokens pro-rated to
  those lines' bytes exceed the cap. Both rules are measured, not documented. No tokenizer
  runs offline, so T is unknown here: ``page_estimate`` applies both rules at every
  bytes-per-token ratio across the range measured in this repository and keeps the SMALLEST
  page, because a dense band just past a short page can trigger the reduced regime at a
  ratio where the page is long.
* **What must arrive.** ``SESSION_NOTES.md``: the front matter plus the ``K`` newest
  non-stub records. K=2 is the operator's ruling: both mandated reads (Phase 0, and Phase
  3A before the close-out overwrites the stub) need the newest non-stub record; the second
  is one record of margin and context. ``BACKLOG.md``: its plain-language index. The front
  matter has its own budget because it is the part of the page the apparatus writes.

Every page check has two arms. The BYTES arm is the operator's conservative page
(``PAGE_BYTES``, the page at the lowest measured ratio); the LINES arm is the measured page
rule in both regimes. Their remedies differ: a red BYTES arm means the newest records are too
long; a red LINES arm means a dense tail (trim, or reflow it) or a dense head (reflow long
lines near the top). The guard errs conservative: a default ``Read`` that disagrees with it
is the authority.

The retention rule (fire / stop / floor, in bytes) is enforced at trim time by that trim's
proof; this module holds what must be true BETWEEN trims, plus ``check_satisfiable``: that
a trim fired today could obey the rule. It reads files from disk and never git, because
CI checks out shallow.

NEUTER LOOP, mechanised rather than published: ``test_every_check_is_the_sole_catcher``
fails if any check could be deleted with every mutant still caught, and ``test_next_state``
re-runs that proof in the states the next close-out, the next claim and the next trim
produce -- learning #241, which this module's first two drafts each violated.
"""

from __future__ import annotations

import math
import pathlib
import re
import shutil
from collections.abc import Callable, Iterator
from typing import NamedTuple

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

SESSION_NOTES = "SESSION_NOTES.md"
BACKLOG = "BACKLOG.md"
CHANGELOG = "CHANGELOG.md"
LEARNINGS = "PROJECT_LEARNINGS.md"
CLAUDE = "CLAUDE.md"
CONVENTIONS = "docs/methodology/PROJECT_CONVENTIONS.md"
RUNNER = "SESSION_RUNNER.md"

MANDATED = (SESSION_NOTES, BACKLOG, CHANGELOG, LEARNINGS)
KNOWN_REFUSED: tuple[str, ...] = (CHANGELOG, LEARNINGS)   # ruling 2026-09-10: declare, guard, file
DECLARING = (CLAUDE, CONVENTIONS)
MIRRORED = (*MANDATED, *DECLARING, RUNNER)

READ_CAP_TOKENS = 25_000        # [M] the harness names it: "exceeds maximum allowed tokens"
PAGE_FACTOR = 0.85              # [M] S255: a partial view is 0.85 of the cap, counted in lines
REGIME_FACTOR = 0.7             # [M] S255: every reduced page probed was 0.7 of the rule's
TOKEN_OVERHEAD = 5              # [M] S255: a banner's token total is content tokens + 5
MIN_BYTES_PER_TOKEN = 2.49      # [M] S255: lowest whole-file ratio of the four (CHANGELOG.md)
RATIO_MAX = 2.90                # judgment: above the highest measured (PROJECT_LEARNINGS 2.858)
PAGE_TOKENS = round(READ_CAP_TOKENS * PAGE_FACTOR)           # 21,250
PAGE_BYTES = int(PAGE_TOKENS * MIN_BYTES_PER_TOKEN)          # 52,912
READ_REFUSE_BYTES = 256 * 1024  # [M] S255: 262,144 B returns a page; 262,145 B is refused
FRONT_MATTER_BYTES = 8 * 1024   # judgment (S255, not the ruling): PAGE_BYTES minus the largest
                                # K=2 prefix, stubs included, at the 41 commits since S239
K = 2                           # operator ruling 2026-09-10
FIRE_BYTES = 192 * 1024         # operator ruling 2026-09-10 (canonical's Class A pair)
STOP_BYTES = 96 * 1024
FLOOR = 4
CLAIM_STUB_BYTES = 1024         # [M] claim stubs S240-S255 ran 278-962 B; the next one, modelled
ROW_MARGIN = 64                 # judgment: a new table row may name more than any before it

# The Phase 1B claim template, SESSION_RUNNER.md §1B. See _is_stub for what a stub is.
STUB_LINE = "**Status:** Session claimed. Work beginning."
_STUB = re.compile(r"^\*\*Status:\*\* Session claimed\b")
_FIELD = re.compile(r"^\*\*[^*\n]+:\*\*")
_RECORD = re.compile(r"^### What Session (\S+) Did$")
_INDEX_END = re.compile(r"^## Open Items$")
_FENCE = re.compile(r"^(`{3,}|~{3,})")
_TABLE_ROW = re.compile(rb"^\| \d+ \| S\d+ `")


def _refused_clause() -> tuple[str, ...]:
    if not KNOWN_REFUSED:
        return ()
    return ("except " + " and ".join(f"`{p}`" for p in KNOWN_REFUSED) + ", declared over it",)


# Every budget sentence listed here is composed from the constants, so these cannot drift:
# check_declared requires each EXACTLY ONCE in the file it is listed for. A trim's proof reads
# the three retention sentences at its own commit.
_BOTH = (
    f"fire a new trim when the live file exceeds **{FIRE_BYTES:,} B** ({FIRE_BYTES // 1024} KiB)",
    f"cut back to **≤{STOP_BYTES:,} B** ({STOP_BYTES // 1024} KiB)",
    f"never retain fewer than **{FLOOR}** non-stub records",
    f"the front matter plus the **{K}** newest non-stub records must fit in "
    f"**{PAGE_BYTES:,} B**",
    f"front matter at most **{FRONT_MATTER_BYTES:,} B**",
    f"plain-language index must fit in **{PAGE_BYTES:,} B**",
    f"no mandated-read file may exceed **{READ_REFUSE_BYTES:,} B**",
    *_refused_clause(),
    f"**{PAGE_TOKENS:,} tokens** at **{MIN_BYTES_PER_TOKEN} B/token**",
)
DECLARED: dict[str, tuple[str, ...]] = {
    CLAUDE: _BOTH,
    CONVENTIONS: (
        *_BOTH,
        f"keep **{PAGE_BYTES - FRONT_MATTER_BYTES:,} B**",
        f"**{REGIME_FACTOR}** of it",
        f"at least **{CLAIM_STUB_BYTES:,} B**",
        f"K={K} is the operator's ruling",
        f"up to **{RATIO_MAX} B/token**",
    ),
}


class Record(NamedTuple):
    session: str
    start_byte: int
    end_byte: int   # bytes from the top of the file through the end of this record
    end_line: int   # lines from the top of the file through the end of this record
    stub: bool


def _headings(data: bytes, pattern: re.Pattern[str]) -> list[tuple[int, int, re.Match[str]]]:
    """(byte offset, 0-based line index, match) of each column-0 heading outside fences.

    A fence closes only on the character that opened it, at least as long (CommonMark), so a
    ``~~~`` block showing a ``` example cannot expose a heading inside it.
    """
    found = []
    fence = ""
    offset = 0
    for index, line in enumerate(data.splitlines(keepends=True)):
        text = line.decode("utf-8").rstrip("\r\n")
        opener = _FENCE.match(text)
        if fence:
            if opener and set(text) == {fence[0]} and len(text) >= len(fence):
                fence = ""
        elif opener:
            fence = opener.group(1)
        elif match := pattern.match(text):
            found.append((offset, index, match))
        offset += len(line)
    return found


def _is_stub(body: str) -> bool:
    """A record with no body, or one whose leading metadata still says the session is claimed.

    The metadata is the run of leading paragraphs that each OPEN with a ``**Field:**`` line,
    continuation lines included -- where SESSION_RUNNER.md §1B puts the claim. That catches a
    wrapped Deliverable line, a blank line before Status (Sessions 193 and 226) and a Status
    worded off-template (Session 242), while a closed record that QUOTES the template -- in a
    fence, or in prose after its metadata -- is not taken for a stub.
    """
    lines = body.split("\n")[1:]
    if not "".join(lines).strip():
        return True
    opens_paragraph, fence = True, ""
    for line in lines:
        if fence:
            if _FENCE.match(line) and set(line.rstrip()) == {fence[0]}:
                fence = ""
            continue
        if not line.strip():
            opens_paragraph = True
            continue
        if opens_paragraph and not _FIELD.match(line):
            return False
        opens_paragraph = False
        if opener := _FENCE.match(line):
            fence = opener.group(1)
        elif _STUB.match(line):
            return True
    return False


def parse_ledger(data: bytes) -> tuple[int, list[Record]]:
    """(front-matter bytes, records newest first) under the proofs' record grammar."""
    heads = _headings(data, _RECORD)
    total_lines = len(data.splitlines())
    records = []
    for i, (offset, _index, match) in enumerate(heads):
        end_byte, end_line = ((heads[i + 1][0], heads[i + 1][1]) if i + 1 < len(heads)
                              else (len(data), total_lines))
        body = data[offset:end_byte].decode("utf-8")
        records.append(Record(match.group(1), offset, end_byte, end_line, _is_stub(body)))
    return (heads[0][0] if heads else len(data)), records


def nth_non_stub(records: list[Record], n: int) -> Record | None:
    """The record at which the n-th non-stub record is reached, counting from the top."""
    seen = 0
    for record in records:
        seen += not record.stub
        if seen == n:
            return record
    return None


def page_estimate(data: bytes, regime: bool = True) -> tuple[int, bool] | None:
    """(lines one default Read is predicted to deliver, reduced regime?), or None if the
    file returns whole at every ratio in range.

    At each bytes-per-token ratio r across [MIN_BYTES_PER_TOKEN, RATIO_MAX]: T = B / r plus
    the overhead; the page is floor(PAGE_TOKENS x L / T) lines; it is reduced to REGIME_FACTOR
    of that when T x bytes(page) / B exceeds the cap -- the trigger that separated every
    probe. The smallest page over r is returned. ``regime=False`` applies the plain rule alone,
    which is how a test proves the reduced branch load-bearing.
    """
    lines = data.splitlines(keepends=True)
    cumulative = [0]
    for line in lines:
        cumulative.append(cumulative[-1] + len(line))
    total_lines = data.count(b"\n") + 1
    worst: tuple[int, bool] | None = None
    for step in range(round((RATIO_MAX - MIN_BYTES_PER_TOKEN) * 100) + 1):
        ratio = MIN_BYTES_PER_TOKEN + step / 100
        tokens = math.ceil(len(data) / ratio) + TOKEN_OVERHEAD
        if tokens <= READ_CAP_TOKENS:
            continue
        page = math.floor(PAGE_TOKENS * total_lines / tokens)
        head = cumulative[min(page, len(lines))]
        reduced = regime and tokens * head / len(data) > READ_CAP_TOKENS
        if reduced:
            page = math.floor(REGIME_FACTOR * page)
        if worst is None or page < worst[0]:
            worst = (page, reduced)
    return worst


def _lines_remedy(reduced: bool, ledger: bool) -> str:
    if reduced:
        return ("the head of the page is dense enough that the harness delivers a reduced "
                "page: reflow long lines near the top (tables, one-paragraph-per-line prose)"
                + (", or shorten the newest records" if ledger else ""))
    return ("the file's tail is dense enough to shrink the page: "
            + ("the trim that archives it, or reflowing its long lines, widens the page again"
               if ledger else "reflowing its long lines widens the page again"))


class Tree:
    """The files these checks read, as bytes, from one root."""

    def __init__(self, root: pathlib.Path) -> None:
        self.data: dict[str, bytes | None] = {
            rel: (root / rel).read_bytes() if (root / rel).is_file() else None
            for rel in MIRRORED}


def _k_prefix(tree: Tree) -> tuple[bytes, Record] | str:
    data = tree.data[SESSION_NOTES]
    if data is None:
        return f"{SESSION_NOTES} is missing"
    record = nth_non_stub(parse_ledger(data)[1], K)
    if record is None:
        return f"{SESSION_NOTES} holds fewer than {K} non-stub records; K cannot be evaluated"
    return data, record


def _index(tree: Tree) -> tuple[bytes, int, int] | str:
    data = tree.data[BACKLOG]
    if data is None:
        return f"{BACKLOG} is missing"
    ends = _headings(data, _INDEX_END)
    if len(ends) != 1:
        return f"{BACKLOG} has {len(ends)} '## Open Items' headings; the index needs exactly 1"
    return data, ends[0][0], ends[0][1]


def check_ceiling(tree: Tree) -> list[str]:
    problems = []
    for rel in MANDATED:
        data = tree.data[rel]
        if rel in KNOWN_REFUSED:
            continue
        if data is None:
            problems.append(f"{rel} is missing")
        elif len(data) > READ_REFUSE_BYTES:
            problems.append(
                f"{rel} is {len(data):,} B, over the {READ_REFUSE_BYTES:,} B ceiling: a default "
                "Read now returns NOTHING. Trim it before committing.")
    return problems


def check_known_refused(tree: Tree) -> list[str]:
    problems = []
    for rel in KNOWN_REFUSED:
        data = tree.data[rel]
        if data is None:
            problems.append(f"{rel} is missing; it is declared refused, not deleted")
        elif len(data) <= READ_REFUSE_BYTES:
            problems.append(
                f"{rel} is {len(data):,} B, no longer over {READ_REFUSE_BYTES:,} B: its "
                "remediation landed. Remove it from KNOWN_REFUSED and from the 'except ...' "
                f"sentence in {' and '.join(DECLARING)} -- the whole clause, if this empties "
                "the list; mutants M02/M14 follow the list.")
    return problems


def check_front_matter(tree: Tree) -> list[str]:
    data = tree.data[SESSION_NOTES]
    if data is None:
        return [f"{SESSION_NOTES} is missing"]
    front = parse_ledger(data)[0]
    if front > FRONT_MATTER_BYTES:
        return [f"{SESSION_NOTES}'s front matter is {front:,} B against a "
                f"{FRONT_MATTER_BYTES:,} B budget. Move rationale into a record; a trim adds "
                "one table row, never prose."]
    return []


def check_k_bytes(tree: Tree) -> list[str]:
    found = _k_prefix(tree)
    if isinstance(found, str):
        return [found]
    data, record = found
    if page_estimate(data) is not None and record.end_byte > PAGE_BYTES:
        return [f"the front matter plus the {K} newest non-stub records of {SESSION_NOTES} "
                f"take {record.end_byte:,} B against a {PAGE_BYTES:,} B page. Shorten the "
                "newest record (move detail into a planning doc under docs/planning/); a trim "
                "cannot fix this arm, because truncation starts at the top."]
    return []


def check_k_lines(tree: Tree) -> list[str]:
    found = _k_prefix(tree)
    if isinstance(found, str):
        return [found]
    data, record = found
    estimate = page_estimate(data)
    if estimate is not None and record.end_line > estimate[0]:
        return [f"the {K} newest non-stub records of {SESSION_NOTES} end at line "
                f"{record.end_line}, but one Read is predicted to deliver {estimate[0]} lines: "
                + _lines_remedy(estimate[1], ledger=True) + "."]
    return []


def check_index_bytes(tree: Tree) -> list[str]:
    found = _index(tree)
    if isinstance(found, str):
        return [found]
    data, end_byte, _end_line = found
    if page_estimate(data) is not None and end_byte > PAGE_BYTES:
        return [f"{BACKLOG}'s plain-language index is {end_byte:,} B against a "
                f"{PAGE_BYTES:,} B page: Phase 0 no longer receives it whole. Shorten its rows."]
    return []


def check_index_lines(tree: Tree) -> list[str]:
    found = _index(tree)
    if isinstance(found, str):
        return [found]
    data, _end_byte, end_line = found
    estimate = page_estimate(data)
    if estimate is not None and end_line > estimate[0]:
        return [f"{BACKLOG}'s index ends at line {end_line}, but one Read is predicted to "
                f"deliver {estimate[0]} lines: " + _lines_remedy(estimate[1], ledger=False) + "."]
    return []


def _row_allowance(data: bytes, front: int) -> int:
    rows = [len(line) for line in data[:front].splitlines(keepends=True) if _TABLE_ROW.match(line)]
    return max(rows, default=0) + ROW_MARGIN


def check_satisfiable(tree: Tree) -> list[str]:
    """A trim fired today could keep FLOOR non-stub records and still land at STOP_BYTES."""
    data = tree.data[SESSION_NOTES]
    if data is None:
        return [f"{SESSION_NOTES} is missing"]
    front, records = parse_ledger(data)
    record = nth_non_stub(records, FLOOR)
    if record is None:
        return []   # fewer than FLOOR records: a trim would have nothing to cut
    landing = record.end_byte + _row_allowance(data, front)
    if landing > STOP_BYTES:
        return [f"a trim keeping {FLOOR} non-stub records would land at {landing:,} B (its "
                f"table row included), over the {STOP_BYTES:,} B stop: the retention rule has "
                "no compliant cut. Shorten the live records, or take the numbers to the operator."]
    return []


def check_stub(tree: Tree) -> list[str]:
    runner = tree.data[RUNNER]
    if runner is None or STUB_LINE not in runner.decode("utf-8") or not _STUB.match(STUB_LINE):
        return [f"{RUNNER}'s Phase 1B template no longer contains {STUB_LINE!r}, or _STUB no "
                "longer matches it. Update STUB_LINE and _STUB together, or claim stubs will "
                "count as records."]
    return []


def check_declared(tree: Tree) -> list[str]:
    problems = []
    for rel, literals in DECLARED.items():
        data = tree.data[rel]
        text = "" if data is None else data.decode("utf-8")
        for literal in literals:
            if (count := text.count(literal)) != 1:
                problems.append(f"{rel} states {literal!r} {count} times; it must state it "
                                "exactly once, or the prose and this module have drifted.")
        if not KNOWN_REFUSED and "declared over it" in text:
            problems.append(f"{rel} still carries an exemption clause, but KNOWN_REFUSED is "
                            "empty: delete the whole 'except ... declared over it' clause.")
    return problems


CHECKS: dict[str, Callable[[Tree], list[str]]] = {
    "ceiling": check_ceiling,
    **({"known_refused": check_known_refused} if KNOWN_REFUSED else {}),
    "front_matter": check_front_matter,
    "k_bytes": check_k_bytes,
    "k_lines": check_k_lines,
    "index_bytes": check_index_bytes,
    "index_lines": check_index_lines,
    "satisfiable": check_satisfiable,
    "stub": check_stub,
    "declared": check_declared,
}


@pytest.fixture(scope="module")
def tree() -> Tree:
    return Tree(REPO_ROOT)


@pytest.mark.parametrize("name", list(CHECKS))
def test_live(tree: Tree, name: str) -> None:
    problems = CHECKS[name](tree)
    assert not problems, f"check_{name}:\n\n  - " + "\n\n  - ".join(problems)


@pytest.mark.parametrize(("body", "expected"), [
    ("### What Session 9 Did\n**Deliverable:** x (IN PROGRESS)\n**Started:** d\n"
     "**Status:** Session claimed. Work beginning.\n\n", True),
    ("### What Session 9 Did\n**Deliverable:** a Deliverable that wraps\nonto a second line "
     "(IN PROGRESS)\n**Started:** d\n**Status:** Session claimed. Work beginning.\n\n", True),
    ("### What Session 9 Did\n**Deliverable:** x\n\n**Status:** Session claimed.\n\n", True),
    ("### What Session 9 Did\n**Deliverable:** a trim\n**Status:** Session claimed in its own "
     "commit, before any technical work.\n\n", True),
    ("### What Session 9 Did\n\n", True),
    ("### What Session 9 Did\n**Deliverable:** COMPLETE.\n\nProse.\n\n```markdown\n"
     "**Status:** Session claimed. Work beginning.\n```\n", False),
    ("### What Session 9 Did\n**Deliverable:** COMPLETE.\n```\n"
     "**Status:** Session claimed. Work beginning.\n```\n", False),
    ("### What Session 9 Did\n**Deliverable:** COMPLETE.\n\nThe stub read\n"
     "**Status:** Session claimed. Work beginning.\n", False),
    ("### What Session 9 Did\n**Deliverable:** COMPLETE.\n**Started / completed:** d\n\n"
     "#### What landed\n", False),
], ids=["template", "wrapped", "blank-before-status", "off-template", "empty", "fenced-quote",
        "fenced-in-metadata", "prose-quote", "closed"])
def test_stub_classifier(body: str, expected: bool) -> None:
    """Every shape Session 255's reviews found, from the ledger's history: a misclassified
    stub counts as a record (anti-conservative); a misclassified record makes a false red."""
    assert _is_stub(body) is expected


def test_a_fence_hides_headings_only_until_its_own_closer() -> None:
    mixed = (b"### What Session 2 Did\n~~~text\n```\n### What Session 1 Did\n```\n~~~\n"
             b"### What Session 0 Did\n")
    assert [m.group(1) for _o, _i, m in _headings(mixed, _RECORD)] == ["2", "0"]


# ---------------------------------------------------------------------------
# Mutants: proof that each check can FAIL, and that none is redundant.
#
# Each mutant mirrors the files these checks read into a tmp_path, breaks one thing and
# names the check that must catch it. Mutations are written against the STRUCTURE of the
# ledger (the n-th non-stub record, the index heading), never a session number, and those
# that need a partial page or a particular regime construct it -- the next-state batteries
# re-run every mutant in the states the next close-out, claim and trim produce, where a
# mutant built for today's shape would go vacuous (Session 255's reviews found five).
# ---------------------------------------------------------------------------

Mutation = Callable[[pathlib.Path], None]


def _mirror(tmp_path: pathlib.Path) -> pathlib.Path:
    root = tmp_path / "mirror"
    for rel in MIRRORED:
        destination = root / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / rel, destination)
    return root


def _read(root: pathlib.Path, rel: str) -> bytes:
    return (root / rel).read_bytes()


def _write(root: pathlib.Path, rel: str, data: bytes) -> None:
    (root / rel).write_bytes(data)


def _sub(root: pathlib.Path, rel: str, old: str, new: str) -> None:
    """Substitute, asserting the anchor is unique first -- else the mutant is vacuous."""
    text = (root / rel).read_text(encoding="utf-8")
    assert text.count(old) == 1, f"mutant anchor occurs {text.count(old)}x in {rel}: {old!r}"
    (root / rel).write_text(text.replace(old, new, 1), encoding="utf-8")


def _filler(nbytes: int, width: int = 75) -> bytes:
    """At least nbytes of filler, in lines of `width` bytes (ledger prose runs ~75 B/line)."""
    return (b"x" * (width - 1) + b"\n") * max(1, -(-nbytes // width))


def _mean_width(data: bytes) -> int:
    return max(40, round(len(data) / max(1, data.count(b"\n"))))


def _oldest(nbytes: int, width: int = 75) -> bytes:
    """A record of filler BELOW every real one, so it never moves the K-th or FLOOR-th."""
    return b"### What Session 0 Did\n" + _filler(nbytes, width)


def _ledger(root: pathlib.Path) -> tuple[bytes, int, list[Record]]:
    data = _read(root, SESSION_NOTES)
    front, records = parse_ledger(data)
    return data, front, records


def _must(record: Record | None) -> Record:
    assert record is not None, "the ledger has too few records for this mutant"
    return record


def _cap(data: bytes) -> bytes:
    """Keep a grown ledger under the ceiling by dropping its oldest bytes, so a mutant aimed
    at one arm cannot also fire check_ceiling once the real file has grown near it."""
    if len(data) <= READ_REFUSE_BYTES:
        return data
    return data[:data.rfind(b"\n", 0, READ_REFUSE_BYTES) + 1]


def _partial(data: bytes, tail: bytes) -> bytes:
    """Make one Read return a PAGE at every ratio, so a page arm can fire at all."""
    need = int((READ_CAP_TOKENS + TOKEN_OVERHEAD + 1) * RATIO_MAX) + 1 - len(data)
    return data if need <= 0 else data + tail + _filler(need, width=4_000)


def _join_after(data: bytes, start: int) -> bytes:
    """Remove line breaks after byte `start`, byte count unchanged. Record headings and fence
    lines keep their own lines, so the file still parses the same way."""

    def keep(line: bytes) -> bool:
        text = line.decode("utf-8").rstrip("\r\n")
        return bool(_RECORD.match(text) or _FENCE.match(text))

    lines = data[start:].splitlines(keepends=True)
    out = []
    for i, line in enumerate(lines):
        if i + 1 == len(lines) or keep(line) or keep(lines[i + 1]) or not line.endswith(b"\n"):
            out.append(line)
        else:
            out.append(line[:-1] + b" ")
    return data[:start] + b"".join(out)


def _reflow(body: bytes, width: int) -> bytes:
    """The same bytes in lines of at least `width` bytes, its first (heading) line kept."""
    first, _, rest = body.partition(b"\n")
    out, run = [first + b"\n"], b""
    for line in rest.splitlines(keepends=True):
        run += line
        if len(run) >= width:
            out.append(run.replace(b"\n", b" ")[:-1] + b"\n")
            run = b""
    out.append(run)
    return b"".join(out)


def _m01_the_ledger_crosses_the_ceiling(root: pathlib.Path) -> None:
    data = _read(root, SESSION_NOTES)
    _write(root, SESSION_NOTES, data + _oldest(READ_REFUSE_BYTES - len(data) + 1_000))


def _m02_a_refused_file_is_remediated(root: pathlib.Path) -> None:
    data = _read(root, KNOWN_REFUSED[0])
    _write(root, KNOWN_REFUSED[0], data[:data.rfind(b"\n", 0, READ_REFUSE_BYTES - 1_000) + 1])


def _m03_front_matter_bloat_behind_a_short_record(root: pathlib.Path) -> None:
    data, front, records = _ledger(root)
    newest = _must(nth_non_stub(records, 1))
    short = data[:data.rfind(b"\n", newest.start_byte, newest.start_byte + 2_000) + 1]
    grown = short[:front] + _filler(FRONT_MATTER_BYTES - front + 500) + short[front:]
    _write(root, SESSION_NOTES, grown + data[newest.end_byte:])


def _m04_the_newest_records_outgrow_the_page(root: pathlib.Path) -> None:
    """The newest records outgrow the page in BYTES, and in bytes only: each of the K newest
    non-stub records is rewritten one paragraph to a line -- the same bytes in far fewer lines --
    and the K-th is then grown past PAGE_BYTES by one long line. Growing alone is not enough: the
    long line raises the file's mean line width, the page shrinks with it, and in a ledger a trim
    has just cut the page ends before the K prefix does, so check_k_lines fires too and
    check_k_bytes is the sole catcher of nothing (Session 256, found by the state
    after-a-trim-then-its-close-out)."""
    data, _front, records = _ledger(root)
    kth = _must(nth_non_stub(records, K))
    for record in records[:records.index(kth) + 1]:
        if not record.stub:    # _join_after keeps the byte count, so every offset still holds
            data = (data[:record.start_byte]
                    + _join_after(data[record.start_byte:record.end_byte], 0)
                    + data[record.end_byte:])
    line = b"x" * (PAGE_BYTES - kth.end_byte + 500) + b"\n"
    _write(root, SESSION_NOTES, _cap(data[:kth.end_byte] + line + data[kth.end_byte:]))


def _m05_a_dense_ledger_tail_shrinks_the_page(root: pathlib.Path) -> None:
    data, _front, records = _ledger(root)
    data = _partial(data, b"### What Session 0 Did\n")
    _write(root, SESSION_NOTES, _join_after(data, _must(nth_non_stub(records, K)).end_byte))


def _index_line_end(data: bytes) -> int:
    offset = _headings(data, _INDEX_END)[0][0]
    return data.index(b"\n", offset) + 1


def _m06_the_index_outgrows_the_page(root: pathlib.Path) -> None:
    data = _read(root, BACKLOG)
    at = _headings(data, _INDEX_END)[0][0]
    line = b"x" * (PAGE_BYTES - at + 500) + b"\n"
    _write(root, BACKLOG, data[:at] + line + data[at:])


def _m07_a_dense_backlog_tail_shrinks_the_page(root: pathlib.Path) -> None:
    data = _partial(_read(root, BACKLOG), b"")
    _write(root, BACKLOG, _join_after(data, _index_line_end(data)))


def _m08_the_retention_rule_has_no_compliant_cut(root: pathlib.Path) -> None:
    data, _front, records = _ledger(root)
    beyond_k = _must(nth_non_stub(records, K + 1)).end_byte
    floor_end = _must(nth_non_stub(records, FLOOR)).end_byte
    # Padded at the ledger's own line width, so the page neither shrinks nor grows into the
    # head -- only this check may fire.
    pad = _filler(STOP_BYTES - floor_end + 1_000, width=_mean_width(data))
    _write(root, SESSION_NOTES, data[:beyond_k] + pad + data[beyond_k:floor_end])


def _m09_the_claim_template_is_reworded(root: pathlib.Path) -> None:
    _sub(root, RUNNER, STUB_LINE, STUB_LINE.replace("claimed", "started"))


def _m10_claude_restates_a_budget_wrongly(root: pathlib.Path) -> None:
    first = DECLARED[CLAUDE][0]
    _sub(root, CLAUDE, first, first.replace(f"{FIRE_BYTES:,}", "200,000"))


def _m11_conventions_drops_a_budget(root: pathlib.Path) -> None:
    _sub(root, CONVENTIONS, DECLARED[CONVENTIONS][4], "front matter kept small")


def _m12_the_index_heading_is_renamed(root: pathlib.Path) -> None:
    _sub(root, BACKLOG, "\n## Open Items\n", "\n## Open work\n")


def _m13_one_non_stub_record_remains(root: pathlib.Path) -> None:
    data, _front, records = _ledger(root)
    _write(root, SESSION_NOTES, data[:_must(nth_non_stub(records, 1)).end_byte])


def _m14_a_refused_file_is_deleted(root: pathlib.Path) -> None:
    (root / KNOWN_REFUSED[-1]).unlink()


def _m15_a_mandated_file_is_deleted(root: pathlib.Path) -> None:
    (root / BACKLOG).unlink()


def _m16_an_empty_heading_hides_an_overflow(root: pathlib.Path) -> None:
    """A heading with no body must not count as a record. Here the true K prefix overflows;
    counted as a record, the empty heading would let K stop one record early and pass."""
    data, front, records = _ledger(root)
    at = _must(nth_non_stub(records, K)).end_byte
    data = data[:at] + _filler(PAGE_BYTES - at + 800) + data[at:]
    empty = b"### What Session 9999 Did\n\n"
    _write(root, SESSION_NOTES, _cap(data[:front] + empty + data[front:]))


def _m17_a_budget_sentence_is_duplicated(root: pathlib.Path) -> None:
    target = root / CLAUDE
    target.write_bytes(target.read_bytes() + b"\n" + DECLARED[CLAUDE][0].encode() + b"\n")


def _m18_a_claim_worded_off_template_hides_an_overflow(root: pathlib.Path) -> None:
    """A claim stub whose Status departs from the template, after a blank line (Sessions
    193, 226 and 242 between them), is still a stub. Its bytes push the true K prefix over;
    counted as a record, it would pass."""
    data, front, records = _ledger(root)
    head = (b"### What Session 9999 Did\n**Deliverable:** a trim (IN PROGRESS)\n\n"
            b"**Status:** Session claimed in its own commit, before any technical work.\n\n")
    body = _filler(PAGE_BYTES - _must(nth_non_stub(records, K)).end_byte + 500)
    _write(root, SESSION_NOTES, _cap(data[:front] + head + body + data[front:]))


def _reduced_page_candidates(data: bytes, kth: Record) -> Iterator[bytes]:
    """Shapes that can put the page into the reduced regime. First a sparse tail -- blank lines
    at the bottom widen the page until its head holds more than the cap, the shape a real probe
    reduced -- which works whatever the ledger's size; then long lines reflowed into the
    records just past K, which works only while the page is a small share of the file."""
    blank = 32
    while blank < 200_000:
        yield data + b"\n" * blank
        blank = blank * 5 // 4 + 1
    later = [r for r in parse_ledger(data)[1] if r.start_byte >= kth.end_byte]
    for n in range(1, len(later) + 1):
        for width in (750, 1_500, 3_000, 6_000, 12_000):
            out = data
            for r in later[:n]:
                out = out[:r.start_byte] + _reflow(out[r.start_byte:r.end_byte], width) \
                    + out[r.end_byte:]
            yield out


def test_the_reduced_page_can_cut_the_k_prefix(tmp_path: pathlib.Path) -> None:
    """The reduced-page branch of page_estimate is load-bearing: on a ledger-shaped file whose
    plain page would still deliver the K prefix, a shape that reaches the regime makes
    check_k_lines fire. Built synthetically, so it holds in every state of the real ledger --
    as a mutant (M19) it was unbuildable in small states, where the regime cannot cut K at all."""
    front = b"# Session Notes\n\n" + _filler(6_000) + b"---\n\n## ACTIVE TASK\n\n"
    data = front + b"".join(
        b"### What Session %d Did\n**Deliverable:** COMPLETE.\n\n" % session + _filler(18_000)
        for session in range(12, 0, -1))
    kth = _must(nth_non_stub(parse_ledger(data)[1], K))
    for out in _reduced_page_candidates(data, kth):
        reduced, plain = page_estimate(out), page_estimate(out, regime=False)
        if reduced and plain and reduced[1] and reduced[0] < kth.end_line <= plain[0]:
            break
    else:
        pytest.fail("no candidate shape reaches the reduced regime on the synthetic ledger")
    tree = Tree(tmp_path)
    tree.data[SESSION_NOTES] = out
    assert check_k_lines(tree), "the reduced page cuts the K prefix, but check_k_lines is silent"


MUTANTS: tuple[tuple[str, str, Mutation, str], ...] = (
    ("M01", "the ledger crosses the refusal ceiling", _m01_the_ledger_crosses_the_ceiling,
     "ceiling"),
    *((("M02", "a refused file is remediated but still exempt",
        _m02_a_refused_file_is_remediated, "known_refused"),) if KNOWN_REFUSED else ()),
    ("M03", "front matter bloats behind a short newest record",
     _m03_front_matter_bloat_behind_a_short_record, "front_matter"),
    ("M04", "the newest records outgrow the page in bytes",
     _m04_the_newest_records_outgrow_the_page, "k_bytes"),
    ("M05", "a dense ledger tail shrinks the page in lines",
     _m05_a_dense_ledger_tail_shrinks_the_page, "k_lines"),
    ("M06", "the index outgrows the page in bytes", _m06_the_index_outgrows_the_page,
     "index_bytes"),
    ("M07", "a dense backlog tail shrinks the page in lines",
     _m07_a_dense_backlog_tail_shrinks_the_page, "index_lines"),
    ("M08", "no cut keeping the floor lands under the stop",
     _m08_the_retention_rule_has_no_compliant_cut, "satisfiable"),
    ("M09", "the Phase 1B template is reworded", _m09_the_claim_template_is_reworded, "stub"),
    ("M10", "CLAUDE.md restates a budget wrongly", _m10_claude_restates_a_budget_wrongly,
     "declared"),
    ("M11", "PROJECT_CONVENTIONS.md drops a budget", _m11_conventions_drops_a_budget,
     "declared"),
    ("M12", "the index heading is renamed", _m12_the_index_heading_is_renamed, "index_bytes"),
    ("M13", "fewer than K non-stub records remain", _m13_one_non_stub_record_remains,
     "k_bytes"),
    *((("M14", "a refused file is deleted", _m14_a_refused_file_is_deleted,
        "known_refused"),) if KNOWN_REFUSED else ()),
    ("M15", "a mandated file is deleted", _m15_a_mandated_file_is_deleted, "ceiling"),
    ("M16", "an empty heading hides an overflow", _m16_an_empty_heading_hides_an_overflow,
     "k_bytes"),
    ("M17", "a budget sentence is stated twice", _m17_a_budget_sentence_is_duplicated,
     "declared"),
    ("M18", "an off-template claim stub hides an overflow",
     _m18_a_claim_worded_off_template_hides_an_overflow, "k_bytes"),
)


def _fired(root: pathlib.Path) -> set[str]:
    tree = Tree(root)
    return {name for name, check in CHECKS.items() if check(tree)}


def _skip_if_live_fails() -> None:
    if _fired(REPO_ROOT):
        pytest.skip("test_live is red; fix that first -- every mutant needs a green baseline")


@pytest.mark.parametrize(
    ("mutant_id", "description", "mutate", "expected"), MUTANTS, ids=[m[0] for m in MUTANTS])
def test_mutant_is_caught(tmp_path: pathlib.Path, mutant_id: str, description: str,
                          mutate: Mutation, expected: str) -> None:
    _skip_if_live_fails()
    root = _mirror(tmp_path)
    mutate(root)
    fired = _fired(root)
    assert expected in fired, (
        f"{mutant_id} ({description}) was NOT caught by check_{expected}; fired: "
        f"{sorted(fired) or 'NONE -- the mutant survived every check'}")


def _battery(tmp_path: pathlib.Path, successor: Mutation | None) -> list[str]:
    """Every mutant, on a mirror first moved to `successor`'s state. Problems: the state
    itself fails, a mutant is not caught, or a check is the sole catcher of no mutant."""
    base = _mirror(tmp_path / "base")
    if successor:
        successor(base)
    tree = Tree(base)
    live = [f"check_{name}: {msg}" for name, check in CHECKS.items() for msg in check(tree)]
    if live:
        return live
    problems, sole = [], {}
    for mutant_id, description, mutate, expected in MUTANTS:
        root = _mirror(tmp_path / mutant_id)
        if successor:
            successor(root)
        try:
            mutate(root)
        except AssertionError as error:
            problems.append(f"{mutant_id} ({description}) cannot be built here: {error}")
            continue
        fired = _fired(root)
        if expected not in fired:
            problems.append(f"{mutant_id} ({description}) not caught by check_{expected}; "
                            f"fired: {sorted(fired) or 'NONE'}")
        if len(fired) == 1:
            sole.setdefault(next(iter(fired)), mutant_id)
    problems += [f"check_{name} is the sole catcher of no mutant, so it could be deleted "
                 "with every mutant still caught" for name in sorted(set(CHECKS) - set(sole))]
    return problems


def test_every_check_is_the_sole_catcher(tmp_path: pathlib.Path) -> None:
    """The neuter loop, mechanised: delete any one check and some mutant must survive."""
    _skip_if_live_fails()
    problems = _battery(tmp_path, None)
    assert not problems, "\n  - ".join(["battery on the working tree:", *problems])


# ---------------------------------------------------------------------------
# The next state (learning #241): an assertion can be green in every state that exists and
# have no green state in the next one. From a claim commit the certain successor is its own
# close-out; from a close-out it is the next claim; and a trim is always pending. Each must be
# green, AND every mutant must still be caught there.
# ---------------------------------------------------------------------------

def _successor_closeout(root: pathlib.Path) -> None:
    """At a claim commit, the claim closed out with a record of the ledger's median non-stub
    size, written at its mean line width. At a close-out commit there is nothing to close."""
    data, _front, records = _ledger(root)
    if not records or not records[0].stub:
        return
    sizes = sorted(r.end_byte - r.start_byte for r in records if not r.stub)
    median = sizes[len(sizes) // 2] if sizes else 16_384
    heading = data[records[0].start_byte:data.index(b"\n", records[0].start_byte) + 1]
    head = heading + b"**Deliverable:** COMPLETE.\n\n"
    record = head + _filler(max(1, median - len(head)), width=_mean_width(data))
    _write(root, SESSION_NOTES, data[:records[0].start_byte] + record + data[records[0].end_byte:])


def _successor_claim(root: pathlib.Path) -> None:
    """The next session's Phase 1B stub. At a claim commit the newest record is already a
    stub, and its successor is its own close-out: no change."""
    data, front, records = _ledger(root)
    if records and records[0].stub:
        return
    newest = max((int(r.session) for r in records if r.session.isdigit()), default=0)
    head = (f"### What Session {newest + 1} Did\n**Deliverable:** (IN PROGRESS)\n"
            f"**Started:** 2026-01-01 (UTC)\n{STUB_LINE}\n").encode()
    stub = head + _filler(max(1, CLAIM_STUB_BYTES - len(head) - 1)) + b"\n"
    _write(root, SESSION_NOTES, data[:front] + stub + data[front:])


def _successor_closeout_then_claim(root: pathlib.Path) -> None:
    _successor_closeout(root)
    _successor_claim(root)


def _successor_trim(root: pathlib.Path) -> None:
    """A trim keeping exactly FLOOR non-stub records and adding the widest plausible row."""
    data, front, records = _ledger(root)
    keep = _must(nth_non_stub(records, FLOOR))
    rows = [line for line in data[:front].splitlines(keepends=True) if _TABLE_ROW.match(line)]
    assert rows, "the front-matter table has no rows to model the trim's own row on"
    at = data.index(rows[-1]) + len(rows[-1])
    row = max(rows, key=len).rstrip(b"\n") + b" " * ROW_MARGIN + b"\n"
    _write(root, SESSION_NOTES, data[:at] + row + data[at:keep.end_byte])


def _successor_trim_then_closeout(root: pathlib.Path) -> None:
    """A trim, then the close-out of the session that made it: the smallest ledger a trim
    session leaves, with its newest record at full size. No other model reaches that state, and
    it is where a mutant built for a large ledger first went vacuous (Session 256)."""
    _successor_trim(root)
    _successor_closeout(root)


@pytest.mark.parametrize(
    "successor", [_successor_closeout, _successor_claim, _successor_closeout_then_claim,
                  _successor_trim, _successor_trim_then_closeout],
    ids=["after-the-close-out", "after-the-next-claim", "after-close-out-then-claim",
         "after-a-floor-keeping-trim", "after-a-trim-then-its-close-out"])
def test_next_state(tmp_path: pathlib.Path, successor: Mutation) -> None:
    _skip_if_live_fails()
    problems = _battery(tmp_path, successor)
    assert not problems, "\n  - ".join([
        f"in the state {successor.__name__} produces (fix the CURRENT state now, or the "
        "next commit cannot be green):", *problems])
