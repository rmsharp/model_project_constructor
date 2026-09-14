# Session Notes

**Purpose:** Continuity between sessions. Each session reads this first and writes to it before closing out.

**One trim, one row — and that is the rule now (Session 254, on the operator's ruling of
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

**Shards stay write-once.** A tenth trim writes a tenth file; it never appends to one of these.
That is also why every shard after the first is named as a range rather than in the first's
open-ended `-through-S216` form — `docs/methodology/PROJECT_CONVENTIONS.md` §3.1 carries the rule
and the reason.

**A shard banner is a snapshot of its own cut; this table is the authority.** Several banners still
route sessions to this live file that have since moved into a shard. Each was true when it was
written, none may be repaired, and no proof can notice: every shard proof reads its prose at its own
trim commit, so from the moment a trim lands its prose is checked by nothing until the next one.
That is this apparatus's largest hole, it is measured rather than suspected, and only three
mechanisms close any of it: the working-tree arms `R6`, `R7`, `R8` and `C6` below;
`tests/test_session_notes_census.py`, which holds the prose files outside this one against the
shards on every CI run; and `tests/test_read_budget.py`, which holds the read-budget sentences and
this file's front matter to their budgets.

**Two things are bequeathed to the tenth trim. They are instructions, not notes.**

1. **The `L`-numbering collision must not be re-opened.** A fourteenth assertion was drafted at the
   seventh trim and REJECTED on measurement; a *different* `L14` then shipped at the eighth. Both
   facts live in Sessions 242's and 245's records. A later trim must not resurrect the rejected one
   believing it is the live one. That hazard is also why the two collapse proofs are lettered `C`
   and `R`: neither is an `L`, and neither letter is an option letter in the review document.
2. **A sweep result is a deliverable** — publish it, and never repeat a sweep sentence unchanged.

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
| 9 | S256 `this commit` | 248 → 242 | 7 | 1,681 | `SESSION_NOTES-S248-through-S242.md` | 1,732 | 256 → 249 | none |

*`trim` is the session and the commit that added its shard — the newest row cannot name the
commit it is written in, so it says `this commit` until the next trim resolves it; `archived` is
the session span that left this file and `rec` how many record headings went with it; `lines`, the
lines they took; `shard`, that file's total; `left live`, what this file was left holding at that
cut; `added`, the assertions that trim contributed to the inherited set. Each shard's proof is its
own path with `.verify.sh` appended.*

**The proofs, and what each can see.** The first collapse is
[`SESSION_NOTES-pointer-collapse.verify.sh`](docs/architecture-history/SESSION_NOTES-pointer-collapse.verify.sh),
lettered `C`; this one is
[`SESSION_NOTES-pointer-collapse-S254.verify.sh`](docs/architecture-history/SESSION_NOTES-pointer-collapse-S254.verify.sh),
lettered `R`, and the 276 lines of front matter it replaced are embedded in it verbatim.
Neither is a shard proof and neither is an `L`. Both hold the records byte-identical across their
own commit — a collapse commit carries no record edit, the same rule `CLAUDE.md` sets for a trim —
and both COMPOSE the rows that stood at their own commit from figures measured at each shard's
add-commit instead of comparing against a typed one. A row a later trim adds is composed once, by
that trim's own `L12/row` at its trim commit; between trims only `R7` reads it, and only its span —
the rest of it is guarded by nothing, which `BACKLOG.md` files. `R7` proves the `archived` spans
tile the history with no gap and no overlap, which is what allows the routing clauses to be deleted
rather than kept in
parallel. `R6`, `R7`, `R8` and `C6`
are the only proof assertions that read this file from the WORKING TREE; every other proof reads
this file at a commit that has already passed. That is why the census guard exists for the prose
files outside this one, and the read-budget guard for this file's size and the budget sentences. **Run both modes over every proof in `docs/architecture-history/`** — a plain
run proves the world is intact and cannot see a proof that has stopped being able to fail;
`--self-test` proves the proof can fail and is blind to real corruption. `CLAUDE.md` carries the
loop and the reason neither half is sufficient.

**Cutting is by byte position, never by authorship.** This ledger files a handoff evaluation under
its author, so Session N's evaluation of N−1 sits inside N's record, and every cut so far has split
one from its subject. Expect that seam at every boundary. What these nine trims found, argued and
rejected stays in their own records and, for the blocks that stood here, at the commits above. What
they left BINDING is in `CLAUDE.md`'s `SESSION_NOTES.md`-is-trimmed bullets, which this collapse
updates rather than contradicts.

---

## ACTIVE TASK

### What Session 256 Did
**Deliverable:** **The ninth trim of `SESSION_NOTES.md` — COMPLETE.** Sessions 248 → 242 (seven
records, 1,681 lines, a pure byte slice) are in
[`docs/architecture-history/SESSION_NOTES-S248-through-S242.md`](docs/architecture-history/SESSION_NOTES-S248-through-S242.md)
(1,732 lines) beside its proof. The live file landed at 97,109 B and keeps six non-stub records; the
front-matter table gained row 9. The proof adds **no** assertion — `L15` was deferred on the
operator's ruling F — rewrites `L11` to the byte rule, and ships 108 mutants.

**Started / completed:** 2026-09-11 → 2026-09-14 (UTC). **Commits: five** — `bf776a9` (claim,
alone), `3a141ec` and `8e6bdca` (guard fixes the trim's next states needed, each green before and
after the trim), `9342637` (the trim, no record edit), and this close-out. **`CHANGELOG.md`
entry: YES** — `tests/` logic changed in two files (§2 is a directory test).

#### The cut, and why this one

The byte rule fired at 222,937 B. The canonical trimmer's `choose_cut` keeps the LARGEST newest
prefix under the stop, so the cut is the fewest records that land at or under 98,304 B: 248 → 242.
Keeping 248 as well would have landed at 117,506 B. A floor-only reading (archive down to four
non-stub records) would also have complied; the canonical semantics decided it.

#### `L15` was not built — the operator ruled

Session 254 bequeathed `L15` (a file census of a trim's own sweep) as an instruction, and Session
255 repeated it. Ruling F (budgets review §13.1) had already ended the assertion-per-trim convention,
and §8 row F says of `L15` "F is the decision not to build it". A mapping agent found the conflict
and I put it to the operator: **follow ruling F; do not build `L15`; record its deferral as a
decision.** Recorded in `CLAUDE.md`'s trim bullets with F's other half — no assertion is owed per
trim, and the CI `--self-test` step is the substitute the ruling named — and in review §15.

**The sweep, as a dated fact** (what the bequest wanted, published rather than asserted): at the
trim commit `9342637`, `git grep -l 'SESSION_NOTES-[A-Za-z0-9-]*\.md'` returns **29** files — the
nine shards and their nine proofs, both collapse proofs, the four prose files, this ledger,
`PROJECT_LEARNINGS.md`, two planning documents and the census guard — and the broad
`SESSION_NOTES-` form **32**; the broad form's extra three are `.github/workflows/ci.yml`,
`CHANGELOG.md` and `docs/architecture-history/evolution-page-plan.md`. Every live shard-set
statement in `CLAUDE.md`, `README.md`, `BACKLOG.md` and `PROJECT_CONVENTIONS.md` was updated.
Left, with reason: `ci.yml`'s "any of the eight shards" (Session 253's dated measurement), the
budgets review's dated figures, and the frozen banners.

#### Five defects fixed before the trim could land — the #241 class, every one

Each was found by modelling a state the trim creates, reproduced red first, and fixed alone:

1. **`M04` (read-budget guard, `3a141ec`)** — one ~22 KB line shrank a trimmed ledger's page into
   the K prefix; red at this trim's own close-out for every compliant cut. New state:
   `after-a-trim-then-its-close-out`. Session 255's sweep had called this cycle green.
2. **`M50` (R-series, `3a141ec`)** — a hard-coded gap span that row 9 turned into an overlap, leaving
   `R7 LIVE-GAP` reached by no mutant. It now derives its span from the newest live row.
3. **`M01` and `M08` (`8e6bdca`)** — fixed-width padding and a truncated tail moved the page near a
   wide close-out. New state: `after-a-wide-close-out-then-claim`, red before, green after.
4. **`M04` again (`8e6bdca`)** — clear of `check_satisfiable` by 226 B that nothing asserted; its
   overshoot is now given back from the next record.
5. **Six census mutants (`8e6bdca`)** — re-anchored by hand for this trim, so the tenth would redo it;
   they now derive their anchors from the shard set.

#### The proof: re-targets, strengthenings, two new arms — and still no new assertion

Every inherited operand that read retired prose was found by running the S241 proof's declarations
against the working tree (23 of 101 flagged) and re-targeted: `L2` holds a row insertion; `L5`'s
third copy is the table; `L12/row` composes row 9 cell by cell; the census sentences moved into the
banner `L6` pins; `L12/cap` holds the 262,144 B refusal ceiling; `L14` took the eighth shard's
figures. `L11`'s floor counts non-stub records with a frozen copy of the guard's classifier (`M58`,
floor 7, proves it load-bearing). On the review's evidence four inherited arms now match only on
digit or word boundaries and both census arms parse by position; `L2/position` and an `L12/row`
unreadable-proof arm are new. Row 9's trim cell says `this commit` — no commit can contain its own
hash — and the legend says the next trim resolves it.

#### The review gated the commit

Twelve agents: six lenses (the cut, re-target fidelity, attack, next states, prose, the guards),
each followed by a verifier trying to refute it. **38 findings; 35 confirmed, 1 refuted, 2 partly.**
Fixed before the trim commit: both false "every row / one owner" claims; the position hole; the
substring matches; the unfilled coverage token; `M01`/`M08`/`M04` (above); every underived figure I
had introduced (a shard named for Sessions 242/245, "for Sessions 242 and up", "the eight ancestor
shards", a stale token count); F's substitute misnamed; two stale BACKLOG counts. **Filed, not
fixed:** row 9 is guarded by nothing between trims — only its span is read. A reviewer rewrote most
of its cells on disk and every proof and guard stayed green. The BACKLOG item "front matter is
guarded only at its table rows" now carries that evidence and the tested design; it is a guard
change, not a trim. **Declined:** a claim-first successor model (its verifier showed it regresses at
a 25 KB close-out) and `ci.yml`'s dated comment.

#### Verification

- All eleven proofs green in both modes at `9342637`, the new one reading its artifacts from that
  commit with its write-once arm live; both guards 71/71; full suite 1,384 passed + 9 live-skipped;
  `ruff` and `uv run mypy` clean.
- The sweep, against frozen artifacts: every assertion but the overlapped L0, L1, L3 and L4 has sole
  catchers; 48 of 68 arms uniquely catch a mutant, and the 20 that do not are grouped by cause in
  the proof's header. A first sweep found three L2 arms reachable only in company; M98–M100 isolate
  them.
- Next states, in a clone: the trim commit, then Session 256 close-outs of 8 and 16 KB each followed
  by Session 257's claim and close-out — all green. At 24 and 30 KB the guard's reds are genuine:
  the modelled next close-out breaches the page (56,995 B against 52,912). This record is sized for it.
- Probe: the shard is 48,717 tokens by an explicit `offset`/`limit` `Read`, so a default `Read`
  returns an announced partial view, as its banner says. After this record landed (#214; measured
  before this sentence was added), a default `Read` of this file showed `lines 1-744 of 1435 total
  (40939 tokens, cap 25000)`: the front matter and Sessions 256, 255 and 254 whole, 253 cut. K=2
  holds with a record to spare.

### Session 255 Handoff Evaluation (by Session 256)

**Score: 6/10.** **+** What's-next #1 was exact and every clause was load-bearing: a row not a block,
row and archive together, rewrite `L11`, re-target the retired operands, ≥4 non-stub, ≤98,304 B,
both guards, both modes. Its gotchas all applied, and the byte rule it built made the cut a
computation rather than a debate. **−** "Build `L15`" contradicted an operator ruling the handoff did
not mention; only a history agent caught it. **−** Its own guard had no green state after this
trim's close-out: the "30-state sweep … the ninth trim and its cycle" was red for every compliant
cut — the #241 class again, in the session whose learnings name it. **−** Its list of retired
operands missed two and named one false positive. **ROI: high** — the defects were in its code, not
its instructions.

### Session 256 Self-Assessment

**Score: 7/10.**
**+ Mapped before editing.** Eight analysts, two of them in throwaway clones, found the `M04`, `M50`
and `L15` problems before a line was written; each guard fix reproduced its failure red first.
**+ Asked the one question that was the operator's** (`L15` against ruling F) and nothing else.
**+ The review gated the commit**, and every major finding was fixed or filed with its evidence.
**− My first proof draft carried defects a review had to find** — the position hole, substring
matches, an unfilled token, a false "one owner" sentence left standing, and underived figures I
wrote myself. **− The #241 class recurred in code I had just edited** (`M01`/`M08`, one commit after
`3a141ec`) and I did not find it — the review did. **− Five commits and a ~2,000-line proof for a
trim**; the row-9 guard is left for a later session. **− Cost:** ~4M subagent tokens over two
workflows, plus two sweeps.

**What's next.**
1. **The row-9 guard** — BACKLOG "The ledger's front matter is guarded only at its table rows":
   compose every row's cells except the hash from the disk and require them in the table. Operator
   call per that item; ruling F already names the CI guard as its home.
2. **The two refused files** (`PROJECT_LEARNINGS.md`, `CHANGELOG.md`) — operator calls.
3. **The tenth trim**, when the file next exceeds 196,608 B: resolve row 9's `this commit` to its
   hash as a declared substitution and verify it; copy `L0`–`L14` from the ninth proof; both carried
   bequests apply. `L15` has now named two different unbuilt checks — resurrect neither by name.
4. **Carried:** the dashboard sync (outside this repo); `README.md`'s hand-typed test counts; pushing
   (six commits ahead of `origin`) is the operator's call.

**Key files.** The new proof (its header first); `tests/test_read_budget.py` (`M01`, `M04`, `M08`
and the two new next-state models); `tests/test_session_notes_census.py` (derived anchors); the
BACKLOG item named in #1.

**Gotchas.**
1. The new proof is write-once — its figures are assembled from the artifacts; never hand-edit it.
2. Row 9's `this commit` is by design; the tenth trim resolves it and should verify the hash.
3. Between trims only `R7` reads row 9, and only its span (what's-next #1).
4. A figure near "shard" in the four prose files trips the census scan; a figure that happens to
   equal an ancestor's trips `L14/complete` at a trim (a 721 B size did). Reword; never allowlist.
5. A Session 256-sized close-out of 24 KB or more already makes the guard predict that the NEXT
   close-out cannot fit — measured. Keep close-outs near the median (~15 KB).
6. `uv run pytest tests/test_read_budget.py --no-cov` before every close-out; `command grep`; the two
   refused files; `uv run mypy` with no path.

### What Session 255 Did
**Deliverable:** **Option D, widened — COMPLETE.** The four mandated-read files have byte budgets,
held against the working tree on every CI run by `tests/test_read_budget.py`; the line rule
(1,500 / 1,050 / 4) is retired. Ruling recorded in `docs/methodology/PROJECT_CONVENTIONS.md` §5;
rule in `CLAUDE.md`'s retention bullet; premises corrected in `docs/planning/ledger-budgets-review.md`
§14. No trim; no record moved.

**Started / completed:** 2026-09-10 (UTC). **Commits:** `85865d5` (claim, alone), `e768e1f` (guard,
rule and prose), `078ee60` (BACKLOG items, CHANGELOG, review §14), and this close-out.
**`CHANGELOG.md` entry: YES** — `tests/` logic (PROJECT_CONVENTIONS §2).

#### The ruling was measured before it was asked

§13.1 ruled D at K=3, "reachable once E lands". Measured first, with default-`Read` probes: one
`Read` of this file delivered the front matter and **two** complete records, and K=3 had fit at a
minority of the 41 commits since Session 239 (K=2 at all 41). Every K figure in circulation —
§13.4's 4, Session 254's 5 — had counted claim stubs. The operator was asked three questions and
chose all three recommendations (2026-09-10): **K=2 with a byte trim trigger** (fire above
196,608 B, cut to ≤98,304 B, keep ≥4 non-stub records); for the two files refused outright,
**declare, guard, file**; for `BACKLOG.md`, **its index arrives whole**.

**I put three wrong figures into that question.** I summarised a 41-row table by eye as "44", and
both K=3 counts were off. A script caught it before any file carried them; the conclusion held.
Learning #246.

#### What the probes found (review §14.3, against the premises they falsify)

- **The page is sized by the whole file.** Past the cap one `Read` delivers
  `floor(0.85 × 25,000 × L / T)` lines. Twenty long lines appended at the bottom cut an identical
  head from 730 lines to 299.
- **A second regime:** 0.7 of that page when `T × bytes(page) / B` exceeds the cap — six of
  thirteen real probes; a sparse tail alone triggers it. Found by the first review, pinned by the
  second.
- **Refusal is strictly over 262,144 bytes**, and an explicit `offset`/`limit` `Read` over the cap
  meters even a refused file exactly (`CHANGELOG.md` 264,293 tokens, `PROJECT_LEARNINGS.md`
  104,523).
- **No tokenizer runs offline**, so §11's "probe script" cannot exist; the guard is a deliberately
  conservative byte proxy, worst case over the measured 2.49–2.9 B/token range.

#### The guard

Ten checks; eighteen mutants; a synthetic test proving the reduced-page branch load-bearing; unit
tests pinning the stub classifier and the fence rule against every historical shape; and a battery
that fails if any check is the sole catcher of none, re-run in the states the next close-out, the
next claim and the next trim produce. **Run it at every close-out.**

#### Two reviews gated the commit — and the second found my fixes' defects

**First** (11 agents): 45 findings, 36 survived refutation, plus 3 from a critic — the second
regime (G1); an empty heading and a trim session's off-template claim counted as records (G2, N1);
mutants vacuous in a plausible next state (F1–F8); a remedy wrong for the lines arm (P2); a
front-matter budget whose justification ignored stubs (10,240 → 8,192 B); a K=2 rationale that
misread `SESSION_RUNNER.md` (both mandated reads need ONE non-stub record; K=2 is margin, by
ruling).

**Second** (5 agents, verification only): **a blocker in my fixes** — no green state for this very
close-out, because two mutants had fixed geometry and the next-state test never modelled a close-out
at a claim commit; a classifier regression on two historical stubs (Sessions 193, 226); and a page
arm with no margin (a real `Read` cut K where the guard stayed green). Fixed with the reviewers'
validated patches, a paragraph-based classifier, a close-out successor, and M19 moved into a
state-independent test after my own sweep showed it unbuildable in small states. Learning #248.

#### Verification

- Gate: **1,382 passed + 9 live-skipped**; `ruff` and `uv run mypy` clean (68 files); ten proofs
  green in both modes; census guard 25/25; the read-budget guard 44/44.
- My 30-state sweep: green in every healthy state (close-outs 2–18 KiB, a wide table, claim →
  close-out → claim, growth to 258 KB, the ninth trim and its cycle). Its reds are real breaches: a
  19 KiB close-out leaves no room for the next claim; at Session 257's claim the next close-out
  would cross the ceiling.
- The page model never predicts more than a real `Read` delivered, on all ten recorded probes; its
  two disagreements are conservative. No close-out among 119 in history classifies as a stub.
- **Probe after this record landed** (learning #214; measured before this bullet was added):
  `showing lines 1-749 of 2964 total (83982 tokens, cap 25000)` — the front matter plus Sessions
  255, 254 and 253 whole, 252 cut. K=2 holds with a record to spare; the guard predicted 705 lines.

### Session 254 Handoff Evaluation (by Session 255)

**Score: 8/10.** What's-next #2 was this session, and its pointers (§13.8, §13.11) were the right
ones. #3 and #4 (a row, never a block; `R7`'s live arms) remain correct and now bind the ninth
trim. Gotchas 6–8 (`uv run mypy` with no path, `command grep`, the refused files) saved real time.
**−** Its central figure was wrong in the direction that mattered: "front matter + 5 complete
records" and "K is unchanged at 5" counted claim stubs — three non-stub records at `a7d3b29`, two at
HEAD — so "E has now made it reachable" (D at K=3) was the premise this session had to take back to
the operator. **−** Its own 25,123 B record is what moved K from three to two: learning #214
happening to the record that cites it. #5 (push) had already been done when I arrived. **ROI:
high** — minutes to read, and it set the deliverable exactly.

### Session 255 Self-Assessment

**Score: 7/10.**
**+ Measured before designing, and before asking** — the operator ruled on numbers re-derived that
hour, not on the ones §13.1 inherited.
**+ The review gated the commit, twice** — Session 254's lesson applied, and the second pass was the
one that caught a blocker in my own next commit.
**+ The neuter loop and the next-state batteries are mechanised**, the close-out included.
**− Three wrong figures reached the operator.** **− My first draft carried underived prose** (the K
rationale, one remedy for two arms, a budget justified without its stubs). **− My fixes shipped the
#241 class again** — green now, no green successor — the fourth time in this lineage, and only the
second review saw it. **− `CLAUDE.md` grew ~1 KB** against a ~25 KB budget it already exceeds.
**− Cost:** ~5.7M subagent tokens over three workflows.

**What's next.**
1. **The ninth trim — due now.** This file is past the new 196,608 B trigger, and my sweep shows the
   guard going red at Session 257's claim (the next close-out would cross the refusal ceiling). The
   trim must: add a table ROW (`R8`); archive and add the row together (`R7`); **rewrite `L11` to
   the byte rule** and re-target every operand that reads retired prose (find them by running the
   S241 proof's declarations against the working tree); build `L15` (the bequeathed file census);
   keep ≥4 non-stub records and land ≤98,304 B. Run both guards and both proof modes.
2. **Two remediation items, each an operator call:** `PROJECT_LEARNINGS.md` and `CHANGELOG.md`.
3. **Carried:** sync the local dashboard (v2.15.2 → canonical v2.17.0, outside this repo);
   `README.md`'s hand-typed test counts; the census guard's number words stop at sixteen.

**Key files.** `tests/test_read_budget.py` (read its docstring first); `PROJECT_CONVENTIONS.md` §5;
`CLAUDE.md`'s retention bullet; review §14; scratchpad `review1.json`, `review2.json`, `sweep.py`.

**Gotchas.**
1. **Run `uv run pytest tests/test_read_budget.py --no-cov` before every close-out commit.** A red
   `after-the-next-claim` test means your record leaves no room for the next claim: shorten it.
2. **At a claim commit the guard models your close-out** at the ledger's median record size; near
   the ceiling your CLAIM goes red — that means trim first.
3. **Long lines near the top shrink the page:** wrap at ~100 columns; keep wide tables out of the
   newest records.
4. **`check_declared` wants each budget sentence exactly once** in `CLAUDE.md` and in
   `PROJECT_CONVENTIONS.md`; quoting one elsewhere in those files turns it red.
5. The census guard's 30-character window around "shard" still applies to those files.
6. `command grep`; the two refused files; `uv run mypy` with no path.

### What Session 254 Did
**Deliverable:** **Option E, applied RETROACTIVELY — COMPLETE.** The three prose pointer blocks
still standing in this file's front matter are rows 6, 7 and 8 of the table above; collapse-on-write
is declared in `docs/methodology/PROJECT_CONVENTIONS.md` §3.1 and **asserted** by `R8` against the
working tree. Front matter **284 lines / 23,029 B → 94 / 7,184**. Operator's words: *"Option E,
retroactive"*. No trim, no shard, no record moved, nothing else started.

**Started / completed:** 2026-09-09 (UTC). **Commits: four** — `8c9bb35` (Phase 1B claim, alone),
`a7d3b29` (the collapse, carrying **no** record edit, which is what `R2` asserts), the close-out, and
a follow-up carrying the five repairs the adversarial review forced (below).
**`CHANGELOG.md` entry: YES** — this session changed `tests/test_session_notes_census.py`, and
`PROJECT_CONVENTIONS.md` §2 gates on `tests/` logic. Session 249 set the precedent for a change to
this same guard. The rest of the session (`docs/`, `CLAUDE.md`, `README.md`, this file) would have
earned none.

#### What the collapse actually removed, and the control that justified it

Three perturbations of the working tree, each restored from a copy and confirmed with
`git diff --exit-code` — **never `git checkout`**:

| perturbation | result |
| --- | --- |
| corrupt the live "authority" block's routing clause **and** one of its size figures | **all 9 proofs GREEN** |
| **DELETE all three prose blocks (lines 5–227) outright** | **all 9 proofs GREEN** |
| rewrite **only** the C-series table's opening line | **exactly 1 RED** — `C6 LIVE` |

**The 276 lines this commit replaced were guarded by nothing**, and the single proof obstacle to a
one-table design was one pinned line. That is the whole argument, and it was measured before
anything was edited rather than asserted afterwards.

**Four figures inside that region had rotted, and the dated one is the argument.** The block called
itself *"the authority"* and said its filename sweep returns **23** files. Measured **26** at HEAD
and **23 at its own cut `4ab6306`** — true when written, silently false since, with three nameable
files added (`SESSION_NOTES-pointer-collapse.verify.sh` S246, `tests/test_session_notes_census.py`
S247, `docs/planning/ledger-budgets-review.md` S248). Also: `CLAUDE.md` **and** the table's own prose
said `C0–C6` and *36 mutants* where the file has **eight** assertions and **46**; and the sentence at
the old line 227 ended mid-clause (*"…so this trim"*). None of the four was read by any assertion.

#### The new proof — the `R`-series, and the two assertions that are new to this lineage

`docs/architecture-history/SESSION_NOTES-pointer-collapse-S254.verify.sh`, **R0–R8, 48 mutants**.
Lettered `R` for the collision reason Session 245 recorded — it is not an `L`, and it is not an §8
option letter either, so `R3` can never be misread as a ruling. A **new file** was required, not an
extension of the `C`-series: `artifacts()` resolves `before`/`after` at `addcommit(SELF)`, so the
C-series' operands are frozen at `2b8c9c9` and it can never see a second collapse.

- **`R7 ROUTING`** — the assertion that licensed *deleting* the nine prose routing clauses rather
  than keeping them in parallel. The declared `archived` spans, sorted, must tile the history with
  no gap and no overlap; **and** the newest archived session plus one must equal the oldest record
  id **in the working tree**. The second arm is the load-bearing one: tiling proves the table agrees
  with itself, not with the file a session opens.
- **`R8 THE RULE`** — collapse-on-write, enforced against the working tree so it binds FUTURE trims:
  no prose pointer-block head, and no member of the `**The N blocks below are frozen**` family, may
  stand in the front matter. `C7` had to *derive* the count in that family because the family
  survived its collapse; asserting the family is **empty** is stronger and cheaper, and it is §11's
  Option E completion criterion mechanised.
- `R3` re-derives **all eight** rows (not just its own three) from each shard at its own add-commit,
  so the table has exactly one owner; its `FIGURE` arm composes the four arithmetic phrases the new
  prose states about itself. `R1` needs **zero** declared substitutions — no prose block survives, so
  none could be falsified, which is the point of the rule rather than an omission.

#### The C-series repair, and the weakening the arm sweep caught

`C6`'s opening-line needle was `NEW_TABLE.split("\n")[0]`, and this collapse replaced that line.
**It could not be re-pointed at `NEW_TABLE`** — `C1` pins that literal at the proof's own add-commit
forever, the trap that file's own header records one field over. So the live anchor became a declared
`LIVE_HEAD`, and `C6` gained **`C6/SUPERSEDED`**, requiring the OLD line to be **absent**: dropping a
requirement would have left both texts legal, and the legal one would be the false one. `M47` is its
mutant.

**Then the per-arm sweep caught a weakening I had introduced and both modes had missed.** A working
tree rebuilt from `after` no longer contained `LIVE_HEAD`, so `C6` began firing for every table
mutant and **`C0/FIGURE` and `C3/FIGURE` silently stopped being the sole objector** to `M39`, `M40`
and `M41`. Measured: **17 unique of 35 before, 16 of 36 after** — one arm gained, two lost, with the
plain run and `--self-test` green throughout. `with_table` now swaps only the ROWS into the real
working tree; coverage is **18 of 36**, the 17 + 1 the arithmetic predicts. **The inherited "17 of 35"
was re-derived against the pre-collapse tree and reproduced exactly** — Session 253's figure was
right, and the regression was mine.

#### Verification

| check | result |
| --- | --- |
| ten proofs, **both** modes | **GREEN/PASS 10/10** — the gate prints nothing, before and after the collapse commit |
| `R`-series whole-assertion neuter | every one of **R0–R8** is the sole objector to ≥2 mutants |
| `R`-series per-arm neuter | **44 statements, 17 uniquely catching**; the 27 grouped by cause in the header |
| `C`-series per-arm neuter | **36 statements, 18 uniquely catching** (was 35/17; +1 arm, +1 unique) |
| census guard | **25/25** — went RED on me once, correctly, on two stranded `FROZEN` entries |
| full gate | **1,338 passed + 9 live-skipped**; `ruff` clean; `uv run mypy` clean (68 files) |
| read-cap probe, empirical | `lines 1-754 of 2,539 (71,499 tokens, cap 25,000)` — front matter **+ 5 complete records**, where it delivered 4 |
| front matter share of the delivered prefix | **13.1%**, was **41.3%** |

**Two figures I got wrong and corrected before committing.** I typed *"37 failure-emitting
statements"* into the C-series header without measuring (it is 36), and I ran `uv run mypy .` and
reported 185 errors when CI's command is `uv run mypy` with no path argument — 68 files, clean.
Both were caught by measuring rather than by review.

**Where I exceeded the plan, and by how much.** §13.3 projected the post-E front matter at **5,051 B
/ 9%** of the delivered prefix; I landed at **7,184 B / 13.1%**, because that projection assumed the
three blocks simply vanish and budgeted nothing for standing prose. The 2,133 B difference buys the
routing rule, the write-once rule, the banner-snapshot rule and the three bequests — and it costs
**nothing** in delivered records: K = 5 either way.

**I claimed the standing block is "fixed-size by construction" and that is not true — the
adversarial review measured the exception.** The *"Three things are bequeathed to the ninth trim"*
list is **12 lines / 1,013 B, 14% of the front matter**, and it IS per-trim by content; so is the
numeral in *"What these eight trims found"* (which `R3/FIGURE` at least derives). Nothing asserts the
bequest list's size, and nothing stops a trim appending to it rather than rewriting it. The honest
statement is narrower: **the block contains no per-trim POINTER content — no block per cut — which
is the growth driver Option E was ruled against.** The bequest seam is the remaining one, it is
filed in `BACKLOG.md`, and a session that finds that list longer than it found it should move the
resolved items into its own record.

#### The adversarial review landed after the commit, and it changed the code

A 5-lens inventory with per-finding refuters and a completeness critic was launched at Phase 2 and
finished after `a7d3b29` was already committed: **116 agents, 0 errors, ~10.3M subagent tokens,
~100 minutes. 110 findings verified — 19 survived, 91 refuted** — plus 12 from the critic. A review
that lands after the commit is a follow-up, not a gate, and it is recorded here as one.

**Eight of the nineteen survivors independently re-derived rows 6, 7 and 8 field-for-field** —
including the composed markdown lines — and agreed with my derivation exactly. Four more predicted
the two obstacles I had already hit (the `FROZEN` literals inside `CLAUDE.md:87`; that the C-series'
`ROWS` must **not** be extended and a separate proof was required). That is corroboration, not
correction.

**Five findings were real defects in the commit, and all five are fixed in the follow-up:**

| # | what it found | fix |
| --- | --- | --- |
| **1** | **`R7/FRONTIER` had NO GREEN STATE after the next trim.** It compared the FROZEN declared `ROWS` (max archived 241) against the LIVE oldest record id, so a ninth trim fails it — while extending `ROWS` fails `R3 SET` and editing `NEW_BLOCK` fails `R1`. **The C3 "rows cannot be extended" trap, reproduced one level up, inside my brand-new arm, in the session whose own record calls that trap out.** | `R7` split into a frozen-declaration half and **live** arms that parse the `archived` column out of the working tree. Verified by simulating a ninth trim three ways: archive-without-row → RED, archive-and-row → **GREEN**, overlapping row → RED. `M49`/`M50` added, each isolating one live arm. |
| **2** | My what's-next #4 told the ninth trim to satisfy `R7` — **impossible** given #1, and it was the only guidance that session had. | rewritten, with the three simulation outcomes stated. |
| **3** | `R8`'s family regex was inherited from `C7` and **never matched the singular form.** `**The two blocks below are frozen` matched; `**The block below is frozen` did not — and **both** stood in the front matter I deleted, so `C7` could only ever have caught one of the two members of the family it was written for. | count word made optional. |
| **4** | The front-matter byte figure is **wrong in two live files**: `CLAUDE.md` and `CHANGELOG.md` said `94 / 7,179` where the measurement, the proof's own output and this record all say **7,184**. A stale figure from an earlier build, in the commit whose subject is stale figures. | corrected in both. |
| **5** | `docs/planning/ledger-budgets-review.md` pins `SESSION_NOTES.md:185`, `:256` and `:277` — **all three inside the region I deleted.** One of them (`:277`) presented as a backticked quotation a string that **never existed in that file at any commit**, so that inventory row was unverifiable before the collapse too. | six sites annotated: what was deleted, where it survives, and which §13.11 rows Session 254 closed. |

**Two more survivors are residual gaps, filed rather than fixed** (`BACKLOG.md`): the standing block
is guarded only at its table rows and spans — a six-way control showed deleting the routing sentence,
the write-once rule, the banner-snapshot rule or the legend leaves every proof green (an improvement
in **cost**, not in **safety**, and the record should not be read as claiming otherwise); and
**neither collapse proof is guarded by anything** — not `L10`'s declared list, not the census guard's
glob, and CI errors only when *zero* proofs are found, so the file the front matter names as the
second custodian of the deleted prose can vanish silently.

**One critic finding corrected a claim in this record** — the bequest list is a per-trim growth seam
(above) — and **one corrected my own prompt**: commit `020ba3f`, which I cited to the agents as the
losslessness counterexample, is not an object in this repository. It is a sibling-repo commit reached
through a quotation. A later session should not go looking for it here.

### Session 253 Handoff Evaluation (by Session 254)

**Score: 9/10.** The best handoff this lineage has produced for a session that had to touch the
apparatus itself. It named the deliverable, named the trap, and was right about both.

- **+ What's-next #1 was the entire session**, including the two things that actually governed the
  design: *"`OLD_BLOCKS` and `NEW_TABLE` are pinned at `2b8c9c9`"* and **"`C6` reads the working tree
  and will need its own declared substitution."** That second clause is the single most valuable
  sentence in the handoff — it predicted the only proof obstacle, correctly, before I looked.
- **+ Gotcha 1 (run BOTH modes, neither is sufficient)** — load-bearing twice: once for the routine
  gate, and once when it was *still* not enough and the per-arm sweep found what both modes missed.
  That is not a defect in the gotcha; it is the next layer down, and gotcha 3 points at it.
- **+ Gotcha 5 (the census guard fires within 30 characters; reword, do not exempt)** paid exactly as
  written. The guard went red, and I dropped two stranded entries rather than adding one.
- **+ Gotcha 6 (`command grep`)** — eighth session running, used in every count published here.
- **+ Gotcha 7 (`PROJECT_LEARNINGS.md`/`CHANGELOG.md` are refused by a default `Read`)** — saved two
  failed reads; I used `wc -c`, `sed -n` and `command grep` throughout.
- **+ It re-derived its own inherited figures and said so**, which is why I trusted "35 statements"
  enough to test it — and it reproduced exactly.
- **− The only miss is one it could not have avoided:** its self-assessment says *"~4.4M subagent
  tokens … a large bill for a two-file repair"*, and I repeated the pattern at similar scale for a
  larger change without first checking whether the inventory would finish inside the session. Not
  its fault; noted because the next session inherits the same temptation.
- **ROI: very high.** Five minutes to read; it removed every structural decision except the shape of
  the new prose.

### Session 254 Self-Assessment

**Score: 7/10 — revised down from 8 after the adversarial review landed.** The deliverable is
complete and now genuinely sound: it ends a condition §2 of the review document says has held since
the first trim, and the rule that keeps it that way is asserted rather than announced. But I
committed `a7d3b29` with a **no-green-state trap inside my own new assertion** — the exact trap this
lineage documents twice and my own record names — and I found it only because a review I had
launched happened to finish before I stopped working. Had it finished an hour later, the ninth trim
would have hit an unreachable state with my record telling it the arm was correct. Everything below
the first minus is what an 8 would have looked like; the trap is what it actually was.

**+ I measured the premise before acting on it, with a control**, including the perturbation that
matters most — deleting all three blocks and watching nine proofs stay green. That converted "the
plan says this is safe" into "this is safe, and here is the experiment".
**+ I built the new prose with a script**, so rows 1–5 are copied byte-for-byte and rows 6–8 are
composed from figures derived at each shard's own add-commit. No table figure in this file was typed.
**+ `R7` and `R8` are the two assertions this deliverable actually needed**, and neither existed in
the lineage: one licenses a deletion, the other makes a convention enforceable.
**+ The dated sweep census (23 at its own cut, 26 now)** is the strongest evidence I found, and I
found it by re-measuring a claim rather than by reading it.
**+ The guard adjudicated me and I let it** — third session running — and I dropped the stranded
exemptions rather than re-pointing them, after verifying the scan was clean without them.
**+ I corrected my own `mypy` claim** rather than reporting a regression that was my invocation.

**− I shipped `R7/FRONTIER` with no green state after the next trim.** It mixed a frozen operand
with a live one. Both modes green, all 48 mutants caught, my own controls green — because every one
of them tested *this* world, and the defect only exists in the *next* one. **The lesson is sharper
than "run the sweep": an assertion that reads both a frozen declaration and a live artifact must be
tested against a simulated future state, and nothing in this project's toolkit does that.** I
simulated a ninth trim only after a reviewer told me to.
**− I introduced a real weakening into the `C`-series and neither verification mode saw it.**
`C0/FIGURE` and `C3/FIGURE` lost their unique mutants the moment I re-anchored `C6`. Both modes were
green across the regression. Only the per-arm neuter sweep found it — and I ran that because
`CLAUDE.md` mandates it for a new proof, not because I suspected the old one. **Had I shipped the
`R`-series without touching `C6`'s fixture, this session would have published a green gate over a
quietly weaker proof, which is precisely the class Session 253 existed to close.**
**− I typed "37 failure-emitting statements" into a header block whose subject is unmeasured
figures.** Wrong by one. I caught it by measuring, but I wrote it first — the same defect Sessions
252 and 253 each recorded against themselves.
**− I exceeded §13.3's front-matter projection by 42%** and only justified it after the fact. The
justification holds (K is unchanged at 5), but I should have computed the budget before writing the
prose, not after.
**− The adversarial inventory did not finish before I committed, and it should have gated.** I
launched it at Phase 2 and completed the deliverable from my own measurements while it ran; it
returned ~100 minutes later, after `a7d3b29`. It then found five real defects including the blocker
above. **Eight of its survivors also re-derived my rows field-for-field and agreed exactly**, so the
measurement half of my work was independently confirmed — but the design half was not reviewed until
after it shipped. A ~10.3M-token review that lands after the commit buys a follow-up commit instead
of a correct one.
**− ~10.3M subagent tokens**, the most expensive verification in this lineage by a factor of two. It
paid — it caught a trap that would have blocked the next session — but the bill belongs on the record.

**Against the bar:** S252 showed a document's conclusions had expired; S253 showed the apparatus's
verification recipe was wrong everywhere it was written down. S254's equivalent is showing the
recipe is **still not sufficient, in two independent directions.** A proof can be weakened while
both mandated modes report success — only the per-arm sweep sees it (learning #237). And an
assertion can be green against every state that exists while having **no reachable green state in
the next one** — nothing in this project tests that, and the only reason it was caught here is that
a review outlived the commit. Learning #241.

**What's next.**

1. **Nothing outstanding from the review — it landed and was acted on in-session.** 110 findings
   verified, 19 survived, 12 from the critic; five were real defects and all five are fixed in the
   follow-up commit, two are filed in `BACKLOG.md`, and the rest were corroboration or no-action.
   The table above lists every one. **Start at #2.**
2. **Then Option D, widened** — the front-matter budget, K in **bytes**, over the four mandated-read
   files. §13.8 and §13.11. **E has now made it reachable**: front matter is 13.1% of the delivered
   prefix, and §13.3's precondition was that D at K=3 is unreachable above ~33%.
3. **The ninth trim is over its trigger and the arithmetic has changed.** This file measures
   **2,538 lines** before this record lands — **re-measure**, it moves with every edit — against the
   1,500-line trigger. The front matter is no longer the binding quantity, which is exactly what E
   was for. **The ninth trim must write a ROW, not a block**, and `R8` will go red if it does not.
4. **`R7`'s frontier arm binds the ninth trim, and it took a review plus a repair to make that
   possible.** As first shipped it compared the FROZEN declared `ROWS` (max archived 241) against
   the LIVE oldest record id, so the ninth trim had **no green state at all** — the C3
   "rows cannot be extended" trap reproduced one level up, inside the new arm, in the session whose
   own record calls that trap out. Found by the adversarial review, reproduced here by simulating a
   ninth trim, and **fixed**: `R7`'s live arms now parse the `archived` column out of the WORKING
   TREE. Verified by simulation — a trim that archives records **and** adds its row is GREEN; one
   that archives without adding the row is RED (`R7 FRONTIER`); one whose row overlaps is RED
   (`R7 LIVE-OVERLAP`). **So: add the row and archive the records, in the same trim.**
5. **Push.** This clone is now **10 commits ahead of `origin/master`**, which last saw Session 249.
   The CI `proofs` job added in Session 253 still has never run.
6. **Carried, unchanged:** sync the local dashboard (v2.15.2 vs canonical v2.17.0, outside this
   repo); `BACKLOG.md`'s plain-language index still renders as several tables; the census guard's
   `SPELLED`/`ORDINAL` maps stop at sixteen (S249 #3, still unfiled); `tests/eval/README.md`'s three
   stale statements, now a ninth session.

**Key files.**
- `docs/architecture-history/SESSION_NOTES-pointer-collapse-S254.verify.sh` — the `R`-series. Read
  its header first: the nine assertions, the control experiments, and the measured neuter table.
  `R7`/`R8` are the new ones. **Locate by content, never by line number.**
- `docs/architecture-history/SESSION_NOTES-pointer-collapse.verify.sh` — `LIVE_HEAD` (declared, just
  after `DECLARED_OLD_LINES`), `C6/SUPERSEDED`, `with_table` in `self_test()`, and the
  `SESSION 254` header block recording the weakening and its repair.
- `docs/methodology/PROJECT_CONVENTIONS.md` §3.1 — collapse-on-write, declared as convention.
- `CLAUDE.md` — the rewritten collapse bullet. It **states no assertion or mutant count on purpose**.
- `tests/test_session_notes_census.py` — two `FROZEN` entries dropped, with the reason in a comment
  at their former location.
- `/private/tmp/claude-501/…/scratchpad/measurements-s254.md` — every figure with its command;
  `build_front.py`, `derive_rows.py`, `neuter.py`, `sweep_final.py` are the scripts that produced them.
- Inventory workflow journal (still running at close-out):
  `~/.claude/projects/-Users-rmsharp-Development-model-project-constructor/3fdb0739-d8ba-4856-a11c-098817ec32d6/subagents/workflows/wf_383a901d-415/journal.jsonl`.

**Gotchas.**
1. **A green plain run AND a green `--self-test` still miss a weakened arm.** This session proved it:
   re-anchoring `C6` cost two arms their unique mutants with both modes green. **After changing any
   assertion or self-test fixture, re-run the per-arm neuter sweep and compare unique coverage to the
   published figure.** The loop is in both proofs' headers.
2. **Three commits, not two, and the order is load-bearing.** `R2` asserts the records zone is
   byte-identical across the collapse commit, so the claim stub, the collapse, and the close-out are
   three separate commits. Bundling the record with the collapse holds `R2` red forever.
3. **`R8` will fire on the ninth trim if it writes prose.** That is deliberate. Add a row to the
   table; put the rationale in the session's record. The table's `archived` column is the routing
   table now — there are no prose routing clauses left to update.
4. **`C1` pins `NEW_TABLE` at `2b8c9c9` forever and `R1` pins `NEW_BLOCK` at `a7d3b29` forever.**
   Neither literal can be re-pinned; there is no green state containing an edited one. Prose inside
   the collapsed block may still be repaired — that is what `LIVE_HEAD`-style declared anchors are
   for — but the frozen literals stay frozen.
5. **The census guard's `FROZEN` entries are claims about prose.** Reword a guarded sentence and its
   entry strands, turning the guard red **and taking every mutant test with it** (17 failures, one
   cause). Drop the entry if the new prose needs no exemption; verify by running the scan, not by
   reading it.
6. **CI's type check is `uv run mypy` with no path argument** (68 files, clean). `uv run mypy .`
   pulls in out-of-scope tests and reports errors that are not regressions.
7. **`command grep` for every count** — bare `grep` is a `ugrep --ignore-files` wrapper.
8. **`PROJECT_LEARNINGS.md` and `CHANGELOG.md` are REFUSED by a default `Read`.**
   `PROJECT_LEARNINGS.md` is 290.5 KB at close-out — re-measure with `wc -c`, never quote it.
9. **`gh issue list` is empty by design** until UAT.

### What Session 253 Did
**Deliverable:** **The unfalsifiable proof is repaired — COMPLETE.**
`docs/architecture-history/SESSION_NOTES-pointer-collapse.verify.sh` passes `--self-test` with
`M16`/`M17` catching again; a `proofs` job in `.github/workflows/ci.yml` runs **both** modes over
every `*.verify.sh` in `docs/architecture-history/` on push and PR. No pinned literal, no assertion,
no archived file and no ancestor proof was touched. Operator's words: the backlog item's own title.

**Started / completed:** 2026-09-09 (UTC). **Commits: two** — `5def6b9` (Phase 1B claim, alone) and
this one. **`CHANGELOG.md` entry: YES** — `PROJECT_CONVENTIONS.md` §2's directory test puts
`.github/workflows/` inside the gate (operator ruling, Session 244, "not a judgement test"), and this
session adds a job to `ci.yml`.

#### What was wrong, and what the repair actually is

`M16`/`M17` corrupted the working tree with `live_wt.replace(NEW_TABLE, …)`. `NEW_TABLE` is a
51-line pinned literal of **table plus prose**; `C6` reads only the composed rows and the table's
opening line. Session 249 correctly repaired the read-cap sentence inside that prose at `5243242`,
`NEW_TABLE` stopped matching (4,273 of 4,369 characters still agree — the divergence is the
literal's last sentence), both replacements became no-ops, and `C6` was handed pristine input. **The
assertion was never wrong; the fixture was.** Re-derived here, not inherited: last matched at
`b1d761f`, broke at `5243242`, and the proof was plain-GREEN / self-test-RED at **8 consecutive
commits** across Sessions 249–252 (measured per commit in an isolated clone).

**The filing's proposed remedy was tested and rejected on evidence.** `BACKLOG.md` said *"Re-pin one
literal"*. `C1` resolves its `after` operand at this file's own add-commit `2b8c9c9` **forever**, and
that commit carries the old sentence: a re-pinned `NEW_TABLE` fails `C1 TABLE MISSING` and
`C1 CONFINEMENT` at once, permanently. There is no green state containing one. The repair went where
the same item's last paragraph already pointed — the mutants.

`live_table_replaced(lw, put="")` strips **the same expressions `C6` counts** — `rows_of(NEW_TABLE)`
and `new_table.split("\n")[0]`, neither carrying a trailing newline. Measured over three drift
classes: a row-content edit and an opening-line edit turn **both** modes red together; a prose edit
inside the block — the exact class that caused this bug — leaves both green.

**And the class, not the instance.** The `--self-test` driver now compares each mutant's 10-tuple of
arguments against the pristine tuple and reports **`NO-OP`** — a distinct hard failure — for any
mutant that changed nothing. `SURVIVED` names the wrong culprit: it says the assertion missed a
corruption when the corruption never happened. Session 252 needed a bisect to learn that difference;
the self-test now prints it.

#### The finding that outlives the repair

**Neither mode subsumes the other, and every published recipe was one-mode.** Measured with controls:

| mode | proves | is blind to |
| --- | --- | --- |
| `bash "$f"` | the world is intact | a proof that can no longer fail (8 commits, 2 inert mutants, green throughout) |
| `bash "$f" --self-test` | the proof can fail | **real corruption** — append a line to any archived file and its `--self-test` still PASSES, because every mutant then fails for the corruption's sake and scores as *caught* |

The plain run's coverage is **lineage-wide, not per-file**: for the two oldest proofs (which define
only `L0`–`L4`, none of which reads disk) their own file's corruption leaves them green, and `L9` in
every proof from the S227 one forward is what catches it. `CLAUDE.md`'s trimmed-file bullet now
carries the two-mode loop and why each half is necessary; it previously mandated `--self-test` alone.

#### Verification

| check | result |
| --- | --- |
| nine proofs, **both** modes | **GREEN/PASS 9/9** — the corrected gate prints nothing |
| `M16` reverted / `M17` reverted / both | exit 2, `NO-OP`, correctly diagnosed each time |
| `C6` neutered (type-preserving `return []`) | `M16, M17, M34, M35, M43` survive — matches the header's own table exactly |
| CI step run verbatim | exit 0, 9 groups, 0 errors; exit 1 on a corrupted archive **and** on a re-broken mutant |
| shallow-clone control | all nine RED at depth 1 → `fetch-depth: 0` is load-bearing |
| census guard | **25/25** — went RED on me once, correctly, on a census claim I wrote into `CLAUDE.md`; reworded to state no census rather than exempted |
| full gate | **1338 passed + 9 live-skipped @ 97.98%**, `ruff` and `mypy` clean |
| adversarial review | 7 lenses + per-finding refuters + completeness critic; **42 agents, 0 errors**, ~4.4M subagent tokens; 10 confirmed, 24 rejected |

**Three review findings changed the code.** (1) I had written *"it is filed in `BACKLOG.md`"* about
the residual gap — **and nothing was filed**; 7 of 7 lenses reported it, the most-reported finding of
the session. The filing now exists. (2) My first helper searched for `row + "\n"` while `C6` counts a
bare `row` — **the same failure shape as the bug being repaired**, one field over; a trailing space on
a row would have left the plain run green and killed the self-test on an assert. (3) The CI step
exited 0 for a proof that ignores `--self-test` entirely, because every proof here ignores an
unrecognised flag; it now requires the `SELF-TEST OK` line. The **critic** found a fourth: the DONE
gate's own `VERIFY` command is `--self-test`-only and therefore passes on an already-corrupt world.

**One rejected finding was re-measured by hand and the rejection confirmed:** the header's *"35
failure-emitting statements"* is correct (33 `out.append` + 2 early `return ["C…`), so no item was
filed against it. A reviewer had counted one form and called it stale.

### Session 252 Handoff Evaluation (by Session 253)

**Score: 8/10.** It defined this session completely and its gotchas were load-bearing throughout.

- **+ What's-next #1 was the entire deliverable**, and the `BACKLOG.md` item behind it carried the
  mechanism, the dating, the DONE gate and a VERIFY command. I never had to discover the problem.
- **+ Gotcha 1 — "run both, treat the plain loop as necessary, never sufficient"** — is the single
  most valuable line in the handoff, and this session measured *why* it is true in both directions.
- **+ Gotcha 4 (census guard, 30-character window)** paid immediately: the guard went red on my
  `CLAUDE.md` sentence and I knew from the gotcha to reword rather than exempt.
- **+ Gotchas 5 and 6** (`command grep`; the two files a default `Read` refuses) — both load-bearing,
  seventh session running for #5.
- **+ Key files were exact** — `NEW_TABLE`, `C6`, `M16`/`M17` at the mutant table.
- **− The item's own remedy is impossible.** *"Re-pin one literal"* cannot be done: `C1` pins the
  post-collapse front matter at the add-commit forever. Ten minutes to test and discard. Mitigated
  only because the same item's last paragraph says the opposite and is right.
- **− The DONE gate contradicts gotcha 1.** The gate is `--self-test`-only, so it certifies a tree
  whose archived history is already damaged — the same one-mode error the gotcha warns about, written
  by the same session, in the criteria this session is closed against. Corrected here.
- **ROI: very high.** It cost five minutes and defined the session.

### Session 253 Self-Assessment

**Score: 8/10.** The deliverable is complete, verified in both modes, and the fix is at the class
level rather than the instance. What holds it at 8 is that I wrote an unverified claim into the very
header block arguing that claims must be measured, and that a review — not I — caught me
reintroducing the repaired bug's own shape.

**+ I tested the filed remedy instead of following it**, and the experiment redirected the repair.
**+ I fixed the class.** A `str.replace` whose needle has drifted is silent; it is now loud, with a
message naming the right culprit.
**+ I found that neither verification mode subsumes the other** — with controls over every archived
file — which falsified a recipe in `CLAUDE.md`, in the DONE gate, and in my own first CI draft.
**+ I re-derived every inherited figure** — the break commit, the outage span, `95/95`, the header's
arm counts — and one of them (the arm counts) turned a reviewer's finding into a non-finding.
**+ The guard adjudicated me and I let it**, for the second session running.

**− I wrote *"it is filed in `BACKLOG.md`"* when nothing was filed.** In the block arguing for
measured claims. Seven of seven lenses found it. **This project's signature defect, committed inside
the repair that catalogues it** — the same sentence Session 252 wrote about itself.
**− My first repair reintroduced the bug's own shape.** `row + "\n"` against `C6`'s bare `row`.
I had just spent an hour characterising *needle ≠ haystack* and then wrote one.
**− I measured that `--self-test` is blind to corruption and did not connect it to the gate I was
being judged by.** The critic did. That is a synthesis failure, not a measurement failure.
**− ~4.4M subagent tokens**, the most expensive verification in this lineage. It changed three things
in the code and found a fourth, so it paid — but it is a large bill for a two-file repair.

**Against the bar:** S249 showed a premise was executable; S252 showed a document's conclusions had
expired. S253's equivalent is showing that **the apparatus's own verification recipe was wrong in
every place it was written down** — and that the proof it was meant to certify had been unable to
fail for four sessions while every published check reported success.

**What's next.**

1. **Option E, retroactive** — collapse the standing prose blocks in this file's front matter and
   make collapse-on-write the rule. `§11`'s E criterion, `§13.3`'s target arithmetic. **Re-read
   `C0`/`C1` first:** `OLD_BLOCKS` and `NEW_TABLE` are pinned at `2b8c9c9` and an E-collapse rewrites
   the region around them. `C6` reads the working tree and will need its own declared substitution.
2. **Then Option D, widened**, K in bytes. §13.8 and §13.11.
3. **The ninth trim is over its trigger.** This file measures **2,721 lines** at close-out (re-measure
   — it moves with every edit) against the 1,500-line trigger. Session 252's gotcha 3 has the
   floor-4 arithmetic; **re-measure before trimming**, and note that E lands in the same front matter.
4. **Two new `BACKLOG.md` items** filed this session: the partially-inert-mutant gap (7 of 46 mutants
   change more than one argument slot and the guard sees whole tuples only — all seven read frozen
   operands, so nothing is broken today), and CI's detection latency versus this repo's push cadence
   (**operator call**).
5. **Push.** This clone was 7 commits ahead of `origin/master` at Phase 0 — `origin/master` last saw
   Session 249. The new CI job cannot run until someone pushes, which is finding #4's whole point.
6. **Carried, unchanged:** sync the local dashboard (v2.15.2 vs canonical v2.17.0, outside this repo);
   `BACKLOG.md`'s plain-language index still renders as several tables rather than one; the census
   guard's `SPELLED`/`ORDINAL` maps stop at sixteen (S249 #3, still unfiled); `tests/eval/README.md`'s
   three stale statements, now an eighth session.

**Key files.**
- `docs/architecture-history/SESSION_NOTES-pointer-collapse.verify.sh` — `live_table_replaced` (in
  `self_test()`, just above `FAKE_ROW`), the `pristine`/`inert` guard in the driver loop, and the
  `SESSION 253 REPAIR` header block. **Locate by content, never by line number.**
- `.github/workflows/ci.yml` — the `proofs` job: `fetch-depth: 0`, both modes, the `SELF-TEST OK` grep.
- `CLAUDE.md` — the trimmed-file bullet's two-mode loop (replaced a `--self-test`-only mandate).
- `BACKLOG.md` — the two new items at the former location of the closed one, and its two index rows.
- `/private/tmp/claude-501/…/scratchpad/measurements-s253.md` — every figure with its command.

**Gotchas.**
1. **Run BOTH modes; neither is sufficient.** The loop is in `CLAUDE.md` now. A plain run cannot see
   an inert mutant; `--self-test` cannot see a corrupted archive. Session 252's gotcha 1 was right and
   its own DONE gate contradicted it.
2. **`--self-test` never calls `check()` on pristine input** — `self_test(...)` then `sys.exit(0)`
   precedes the plain `check(...)`. That is *why* it is blind to corruption. Do not "simplify" the CI
   job to one mode.
3. **Editing this file can still disarm a mutant** — that has not changed, only this one proof's
   exposure to it. After any front-matter edit run **both** modes, and read the first line of the
   self-test output: `NO-OP` means your edit broke a fixture, `SURVIVED` means it broke an assertion.
4. **A proof that ignores `--self-test` exits 0.** All nine parse their own argv and ignore unknown
   flags. The CI job greps for `SELF-TEST OK`; a hand-run loop that only checks exit codes does not.
5. **The census guard fires on any numeral within 30 characters of the word it watches** — it caught
   me in `CLAUDE.md`. Reword so the sentence states no census; an exemption is permanent work.
6. **`command grep` for every count** — bare `grep` is a `ugrep --ignore-files` wrapper.
7. **`PROJECT_LEARNINGS.md` and `CHANGELOG.md` are REFUSED by a default `Read`** (262,144 B boundary).
   `PROJECT_LEARNINGS.md` is 287.0 KB at close-out — re-measure with `wc -c`, never quote it.
8. **`PROJECT_LEARNINGS.md` rows 224–230 are two-column**, missing `Source` and `When to Apply`.
   Pre-existing, not fixed here. Rows 231–236 are well-formed.
9. **`gh issue list` is empty by design** until UAT.

### What Session 252 Did
**Deliverable:** **The operator's ruling on [`docs/planning/ledger-budgets-review.md`](docs/planning/ledger-budgets-review.md)
§8 — COMPLETE.** Every figure re-derived at HEAD, the options presented, the ruling recorded in
[`§13`](docs/planning/ledger-budgets-review.md) and `BACKLOG.md`. **Nothing was executed** — no trim, no
re-tune, no `CLAUDE.md` edit, no option implemented. Operator's words: *"finish what Session 251
claimed"*, then six rulings. No other work started.

**Started / completed:** 2026-09-07 → 2026-09-08 (UTC). **Commits: two** — `effc3f5` (Phase 1B claim,
alone) and this one. **No `CHANGELOG.md` entry:** `PROJECT_CONVENTIONS.md` §2 gates on `src/`,
`packages/`, `scripts/`, `.github/workflows/` or `tests/` logic; this session touched
`docs/planning/`, `BACKLOG.md` and this file only. Checked against the rule, and against the four
doc-only precedents Session 250 recorded (`7075f7b`, `efc24a6`, `99e9abf`, `bfeb2a7`).

#### The ruling

| option | ruling |
| --- | --- |
| **E — collapse-on-write, RETROACTIVE** | **RULE FOR — first** |
| **D — front-matter budget** | **RULE FOR — second, WIDENED** to the four mandated-read files; K in bytes |
| **F — end assertion-per-trim** | **RULE FOR, narrowed** — with a CI step running `--self-test` |
| **B, C, G, H** | **DECLINED** |
| the `--self-test` break (new, below) | **its own session, ahead of all three** |

**§9 recommended D before E; the ruling inverts that**, on §13.3's arithmetic. **G's decline is
recorded on corrected grounds** — §9's stated reason is falsified (below).

#### What moved under the document, and why it mattered

- **§3.2's "empty constraint set" and §3.4's "a ruling is on the critical path" are STALE.** The
  retention rule is *satisfiable* at HEAD: floor-4 retains Sessions 252, 251, 250, 249 and lands at
  **664 lines** against the 1,050 target. **The cause is that Session 251 abandoned its claim**,
  leaving a permanent 15-line record, next to Session 250's unusually short 157. **An abandoned
  session bought, for free, exactly the one-trim reprieve Options B and C were priced at a session
  each to buy** — which is the whole case for declining both. Under a *four substantive records*
  reading it is still unsatisfiable (1,216); both readings are in §13.2.
- **§12.1's `K = 1` is now `K = 4`.** A default `Read` returns `lines 1-753 of 2346 (66193 tokens, cap
  25000)` — front matter plus four complete records, cutting inside Session 248's. **The file grew 21%
  in tokens and what one `Read` delivers went from one record to four.** That is §1.3's thesis
  demonstrated rather than argued, and it is the strongest single argument for D.
- **Option E is ~52× at the margin, not §8's ~2× or §12.2's ~6.9×.** Both earlier prices amortise the
  collapse's one-time frame across five trims. Measured: a prose pointer block costs **6,110 B/trim =
  11.0% of the one-`Read` budget, permanently**; a table row costs **117 B = 0.21%**.
- **D and E are not independent.** Front matter is 41% of the 55,783 B delivered prefix (the three
  standing prose blocks alone are 33%), so **1.8** median records fit; after E, 9% and **2.8**. **D at
  K=3 is arithmetically unreachable until E lands.** And E-retroactive is the only option on the table
  that produces a post-trim ledger which **reads whole** (18,977 tokens against a 25,000 cap) — §2
  records that the system's success state has always been a file that still truncates.
- **Every cost figure moved against the apparatus:** ledger sessions 7 of the last 10 (was 5), 10 of 20
  (was 8), longest run 5 (was 3); `src/`/`packages/` untouched since Session 223 — **29 sessions, 95
  commits**; 9 open code/harness defects, unchanged. Lines added since the first trim: apparatus
  **+43,225 across 19 files** against **+40 in one file** for product code, ~**1,080 : 1**.

#### The finding that outlives the ruling

**`SESSION_NOTES-pointer-collapse.verify.sh` has failed its own `--self-test` since Session 249 while
its ordinary run stays green.** `M16` and `M17` survive. They mutate by `live_wt.replace(NEW_TABLE,…)`;
`NEW_TABLE` is no longer a substring of this file, so both are no-ops and `C6` sees clean input. `C6`'s
plain run survives because it checks each table row and the opening line individually.

**Dated by bisecting `NEW_TABLE in git show <sha>:SESSION_NOTES.md`:** last matched at `b1d761f`, broke
at **`5243242` — Session 249's Option A**, which rewrote the *"`grep` the shards; `Read` none"* sentence
inside the pinned region. A correct repair that silently disarmed two mutants. The proof file itself has
been touched exactly once, at its own commit. **`C6` is the only assertion in this lineage that reads
the working tree** — what `CLAUDE.md` calls the closure of *"the largest hole this apparatus has."*
`CLAUDE.md` already mandates *"Run `--self-test` before trusting a green run."* Four sessions ran the
plain loop and saw green. **This is why F's CI substitute is ruled as `--self-test`, not `bash "$f"`.**

#### G: the reason §9 gave is false, the decline still stands

Pairing every record with the score its successor awarded it, n = **173** across this file and all eight
archives: **r(lines) = −0.087** — records scoring ≥9 have a median of **95** lines against 134 for ≤8, so
*"the 9s and 10s are the long ones"* is contradicted. But **r(bytes) = +0.070** — the sign flips, because
the older records are short in lines and long in bytes. In the modern regime (S217+, n=28) r = +0.106 and
**0 of 28 records fit either cap**, so the data cannot test the claim at all. The decline rests instead
on: §8's 120–150 line form is exceeded by **100%** of the last 33 records; **the operator already
ratified 12,288 B upstream** (`~/Development/methodology/…/record-budget-reduction-plan.md:3`, enforced
at `bin/check-handoff:665`) with its §7 saying *"No adopter receives any file this plan changes"*; and
the controlled measurement that settled it upstream does not exist here.

#### Verification

| check | result |
| --- | --- |
| census guard | **25/25** — and it went **RED on me once**, correctly, on `95/95` sitting within 30 characters of the word it watches. Fixed by naming the file instead of the category, not by exempting it |
| nine `*.verify.sh`, plain run | **GREEN** before and after — which is precisely the problem this session found |
| `--self-test`, all nine | **eight pass; the collapse proof exits 2.** `SESSION_NOTES-S241-through-S239.md.verify.sh` catches 95 of 95 |
| full suite | **not re-run** — no `src/`, `packages/` or test-logic change |
| independent re-derivation | 8 measurement arms + 8 adversarial refuters + 1 completeness critic, **17/17 completed, 0 errors**, ~1.66M subagent tokens |

### Session 251 Handoff Evaluation (by Session 252)

**Score: 1/10 — a ghost session that left exactly one thing, and that one thing worked.**

Session 251 claimed this deliverable on 2026-09-03 and produced nothing: no work commit, no close-out,
no self-assessment, and **no evaluation of Session 250's handoff, which is now permanently unwritten.**
Its claim commit `63bf3d6` was `HEAD` four days later with a clean tree.

- **+1, and it is not nothing.** The Phase 1B stub did its whole job. I lost no time discovering what
  had happened, and I inherited a correctly-scoped deliverable in the session's own words. **Failure
  mode #14's countermeasure worked exactly as designed on the exact failure it was built for.**
- **−.** Everything else. The stub is left standing verbatim and annotated rather than overwritten,
  because erasing it would erase the evidence.
- **Unscoreable and worth recording:** its abandonment is what made the ninth trim legal again (§13.2).
  A session that did nothing improved the ledger's arithmetic more than the two options proposed to.

### Session 250 Handoff Evaluation (by Session 252)

**Score: 9/10.** The handoff I actually inherited, one session further back.

- **What's-next #1 was this session's entire scope**, in one line, with "present it and stop".
- **Gotcha 5 (`command grep`)** — load-bearing in every count published here, sixth session running.
- **Gotcha 1 (a workflow's failed arms return `null` and `[]`)** — I checked the `<failures>` block
  before trusting the aggregate. 17/17 this time, but I would not have known to look.
- **Gotcha 2 (the `CHANGELOG.md` question is settled — do not re-litigate)** — saved a precedent hunt.
- **−1: what's-next #2 was wrong on arrival.** *"The ninth trim is due and still cannot be run
  compliantly."* Measured at Phase 0, it can. Not wrong when written — Session 251's abandonment
  changed it — but it is the third consecutive handoff to carry that sentence unmeasured, and its own
  #2 says *"re-measure at Phase 0"*, which is the instruction that caught it.
- **ROI: very high.** It defined the session and cost three minutes.

### Session 252 Self-Assessment

**Score: 8/10.** The ruling is recorded on re-derived figures, two of the document's load-bearing
premises were falsified before the operator ruled on them, and the session found a live defect in the
apparatus the ruling is about. What holds it at 8 is that I presented a recommendation on G before the
critic had returned, and the critic's evidence went against my reasoning.

**+** **I re-derived instead of quoting, and the two biggest figures had both moved** — the retention
rule is satisfiable, and `K` went 1 → 4. Both would have been inherited as true.
**+** **I found the `--self-test` break and dated it to the commit**, in a session whose subject is
whether the apparatus is worth its cost. It is the strongest evidence on both sides at once.
**+** **I went back to the operator after the ruling** when the critic produced evidence that G's
stated ground was false and that the operator had ratified the mechanism upstream. Re-opening a
decided question is expensive; presenting it once, with the measurement, was right.
**+** **The guard adjudicated me and I let it.** It went red on `95/95`; I made the sentence more
precise rather than adding a `FROZEN` exemption.
**+** **17/17 subagents, zero failures**, after Session 250 lost four of five to a rate limit.

**−** **I recommended declining G on §9's reason without testing it first.** The correlation took one
script. I presented it, the operator ruled, and then the critic falsified the premise — so the operator
ruled twice on one option because I did not measure before recommending. **That is this project's
signature defect committed inside the session that catalogues it.**
**−** **My §13.3 pricing is in bytes, not tokens.** No arm could run a tokenizer. It agrees with
§12.2's token figure by an independent route (6.71× vs 6.92×), and I labelled it — but it is a proxy.
**−** **One of my own measurement arms asserted what §3.2 says without opening it.** A refuter caught
it. I wrote the prompt that let it.
**−** **~1.66M subagent tokens.** Justified — the critic alone changed a ruling — but it is the second
most expensive session in this lineage.

**Against the bar:** S248 falsified the premise the apparatus rests on; S249 showed the premise was
executable. S252's equivalent is showing that **the document's own conclusions had expired in four
sessions** — the rule it called unsatisfiable is satisfiable, the K it measured at 1 is 4, and the
proof it counted as green cannot be trusted.

**What's next.**

1. **The `--self-test` repair — ruled as the next session's deliverable**, ahead of E, D and the CI
   step. Filed in `BACKLOG.md` with the mechanism, the dating, the DONE gate and the VERIFY command.
2. **Then Option E, retroactive** — collapse the three standing prose blocks and make collapse-on-write
   the rule. §11's E criterion applies; §13.3 has the target arithmetic.
3. **Then Option D, widened** to `SESSION_NOTES.md`, `BACKLOG.md`, `CHANGELOG.md` and
   `PROJECT_LEARNINGS.md`, with K expressed in **bytes** against the delivered prefix and stubs
   excluded from K. §13.8 and §13.11 have the ruling and the refinement.
4. **Then the CI step**, running `--self-test` on all nine. It is one line and F depends on it.
5. **Sync the local dashboard.** `~/Development/methodology_dashboard.py` is v2.15.2 against canonical
   v2.17.0; the sync command is in the dashboard's own startup warning. Outside this repo.
6. **`BACKLOG.md`'s plain-language index still renders as four tables**, not one — S250's #5, now one
   fragment worse because I appended a row the same way. Two blank-line deletions.

**Key files.**
- `docs/planning/ledger-budgets-review.md` **§13** — the ruling, the re-derived figures, and **§13.11**,
  the eleven figures in §8/§12/Appendix A that are stale at HEAD.
- `BACKLOG.md` — the new item *"A shard proof has been silently unfalsifiable since Session 249"*, and
  the ledger-budgets row now marked RULED.
- `docs/architecture-history/SESSION_NOTES-pointer-collapse.verify.sh` — `NEW_TABLE` (the literal that
  no longer matches), `C6` (~`def C6`), and `M16`/`M17` at the mutant table.
- `~/Development/methodology/docs/planning/record-budget-reduction-plan.md` and
  `~/Development/methodology/bin/check-handoff:665` — the upstream G ratification and its enforcement.
- `/private/tmp/claude-501/…/scratchpad/measurements-s252.md` — every figure with its command.

**Gotchas.**
1. **The nine-proof loop is not a check on the apparatus.** `bash "$f"` and `bash "$f" --self-test`
   disagree today. Run **both**, and treat the plain loop as necessary, never sufficient.
2. **Editing this file can disarm a proof without failing it.** `5243242` is the worked example: a
   correct prose repair inside a pinned literal turned two mutants into no-ops. **After any front-matter
   edit, run `--self-test`, not the plain loop.**
3. **The ninth trim is legal and the margin is measured, not projected.** With this record written, a
   floor-4 cut (Sessions 252, 251, 250, 249) lands at **854 lines** before the new pointer block —
   **196 lines of headroom** under the 1,050 target, so it stays compliant even at the eighth trim's
   96-line block. This record was sized to that budget deliberately (199 lines against a 320 ceiling).
   **Re-measure before trimming**: the number moves with every close-out, and Session 251's abandoned
   15-line record is what is paying for most of the headroom.
4. **The census guard fires on any numeral within 30 characters of the word "shard"** (`VOCABULARY`,
   `WINDOW = 30`). It caught `95/95` here. Name the file rather than the category; `FROZEN` is a last
   resort and the companion staleness test makes entries permanent work.
5. **`command grep` for every count** — bare `grep` is a `ugrep --ignore-files` wrapper.
6. **`PROJECT_LEARNINGS.md` and `CHANGELOG.md` are REFUSED by a default `Read`** — zero content. The
   exact boundary is 262,144 B, measured.
7. **The Phase 0 dashboard under-reports read-cap risk on this machine.** The local copy is v2.15.2 and
   still measures lines against 2,000; canonical v2.17.0 measures bytes against a token-derived budget.
8. **`gh issue list` is empty by design** until UAT.

### What Session 251 Did
**Deliverable:** Present the outstanding ruling on
[`docs/planning/ledger-budgets-review.md`](docs/planning/ledger-budgets-review.md) §8 — options D, E and F,
and the still-unruled B, C, G and H — to the operator with every figure re-derived at HEAD; record the
ruling; execute nothing (IN PROGRESS)
**Started:** 2026-09-03 18:07 UTC
**Status:** Session claimed. Work beginning.

**ABANDONED — annotation added by Session 252, 2026-09-07.** This session claimed the task and
produced nothing further. Evidence: its claim commit `63bf3d6` was `HEAD` when Session 252 oriented,
four days later, with a clean working tree — no work commit, no close-out, no self-assessment, no
handoff evaluation of Session 250. Nothing above this line was written by Session 252; the stub is
left standing verbatim because that is exactly what Phase 1B exists to leave behind (failure mode
#14). The deliverable it names was carried forward unchanged.

### What Session 250 Did
**Deliverable:** **Fix the three stale per-directory test counts in `README.md` — COMPLETE.**
Operator's words: *"fix the three stale test counts in README.md"*. Each numeral was re-measured
against a fresh `pytest --collect-only`, not pasted from the Session 247 filing. No other work started.

**Started / completed:** 2026-09-03 (UTC). **Commits: three** — `fd1d855` (Phase 1B claim, alone),
`47fcd90` (the fix, with the `BACKLOG.md` row maintenance the file's own "Maintain it" rule requires
in the same commit), and this close-out.

**No `CHANGELOG.md` entry.** `README.md` and `BACKLOG.md` only; `PROJECT_CONVENTIONS.md` §2's gate
(`src/`, `packages/`, `scripts/`, `.github/workflows/`, `tests/` logic) is not met. Checked against
precedent as well as the written rule: four earlier commits removed a `BACKLOG.md` item heading
without touching `CHANGELOG.md` (`7075f7b`, `efc24a6`, `99e9abf`, `bfeb2a7`).

#### What was measured

| `README.md` row | said | collects now | Session 247 filed |
| --- | ---: | ---: | ---: |
| `data_agent_package/` | 207 | **257** | 257 |
| `eval/` | 94 | **157** | 157 |
| `test_llm_json_parity.py` | 16 | **34** | 34 |

Collection reports **1,347** tests; `test_eval_live.py` collects 9, all `live`-marked, so 1,338 run
without credentials — which is the headline sentence at `README.md:151`. **Every row in the block was
re-measured, not just the three**: schemas 99, agents/data 19, agents/intake 155, agents/website 199,
orchestrator 250, ui/intake 32, scripts 109, decoupling 2, vocab guard 6, wiki-citation guard 3,
census guard 25. The block's numerals sum to 1,347. The three filed figures held because no test file
changed between Sessions 247 and 250 — the re-measurement is what established that, at a cost of
under a minute.

**Independent confirmation, partial.** One workflow agent re-ran collection from scratch and
reproduced every row, the sub-split and the total (its per-file breakdown is in the workflow journal,
key file below). **Four sibling arms failed** — a second measurement method, the repository sweep, and
two adversarial critics — on a subagent session limit (*"You've hit your session limit · resets
12:50am America/Detroit"*). The aggregate came back `sweep: null, critics: []`. The sweep and the
critique were then done inline by me; the measurement is independently confirmed, the critique is not.

#### Sweep — every live site stating a test count

`git grep` for count-shaped phrases across the tree, ledgers excluded (`SESSION_NOTES.md`,
`CHANGELOG.md`, `PROJECT_LEARNINGS.md`, `docs/architecture-history/`), then a second sweep by the
NAMES of what is counted (`data_agent_package/`, `test_llm_json_parity`, "repo map"):

- `README.md:151` — the headline; consistent with collection.
- **`docs/wiki/model_project_constructor/Contributing.md:104`** — a **second per-directory census**,
  found only by the name sweep: it counts test *functions* (`def test_`), not collected tests, and
  says so. Measured with the page's own command: `data_agent_package/`, `eval/`, `scripts/` and the
  top-level files are stale, as are its total and its pass/skip sentence. **Filed in `BACKLOG.md` with
  the like-for-like table, not fixed** — a different file, a different denominator, and anything under
  `docs/wiki/` auto-publishes to the live GitHub wiki on commit, which the operator did not ask for.
- `audits/2026-06-10-wiki-vs-code-accuracy-audit.md:417` and
  `executive-summaries/stakeholder-readiness-dossier.qmd:44,75` — dated snapshots stating their own
  session; historical, not live claims.

#### Verification

| check | result |
| --- | --- |
| census guard `tests/test_session_notes_census.py` | **25/25** after each edit (`README.md` and `BACKLOG.md` are two of its four files) |
| nine `docs/architecture-history/*.verify.sh` | **GREEN** before and after |
| full suite | **not re-run** — collection only (1,347); no test file changed; last run S249: 1,338 passed, 9 skipped |
| `README.md` block arithmetic | rows sum to 1,347 = collected; 1,338 + 9 = 1,347 |

### Session 249 Handoff Evaluation (by Session 250)

**Score: 9/10.** Its what's-next #4 named this task in one line, and its gotchas were load-bearing
for a session that touched none of its own subject matter.

- **"Numerals already measured"** — true, and I re-measured anyway, which its own gotcha family
  demands. All three matched. That is the right outcome of a handoff figure: confirmed, not copied.
- **Gotcha 6 (`command grep`)** — used in every count, fifth session running.
- **Gotcha 4 (run the guard AND the proofs)** — followed after each edit.
- **Gotcha 5 (`PROJECT_LEARNINGS.md` is refused by a default `Read`)** — saved a failed read; I used
  `tail` and `head`.
- **Gotcha 7 (`gh issue list` is empty by design)** — saved a question.
- **−1: gotcha 8 was stale on arrival.** *"`master` is 17 commits ahead of `origin/master`"* — measured
  0 ahead, 0 behind at Phase 0; the operator pushed between sessions. Not wrong when written, but a
  push-state fact has a shelf life of one operator action and should be phrased as "re-measure",
  the way its own #2 phrases the ledger size.
- **Missing, not scored:** that `BACKLOG.md`'s header (*"Completed items move to `CHANGELOG.md`"*)
  reads against §2 for a documentation-only close. Cost one precedent check. Also that the wiki
  carries a second census — but that belongs to Session 247's filing, which swept `README.md`'s
  block, not the repository.
- **ROI: high.** About three minutes to read; it removed every decision except the measurement.

### Session 250 Self-Assessment

**Score: 8/10.** The deliverable is complete, verified two ways, and exactly the size it was asked
to be. What holds it at 8 is that the adversarial half of the verification was mine, not
independent, and that a second stale census sits one file over, filed rather than fixed.

**+** **Re-measured, every row, two methods.** Mine and one independent collection pass agree on
all fifteen figures and the total.
**+** **Scope held.** Three numerals plus the same-commit row maintenance `BACKLOG.md` requires of
any session that changes an item; the wiki census was filed with evidence, not edited, because a
wiki edit publishes.
**+** **Swept by name, not by number.** A numeral sweep found nothing; the directory-name sweep found
the wiki's second census immediately.
**+** **Guard and proofs after each edit, not once at the end.**
**+** **Checked the `CHANGELOG.md` question against the written rule and against precedent**, and
recorded both, so the next documentation-only close does not repeat the check.

**−** **Four of five verification agents died on a rate limit.** The critique of my own edit was
done by me. The one surviving agent makes the *measurement* independent; nothing makes the
*review* independent. Recorded as such rather than rounded up.
**−** **I typed "fourteen rows" in a draft** of the `BACKLOG.md` row — a hand count of rows, in a
session about hand-typed counts — and deleted it before commit. Caught, but it was written.
**−** **The plain-language index in `BACKLOG.md` renders as three tables, not one.** Sessions 247
and 248 each appended their row after a blank line, so the `README.md` row and the ledger-budgets
row each render as a header-less one-row table; my new row sits in the same shape. Deliberately not
fixed — outside the ask — and named in what's-next.
**−** **~97k subagent tokens bought one confirmed measurement** and four failures.

**Against the bar:** S249 corrected a false premise at every live site and found the machinery that
would have re-minted it. S250 is a three-numeral fix and belongs at that scale; its one carry-forward
is that the class S247 named — counts nobody derives — has a second instance, in a second
denominator, one file away.

**What's next.**

1. **The operator still owes a ruling on D, E and F** of `docs/planning/ledger-budgets-review.md`
   §8 — unchanged from Session 249's #1. Present it and stop.
2. **The ninth trim is due and still cannot be run compliantly** before that ruling. The ledger is
   over the >1,500-line trigger; re-measure at Phase 0.
3. **The census guard's `SPELLED`/`ORDINAL` maps stop at sixteen** — S249 #3, still unfiled.
4. **NEW: the wiki's `Contributing.md` test-function census** — filed in `BACKLOG.md` with the
   measurement and the command. One paragraph; publishes to the live wiki on commit.
5. **`BACKLOG.md` plain-language index** — delete the blank line before the `README.md` row and the
   one before the *"Are the ledger budgets"* row so the three fragments render as one table. Two
   deletions, next time that file is touched.
6. **The `post-merge` hook**, then the two delivered plans, then the docs toolchain ceiling — S249 #5.

**Key files:**
- `README.md:100`, `:101`, `:114` — the three corrected rows; `:151` — the headline sentence they
  must agree with.
- `BACKLOG.md` — the rewritten item *"`README.md`'s test counts are hand-typed and will drift again"*
  (verification command inside) and the new item for the wiki census (like-for-like table and
  command inside). Both have plain-language rows.
- `docs/wiki/model_project_constructor/Contributing.md:104-108` — the second census and its own
  `grep` command, annotated *"997 at time of writing"*.
- Workflow journal with the independent measurement's per-file breakdown:
  `~/.claude/projects/-Users-rmsharp-Development-model-project-constructor/f527cbf0-9aef-4136-b1be-ba98dd6419d4/subagents/workflows/wf_6e3922f5-499/journal.jsonl`.

**Gotchas:**
1. **A workflow's failed arms return `null` and `[]` in the aggregate** — indistinguishable from
   "searched, found nothing". Read the notification's `<failures>` block before treating a result as
   coverage. Subagent limits reset on a clock; the arms can be re-run after it.
2. **`BACKLOG.md`'s header says completed items move to `CHANGELOG.md`; §2 says documentation-only
   work earns no entry.** §2 is the written gate and four earlier doc-only closes followed it. Do not
   re-litigate; do not edit the header without an operator ruling.
3. **Two censuses, two denominators.** `README.md` counts collected tests; the wiki counts `def test_`
   functions. A parametrized function is one of the latter and many of the former. Never reconcile
   one to the other's figures.
4. **Anything under `docs/wiki/` publishes on commit** via `.githooks/post-commit`. A one-paragraph
   wiki count fix is an outward-facing change.
5. **`command grep` for every count** — bare `grep` is a `ugrep --ignore-files` wrapper (S249 #6).

### What Session 249 Did
**Deliverable:** **Option A of [`docs/planning/ledger-budgets-review.md`](docs/planning/ledger-budgets-review.md) §8 — COMPLETE.**
The false read-cap premise is corrected at every live site; every frozen copy is left alone and
marked unrepairable in the live copies. **No trim, no re-tuning, nothing ruled** (§9 sequencing:
A lands BEFORE the ninth trim; `SESSION_RUNNER.md` FM #18). No other work started.

**Started / completed:** 2026-08-26 (UTC). **Commits: five** — `b1d761f` (Phase 1B claim, alone),
`5243242` (the corrections), `5bf79a6` (the site the first pass missed), `7df555b` (acting on the
adversarial review), and this close-out. **Operator this session:** *"go"*, then a question about
where §8/§9 live, then *"A"*.

**`CHANGELOG.md` entry written** — `PROJECT_CONVENTIONS.md` §2 gates on `src/`, `packages/`,
`scripts/`, `.github/workflows/` or **`tests/` logic**, and this session changed `tests/` logic. The
prose corrections alone would have earned none; checked against the written rule, not recalled.

#### What a `Read` past the cap actually does — measured, three regimes, not one

All eight archives probed with a default `Read`. **I ran three of these first-hand** (marked ✎); the
other five were delegated and every line/byte count was re-derived by me before publishing.

| archive | lines | bytes | default `Read` |
| --- | ---: | ---: | --- |
| `…through-S216` | 24,590 | 4,074,951 | **REFUSED** ✎ — `File content (3.9MB) exceeds maximum allowed size (256KB)`, **zero content** |
| `…S224-through-S221` | 933 | 69,814 | PARTIAL, lines 1–752 of 934, 26,374 tokens |
| `…S231-through-S228` | 976 | 69,921 | PARTIAL ✎, lines 1–766 of 977, 27,077 tokens, cap 25,000 |
| `…S235-through-S232` | 1,057 | 79,707 | PARTIAL, lines 1–732 of 1,058, 30,683 tokens |
| `…S220/S227/S238/S241` | 804/790/644/792 | 63,757/58,000/47,692/57,269 | whole (S227 ✎) |

**Three regimes, and the middle one is the only one anybody had described.** Under the token cap a
`Read` returns an announced `PARTIAL view` naming the overage and the next page; past a separate
**byte** ceiling it is refused outright and returns nothing. Nothing is ever silent, and
`offset`/`limit` reach every line in both cases. **So "the seven newer ones read whole today" was
false — and the census guard COMPOSED and REQUIRED that sentence.**

#### The premise was executable, not just prose — and that is the finding

- **`tests/test_session_notes_census.py` required two of the false sentences** (`:261`, `:267`).
  The guard derives line counts from disk and cannot derive tokens, so it would have held
  `BACKLOG.md` **red against the true sentence and green against the false one.**
- **`"read_cap": 2000` is a hand-declared constant in three write-once proofs.** `L12/cap` fails a
  cut whose shard's LINE count reaches it, with the message *"truncates in silence"*. The S235
  proof's arm **passes** — 1,057 < 2,000 — certifying a file that a default `Read` cannot deliver.
  Pinned by `L10`; unrepairable.
- **The ninth trim is mechanically forced to mint a NEW frozen falsehood** unless five things change.
  `BACKLOG.md`'s read-cap item now names all five (below, gotcha 2).

#### Verification

| check | result |
| --- | --- |
| nine `*.verify.sh` | **GREEN** before, after each of the three passes, and at commit |
| census guard | **25/25**, and it went **RED twice on me** during the work — both times correctly |
| full suite | **1,338 passed, 9 skipped** — unchanged; no test added or removed |
| §11 completion criterion | met; **and shown to be too narrow** — it missed a live site (learning #216) |
| wide re-sweep, both claim families, whole tree | no live file asserts the premise |
| `L11`'s three `POLICY` literals | all still match `CLAUDE.md` verbatim — **S248's dragon 2 does not bind** |

#### Where I was wrong, and what caught it

1. **I missed `docs/planning/repository-rename.md:299`** — a live table cell telling the reader the
   S216 archive *"truncates at 2,000 with no marker"*. My own sweep listed the file and I did not
   drill into it. Found by an independent inventory; **the plan's own VERIFY grep cannot match that
   phrasing either.**
2. **I restated a measured count in three live files** — in the session whose subject is figures
   that were true once. Fixed: one authority, two definite negations that carry no number.
3. **I wrote "nothing in this repository can measure the agent harness"** and then measured a byte
   proxy accurate to within 3.4% at three cuts. The fleet tool had re-denominated onto exactly that
   proxy **38 minutes before my first commit** (`methodology@9e71f83`).
4. **A first draft wrote around the guard's trigger word** — "archived file" where "shard" was
   natural — and passed clean. Rewritten honestly, the scan went red and named three numbers.
5. **`5243242`'s message cites `:264`; the composer is at `:267`.** A hand-typed coordinate in the
   anti-hand-typed-figure commit. Corrected in `7df555b`'s message, not by rewriting history.

#### One filed defect refuted, with evidence

**Session 248's defect #9 does not hold.** `CLAUDE.md:82`'s *"`READ_CAP_WATCHED` is an exact-path set
containing none"* — "none" takes **the shards** as antecedent, and the set contains none of them, so
the sentence was TRUE. An independent adjudication reached the same verdict after arguing the
strongest case against it. The real defect was **elision**: it was the only copy in the project that
dropped the complement, which is what induced the false filing. It now carries it. **The live-defect
count S248 published is nine, not ten.**

### Session 248 Handoff Evaluation (by Session 249)

**Score: 9/10.** It set this session up completely: the deliverable, the sequencing, the method, and
the two traps. I did not have to decide anything about *shape*, only about *content*.

- **"Option A must be sequenced BEFORE the ninth trim, never during it."** Correct as a rule, and it
  is why this session ran clean. **Its stated reason was wrong** — see below — but the instruction
  was right for a different reason it did not give: a trim would have had to declare the new banner
  text and the `read_cap` constant in the same commit.
- **"Do not inherit a single number without re-deriving it."** Load-bearing. Re-deriving the
  inventory is what found `CLAUDE.md:82` and the census guard's `:261`, neither of which is in §1.4's
  six sites — and §1.4's own table says **five** live files while enumerating four, which is the tell.
- **Gotcha 6 (`command grep`)** — used in every count published, fourth session running.
- **Gotcha 2 (the guard scans four files; `SESSION_NOTES.md` is not one)** — exactly right and it
  shaped where I put things.
- **The §11 per-option completion criteria** made "done" decidable in advance. That is the single
  most reusable thing in the document.
- **−1, and it is the same class the handoff warns about.** **Dragon 2 is false as stated:**
  *"`L11/declared` and `L11/figure` read `CLAUDE.md:81`'s exact sentence, so correcting the premise
  obliges the next trim's proof to declare the new text."* Measured — `POLICY`'s three literals stop
  before the parenthetical Option A removes, and all three still match verbatim. The real obligation
  is `L12`'s, one assertion over, and no handoff mentioned it. **A dragon that names the wrong
  assertion sends the next session to guard the wrong thing.**
- **ROI: very high.** ~4 minutes to read; it defined the whole session.

### Session 249 Self-Assessment

**Score: 8/10.** The deliverable is complete and verified, the premise is gone from every live site,
and the two findings that outlast it — the guard enforcing a falsehood, and the machinery that would
have minted a ninth one — are worth more than the text repair. What holds it at 8: **the first pass
was incomplete and I did not catch that myself**, and three of my own errors were the exact defect
classes this session exists to remove.

**+** **I measured instead of inheriting.** Eight probes, three regimes, every line and byte count
re-derived by hand; three probes run first-hand including the one that overturns live prose.
**+** **I found the executable copies.** Option A was scoped as prose; the two things that mattered
were a test that *required* the false sentence and a constant inside three write-once proofs.
**+** **I let the guard adjudicate rather than routing around it** — and published the fact that my
first draft had routed around it.
**+** **The guard is stricter than I found it**: one composed expectation added (derivable, so
composed rather than exempted), the obsolete exemption retired, two honest classifications added.
**+** **I refuted a filed defect with evidence and argued the case against myself first**, rather
than inheriting a count of ten.
**+** **I annotated rather than rewrote** another session's arithmetic (`§8`'s `7.3` records).
**+** **I checked `L11` instead of trusting the dragon**, which is why the ninth trim's real
obligation is now written down.

**−** **My inventory missed a live site my own sweep had listed.** I drilled into five files and not
the sixth. An independent pass found it; so did a second one, independently.
**−** **I restated a measured count in three live files** — the defect class this project reports
more than any other, committed inside the correction of an instance of it.
**−** **I published "nothing in this repository can measure the agent harness"** without spending the
ten minutes that falsify it, in a session whose thesis is that unmeasured claims rot.
**−** **I typed a line number into a commit message and it was wrong** (`:264` for `:267`).
**−** **`CLAUDE.md` grew 25,997 → 27,600 bytes**, further past the ~25 KB budget its own line 101
cites. Option A's text is load-bearing, but I did not try to pay for it elsewhere.
**−** **Two adversarial workflows cost ~2.8M tokens** to produce six acted-on findings. Worth it, but
the inventory sweep largely re-derived what I had already done by hand.

**Against the bar:** S247 built the first always-on guard over the live files; S248 falsified the
premise the whole apparatus rests on. S249's equivalent is showing that the premise was **executable**
— that the guard written to keep prose true was requiring a falsehood, and that the trim template
would have manufactured another one — and closing both without touching a frozen byte.

**What's next.**

1. **The operator still owes a ruling on D, E and F.** A is done; B–H are open. §9 recommends
   **D, then E, and *consider* F**. Two new inputs since S248 wrote that: **the 1,050 target is
   INSUFFICIENT, not merely unjustified** (a compliant trim yields 80,349 B against a ~56,750 B
   one-`Read` budget), and **a byte budget is now derivable in-repo**, which is exactly what D needs
   and what S248 assumed impossible. **Present it and stop** ([#184](PROJECT_LEARNINGS.md)).
2. **The ninth trim is due** (`SESSION_NOTES.md` is over the >1,500 trigger — re-measure at Phase 0)
   and still **cannot be run compliantly**. Do not run it before the ruling.
3. **The census guard's `SPELLED`/`ORDINAL` maps stop at sixteen** (`tests/test_session_notes_census.py`)
   — a seventeenth shard raises `KeyError`. Carried from S248 #3, still unfiled, one line.
4. **`README.md`'s three stale per-directory test counts** — S247's #2, numerals already measured.
5. **The `post-merge` hook**, then the two delivered plans, then the docs toolchain ceiling. The
   oldest unblocked item is the dialect-gate one, not the hook.

**Key files:**
- `docs/planning/ledger-budgets-review.md` — §8 options, §9 recommendation, §11 per-option DONE
  criteria. **§1.4's site list is incomplete** (it enumerates four live files and its own table says
  five; it omits `CLAUDE.md:82`, the census guard and `repository-rename.md:299`).
- `BACKLOG.md`, the read-cap item — now the **single authority** for which archives read whole, the
  five machinery changes the ninth trim owes, the stale glob recommendation, and the upstream
  re-denomination.
- `tests/test_session_notes_census.py` — composers for the two re-cut sentences; `FROZEN` for the
  two classifications; `SPELLED`/`ORDINAL` for the latent `KeyError`.
- `docs/architecture-history/SESSION_NOTES-S241-through-S239.md.verify.sh` — `POLICY` (L11's three
  literals, **unaffected**), `SIZES["read_cap"]`, the `SIZE_PROSE` banner row, `L12/cap`, `M63`.
- `~/Development/methodology/tools/methodology_dashboard.py` — **outside this repo**, already
  re-denominated (`9e71f83`). The local `~/Development/methodology_dashboard.py` is stale v2.15.2.

**Gotchas:**
1. **`CLAUDE.md:81` no longer justifies its own numbers, deliberately.** They stand unchanged and
   unjustified pending the ruling. Do not "restore" a rationale; do not re-tune them outside a
   session ruled for B–E.
2. **A ninth trim must change FIVE things or it mints a permanent falsehood** — the `SIZE_PROSE` row
   keyed to `read_cap`, the `SIZES` key, the `L12/cap` arm, the `M63` mutant (built on the banner
   string in **four** places), the `--self-test` print — **and the banner itself**. Copying the
   template forward is the failure mode.
3. **The census guard triggers on proximity to the word "shard".** Rewording around it leaves text
   unchecked and the suite cannot tell. Write the natural word. If a flagged number is derivable,
   **compose it**; an exemption is the last resort.
4. **Run the guard AND the nine proofs.** The proofs read prose from their own trim commits and
   cannot see live edits — a green loop after a commit proves nothing about prose (S248 gotcha 3,
   confirmed again here).
5. **`PROJECT_LEARNINGS.md` and `CHANGELOG.md` are REFUSED by a default `Read`** — zero content, not
   truncation. `grep` them or use `offset`/`limit`. `CLAUDE.md`'s pointer now says so.
6. **`command grep` or `git grep` for every count** — bare `grep` is a `ugrep --ignore-files` wrapper.
   Load-bearing again this session.
7. **`gh issue list` is empty by design** — the product is feature-complete; the tracker opens at UAT.
8. **`master` is 17 commits ahead of `origin/master`** — measured with `git fetch` + `git rev-list
   --count origin/master..master`. The push is the operator's call.
9. **Do not re-discover the frozen falsehoods.** Seven of eight shard banners assert the old cap and
   three are provably wrong today. They are write-once. Leave them.

