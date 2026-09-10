#!/usr/bin/env bash
# SESSION_NOTES-pointer-collapse-S254.verify.sh -- the proof for Session 254's RETROACTIVE collapse
# of the three pointer blocks that were still standing in SESSION_NOTES.md's front matter, and for
# the RULE that replaces them: one trim, one row.
#
#   bash <this>              prove the collapse changed exactly what it declared, and nothing else
#   bash <this> --self-test  prove this proof can FAIL (exit 2 if any mutant survives OR if any
#                            mutation turns out to have changed nothing -- the NO-OP guard, S253)
#
# NOT A TRIM, NOT A SHARD PROOF, AND NOT THE `C`-SERIES. No record moved, no shard was written, no
# session was archived. Its assertions are lettered R0-R8 -- `R` for the RETROACTIVE collapse. The
# letter is chosen the way the C-series chose its own, and for the same reason: Session 245 had to
# record an `L14` collision to stop a later trim resurrecting a rejected assertion under a live
# name, and a distinct namespace removes that failure mode for a fraction of the cost. `R` is also
# NOT an option letter in `docs/planning/ledger-budgets-review.md` section 8 (A-H), so `R3` can
# never be misread as a ruling.
#
# WHAT THIS EXISTS TO PROVE. Operator ruling, 2026-09-07 (`docs/planning/ledger-budgets-review.md`
# section 13.1): **Option E, applied RETROACTIVELY, first** -- ahead of Option D, on the arithmetic
# in section 13.3. Option E is "collapse-on-write": every trim writes its pointer block as a table
# ROW, never as prose, and the trim's rationale lives in that session's own record. Retroactive
# means the blocks already standing are collapsed too. Section 13.3 measured why the retroactive
# half is the part that matters: a prose pointer block costs this front matter ~6,110 B every trim
# and a row ~117 B, and at the front-matter size that stood before this commit Option D was
# arithmetically unreachable at K=3.
#
# THE PREMISE WAS RE-DERIVED AT HEAD, WITH CONTROLS, NOT INHERITED. Session 246 measured that
# compressing this front matter disturbs no shard proof. Session 254 re-ran it as three
# perturbations of the working tree, restoring from a copy each time (never `git checkout`):
#
#   corrupt the live "authority" block's routing clause AND one of its size figures  -> 9/9 GREEN
#   DELETE all three standing prose blocks outright                                  -> 9/9 GREEN
#   rewrite ONLY the C-series table's opening line                                   -> 1 RED (C6)
#
# The second line is the whole argument for this deliverable and the whole argument for R6: the 276
# lines of front matter this commit replaces were guarded by NOTHING, and the one thing that noticed
# any of it was the single working-tree arm the previous collapse left behind.
#
# THE NINE ASSERTIONS
#
#   R0 PIN         OLD_PROSE -- the 276 replaced lines, embedded below verbatim -- occurs exactly
#                  once in SESSION_NOTES.md at the declared pre-collapse commit, is exactly 276
#                  lines, and the figure the new block PRINTS for it is that same integer. A PIN,
#                  not a derivation, and labelled as one: the literal was generated FROM the
#                  artifact, so R0 cannot discover that replacing it was wrong. What it does is
#                  make either copy impossible to change alone, and give this file custody of the
#                  second copy -- so "nothing was lost" does not rest on git alone.
#   R1 CONFINEMENT the post-collapse front matter is the pre-collapse front matter with exactly ONE
#                  OLD_PROSE -> NEW_BLOCK replacement and nothing else. The C-series needed three
#                  declared substitutions besides its replacement because it cut toward blocks that
#                  survived and falsified their positional prose. This collapse leaves no prose
#                  block standing, so there is nothing left to falsify and the substitution list is
#                  EMPTY -- which is not an omission but the point of the rule, and R8 is the
#                  assertion that keeps it true.
#   R2 RECORDS     the records zone is byte-identical across the collapse: same bytes, same order,
#                  same count, zero added. CLAUDE.md's two-commits rule says a trim commit carries
#                  no record edit; a collapse commit carries none either. Session 254's Phase 1B
#                  stub was committed ALONE, before this, precisely so this assertion can hold.
#   R3 DERIVED     for each of the EIGHT rows -- not only the three this collapse added -- the
#                  archived record-heading count, the archived line count and the shard's total are
#                  MEASURED from that shard at its own add-commit, and the row's entire markdown
#                  line is then COMPOSED from the measurements and required to occur verbatim,
#                  exactly once, in NEW_BLOCK. Re-deriving rows 1-5 is deliberate: after this commit
#                  the table has exactly one owner, rather than five rows proved by C3 against a
#                  literal frozen at that proof's own add-commit and three proved here.
#                  R3/FIGURE additionally COMPOSES the four arithmetic phrases the new prose states
#                  about itself -- its own row count, how many blocks the first collapse took, which
#                  ordinals this one added, and which trims they were -- from the declared row sets.
#   R4 PROVENANCE  for each row: the declared trim sha IS the commit that added that shard; the
#                  declared archived span IS what the shard holds; the declared "left live" span IS
#                  what SESSION_NOTES.md held at that commit; and both the shard and its .verify.sh
#                  exist on disk.
#   R5 ASSERTIONS  for each row: the assertion set that trim CONTRIBUTED, derived by parsing
#                  `^def L<N>(` out of that trim's proof AT ITS OWN ADD-COMMIT and subtracting its
#                  predecessor's set, equals the declared "added" column. Read at the add-commit,
#                  never from disk: L10 proves disk == add-commit, so reading disk would make this
#                  silently depend on L10 holding.
#   R6 LIVE        the WORKING TREE's SESSION_NOTES.md carries every composed row exactly once and
#                  NEW_BLOCK's opening line exactly once; no longer contains OLD_PROSE; and no
#                  longer contains the C-series table's OLD opening line. That last arm is what
#                  makes the substitution PROVED rather than merely permitted -- C6 pinned that
#                  line against the working tree, this collapse had to change it, and a proof that
#                  only stopped requiring it would leave both texts legal.
#                    PER ROW, NOT PER BLOCK, inheriting C6's hard-won reason: a whole-block literal
#                    pinned against `after` at this file's own add-commit has no green state once
#                    any prose in it is later corrected. Rows are the load-bearing half and R3
#                    derives them; the prose between them stays free to be repaired.
#   R7 ROUTING     the assertion that licenses DELETING the nine prose routing clauses instead of
#                  keeping them in parallel: the declared archived spans, sorted, TILE the history
#                  with no gap and no overlap from the oldest session to the newest archived one --
#                  and the newest archived session plus one EQUALS the oldest record id in the
#                  WORKING TREE. Internal consistency is not enough; the second arm is what proves
#                  the table's routing agrees with the file a session actually opens. Nothing in the
#                  L-series or the C-series asserted either half.
#   R8 THE RULE    collapse-on-write, enforced rather than announced, and read from the WORKING TREE
#                  so that it binds FUTURE trims and not merely this commit: the surviving front
#                  matter contains no prose pointer-block head (`**<Ordinal> trim (Session N)`) and
#                  no member of the positional `**The N blocks below are frozen**` family. If the
#                  ninth trim writes a block instead of a row, this goes RED. C7 had to DERIVE the
#                  count in that family because the family survived its collapse; R8 asserts the
#                  family is EMPTY, which is a stronger and much cheaper invariant -- and it is the
#                  section 11 completion criterion for Option E, mechanised.
#
# WHAT IT DOES NOT PROVE. It does not prove the collapse was WISE -- that was the operator's call.
# It does not prove the surviving prose is TRUE. It does not re-prove any of the eight cuts, nor
# Session 246's collapse: each has its own proof pinned to its own commit; run those too. And it
# says nothing about the records, beyond that this commit did not touch them.
#
# ------------------------------------------------------------------------------------------------
# THE NEUTER SWEEP -- BOTH LEVELS, MEASURED, AND PUBLISHED IN THE SAME COMMIT AS THE PROOF. The
# eighth trim shipped with its sweep outstanding and asked its successor to run it; that is the
# habit this header refuses to inherit. Every figure below was produced by running the loop with
# the exit code checked each time: 0 or 2, never 1. An early-`return [...]` guard is neutered to
# `return []`, never to `pass` -- the non-type-preserving form is what reported sixty arms as
# unreachable in Session 245 and cost that session a finding.
#
#   WHOLE ASSERTION -- neuter one function at a time to `return []`; every one of the nine is
#   load-bearing, and each is the SOLE objector to at least two mutants:
#     R0  -> M2, M3, M4, M5, M48                    R1  -> M6, M7, M8
#     R2  -> M9, M10, M11                           R3  -> M12-M16, M18-M23 (eleven)
#     R4  -> M27, M28, M29                          R5  -> M32, M33
#     R6  -> M34, M35, M37                          R7  -> M43, M49, M50, M46, M47
#     R8  -> M44, M45
#
#   PER ARM -- 48 failure-emitting statements inside R0-R8 (46 `out.append` plus 2 early
#   `return ["R...`); **17 uniquely catch a mutant, 31 do not.** An arm no mutant can reach is the
#   defect Session 224 and Session 228 each shipped, and the only way to find one is to neuter arms
#   one at a time. Both lists are below: what uniquely catches, then what does not and why.
#
#   THE 17 WITH UNIQUE COVERAGE -- neuter it and the named mutant survives, nothing else:
#     arm 1 R0 PIN, arm 2 R0 PIN, arm 4 R0 FIGURE
#     arm 10 R2 RECORD ORDER, arm 13 R3 SIZE `%s`, arm 19 R3 FIGURE
#     arm 24 R4 LEFT-LIVE `%s`, arm 25 R4 GONE `%s`, arm 26 R5 `%s`
#     arm 30 R6 LIVE, arm 31 R6 LIVE, arm 33 R6 SUBSTITUTED
#     arm 41 R7 LIVE-OVERLAP, arm 42 R7 LIVE-GAP, arm 45 R7 FRONTIER
#     arm 47 R8 THE RULE, arm 48 R8 THE RULE
#
#   THE 31 ARMS WITH NO UNIQUELY-CATCHING MUTANT, grouped by cause:
#
#   * PROVABLY SUBSUMED BY THE LIVE ARMS -- R7/OVERLAP and R7/GAP read the DECLARED spans, and a
#     declared span cannot break tiling without breaking it on disk too: R3/ROW requires the
#     composed row (which carries that span) to be in NEW_BLOCK, and R6 requires every NEW_BLOCK row
#     to be in the working tree, so R7/LIVE-OVERLAP or R7/LIVE-GAP always fires with them. They are
#     kept because they name the SHARD in the message where the live arms can only name numbers.
#     **Measured, and it is a deliberate trade:** before R7 was split, M46/M47 isolated the declared
#     arms and the live arms did not exist. Splitting moved their unique coverage to the live half --
#     which is the half that binds a later trim, so this is the direction the coverage should move.
#   * MUTANT TAKEN BY A SIBLING -- mutating any declared ROW field also changes the line R3/ROW
#     composes, so ROW and SET fire alongside whatever the mutant was written for: R3/SESSION,
#     R3/ORDINAL, R3/ROW, both R3/SET arms, R4/PROVENANCE, R4/SPAN, R5/ASSERTIONS, and both
#     R7/SPAN grammar guards. R0/SIZE loses its mutant the same way -- M2 moves DECLARED_OLD_LINES
#     and R0/FIGURE requires that same integer in the prose.
#   * REACHABLE, NEVER ALONE -- degradation guards that only fire in company, because a world broken
#     enough to reach them breaks a sibling too: R3/unreadable, R3/no-headings, R4/no-add-commit,
#     R4/LEFT-LIVE-unreadable, R5/no-def-L, R7/LIVE-TABLE-unparseable, the two remaining
#     R7/FRONTIER degradation guards, and the two `is MISSING` early returns in R6 and R8 -- M38
#     removes the file and R6, R7 and R8 all object at once, which is correct and costs each of them
#     a unique mutant.
#   * MUTUALLY SHADOWING -- R2's LOST-OR-EDITED and ADDED always fire together (an edited record is
#     one lost and one added); R2 as a whole uniquely catches M9, M10 and M11.
#   * PROVABLY SUBSUMED -- R1/BLOCK MISSING cannot fail without R1/CONFINEMENT failing, since `want`
#     contains the block by construction. Kept as a better message than a byte-offset diff.
#     R1/ANCHOR and R1/CONFINEMENT shadow each other for the same reason.
#
# A green --self-test whose mutants never exercise a NEW arm is the same lie as a green run. R7 and
# R8 are new in this lineage, so each carries mutants of its own, and R6's new fourth arm does too.
# ------------------------------------------------------------------------------------------------

set -euo pipefail
exec python3 - "$@" <<'PYEOF'
import re, subprocess, sys
from collections import Counter

LIVE = "SESSION_NOTES.md"
SELF = "docs/architecture-history/SESSION_NOTES-pointer-collapse-S254.verify.sh"
ARCH = "docs/architecture-history/"

# ---- the declared pre-collapse commit. Hand-supplied. R1's `before` is read from it (or from the
#      collapse commit's parent once that exists, which must agree with it). ----
PRE = "8c9bb35"

RECORD_START = re.compile(r"^### What Session (\S+) Did$")
DEF_L        = re.compile(r"^def (L\d+)\(", re.M)
TABLE_ROW    = re.compile(r"^\| \d+ \| ")
# R8's two families. BLOCK_HEAD is a prose pointer block's first line; BLOCKS_BELOW is the
# positional claim family C7 had to derive a count for. Both must be ABSENT after this collapse.
BLOCK_HEAD    = re.compile(r"^\*\*(\w+) trim \(Session \d+\)", re.M)
BLOCKS_BELOW  = re.compile(r"\*\*The (\w+ )?blocks? below (?:are|is) frozen", re.M)
# The count word is OPTIONAL. Inherited from C7, this read `The (\w+) blocks?` and therefore
# matched "**The two blocks below are frozen" but NOT "**The block below is frozen" -- and BOTH
# forms stood in the front matter this collapse removed. C7 could only ever have caught one of
# the two members of the family it was written for. Found by an adversarial review of THIS
# commit; the gap is closed here rather than inherited.
SPELLED = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
           8: "eight", 9: "nine", 10: "ten"}
ORDINAL = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth",
           7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth"}

DECLARED_OLD_LINES = 276        # R0: how many front-matter lines this collapse replaced
NEW_ORDINALS = (6, 7, 8)        # R3/FIGURE: the rows THIS collapse added

# The C-series pinned this line against the working tree. This collapse had to replace it, so R6
# proves it is GONE rather than merely stopping to require it.
C_SERIES_OLD_HEAD = ("**The first five trims are one table now (Session 246).** Their pointer "
                     "blocks stood here \u2014 176")

OLD_PROSE = r"""**Eighth trim (Session 245). Archived Sessions 241 → 239 — 3 record headings, 721 lines** into
[`docs/architecture-history/SESSION_NOTES-S241-through-S239.md`](docs/architecture-history/SESSION_NOTES-S241-through-S239.md)
— same shape, same newest-on-top order, frozen and byte-for-byte unedited. **This live file now
holds Sessions 245 → 242 only** — four records, the floor `CLAUDE.md` sets. Its proof is
[`SESSION_NOTES-S241-through-S239.md.verify.sh`](docs/architecture-history/SESSION_NOTES-S241-through-S239.md.verify.sh):
the fourteen assertions inherited from the seventh trim, plus **L14** — every ANCESTOR shard's span
and size figure in the four files no earlier proof reached, derived from those shards at their own
add-commits. L13 comes forward over **eight span sentences** stating which sessions moved, now with
a uniqueness arm; L14 is held against **32 declared literals** carrying **45 figures**, and by an
arm that proves that list is COMPLETE rather than merely correct.

**L14 exists because a shard's figures stop being read the moment it becomes an ancestor.** `L12`
closed the SIZE figures a trim states about its own cut; `L13` closed the SPANS. Both are scoped to
their own artifacts by construction — L12 measures the shard in hand, L13 derives from the ids of
the two files in hand — so at the ninth trim every figure this block states about
`SESSION_NOTES-S241-through-S239.md` falls out of reach and joins the rest. That is not
hypothetical: seven ancestors' worth were unread at this cut, and every one of them is TRUE,
re-measured here against each shard's own add-commit blob rather than against the working tree.
**`L14/set` is the arm that matters most** — it holds the shards the declared literals name against
`ROUTING`'s ancestor set, so a ninth trim cannot quietly leave this cut's shard outside L14's
reach, which is precisely how the hole stayed open for seven trims.

**The bequest that named L14 mis-counted it — and so did three of my own counts, which is why
`L14/complete` exists.** Session 242's bequest, quoted verbatim in its own record below and replaced
in its pointer block by this trim, said *"`(220→217, 804 lines)` and its fifteen siblings"* —
sixteen. Measured: **32** literals carrying **45** figures — eight spans in
`PROJECT_CONVENTIONS.md`'s naming rule, seven in `README.md`'s repo map, ten literals carrying
sixteen size figures in `BACKLOG.md` (which states the ancestor sizes in THREE places, not one — the
read-cap item's chain, the plain-language index row, and a parenthetical correcting a figure that
was wrong in Session 228), and seven span-and-size pairs in `CLAUDE.md`'s shard list.

**Four counts were typed before one was derived, all in this session.** The hand count said 28/36.
A first scan said 31/44 and shipped green. An adversarial review's independent scan found **45**
occurrences against 44 declared — the missed one an aside in `PROJECT_CONVENTIONS.md`, *"since
216→1 sit in the earlier file"*, nowhere near the list it belongs to. So the fix is not the 45th
literal. It is **`L14/complete`**, which scans each of the four files for every ancestor span and
size figure and fails unless each occurrence falls inside a declared literal. L14 now proves its
own list is complete instead of asserting it, which is learning
[#126](PROJECT_LEARNINGS.md) mechanised: *the list was written by someone who had not run it.*

**A second underived count sits in the block below, measured rather than alleged.** It says the
refined sweep *"returns nineteen files ... and the seven shards with their seven proofs"*. Nineteen
is the measurement at that trim's PARENT, `f26233a`; the enumeration beside it describes the
post-shard set, which measures **21** both at the trim commit `e7d5b03` and at HEAD. Both were run
here, not reasoned about. It is NOT repaired — that block is frozen and the sentence reports that
trim's own sweep — but it is recorded, because a FILE CENSUS is a third field, beside L12's sizes
and L13's spans, that nothing derives. **That is the ninth trim's L15**, and this sentence states
no count for it on purpose.

**Note the collision: the block below rejects an "L14" that is not this one.** That paragraph
records a fourteenth assertion drafted and dropped at the seventh trim — a census of stale shard
BANNERS, which would have measured four where the truth was five. It was rejected for a good
reason and it stays rejected. The L14 shipped here has a different subject; the name is reused only
because it is the next ordinal. Both are recorded so a later trim does not resurrect the dead one
believing it is the live one.

**The sweep was re-derived a fourth time, and the result is published rather than assumed.**
`git grep -l 'SESSION_NOTES-[A-Za-z0-9-]*\.md'` returns **23** files: the four `L8` reads, this one,
`PROJECT_LEARNINGS.md`, `docs/planning/repository-rename.md`, and the eight shards with their eight
proofs. The broad form adds `CHANGELOG.md` and `docs/architecture-history/evolution-page-plan.md`
on the phrase `SESSION_NOTES-as-rationale` — the sixth trim's prediction, confirmed by the seventh
and tested a third time here. Those two stay undeclared for the reason the seventh gave: each names
ONE shard inside a frozen statement and states no census, so `L8/set` would turn a correct record
red. **No fifth file, and no new unread count-carrying string inside the four** — the seventh
trim's four are still declared and still read, and the ancestor figures its sweep flagged are
`L14`'s now.

**Eight shards exist now, and none is a prefix of any other.** To place Session N, open the file
this table names. **This block is the authority**, and these nine clauses are machine-checked here,
in the shard's banner, and in `CLAUDE.md`:

**N ≤ 216** → `SESSION_NOTES-through-S216.md`; **217 ≤ N ≤ 220** → `SESSION_NOTES-S220-through-S217.md`;
**221 ≤ N ≤ 224** → `SESSION_NOTES-S224-through-S221.md`; **225 ≤ N ≤ 227** → `SESSION_NOTES-S227-through-S225.md`;
**228 ≤ N ≤ 231** → `SESSION_NOTES-S231-through-S228.md`; **232 ≤ N ≤ 235** → `SESSION_NOTES-S235-through-S232.md`;
**236 ≤ N ≤ 238** → `SESSION_NOTES-S238-through-S236.md`; **239 ≤ N ≤ 241** → `SESSION_NOTES-S241-through-S239.md`;
**N ≥ 242** → `SESSION_NOTES.md`.

`grep` the shards; `Read` none of them. **Shards stay write-once** — a ninth trim writes a ninth
file; it never appends to one of these eight.

**Six shard banners are stale now, and none may be repaired.** The S220 shard's still says *"the
live ledger when N ≥ 221"*; the S224, S227, S231 and S235 shards' banners still route Sessions 225,
228, 232 and 236 and up to this file; and the S238 shard's — which predicted in its own text that
it would join them "at the eighth trim" — now has. All six were true at their own cut, and none can
notice: the S220 proof predates L5, and the rest read their artifacts at their own trim commits.
Ours joins them at the ninth trim. **A shard banner is a snapshot of its own cut; this block is the
authority.**

**The two blocks below are frozen at the SEVENTH and SIXTH trims and describe THOSE cuts; the five
older ones are the table beneath them (Session 246).** This trim falsified exactly four passages of
the seventh trim's block — which sessions this live file holds, its routing paragraph, its count of
stale shard banners, and its claim that the ancestor figures are still unread — and rewrote all
four as declared substitutions the proof checks by exact equality. Every other byte of that block
is original and the older six were untouched at that cut. Each earlier proof reads its artifacts at
its own shard's commit, so none is disturbed; all seven were re-run green at this cut.

**Seventh trim (Session 242). Archived Sessions 238 → 236 — 3 record headings, 583 lines** into
[`docs/architecture-history/SESSION_NOTES-S238-through-S236.md`](docs/architecture-history/SESSION_NOTES-S238-through-S236.md)
— same shape, same newest-on-top order, frozen and byte-for-byte unedited. At that seventh cut
this live file was left holding Sessions 242 → 239 — four records, the floor `CLAUDE.md`
sets; the eighth trim above has since cut it again. Its proof is
[`SESSION_NOTES-S238-through-S236.md.verify.sh`](docs/architecture-history/SESSION_NOTES-S238-through-S236.md.verify.sh):
the thirteen assertions inherited from the sixth trim, plus **L13** — this shard's own FILENAME and
**eight declared sentences** stating which sessions moved, held against the record ids the two files
actually contain — eight declared, not "every": an adversarial review pushed a wrong span through
the first draft's uncounted one, and that count is itself checked now.

**L13 exists because a shard's filename is routing information that nothing ever derived.**
`docs/methodology/PROJECT_CONVENTIONS.md` gives the rule that produces one —
`<STEM>-<NEWEST>-through-<OLDEST>.md` after the first shard — and seven trims have hand-typed a name
under it with no proof ever parsing one. Measured, not suspected: a shard misnamed
`SESSION_NOTES-S238-through-S235.md` while holding Sessions 238 → 236 satisfies **L5/3** (the clause
says 236-238, which is what the cut archived), **L5/4** (the file that clause names really does hold
236-238) and **L8/set** (every file names the same wrong shard) at once. The span sentences had the
same shape — pinned only against a declaration the same author wrote, which is what **L12** closed
for sizes, one field over.

**Three inherited literals were SPLIT here, and every earlier pointer block's "narrowed nothing" is
a claim this one cannot make.** `L8`'s `PROJECT_CONVENTIONS.md` string now stops at *"(Session
242,"*; `L8` no longer requires `README.md`'s shard map line; `L12`'s banner literals were re-cut to
begin after the span. Each tail moved to **L13**, because a string two assertions read gives the
newer one no mutant of its own. **Net reach is unchanged** — every byte the sixth trim required is
still required, by `L8`, `L12`, `L13` or `L8/set` — but in two pieces, so a session grepping for one
of the old whole strings will not find it.

**A fourteenth assertion (L14) was drafted and rejected, and the measurement is the reason.** Every
pointer block states how many shard banners are stale and nothing derives it. A census counting
banners whose routing tables disagree with this block measures **four** — S224, S227, S231, S235 —
where the truth is **five**: the S220 banner routes in prose (*"the live ledger when N ≥ 221"*) in
no parseable clause form, and the S216 banner states no forward-looking rule at all. Mechanising
the parseable predicate would turn a correct sentence red.

**Seven shards existed at that cut, and none was a prefix of any other.** The routing table that
stood here named those seven and sent every session from 239 up to this live file; the eighth trim
falsified that last clause — Sessions 241 → 239 are in a shard now — and the table above replaces
it. `grep` the shards; `Read` none. **Shards stay write-once** — an eighth trim wrote an eighth
file; it did not append to one of those seven.

**Five shard banners were stale at that cut; six are now.** The S238 shard's own prediction that
it would join the S220, S224, S227, S231 and S235 banners "at the eighth trim" has come true. All
six were true at their own cut, and none can notice: the S220 proof predates L5, and the rest read
their artifacts at their own trim commits.

**The sweep found FOUR unread strings, and the first draft of this paragraph published one.**
`git grep -l 'SESSION_NOTES-[A-Za-z0-9-]*\.md'` — the refined form the sixth trim recommended —
returns nineteen files: the four **L8** reads, this one, `PROJECT_LEARNINGS.md`,
`docs/planning/repository-rename.md`, and the seven shards with their seven proofs. It **drops
`CHANGELOG.md` and the evolution plan**, which the broad form still returns on the phrase
`SESSION_NOTES-as-rationale` — a sixth-trim prediction, tested here and held. The two candidates
stay undeclared: each names ONE shard inside a frozen statement and states no census, so `L8/set`,
which requires a declared file to name the whole set, would turn a correct record red. Inside the
four declared files, **four** count-carrying strings were read by no
assertion: `CLAUDE.md`'s *"holds the newest 4 sessions"*, `PROJECT_CONVENTIONS.md`'s *"the third,
fourth, fifth, sixth and seventh trims all did"*, and `BACKLOG.md`'s *"Sessions 224, 228, 231, 235,
239 and 242 widened this:"* and its *"and the seventh,"*. **All four are declared now** — the last
three only because an adversarial review reverted each one and watched all seven proofs stay green.
**Left for the eighth trim on purpose, and read there:** every ANCESTOR shard's span and size
figure in those same four files. The eighth trim's `L14` holds all of them, and the count this
sentence gave for them was itself underived — the block above measures it.

**The block below is frozen at the SIXTH trim and describes THAT cut; the five older ones are the
table beneath it (Session 246).** This trim falsified exactly three passages of the sixth trim's
block — which sessions this live file holds, its routing paragraph, and its count of stale shard
banners — and rewrote all three as declared substitutions the proof checks by exact equality. Every
other byte of that block is original and the older five were untouched at that cut. Each earlier
proof reads its artifacts at its own shard's commit, so none is disturbed; all six were re-run
green at this cut.

**Sixth trim (Session 239). Archived Sessions 235 → 232 — 4 record headings, 1,004 lines** into
[`docs/architecture-history/SESSION_NOTES-S235-through-S232.md`](docs/architecture-history/SESSION_NOTES-S235-through-S232.md)
— same shape, same newest-on-top order, frozen and byte-for-byte unedited. At that sixth cut
this live file was left holding Sessions 239 → 236 — four records, the floor `CLAUDE.md`
sets; the seventh trim above has since cut it again. Its proof is
[`SESSION_NOTES-S235-through-S232.md.verify.sh`](docs/architecture-history/SESSION_NOTES-S235-through-S232.md.verify.sh):
the twelve assertions inherited from the fifth trim, none of them narrowed or weakened, plus
**L12** — every number this trim states about the size of its own artifacts, derived from the
artifacts and held against the prose that states it.

**L12 exists because the fifth trim's own figures were checked by nothing, and this is the defect
this project reports most.** That trim's pointer block says *"4 record headings, 918 lines"*, its
banner says *"At 976 lines it sits under the 2,000-line agent read cap"*, and `BACKLOG.md` says
*"(976 lines)"*. **All three are correct** — re-measured at this cut: 976 lines, 918 of them
records. But nothing compared any of them to the artifact. They are literal text, pinned by L2/b1
and L6 against a declaration the same author wrote, so a trim that typed the wrong figure would
have shipped it green in three places at once — and five consecutive sessions have now
self-reported a numeral typed instead of derived. L12 measures the archived heading count, the
archived line count and the shard's total line count; holds all three against hand-declared
integers; asserts the shard is under the read cap it claims to be under; and holds those integers
against the formatted numbers that actually appear in this block, in the shard's banner, in
`README.md` and in `BACKLOG.md`. Two independent halves, six arms, nine mutants.

**Six shards existed at that cut, and none was a prefix of any other.** The routing table that
stood here named those six and sent every session from 236 up to this live file; the seventh trim
falsified that last clause — Sessions 238 → 236 are in a shard now — and the table above replaces
it. `grep` the shards; `Read` none. **Shards stay write-once** — a seventh trim wrote a seventh
file; it did not append to one of those six.

**Four shard banners were stale at that cut; five are now.** The S235 shard's own prediction
that it would join the S220, S224, S227 and S231 banners "at the seventh trim" has come true. All
five were true at their own cut, and none can notice: the S220 proof predates L5, and the rest read
their artifacts at their own trim commits. **A shard banner is a snapshot of its own cut; this block is the authority.**

**The sweep was re-run and found no new copy — which is a result, not a formality.**
`git grep -l 'SESSION_NOTES-'` returns nine files: the four L8 already reads, this one, and **four
that are new since the fifth trim swept** — `CHANGELOG.md`, `PROJECT_LEARNINGS.md`,
`docs/architecture-history/evolution-page-plan.md` and `docs/planning/repository-rename.md`.
**None of the four is a copy of the shard census, and declaring any of them would have shipped a
falsehood.** `CHANGELOG.md` and the evolution plan match only on the phrase
`SESSION_NOTES-as-rationale`, which is not a filename — the sweep string over-matches, and
`git grep -l 'SESSION_NOTES-[A-Za-z0-9-]*\.md'` drops both. The other two cite shard filenames
inside frozen historical statements that were true when written and are true now, and neither says
how many shards exist; because `L8/set` requires a declared file to name the *whole* set, declaring
either would have turned a correct record red. That is the fifth trim's own rule — sweep for the
class, never trust the list — applied and, this time, returning nothing. **Sweep again at the
seventh trim rather than trusting this paragraph either.**

**The five blocks that stood below this one — the FIFTH trim's down to the FIRST's — are the table
beneath it now (Session 246); each is still readable at its own commit.** This trim falsified
exactly three passages of the fifth trim's block — its claim about which sessions this live file
holds, its whole routing paragraph, and its count of how many shard banners are stale — and rewrote
all three as declared substitutions the proof checks by exact equality. Every other byte of that
block is original, and the fourth, third, second and first trims' blocks were untouched at that
cut. Each earlier proof reads its artifacts from the commit that added its own shard, so this trim

**The first five trims are one table now (Session 246).** Their pointer blocks stood here — 176
lines, the fifth trim's down to the first's — until the front matter became the half of this file
that grows: Session 245 measured the retention rule's 1,050-line target converging on its four-record
floor, put three remedies to the operator, and this is the one chosen. **Nothing was archived and no
record moved.** Each collapsed block is still readable byte-for-byte in two places — at commit
`ddd5660`, and embedded verbatim in the proof named below, which asserts those two are equal. Every
measurement in the table — every span, count, line total, trim commit and assertion credit — is
DERIVED from the artifacts at their own add-commits, and the proof COMPOSES each row's line from
those measurements rather than comparing against it. Two fields are declarations the proof checks
rather than measurements it takes: the ordinal, which is definitional, and the trim's session
number, which it re-derives as the newest record this file held at that commit.

| # | trim | archived | rec | lines | shard, under `docs/architecture-history/` | shard | left live | added |
|--:|------|----------|----:|------:|------------------------------------------|------:|-----------|-------|
| 1 | S222 `a9510ca` | 216 → 1 | 206 | 24,564 | `SESSION_NOTES-through-S216.md` | 24,590 | 222 → 217 | L0, L1, L2, L3 |
| 2 | S224 `07e1ab9` | 220 → 217 | 5 | 774 | `SESSION_NOTES-S220-through-S217.md` | 804 | 224 → 221 | L4 |
| 3 | S228 `e4ca944` | 224 → 221 | 4 | 891 | `SESSION_NOTES-S224-through-S221.md` | 933 | 228 → 225 | L5, L6, L7 |
| 4 | S231 `f3fea4e` | 227 → 225 | 3 | 738 | `SESSION_NOTES-S227-through-S225.md` | 790 | 231 → 228 | L8, L9 |
| 5 | S235 `a7512cb` | 231 → 228 | 4 | 918 | `SESSION_NOTES-S231-through-S228.md` | 976 | 235 → 232 | L10, L11 |

*`archived` is the session span that left this file and `rec` how many record headings went with it;
`lines`, the lines they took; `shard`, that file's total; `left live`, what this file was left
holding at that cut; `added`, the assertions that trim contributed to the inherited set. Each
shard's proof is its own path with `.verify.sh` appended.*

The proof is
[`SESSION_NOTES-pointer-collapse.verify.sh`](docs/architecture-history/SESSION_NOTES-pointer-collapse.verify.sh),
and its assertions are lettered **C0–C6** rather than numbered: this is not a trim, they are not the
`L`-series, and Session 245 had to record an `L14` collision to stop a later trim resurrecting a
rejected assertion under a live name. **C6 holds this table against the WORKING TREE; no `L`-series
assertion holds any PROSE against it** — which is the finding worth carrying forward on its own.
Every shard proof resolves its prose operands from its own trim commit: the live file *and*
`CLAUDE.md`, `README.md`, `BACKLOG.md` and `PROJECT_CONVENTIONS.md` are all read as they stood
**then**. What the `L`-series does read from disk is the shards and the proof scripts, by `L7`,
`L9` and `L10` — bytes, not claims. So the moment a trim lands, every
prose copy this apparatus exists to keep in step stops being checked — this front matter, the block
above that calls itself "the authority", and all four files `L8` reaches. Session 246 measured it,
with a control: corrupt the live pointer block's routing clause and figures, or `CLAUDE.md`'s shard
census, or `BACKLOG.md`'s, or `PROJECT_CONVENTIONS.md`'s, and all eight proofs stay green; edit an
ancestor shard on disk and they go red. Session 245's gotcha 2 — that those four are read *live* —
held only while its own trim was uncommitted. C6 closes this for the table above and nothing else.
**The rest is the ninth trim's, and it is the largest hole this lineage has.**

**Cutting is by byte position, never by authorship.** This ledger files a handoff evaluation under
its author, so Session N's evaluation of N−1 sits inside N's record and every cut so far has split
one from its subject. Expect that seam at every boundary. What these five trims found, argued and
rejected stays in their own blocks at the commits above; what they left BINDING is in `CLAUDE.md`'s
two `SESSION_NOTES.md`-is-trimmed bullets, which no collapse touches. **`grep` the shards; `Read`
none** — the first is 24,590 lines and a default `Read` of it is refused outright, not all of the
seven newer shards read whole either, and nothing watches any of them. (This
sentence claimed a silent stop at 2,000 lines until Session 249; measured, that is false.)

"""

NEW_BLOCK = r"""**One trim, one row — and that is the rule now (Session 254, on the operator's ruling of
2026-09-07).** Every trim moves retired records into a frozen shard, and each one used to write a
prose pointer block here. Five of those blocks became the table below at Session 246; the three
that were still standing — the sixth, seventh and eighth trims' — are rows 6, 7 and 8 of it now,
and every future trim adds a row instead of a block. **Nothing was archived and no record moved.**
The retired prose is readable byte-for-byte in three places: at the pre-collapse commit `8c9bb35`,
embedded verbatim inside the proof named below, and — for the rationale each block argued — in the
record of the session that wrote it. `docs/planning/ledger-budgets-review.md` §8 row E is the
mechanism; §13.1 is the ruling; §13.3 is the arithmetic that put E ahead of D.

**To place Session N, read the `archived` column.** The row whose span contains N names the file
that holds it; a session newer than the newest archived span is in this file. Those spans tile the
whole history with no gap and no overlap, and the proof ASSERTS that rather than trusting it — so
**the table is the routing table**, and the prose clauses that used to state it are gone rather than
duplicated. **`grep` the shards; `Read` none** — a default `Read` of the largest is refused
outright, not all of the others come back whole either, and nothing watches any of them.

**Shards stay write-once.** A ninth trim writes a ninth file; it never appends to one of these.
That is also why every shard after the first is named as a range rather than in the first's
open-ended `-through-S216` form — `docs/methodology/PROJECT_CONVENTIONS.md` §3.1 carries the rule
and the reason.

**A shard banner is a snapshot of its own cut; this table is the authority.** Several banners still
route sessions to this live file that have since moved into a shard. Each was true when it was
written, none may be repaired, and no proof can notice: every shard proof reads its prose at its own
trim commit, so from the moment a trim lands its prose is checked by nothing until the next one.
That is this apparatus's largest hole, it is measured rather than suspected, and only two mechanisms
close any of it: the working-tree arms `R6` and `C6` below, and
`tests/test_session_notes_census.py`, which holds the prose files outside this one against the
shards on every CI run.

**Three things are bequeathed to the ninth trim. They are instructions, not notes.**

1. **`L15`, the FILE CENSUS.** Every trim states how many files its sweep returned, and nothing
   derives it. The figure retired from this front matter today had rotted from true to false with
   every proof green — Session 254's record names the files that moved it.
2. **The `L`-numbering collision must not be re-opened.** A fourteenth assertion was drafted at the
   seventh trim and REJECTED on measurement; a *different* `L14` then shipped at the eighth. Both
   facts live in Sessions 242's and 245's records. A later trim must not resurrect the rejected one
   believing it is the live one. That hazard is also why the two collapse proofs are lettered `C`
   and `R`: neither is an `L`, and neither letter is an option letter in the review document.
3. **A sweep result is a deliverable** — publish it, and never repeat a sweep sentence unchanged.
   Both items above exist because a session did the second thing.

| # | trim | archived | rec | lines | shard, under `docs/architecture-history/` | shard | left live | added |
|--:|------|----------|----:|------:|------------------------------------------|------:|-----------|-------|
| 1 | S222 `a9510ca` | 216 → 1 | 206 | 24,564 | `SESSION_NOTES-through-S216.md` | 24,590 | 222 → 217 | L0, L1, L2, L3 |
| 2 | S224 `07e1ab9` | 220 → 217 | 5 | 774 | `SESSION_NOTES-S220-through-S217.md` | 804 | 224 → 221 | L4 |
| 3 | S228 `e4ca944` | 224 → 221 | 4 | 891 | `SESSION_NOTES-S224-through-S221.md` | 933 | 228 → 225 | L5, L6, L7 |
| 4 | S231 `f3fea4e` | 227 → 225 | 3 | 738 | `SESSION_NOTES-S227-through-S225.md` | 790 | 231 → 228 | L8, L9 |
| 5 | S235 `a7512cb` | 231 → 228 | 4 | 918 | `SESSION_NOTES-S231-through-S228.md` | 976 | 235 → 232 | L10, L11 |
| 6 | S239 `28879a0` | 235 → 232 | 4 | 1,004 | `SESSION_NOTES-S235-through-S232.md` | 1,057 | 239 → 236 | L12 |
| 7 | S242 `e7d5b03` | 238 → 236 | 3 | 583 | `SESSION_NOTES-S238-through-S236.md` | 644 | 242 → 239 | L13 |
| 8 | S245 `4ab6306` | 241 → 239 | 3 | 721 | `SESSION_NOTES-S241-through-S239.md` | 792 | 245 → 242 | L14 |

*`archived` is the session span that left this file and `rec` how many record headings went with it;
`lines`, the lines they took; `shard`, that file's total; `left live`, what this file was left
holding at that cut; `added`, the assertions that trim contributed to the inherited set. Each
shard's proof is its own path with `.verify.sh` appended.*

**The proofs, and what each can see.** The first collapse is
[`SESSION_NOTES-pointer-collapse.verify.sh`](docs/architecture-history/SESSION_NOTES-pointer-collapse.verify.sh),
lettered `C`; this one is
[`SESSION_NOTES-pointer-collapse-S254.verify.sh`](docs/architecture-history/SESSION_NOTES-pointer-collapse-S254.verify.sh),
lettered `R`, and the 276 lines of front matter it replaced are embedded in it verbatim.
Neither is a shard proof and neither is an `L`. Both hold the records byte-identical across their
own commit — a collapse commit carries no record edit, the same rule `CLAUDE.md` sets for a trim —
and both COMPOSE each row of the table above from figures measured at a shard's own add-commit
instead of comparing against a typed one. `R` re-derives **every** row rather than only the ones it
added, so the table has exactly one owner; and it proves the `archived` spans tile the history with
no gap and no overlap, which is what allows the routing clauses to be deleted rather than kept in
parallel. `R6` and `C6`
are the only assertions in this repository that read the WORKING TREE; everything else reads its
operands at a commit that has already passed, which is why the census guard exists for the four
files outside this one. **Run both modes over every proof in `docs/architecture-history/`** — a plain
run proves the world is intact and cannot see a proof that has stopped being able to fail;
`--self-test` proves the proof can fail and is blind to real corruption. `CLAUDE.md` carries the
loop and the reason neither half is sufficient.

**Cutting is by byte position, never by authorship.** This ledger files a handoff evaluation under
its author, so Session N's evaluation of N−1 sits inside N's record, and every cut so far has split
one from its subject. Expect that seam at every boundary. What these eight trims found, argued and
rejected stays in their own records and, for the blocks that stood here, at the commits above. What
they left BINDING is in `CLAUDE.md`'s `SESSION_NOTES.md`-is-trimmed bullets, which this collapse
updates rather than contradicts.

"""

# ---- the eight collapsed trims. Hand-declared; R3/R4/R5 measure every field from git and
#      compare. (ordinal, trim session, trim sha, archived span, headings, archived lines,
#      shard basename, shard total lines, live span left behind, assertions that trim added) ----
ROWS = (
    (1, "222", "a9510ca", ("216", "1"),   206, 24564,
     "SESSION_NOTES-through-S216.md",       24590, ("222", "217"), ("L0", "L1", "L2", "L3")),
    (2, "224", "07e1ab9", ("220", "217"),    5,   774,
     "SESSION_NOTES-S220-through-S217.md",    804, ("224", "221"), ("L4",)),
    (3, "228", "e4ca944", ("224", "221"),    4,   891,
     "SESSION_NOTES-S224-through-S221.md",    933, ("228", "225"), ("L5", "L6", "L7")),
    (4, "231", "f3fea4e", ("227", "225"),    3,   738,
     "SESSION_NOTES-S227-through-S225.md",    790, ("231", "228"), ("L8", "L9")),
    (5, "235", "a7512cb", ("231", "228"),    4,   918,
     "SESSION_NOTES-S231-through-S228.md",    976, ("235", "232"), ("L10", "L11")),
    (6, "239", "28879a0", ("235", "232"),    4,  1004,
     "SESSION_NOTES-S235-through-S232.md",   1057, ("239", "236"), ("L12",)),
    (7, "242", "e7d5b03", ("238", "236"),    3,   583,
     "SESSION_NOTES-S238-through-S236.md",    644, ("242", "239"), ("L13",)),
    (8, "245", "4ab6306", ("241", "239"),    3,   721,
     "SESSION_NOTES-S241-through-S239.md",    792, ("245", "242"), ("L14",)),
)

ROOT = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                      capture_output=True, text=True, check=True).stdout.strip()
MISSING = object()


def blob(ref):
    r = subprocess.run(["git", "show", ref], capture_output=True, cwd=ROOT)
    if r.returncode:
        return None
    return r.stdout.decode("utf-8")          # bytes -> str; never $(...) which eats trailing newlines


def worktree(rel):
    try:
        with open("%s/%s" % (ROOT, rel), encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return MISSING


def addcommit(rel):
    r = subprocess.run(["git", "log", "--diff-filter=A", "--format=%H", "--", rel],
                       capture_output=True, text=True, cwd=ROOT)
    out = [l for l in r.stdout.split() if l]
    return out[-1] if out else None


def scan(lines):
    inside = False
    for i, raw in enumerate(lines):
        s = raw.rstrip("\r\n")
        if s.startswith("```") or s.startswith("~~~"):
            yield i, s, inside
            inside = not inside
            continue
        yield i, s, inside


def zones(text):
    """-> (front, [record, ...]). A record is a heading-delimited BYTE SPAN, never a session."""
    lines = text.splitlines(keepends=True)
    st = [i for i, s, ins in scan(lines) if not ins and RECORD_START.match(s)]
    if not st:
        return text, []
    bounds = st + [len(lines)]
    return "".join(lines[:st[0]]), ["".join(lines[a:b]) for a, b in zip(st, bounds[1:])]


def ids(text):
    _f, recs = zones(text)
    return tuple(RECORD_START.match(r.splitlines()[0]).group(1) for r in recs)


def row_line(ordinal, sess, sha, span, rec, arch_lines, shard, total, live, added):
    """The row's markdown line, COMPOSED from the values -- never matched loosely against the
    table. R3 feeds this the MEASURED numbers, so a typed figure cannot survive."""
    return ("| %d | S%s `%s` | %s \u2192 %s | %d | %s | `%s` | %s | %s \u2192 %s | %s |"
            % (ordinal, sess, sha, span[0], span[1], rec, format(arch_lines, ","),
               shard, format(total, ","), live[0], live[1], ", ".join(added)))


def rows_of(text):
    return [l for l in text.split("\n") if TABLE_ROW.match(l)]


LIVE_SPAN = re.compile(r"^\| \d+ \| [^|]+\| (\d+) \u2192 (\d+) \|")


def live_spans(front):
    """The archived spans as the WORKING TREE's table states them. R7's live arms read these, never
    the declared ROWS -- see R7's docstring for the trap that forced it."""
    out = []
    for l in rows_of(front):
        m = LIVE_SPAN.match(l)
        if m:
            out.append((int(m.group(2)), int(m.group(1))))     # (oldest, newest)
    return sorted(out)


def declared_front(before_front, old_prose, new_block):
    """The front matter this collapse is ALLOWED to produce. ONE replacement, no substitutions --
    see R1's docstring for why the list is empty rather than merely short."""
    return before_front.replace(old_prose, new_block, 1)


def gather(rows):
    """Everything read from git, once. Shards and proofs are read AT THEIR OWN ADD-COMMITS, never
    from disk -- L9/L10 prove disk == add-commit, so reading disk would make these assertions
    silently depend on those two holding."""
    world = {}
    for row in rows:
        shard = row[6]
        rel = ARCH + shard
        prel = rel + ".verify.sh"
        ssha = addcommit(rel)
        psha = addcommit(prel)
        world[shard] = {
            "addsha": ssha,
            "shard": blob("%s:%s" % (ssha, rel)) if ssha else None,
            "live": blob("%s:%s" % (ssha, LIVE)) if ssha else None,
            "proof": blob("%s:%s" % (psha, prel)) if psha else None,
            "shard_disk": worktree(rel),
            "proof_disk": worktree(prel),
        }
    return world


# =====================================================================================
# The assertions. Each returns a list of failure strings; empty == holds.
# =====================================================================================

def R0(pre_live, old_prose, declared_lines, new_block):
    """A PIN, not a derivation -- see the header. It makes the two copies of the replaced prose
    impossible to change alone, and gives this file custody of the second one."""
    out = []
    if pre_live is None:
        return ["R0 PIN: the declared pre-collapse commit %s does not hold %s -- the declaration "
                "is wrong, or the history was rewritten" % (PRE, LIVE)]
    n = pre_live.count(old_prose)
    if n != 1:
        out.append("R0 PIN: the %d replaced lines occur %d times in %s at %s (want exactly 1) -- "
                   "the embedded copy is not the text that was replaced"
                   % (declared_lines, n, LIVE, PRE))
    got = old_prose.count("\n")
    if got != declared_lines:
        out.append("R0 SIZE: the embedded replaced text is %d lines; the collapse declares %d"
                   % (got, declared_lines))
    # L12's shape, and C0/FIGURE's: hold the derived integer against the FORMATTED figure the prose
    # prints. The C-series shipped "176 lines" and "`ddd5660`" read by nothing until a review found
    # them; this arm is that finding, inherited rather than re-learned.
    for what, lit in (("replaced-line count", format(declared_lines, ",")),
                      ("pinned commit", "`%s`" % PRE)):
        if new_block.count(lit) != 1:
            out.append("R0 FIGURE: the new block states the %s %s %d times (want exactly 1) -- the "
                       "prose and the declaration have parted company"
                       % (what, lit, new_block.count(lit)))
    return out


def R1(before_front, after_front, old_prose, new_block):
    """CONFINEMENT. One replacement, no declared substitutions: this collapse leaves no prose
    pointer block standing, so it falsifies no surviving positional claim and has nothing to
    substitute. R8 is what keeps that true of later trims."""
    out = []
    if before_front.count(old_prose) != 1:
        out.append("R1 ANCHOR: the replaced text occurs %d times in the pre-collapse front matter "
                   "(want exactly 1)" % before_front.count(old_prose))
    if new_block not in after_front:
        out.append("R1 BLOCK MISSING: the declared new block is not in the post-collapse front "
                   "matter verbatim -- %d lines replaced and nothing put in their place"
                   % DECLARED_OLD_LINES)
    want = declared_front(before_front, old_prose, new_block)
    if after_front != want:
        i = next((n for n, (a, b) in enumerate(zip(after_front, want)) if a != b),
                 min(len(after_front), len(want)))
        out.append("R1 CONFINEMENT: the front matter changed beyond the single declared "
                   "replacement; first divergence at character %d (%d B got vs %d B declared)"
                   % (i, len(after_front.encode()), len(want.encode())))
    return out


def R2(before_recs, after_recs):
    """A collapse commit carries no record edit -- the same rule CLAUDE.md sets for a trim commit,
    enforced here rather than promised. Session 254's Phase 1B stub was committed alone, first,
    so that this holds."""
    out = []
    if before_recs != after_recs:
        b, a = Counter(before_recs), Counter(after_recs)
        for r in (b - a).elements():
            out.append("R2 RECORD LOST OR EDITED: %r" % r.splitlines()[0][:90])
        for r in (a - b).elements():
            out.append("R2 RECORD ADDED by the collapse commit: %r" % r.splitlines()[0][:90])
        if not out:
            out.append("R2 RECORD ORDER: the records zone holds the same records in a different "
                       "order (%d records)" % len(after_recs))
    return out


def R3(rows, world, new_block):
    """Measure, compose, then require. Every number in the table is built from the artifacts --
    all eight rows, not only the three this collapse added, so the table has one owner."""
    out, composed, seen = [], [], 0
    for (ordinal, sess, sha, span, rec, arch_lines, shard, total, live, added) in rows:
        w = world.get(shard)
        if not w or w["shard"] is None:
            out.append("R3 `%s`: not readable at its own add-commit -- nothing to measure" % shard)
            continue
        lines = w["shard"].splitlines()
        heads = [i for i, s, ins in scan(lines) if not ins and RECORD_START.match(s)]
        if not heads:
            out.append("R3 `%s`: no record headings -- grammar mismatch" % shard)
            continue
        m_rec, m_total, m_arch = len(heads), len(lines), len(lines) - heads[0]
        for what, got, want in (("record headings", m_rec, rec),
                                ("archived lines", m_arch, arch_lines),
                                ("shard total lines", m_total, total)):
            if got != want:
                out.append("R3 SIZE `%s`: measured %d %s at %s; the table declares %d"
                           % (shard, got, what, w["addsha"][:7], want))
        got_sess = ids(w["live"])[0] if w["live"] and ids(w["live"]) else None
        if got_sess != sess:
            out.append("R3 SESSION `%s`: the newest record this file held at %s is Session %s; "
                       "the table credits the trim to Session %s"
                       % (shard, w["addsha"][:7], got_sess, sess))
        if ordinal != seen + 1:
            out.append("R3 ORDINAL `%s`: it is row %d of the table but numbered %d"
                       % (shard, seen + 1, ordinal))
        seen += 1
        want_line = row_line(ordinal, sess, sha, span, m_rec, m_arch, shard, m_total, live, added)
        composed.append(want_line)
        n = new_block.count(want_line)
        if n != 1:
            out.append("R3 ROW `%s`: the row composed from the MEASURED figures occurs %d times in "
                       "the new block (want exactly 1):\n           %s" % (shard, n, want_line))
    # SET: containment per declared row is not enough. A review of the C-series inserted a sixth row
    # naming a shard that does not exist and every assertion stayed green, because C3 iterated ROWS
    # and never the table. Inherited, not rediscovered.
    present = rows_of(new_block)
    for l in [l for l in present if l not in composed]:
        out.append("R3 SET: the table carries a row no declared trim composes: %s" % l[:110])
    if len(present) != len(rows):
        out.append("R3 SET: the table has %d data rows; %d trims are declared"
                   % (len(present), len(rows)))
    # FIGURE: every arithmetic phrase the new prose states ABOUT ITSELF, composed from the declared
    # row sets rather than searched for. C3/FIGURE learned that `count("five") >= 1` is not an
    # assertion when the word occurs twice; these are exact and each is counted.
    n_all, n_new = len(rows), len(NEW_ORDINALS)
    ords = tuple(sorted(NEW_ORDINALS))
    shapes = (
        "What these %s trims found" % SPELLED.get(n_all, "?"),
        "%s of those blocks became the table below at Session 246"
        % SPELLED.get(n_all - n_new, "?").capitalize(),
        "are rows %s of it now"
        % (", ".join(str(o) for o in ords[:-1]) + " and %d" % ords[-1]),
        "the %s trims'"
        % (", ".join(ORDINAL.get(o, "?") for o in ords[:-1]) + " and %s" % ORDINAL.get(ords[-1], "?")),
    )
    for lit in shapes:
        if new_block.count(lit) != 1:
            out.append("R3 FIGURE: the new block states its own arithmetic as %r %d times (want "
                       "exactly 1) -- composed from the declared rows, not searched for"
                       % (lit, new_block.count(lit)))
    return out


def R4(rows, world):
    out = []
    for (_o, _s, sha, span, _r, _al, shard, _t, live, _a) in rows:
        w = world.get(shard)
        if not w or not w["addsha"]:
            out.append("R4 `%s`: git knows no commit that ADDED this shard" % shard)
            continue
        if w["addsha"][:len(sha)] != sha:
            out.append("R4 PROVENANCE `%s`: the table names trim commit %s; the commit that added "
                       "this shard is %s" % (shard, sha, w["addsha"][:7]))
        if w["shard"] is not None:
            got = ids(w["shard"])
            if not got or (got[0], got[-1]) != span:
                out.append("R4 SPAN `%s`: it holds Sessions %s -> %s; the table says %s -> %s"
                           % (shard, got[0] if got else "?", got[-1] if got else "?",
                              span[0], span[1]))
        if w["live"] is None:
            out.append("R4 LEFT-LIVE `%s`: %s is unreadable at %s" % (shard, LIVE, sha))
        else:
            got = ids(w["live"])
            if not got or (got[0], got[-1]) != live:
                out.append("R4 LEFT-LIVE `%s`: at %s the live file held Sessions %s -> %s; the "
                           "table says %s -> %s" % (shard, sha, got[0] if got else "?",
                                                    got[-1] if got else "?", live[0], live[1]))
        for kind, key in (("shard", "shard_disk"), ("proof", "proof_disk")):
            if w[key] is MISSING:
                out.append("R4 GONE `%s`: the %s the table sends readers to is not on disk"
                           % (shard, kind))
    return out


def R5(rows, world):
    """What each trim CONTRIBUTED, derived by parsing its own proof at its own add-commit."""
    out = []
    prev = frozenset()
    for (_o, sess, _sha, _sp, _r, _al, shard, _t, _lv, added) in rows:
        w = world.get(shard)
        if not w or w["proof"] is None:
            out.append("R5 `%s`: its proof is not readable at its add-commit" % shard)
            prev = frozenset()
            continue
        have = frozenset(DEF_L.findall(w["proof"]))
        if not have:
            out.append("R5 `%s`: its proof defines no `def L<N>(` -- grammar mismatch" % shard)
            prev = frozenset()
            continue
        gained = tuple(sorted(have - prev, key=lambda x: int(x[1:])))
        if gained != tuple(added):
            out.append("R5 ASSERTIONS `%s` (Session %s): that proof adds %s over its predecessor; "
                       "the table says %s" % (shard, sess, list(gained), list(added)))
        prev = have
    return out


def R6(live_wt, old_prose, new_block):
    """One of the two assertions in this repository that read the WORKING-TREE front matter."""
    if live_wt is MISSING:
        return ["R6 LIVE: %s is not on disk" % LIVE]
    out = []
    for r in rows_of(new_block):
        n = live_wt.count(r)
        if n != 1:
            out.append("R6 LIVE: a table row occurs %d times in the working tree's %s (want "
                       "exactly 1): %s" % (n, LIVE, r[:110]))
    head = new_block.split("\n")[0]
    if live_wt.count(head) != 1:
        out.append("R6 LIVE: the new block's opening line occurs %d times in the working tree's %s "
                   "(want exactly 1) -- the block was removed or duplicated"
                   % (live_wt.count(head), LIVE))
    if old_prose in live_wt:
        out.append("R6 LIVE: the %d replaced lines are STILL in the working tree's %s -- the "
                   "collapse is declared but not applied" % (DECLARED_OLD_LINES, LIVE))
    # The arm that makes the substitution PROVED rather than permitted. C6 pinned this exact line
    # against the working tree; this collapse had to replace it. A proof that merely stopped
    # requiring it would leave both texts legal, and the stale one is the one that reads "five".
    if C_SERIES_OLD_HEAD in live_wt:
        out.append("R6 SUBSTITUTED: the C-series table's OLD opening line is still in the working "
                   "tree's %s -- it says the table holds five trims, and it holds %d. The C-series "
                   "must be re-pointed at the new line, not merely relieved of the old one."
                   % (LIVE, len(ROWS)))
    return out


def R7(rows, live_wt):
    """The assertion that licenses DELETING the routing clauses -- in two halves, and the split is
    the whole point.

    The DECLARED half tiles the hand-written ROWS: frozen at this commit, so it can only ever
    restate what R3 and R4 already prove. The LIVE half reads the table out of the WORKING TREE and
    is the one that binds a FUTURE trim.

    THE FIRST DRAFT MIXED THEM AND HAD NO GREEN STATE, which an adversarial review of this very
    commit measured and this session then reproduced by simulating a ninth trim. It compared the
    max archived session of the FROZEN ROWS (241) against the LIVE oldest record id. After a ninth
    trim the live file begins at, say, 250 and the arm fails; extending ROWS to nine entries fails
    R3 SET, because NEW_BLOCK is pinned at this file's add-commit with eight rows; and editing
    NEW_BLOCK fails R1. That is the C3 "rows cannot be extended" trap reproduced one level up,
    inside the brand-new arm, in the session whose own record calls that trap out. Reading the
    frontier from the LIVE table instead gives a ninth trim exactly one green state: add the row
    AND archive the records. Which is the behaviour this assertion is supposed to compel."""
    out = []
    # ---- (a) the DECLARED spans, as hand-written in ROWS ----
    spans = []
    for (_o, _s, _sha, span, _r, _al, shard, _t, _lv, _a) in rows:
        try:
            newest, oldest = int(span[0]), int(span[1])
        except ValueError:
            out.append("R7 SPAN `%s`: %r is not a pair of integers -- the routing rule cannot be "
                       "evaluated over it" % (shard, span))
            continue
        if oldest > newest:
            out.append("R7 SPAN `%s`: the declared span %s -> %s runs backwards"
                       % (shard, span[0], span[1]))
            continue
        spans.append((oldest, newest, shard))
    if not spans:
        out.append("R7 TILING: no evaluable declared spans -- nothing to tile")
    spans.sort()
    for (lo1, hi1, s1), (lo2, hi2, s2) in zip(spans, spans[1:]):
        if lo2 <= hi1:
            out.append("R7 OVERLAP: `%s` covers %d-%d and `%s` covers %d-%d -- a session in the "
                       "overlap has two homes and the `archived` column cannot route it"
                       % (s1, lo1, hi1, s2, lo2, hi2))
        elif lo2 != hi1 + 1:
            out.append("R7 GAP: `%s` ends at %d and `%s` starts at %d -- Sessions %d-%d are routed "
                       "to no file at all" % (s1, hi1, s2, lo2, hi1 + 1, lo2 - 1))
    # ---- (b) the LIVE table -- the half that survives a later trim ----
    if live_wt is MISSING:
        out.append("R7 FRONTIER: %s is not on disk -- the live arms cannot run" % LIVE)
        return out
    front = zones(live_wt)[0]
    lspans = live_spans(front)
    if not lspans:
        out.append("R7 LIVE-TABLE: no `archived` spans could be parsed out of the working tree's "
                   "front-matter table -- the routing information a session reads is gone")
        return out
    for (lo1, hi1), (lo2, hi2) in zip(lspans, lspans[1:]):
        if lo2 <= hi1:
            out.append("R7 LIVE-OVERLAP: the table on disk covers %d-%d and %d-%d -- a session in "
                       "the overlap has two homes" % (lo1, hi1, lo2, hi2))
        elif lo2 != hi1 + 1:
            out.append("R7 LIVE-GAP: the table on disk ends a span at %d and starts the next at "
                       "%d -- Sessions %d-%d are routed to no file at all"
                       % (hi1, lo2, hi1 + 1, lo2 - 1))
    newest_archived = max(hi for _lo, hi in lspans)
    live_ids = ids(live_wt)
    if not live_ids:
        out.append("R7 FRONTIER: the working tree's %s holds no records -- the frontier is "
                   "undefined" % LIVE)
        return out
    try:
        oldest_live = int(live_ids[-1])
    except ValueError:
        out.append("R7 FRONTIER: the oldest record id in the working tree is %r, which is not an "
                   "integer -- the frontier cannot be compared" % (live_ids[-1],))
        return out
    if oldest_live != newest_archived + 1:
        out.append("R7 FRONTIER: the table on disk archives up to Session %d, so this file should "
                   "begin at %d; its oldest record is Session %d. A trim that archived records "
                   "without adding its row -- or added a row without archiving -- lands here."
                   % (newest_archived, newest_archived + 1, oldest_live))
    return out


def R8(live_front):
    """COLLAPSE-ON-WRITE, ENFORCED. Read from the WORKING TREE so it binds later trims, not just
    this commit. C7 had to derive the count inside the `**The N blocks below**` family because that
    family survived its collapse; this collapse removes the family, so the invariant is that it is
    EMPTY -- stronger, cheaper, and it is section 11's Option E criterion mechanised. If the ninth
    trim writes a prose pointer block instead of a table row, this goes RED."""
    if live_front is MISSING:
        return ["R8 THE RULE: %s is not on disk" % LIVE]
    out = []
    for m in BLOCK_HEAD.finditer(live_front):
        out.append("R8 THE RULE: a prose pointer block is standing in the front matter -- %r. "
                   "Collapse-on-write says a trim writes a table ROW; put this trim's figures in "
                   "the table and its rationale in that session's record."
                   % live_front[m.start():m.start() + 58])
    for m in BLOCKS_BELOW.finditer(live_front):
        out.append("R8 THE RULE: a positional block-count claim is standing in the front matter -- "
                   "%r. This family went stale at every cut for eight trims; the collapse removed "
                   "it and it must not come back."
                   % live_front[m.start():m.start() + 58])
    return out


def check(before, after, live_wt, rows, old_prose, new_block, pre_live, world,
          declared_lines=DECLARED_OLD_LINES):
    bf, br = zones(before)
    af, ar = zones(after)
    lf = zones(live_wt)[0] if live_wt is not MISSING else MISSING
    fails = []
    fails += R0(pre_live, old_prose, declared_lines, new_block)
    fails += R1(bf, af, old_prose, new_block)
    fails += R2(br, ar)
    fails += R3(rows, world, new_block)
    fails += R4(rows, world)
    fails += R5(rows, world)
    fails += R6(live_wt, old_prose, new_block)
    fails += R7(rows, live_wt)
    fails += R8(lf)
    return fails


# =====================================================================================
def artifacts():
    sha = addcommit(SELF)
    if sha:
        before, after = blob("%s^:%s" % (sha, LIVE)), blob("%s:%s" % (sha, LIVE))
        parent = subprocess.run(["git", "rev-parse", "%s^" % sha], capture_output=True,
                                text=True, cwd=ROOT).stdout.strip()
        src = "the collapse commit %s (parent %s)" % (sha[:7], parent[:7])
        note = None if parent[:len(PRE)] == PRE else (
            "DECLARATION: the collapse commit's parent is %s; PRE declares %s" % (parent[:7], PRE))
    else:
        before, after = blob("HEAD:%s" % LIVE), worktree(LIVE)
        head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, cwd=ROOT).stdout.strip()
        src = "HEAD %s vs the working tree (collapse not yet committed)" % head[:7]
        note = None if head[:len(PRE)] == PRE else (
            "DECLARATION: HEAD is %s; PRE declares %s" % (head[:7], PRE))
    return before, after, worktree(LIVE), blob("%s:%s" % (PRE, LIVE)), src, note


def self_test(before, after, live_wt, pre_live, world):
    bf, _br = zones(before)
    af, ar = zones(after)
    W = lambda f: {k: (dict(v) | f(k, dict(v))) for k, v in world.items()}

    def R(i, field, value):
        """ROWS with one field of one row replaced -- the declaration mutated, never the artifact."""
        r = list(ROWS[i]); r[field] = value
        return ROWS[:i] + (tuple(r),) + ROWS[i + 1:]

    def with_block(nb):
        """A CONSISTENT world in which the new block really is `nb`: `after` rebuilt from `before`,
        and the working tree taken to be that same `after`. Without this every table mutant trips
        R1 CONFINEMENT and R6 and proves nothing about the arm it was written for."""
        a = declared_front(bf, OLD_PROSE, nb) + "".join(_br)
        return a, a

    def live_only(fn):
        """Mutate ONLY the working tree. R0-R5 never see it, so whatever fires is R6, R7 or R8."""
        return live_wt if live_wt is MISSING else fn(live_wt)

    def oldest_record_renamed(t):
        """R7/FRONTIER's mutation: move the OLDEST record id in the working tree. Located by
        `rfind` rather than by regex -- the last heading in the file is the oldest one, and a
        lookahead over a 200 KB body is both slow and easy to get subtly wrong."""
        if t is MISSING:
            return t
        i = t.rfind("### What Session ")
        j = t.find(" Did", i)
        assert i != -1 and j != -1, "self-test fixture: no record heading found in the working tree"
        return t[:i] + "### What Session 299" + t[j:]

    # --- fixture integrity, the C-series idiom: these can only fire in a run where the assertion
    # --- they support is already failing, which is what makes them a backstop and not a predicate.
    NEW_HEAD = NEW_BLOCK.split("\n")[0]
    if live_wt is not MISSING:
        assert live_wt.count(NEW_HEAD) == 1, \
            "self-test fixture: the new block's opening line is not present exactly once on disk"
        for _r in rows_of(NEW_BLOCK):
            assert live_wt.count(_r) == 1, \
                "self-test fixture: table row absent or duplicated on disk: %s" % _r[:70]

    FAKE_ROW = ("| 9 | S999 `deadbee` | 999 → 998 | 7 | 1,234 | "
                "`SESSION_NOTES-S999-through-S998.md` | 1,300 | 999 → 997 | L99 |\n")
    b_extra, l_extra = with_block(NEW_BLOCK.replace("| 8 | S245", FAKE_ROW + "| 8 | S245", 1))
    b_lines, l_lines = with_block(NEW_BLOCK.replace("the 276 lines", "the 999 lines", 1))
    b_pre,   l_pre   = with_block(NEW_BLOCK.replace("`8c9bb35`", "`deadbee`", 1))
    b_eight, l_eight = with_block(NEW_BLOCK.replace("What these eight trims found",
                                                    "What these 8 trims found", 1))
    b_five,  l_five  = with_block(NEW_BLOCK.replace(
        "Five of those blocks became the table below at Session 246",
        "Six of those blocks became the table below at Session 246", 1))
    b_rows,  l_rows  = with_block(NEW_BLOCK.replace("are rows 6, 7 and 8 of it now",
                                                    "are rows 6, 7 and 9 of it now", 1))
    b_ord,   l_ord   = with_block(NEW_BLOCK.replace("the sixth, seventh and eighth trims'",
                                                    "the fifth, seventh and eighth trims'", 1))
    first_row = row_line(*ROWS[0])
    assert first_row in NEW_BLOCK, "self-test fixture missing: composed row 1 absent from the block"
    b_typo, l_typo = with_block(NEW_BLOCK.replace(first_row,
                                                  first_row.replace("24,564", "24,563"), 1))

    # --- R7-isolating fixtures. Each moves the DECLARATION, the TABLE and the SHARD's own record
    # --- ids in step, so R3/ROW, R3/SIZE and R4/SPAN all still hold and only R7 can object.
    def isolate(idx, new_span, old_head, new_head):
        rows_m = R(idx, 3, new_span)
        nb = NEW_BLOCK.replace(row_line(*ROWS[idx]), row_line(*rows_m[idx]), 1)
        assert nb != NEW_BLOCK, "self-test fixture: row %d not found in the block" % (idx + 1)
        a, lw = with_block(nb)
        shard = ROWS[idx][6]
        wd = W(lambda k, v: {"shard": v["shard"].replace(old_head, new_head, 1)
                             if k == shard else v["shard"]})
        assert wd[shard]["shard"] != world[shard]["shard"], \
            "self-test fixture: %r not found in %s" % (old_head, shard)
        return rows_m, a, lw, nb, wd

    ov_rows, ov_after, ov_live, ov_block, ov_world = isolate(
        3, ("227", "224"), "### What Session 225 Did", "### What Session 224 Did")
    gp_rows, gp_after, gp_live, gp_block, gp_world = isolate(
        2, ("224", "222"), "### What Session 221 Did", "### What Session 222 Did")

    # --- R7 LIVE-arm fixtures. An ADDED row is invisible to R6 (which checks only NEW_BLOCK's own
    # --- rows) and to R3/SET (which reads the frozen literal), so it isolates the live arms. This
    # --- is also the shape of the hole an adversarial review found: a bogus row naming a shard that
    # --- does not exist is caught by NOTHING except these arms.
    def live_plus_row(span, retitle_oldest=None):
        if live_wt is MISSING:
            return live_wt
        last = rows_of(NEW_BLOCK)[-1]
        assert live_wt.count(last) == 1, "self-test fixture: last table row not unique on disk"
        bogus = ("| 9 | S258 `deadbee` | %s \u2192 %s | 8 | 1,500 | "
                 "`SESSION_NOTES-S999-through-S998.md` | 1,560 | 258 \u2192 250 | L15 |"
                 % (span[0], span[1]))
        out = live_wt.replace(last, last + "\n" + bogus, 1)
        if retitle_oldest is not None:
            i = out.rfind("### What Session ")
            j = out.find(" Did", i)
            out = out[:i] + "### What Session %s" % retitle_oldest + out[j:]
        return out

    a_rec = ar[0]

    mutants = [
        # ---------------- R0 ----------------
        ("M1  the embedded copy of the replaced prose altered by one character",
         before, after, live_wt, ROWS, OLD_PROSE.replace("Eighth trim", "E1ghth trim", 1),
         NEW_BLOCK, pre_live, world),
        ("M2  the declared replaced-line count is wrong (R0/SIZE, and R0/FIGURE with it)",
         before, after, live_wt, ROWS, OLD_PROSE, NEW_BLOCK, pre_live, world,
         {"declared_lines": 275}),
        ("M3  the new block misstates the replaced-line count it prints (R0/FIGURE)",
         before, b_lines, l_lines, ROWS, OLD_PROSE,
         NEW_BLOCK.replace("the 276 lines", "the 999 lines", 1), pre_live, world),
        ("M4  the new block misstates the pinned pre-collapse commit (R0/FIGURE)",
         before, b_pre, l_pre, ROWS, OLD_PROSE,
         NEW_BLOCK.replace("`8c9bb35`", "`deadbee`", 1), pre_live, world),
        ("M5  the pre-collapse commit does not hold the replaced prose (R0/PIN)",
         before, after, live_wt, ROWS, OLD_PROSE, NEW_BLOCK,
         pre_live.replace(OLD_PROSE, "GONE\n", 1) if pre_live else pre_live, world),

        # ---------------- R1 ----------------
        # --- added because the arm sweep found R0's early return reachable by nothing: M5 mutates
        # --- the CONTENT at PRE, which is a different failure from PRE not holding the file at all.
        ("M48 the declared pre-collapse commit does not hold %s at all (R0/PIN early return)" % LIVE,
         before, after, live_wt, ROWS, OLD_PROSE, NEW_BLOCK, None, world),
        ("M6  an UNDECLARED extra front-matter edit alongside the declared replacement",
         before, after.replace("`grep` the shards; `Read` none",
                               "`grep` the shards; `Read` nothing", 1), live_wt, ROWS,
         OLD_PROSE, NEW_BLOCK, pre_live, world),
        ("M7  the replaced prose occurs twice in `before` (R1/ANCHOR)",
         before.replace(OLD_PROSE, OLD_PROSE + OLD_PROSE, 1),
         after, live_wt, ROWS, OLD_PROSE, NEW_BLOCK, pre_live, world),
        ("M8  the new block never landed in `after` (R1/BLOCK MISSING + CONFINEMENT)",
         before, after.replace(NEW_BLOCK, "", 1), live_wt, ROWS, OLD_PROSE, NEW_BLOCK,
         pre_live, world),

        # ---------------- R2 ----------------
        ("M9  a record EDITED by the collapse commit",
         before, after.replace(a_rec, a_rec.replace("Deliverable", "Deliverab1e", 1), 1),
         live_wt, ROWS, OLD_PROSE, NEW_BLOCK, pre_live, world),
        ("M10 a record ADDED by the collapse commit (the two-commits rule broken)",
         before, after + "\n### What Session 255 Did\n**Deliverable:** smuggled in.\n",
         live_wt, ROWS, OLD_PROSE, NEW_BLOCK, pre_live, world),
        ("M11 the records zone REORDERED, same bytes and same count (R2/RECORD ORDER)",
         before, af + "".join([ar[1], ar[0]] + list(ar[2:])), live_wt, ROWS, OLD_PROSE,
         NEW_BLOCK, pre_live, world),

        # ---------------- R3 ----------------
        ("M12 a declared record-heading count differs from the shard (R3/SIZE)",
         before, after, live_wt, R(1, 4, 6), OLD_PROSE, NEW_BLOCK, pre_live, world),
        ("M13 a declared archived-line count differs from the shard (R3/SIZE)",
         before, after, live_wt, R(5, 5, 1003), OLD_PROSE, NEW_BLOCK, pre_live, world),
        ("M14 a declared shard total differs from the shard (R3/SIZE)",
         before, after, live_wt, R(6, 7, 645), OLD_PROSE, NEW_BLOCK, pre_live, world),
        ("M15 a declared ordinal is out of sequence (R3/ORDINAL)",
         before, after, live_wt, R(2, 0, 9), OLD_PROSE, NEW_BLOCK, pre_live, world),
        ("M16 a trim is credited to the wrong session (R3/SESSION)",
         before, after, live_wt, R(7, 1, "244"), OLD_PROSE, NEW_BLOCK, pre_live, world),
        ("M17 the table carries a row no declared trim composes (R3/SET)",
         before, b_extra, l_extra, ROWS, OLD_PROSE,
         NEW_BLOCK.replace("| 8 | S245", FAKE_ROW + "| 8 | S245", 1), pre_live, world),
        ("M18 one figure inside a table row typo'd, declaration untouched (R3/ROW)",
         before, b_typo, l_typo, ROWS, OLD_PROSE,
         NEW_BLOCK.replace(first_row, first_row.replace("24,564", "24,563"), 1), pre_live, world),
        ("M19 the block stops spelling its own row count (R3/FIGURE)",
         before, b_eight, l_eight, ROWS, OLD_PROSE,
         NEW_BLOCK.replace("What these eight trims found", "What these 8 trims found", 1),
         pre_live, world),
        ("M20 the block misstates how many blocks the FIRST collapse took (R3/FIGURE)",
         before, b_five, l_five, ROWS, OLD_PROSE,
         NEW_BLOCK.replace("Five of those blocks became the table below at Session 246",
                           "Six of those blocks became the table below at Session 246", 1),
         pre_live, world),
        ("M21 the block misstates which ordinals THIS collapse added (R3/FIGURE)",
         before, b_rows, l_rows, ROWS, OLD_PROSE,
         NEW_BLOCK.replace("are rows 6, 7 and 8 of it now", "are rows 6, 7 and 9 of it now", 1),
         pre_live, world),
        ("M22 the block misstates WHICH trims those were (R3/FIGURE, ordinal words)",
         before, b_ord, l_ord, ROWS, OLD_PROSE,
         NEW_BLOCK.replace("the sixth, seventh and eighth trims'",
                           "the fifth, seventh and eighth trims'", 1), pre_live, world),
        ("M23 a shard is unreadable at its own add-commit (R3/unreadable)",
         before, after, live_wt, ROWS, OLD_PROSE, NEW_BLOCK, pre_live,
         W(lambda k, v: {"shard": None if k == ROWS[6][6] else v["shard"]})),
        ("M24 a shard has no record headings at its add-commit (R3/grammar)",
         before, after, live_wt, ROWS, OLD_PROSE, NEW_BLOCK, pre_live,
         W(lambda k, v: {"shard": "no headings here at all\n" if k == ROWS[5][6]
                         else v["shard"]})),

        # ---------------- R4 ----------------
        ("M25 a declared trim sha is not the commit that added the shard (R4/PROVENANCE)",
         before, after, live_wt, R(7, 2, "deadbee"), OLD_PROSE, NEW_BLOCK, pre_live, world),
        ("M26 a declared archived span is not what the shard holds (R4/SPAN)",
         before, after, live_wt, R(6, 3, ("238", "235")), OLD_PROSE, NEW_BLOCK, pre_live, world),
        ("M27 the live file's OLDEST retained id differs at a trim commit (R4/LEFT-LIVE alone)",
         before, after, live_wt, ROWS, OLD_PROSE, NEW_BLOCK, pre_live,
         W(lambda k, v: {"live": v["live"].replace("### What Session 217 Did",
                                                   "### What Session 117 Did", 1)
                         if k == ROWS[0][6] else v["live"]})),
        ("M28 the shard the table sends readers to is gone from disk (R4/GONE)",
         before, after, live_wt, ROWS, OLD_PROSE, NEW_BLOCK, pre_live,
         W(lambda k, v: {"shard_disk": MISSING if k == ROWS[7][6] else v["shard_disk"]})),
        ("M29 a shard's PROOF is gone from disk (R4/GONE)",
         before, after, live_wt, ROWS, OLD_PROSE, NEW_BLOCK, pre_live,
         W(lambda k, v: {"proof_disk": MISSING if k == ROWS[4][6] else v["proof_disk"]})),
        ("M30 SESSION_NOTES.md unreadable at a trim commit (R4/LEFT-LIVE unreadable)",
         before, after, live_wt, ROWS, OLD_PROSE, NEW_BLOCK, pre_live,
         W(lambda k, v: {"live": None if k == ROWS[3][6] else v["live"]})),

        # ---------------- R5 ----------------
        ("M31 a trim is credited with assertions its proof does not add (R5/ASSERTIONS)",
         before, after, live_wt, R(5, 9, ("L12", "L13")), OLD_PROSE, NEW_BLOCK, pre_live, world),
        ("M32 a trim's proof is unreadable at its add-commit (R5/unreadable)",
         before, after, live_wt, ROWS, OLD_PROSE, NEW_BLOCK, pre_live,
         W(lambda k, v: {"proof": None if k == ROWS[7][6] else v["proof"]})),
        ("M33 a trim's proof defines no `def L<N>(` (R5/grammar)",
         before, after, live_wt, ROWS, OLD_PROSE, NEW_BLOCK, pre_live,
         W(lambda k, v: {"proof": "def nothing():\n    pass\n" if k == ROWS[6][6]
                         else v["proof"]})),

        # ---------------- R6 ----------------
        ("M34 one table ROW reverted on disk while the commit keeps it (R6 per-row)",
         before, after, live_only(lambda t: t.replace("| 6 | S239", "| 6 | S249", 1)),
         ROWS, OLD_PROSE, NEW_BLOCK, pre_live, world),
        ("M35 the new block's opening line removed from disk (R6 opening line)",
         before, after, live_only(lambda t: t.replace(NEW_HEAD, "", 1)),
         ROWS, OLD_PROSE, NEW_BLOCK, pre_live, world),
        ("M36 the replaced prose is STILL on disk -- collapse declared, not applied (R6)",
         before, after, live_only(lambda t: t.replace(NEW_HEAD, OLD_PROSE + NEW_HEAD, 1)),
         ROWS, OLD_PROSE, NEW_BLOCK, pre_live, world),
        ("M37 the C-series' OLD opening line is still on disk (R6/SUBSTITUTED -- the NEW arm)",
         before, after, live_only(lambda t: t.replace(NEW_HEAD, C_SERIES_OLD_HEAD + "\n" + NEW_HEAD, 1)),
         ROWS, OLD_PROSE, NEW_BLOCK, pre_live, world),
        ("M38 SESSION_NOTES.md is not on disk at all (R6, R7 and R8 degrade, none crashes)",
         before, after, MISSING, ROWS, OLD_PROSE, NEW_BLOCK, pre_live, world),

        # ---------------- R7 -- NEW IN THIS LINEAGE ----------------
        ("M39 two archived spans OVERLAP -- a session with two homes (R7/OVERLAP)",
         before, after, live_wt, R(3, 3, ("227", "224")), OLD_PROSE, NEW_BLOCK, pre_live, world),
        ("M40 the archived spans leave a GAP -- sessions routed nowhere (R7/GAP)",
         before, after, live_wt, R(2, 3, ("224", "222")), OLD_PROSE, NEW_BLOCK, pre_live, world),
        ("M41 an archived span runs BACKWARDS (R7/SPAN)",
         before, after, live_wt, R(4, 3, ("228", "231")), OLD_PROSE, NEW_BLOCK, pre_live, world),
        ("M42 an archived span is not a pair of integers (R7/SPAN grammar guard)",
         before, after, live_wt, R(1, 3, ("220", "two-seventeen")), OLD_PROSE, NEW_BLOCK,
         pre_live, world),
        ("M43 the FRONTIER breaks: the table's newest archived and the file's oldest record "
         "disagree (R7/FRONTIER -- the arm that reads the working tree)",
         before, after, oldest_record_renamed(live_wt),
         ROWS, OLD_PROSE, NEW_BLOCK, pre_live, world),

        # ---------------- R8 -- NEW IN THIS LINEAGE ----------------
        # --- R7's LIVE arms. M43 already isolates LIVE-FRONTIER (it moves the oldest record id and
        # --- leaves the table alone). These two isolate LIVE-OVERLAP and LIVE-GAP.
        ("M49 a row added to the table ON DISK whose span OVERLAPS an existing one "
         "(R7/LIVE-OVERLAP alone -- an added row is invisible to R6 and to R3/SET)",
         before, after, live_plus_row(("241", "236")), ROWS, OLD_PROSE, NEW_BLOCK, pre_live, world),
        ("M50 a row added ON DISK leaving a GAP, with the frontier moved to match so R7/LIVE-GAP "
         "is the sole objector",
         before, after, live_plus_row(("250", "244"), retitle_oldest="251"),
         ROWS, OLD_PROSE, NEW_BLOCK, pre_live, world),
        ("M44 a PROSE POINTER BLOCK planted in the live front matter (R8 -- the rule broken by a "
         "future trim)",
         before, after,
         live_only(lambda t: t.replace(NEW_HEAD,
                                       "**Ninth trim (Session 258). Archived Sessions 250 → 247.**\n\n"
                                       + NEW_HEAD, 1)),
         ROWS, OLD_PROSE, NEW_BLOCK, pre_live, world),
        # --- R7's tiling arms fire only in COMPANY under M39-M42: mutating a declared span also
        # --- changes the row R3 composes and the span R4 measures. These two isolate them, by
        # --- mutating the declaration, the TABLE and the SHARD together so that R3 and R4 are
        # --- satisfied and R7 is the sole objector. Without them the sweep reports the arms as
        # --- unreachable-alone, which is how Session 224 and Session 228 each shipped an arm no
        # --- mutant could reach.
        ("M46 two spans OVERLAP with the table and the shard made to agree -- R7/OVERLAP ALONE",
         before, ov_after, ov_live, ov_rows, OLD_PROSE, ov_block, pre_live, ov_world),
        ("M47 the spans leave a GAP with the table and the shard made to agree -- R7/GAP ALONE",
         before, gp_after, gp_live, gp_rows, OLD_PROSE, gp_block, pre_live, gp_world),
        ("M45 a positional `**The N blocks below are frozen**` claim planted live (R8)",
         before, after,
         live_only(lambda t: t.replace(NEW_HEAD,
                                       "**The three blocks below are frozen at nothing at all.**\n\n"
                                       + NEW_HEAD, 1)),
         ROWS, OLD_PROSE, NEW_BLOCK, pre_live, world),
    ]
    mutants = [m if len(m) == 10 else m + ({},) for m in mutants]
    # The NO-OP guard (Session 253's repair, inherited deliberately). A `str.replace` whose needle
    # has drifted out of its haystack is SILENT: check() is then handed pristine arguments and
    # reports, accurately and uselessly, that nothing is wrong with them. "SURVIVED" names the wrong
    # culprit for that -- it says the assertion missed a corruption when the corruption never
    # happened. A mutant whose arguments equal the pristine ones is a broken FIXTURE, and is
    # reported as one. Session 252 needed a bisect to learn that difference.
    pristine = (before, after, live_wt, ROWS, OLD_PROSE, NEW_BLOCK, pre_live, world, {})
    bad, inert = [], []
    for name, b, a, lw, rows, op, nb, pl, wd, opt in mutants:
        if (b, a, lw, rows, op, nb, pl, wd, opt) == pristine:
            inert.append(name)
            print("  NO-OP     %s" % name)
            continue
        fails = check(b, a, lw, rows, op, nb, pl, wd, **opt)
        if not fails:
            bad.append(name)
            print("  SURVIVED  %s" % name)
        else:
            codes = sorted({f.split(":")[0].split(" (")[0] for f in fails})
            print("  caught    %-78s -> %s" % (name[:78], ", ".join(codes)))
    if inert:
        print("\nSELF-TEST FAILED: %d mutant(s) MUTATED NOTHING. Their arguments are byte-identical\n"
              "to the pristine ones, so what they report is not `the assertion missed it` but `the\n"
              "corruption never happened`. Repair the MUTATION, never the assertion:" % len(inert))
        for n in inert:
            print("    %s" % n)
    if bad:
        print("\nSELF-TEST FAILED: %d mutant(s) survived. This proof cannot be trusted." % len(bad))
    if inert or bad:
        sys.exit(2)
    print("\nSELF-TEST OK: all %d mutants caught, and every one of them changed its input."
          % len(mutants))


before, after, live_wt, pre_live, source, note = artifacts()
if before is None or after is None:
    sys.exit("cannot read %s from git" % LIVE)
world = gather(ROWS)

if "--self-test" in sys.argv:
    print("--self-test: mutating the artifacts AND the declarations, asserting each is caught.\n")
    self_test(before, after, live_wt, pre_live, world)
    sys.exit(0)

fails = check(before, after, live_wt, ROWS, OLD_PROSE, NEW_BLOCK, pre_live, world)
_bf, br = zones(before)
_af, ar = zones(after)

print("source : %s" % source)
if note:
    print("WARNING: %s" % note)
print("scope  : a COLLAPSE, not a trim -- 0 records moved, 0 shards written, 0 sessions archived")
print("replaced: %d lines of front matter, embedded verbatim in this file and pinned to %s"
      % (DECLARED_OLD_LINES, PRE))
print("added  : a %d-line block; front matter %d -> %d lines (%d -> %d B)"
      % (NEW_BLOCK.count("\n"), _bf.count("\n"), _af.count("\n"),
         len(_bf.encode()), len(_af.encode())))
print("records: %d before, %d after; added by the collapse commit: %d"
      % (len(br), len(ar), max(0, len(ar) - len(br))))
print("rows   : %d trims, every figure measured from its shard at its own add-commit and the row\n"
      "         line COMPOSED from the measurements" % len(ROWS))
print("front  : ONE declared replacement, 0 declared substitutions -- no prose block survives this\n"
      "         collapse, so none could be falsified by it (R8 keeps that true)")
print("checked: R0, R1, R2, R3, R4, R5, R6, R7, R8  <- R6, R7 and R8 read the WORKING TREE; the\n"
      "         L-series reads prose only at its own trim commit")

if fails:
    print("\nFAIL:")
    for f in fails:
        print("  " + f)
    sys.exit(1)

print("\nOK: R0-R8 hold.")
print("    The %d lines this collapse replaced are still readable, byte-for-byte, at %s and in"
      % (DECLARED_OLD_LINES, PRE))
print("    this file; the front matter changed by exactly that one replacement and nothing else;")
print("    not one record was touched; every figure in the table was measured from the shard it")
print("    describes, at that shard's own add-commit, with the row's markdown line composed from")
print("    the measurement rather than compared to it; the archived spans tile the history with no")
print("    gap and no overlap and agree with the oldest record on disk; and NO prose pointer block")
print("    stands in the front matter -- which is collapse-on-write, asserted rather than promised.")
print("    It says NOTHING about whether collapsing was wise -- that was the operator's call --")
print("    nor whether the surviving prose is true. It does not re-prove the eight cuts nor Session")
print("    246's collapse: each has its own proof pinned to its own commit. Run those too.")
print("    A green proof that has never been --self-test'ed proves less than it appears to.")

PYEOF
