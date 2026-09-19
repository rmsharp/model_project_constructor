# Project Conventions

**Project-local supplement to the iterative methodology.** This file documents conventions that are specific to `model_project_constructor` and are not part of the upstream methodology framework. Upstream framework files in `docs/methodology/` (README.md, HOW_TO_USE.md, ITERATIVE_METHODOLOGY.md, `workstreams/*.md`) are imported material and must not be edited from within this project.

---

## 1. Inward vs outward documentation

The wiki is the outward-facing documentation; all other documentation in the repo root and `docs/` is internal to the iterative methodology.

**Outward-facing:** `docs/wiki/model_project_constructor/*.md`. Audience is users and implementers of the generated project. Written in present tense, production-shape language. Freshness-tracked — pages should describe current behavior of the shipped pipeline.

**Inward-facing:** everything else — repo-root `.md` files (`README.md`, `CLAUDE.md`, `CHANGELOG.md`, `BACKLOG.md`, `ROADMAP.md`, `SESSION_NOTES.md`, `SAFEGUARDS.md`, `SESSION_RUNNER.md`, `OPERATIONS.md`, `TROUBLESHOOTING.md`), the `docs/methodology/` framework, `docs/planning/` (and its archive), and any other `docs/` subdirectory except `docs/wiki/`. Audience is the maintainer and the iterative methodology's AI agents. Mixed freshness — some files are append-only historical logs (`SESSION_NOTES.md`, `CHANGELOG.md`), some are freshness-tracked state (`BACKLOG.md`, `ROADMAP.md`), some are point-in-time archives (see §3).

---

## 2. Three-surface split for "what changed"

Three files answer three different questions. Each file carries a per-file opener pointing to the other two.

| File | Audience | Cadence | Purpose |
|---|---|---|---|
| `CHANGELOG.md` (repo root) | Maintainer | Per action — every commit, and every non-commit action (2026-09-19; *was* per behavior change) | Commit-linked ledger. Authoritative; when any summary disagrees, this file wins. The rules are `docs/methodology/FRAMEWORK_APPARATUS.md` §The Action Ledger, which the file's own header points at; the behavior-change gate below is superseded and kept as history. |
| `docs/wiki/model_project_constructor/Changelog.md` | Users and implementers | Release-shaped (episodic) | Audience-facing release summary. Grouped by implementation phase, not by session. Tone may evolve; detail level is curated. |
| `docs/wiki/model_project_constructor/Evolution.md` | Onboarding readers, code-sharing context | User-requested only | Decision-arc narrative — "how the application grew from original concept to current state." Full rewrite each time; see §4. |

**Why three surfaces.** `CHANGELOG.md` answers *"what was committed?"*; `wiki/Changelog.md` answers *"what's new for me?"*; `wiki/Evolution.md` answers *"why is it like this?"*. A reader joining the project has no digestible narrative in the first two — the session log is too raw, the user changelog is too summary. Evolution fills that gap without polluting the other two.

**SUPERSEDED, 2026-09-19 (operator decision (b), Session 259, BL-57 phase P11) — the rest of this
section is history, not a live rule.** The cadence is no longer this project's to set: `CHANGELOG.md`
follows the methodology's ledger rules, `docs/methodology/FRAMEWORK_APPARATUS.md` §The Action Ledger,
which `bin/sync` keeps current and which the ledger's own header now points at. **Every commit carries
its own tagged entry**, and so does every action that leaves no commit; the only exemption is a session
whose diff is empty and that took no action. Entries are `### YYYY-MM-DD · [tag] …` under a `## YYYY-MM`
heading, newest on top. The decision names the two rulings below, both marked SETTLED, and supersedes
them with the rest: they settled *which changes earn an entry*, a question the new rule does not ask.
Nothing already written is retrofitted — see `CLAUDE.md` for what the legacy part of that file holds
and where new entries go. The three paragraphs are kept verbatim so the reasoning stays readable.

**CHANGELOG cadence** *(superseded — history)*. A session earns a `CHANGELOG.md` entry when it changes shipped code — `src/`, `packages/`, `scripts/`, `.github/workflows/` — or adds/changes `tests/` test logic. Documentation-only sessions (the wiki, the rest of `docs/`, the methodology framework, and project-state files such as `SESSION_NOTES.md`, `BACKLOG.md`, `ROADMAP.md`), and sessions whose only code-tree touch is non-behavioral (fixture data, docstring or path strings), are recorded in `SESSION_NOTES.md` and — where user-relevant — surfaced through the wiki `Changelog`/`Evolution`; they do not get a `CHANGELOG.md` entry. A multi-session feature or overhaul may be recorded as a single entry spanning its sessions, dated by its completion/landing commit. *(This refined the earlier "every completed session adds an entry" rule in Session 149: Sessions 114–148 had drifted under the per-session rule — the shipped-code work in that span was backfilled to `CHANGELOG.md` and the documentation-only sessions were left in `SESSION_NOTES.md` per this gate.)*

**`.github/workflows/` is INSIDE the gate: SETTLED, do not re-ask (operator ruling, 2026-08-25,
Session 244)** *(superseded 2026-09-19 — history; there is no gate to be inside now)*. A workflow change alters what this project publishes and when — Session 243 changed
the conditions under which the **public** tutorial site deploys — and that is an outward-facing
behaviour change of exactly the kind this ledger exists to record. **This is a directory test, not a
judgement test:** a change to `ci.yml` earns an entry as surely as one to `publish-tutorial.yml`,
and that uniformity is the whole reason this ruling was preferred over the narrower "only when it
changes what or when something publishes" form, which would reintroduce a per-change adjudication.

**The written rule and the precedent had been pointing opposite ways since Session 149.** Measured
at Session 244: **4** commits in this repository's history touch `.github/` without touching any
gated directory. The two clean pre-amendment cases, `a7508cb` and `4f85a3e` (both 2026-04-20), each
**took** a `CHANGELOG.md` entry in their own commit — but both predate the Session 149 refinement
that produced the directory list above, so the list had never actually been tested against a
workflow-only session until Session 243. Session 243 was given **no** entry, which was correct under
the rule as written then (§1 and the Session 223 ruling both make the written rule beat precedent);
its entry was added **retroactively** under this amendment, dated by its landing commit `9522bbd`,
as an append rather than an edit per §1.

**Measurement-only sessions: SETTLED, do not re-ask (operator ruling, 2026-08-17, Session 223)**
*(superseded 2026-09-19 — history; a measurement-only session now records its action like any other)*. A session that only *runs* the live eval harness — measuring providers, probing variance, reproducing a defect — and changes no `src/`, `packages/`, `scripts/`, or `tests/` logic **does not get a `CHANGELOG.md` entry**. The written gate above is correct as it stands; **Session 216's entry was the deviation, not the precedent.** Do not backfill S216, and do not amend it — `CHANGELOG.md` is an append-only historical ledger (§1), so an entry that should not have been written stays written. Sessions 219, 220, 221 and 222 each flagged this as an unresolved convention-vs-precedent conflict and each correctly followed the written rule; the ruling exists so a fifth session does not spend the same paragraph re-litigating it. The measurement itself is recorded in `SESSION_NOTES.md` and, where it changes what a user should believe about the pipeline, in the wiki `Changelog`/`Evolution`.

---

## 3. Planning-doc archive convention

**Active plans live at `docs/planning/`.** When a plan's primary scope is delivered, move it to `docs/architecture-history/`.

**Tiebreaker rule.** A plan is archive-eligible when its primary scope is delivered, regardless of optional or deferred follow-ups. A plan returns to archive when the final optional scope ships *or* is formally descoped. This prevents a plan from sitting in `docs/planning/` indefinitely because one optional item is still pending.

**Banner on every archived document.** Prepend at the top of each moved file:

```markdown
> *This document is a concept-era artifact preserved for design archaeology. It describes the system as designed on YYYY-MM-DD and may not reflect current implementation. For current state, see `docs/wiki/model_project_constructor/Evolution.md` (design-decision arc) and the code itself (authoritative). See `PROJECT_CONVENTIONS.md` for archive scope.*
```

Replace `YYYY-MM-DD` with the date the document is moved (not the date it was written).

**The banner tracks its template; it is NOT part of the frozen record (operator ruling, Session 240).** The banner is project-added boilerplate, so when its target moves, **every deployed copy is re-pointed in the same commit that moves the target.** Session 147's precedent already requires each deployed copy to be byte-identical to the template above, and that invariant is only maintainable if the copies track it. The repository rename (Session 233) is the worked example of the failure: Phase 4 updated this template and **none** of its copies, leaving 21 dead in-repo banner pointers across 20 files, plus 2 more lines in `CHANGELOG.md`'s preamble — 23 in all, re-pointed in Session 240. Nothing caught it because `repository-rename.md` §7.2 exempted `docs/architecture-history/` and `CHANGELOG.md` **wholesale**, on §3.1's rationale that they are frozen historical records. That rationale is true of their *entries* and false of a banner and a preamble, which record nothing and **navigate** — an exemption is only as fine-grained as the assertion traded for it (learning #135). **One documented exception to byte-identity:** `bedrock-testing-enablement.md` appends a document-specific sentence inside its banner, naming where its still-useful reference tables were carved forward. Text after `for archive scope.` is the document's own; only the template portion tracks.

**Scope of archive.** `docs/architecture-history/` holds planning documents, the repo's concept-era `initial_purpose.txt`, and equivalent point-in-time artifacts. It is **not** a graveyard — archived documents remain publicly linkable as primary-source archaeology. The banner is the signal; the location is secondary.

**What does *not* move.** Freshness-tracked state (wiki pages, `BACKLOG.md`, `ROADMAP.md`), append-only logs (`SESSION_NOTES.md`, `CHANGELOG.md`), and active plans (whose primary scope is still being delivered).

**Ledger shards are the one exception (Session 222).** The *live* append-only log never moves — but a **frozen shard of its retired records** does, as `<STEM>-through-<CUTKEY>.md` beside a `<same>.verify.sh` proving the move was byte-for-byte lossless. This is a size remedy, not an archaeology judgement: a ledger past the agent read cap comes back as an **announced partial view** on every `Read` — the cap is denominated in tokens rather than lines, the notice names the overage and the next page, and past a separate byte ceiling the read is refused outright rather than trimmed. Nothing is dropped in silence (measured Sessions 248–249; reproduction in `docs/planning/ledger-budgets-review.md` Appendix A). A shard therefore does **NOT** carry the concept-era banner above — that banner says "describes the system as designed on YYYY-MM-DD", which is false of a session log — it carries its own banner naming its record count, its session span, and the fact that nothing below it was altered. **Nine instances so far**, and the naming rule above bent at the second: `SESSION_NOTES-through-S216.md` (Session 222, Sessions 216→1), `SESSION_NOTES-S220-through-S217.md` (Session 224, Sessions 220→217), `SESSION_NOTES-S224-through-S221.md` (Session 228, Sessions 224→221), `SESSION_NOTES-S227-through-S225.md` (Session 231, Sessions 227→225) `SESSION_NOTES-S231-through-S228.md` (Session 235, Sessions 231→228), `SESSION_NOTES-S235-through-S232.md` (Session 239, Sessions 235→232) `SESSION_NOTES-S238-through-S236.md` (Session 242, Sessions 238→236), `SESSION_NOTES-S241-through-S239.md` (Session 245, Sessions 241→239) and `SESSION_NOTES-S248-through-S242.md` (Session 256, Sessions 248→242). The `<STEM>-through-<CUTKEY>.md` form is only unambiguous for the FIRST shard, whose span is open at the bottom — a second shard named `-through-S220` would read as "everything through Session 220", which is false, since 216→1 sit in the earlier file. **A non-first shard therefore takes the range form `<STEM>-<NEWEST>-through-<OLDEST>.md`.** This is a deliberate departure, recorded here so a later trim copies the rule rather than the first filename — **the third, fourth, fifth, sixth, seventh, eighth and ninth trims all did**, which is the evidence the note works rather than merely reads well. A corollary of write-once: shard names are load-bearing routing information, and the set of them is only correct when read together — no single shard is authoritative about where Session N lives. The canonical `methodology_trim.py` deliberately refuses `SESSION_NOTES.md` (no generic grammar fallback), so the shard is hand-built and its proof ships a `--self-test` that proves the proof itself can fail.

**A trim's pointer block is a TABLE ROW, never prose — collapse-on-write (operator ruling,
2026-09-07; executed retroactively in Session 254).** Every trim leaves a pointer record in the live
ledger's front matter saying what moved, where it went, and what proves it. For eight trims that
record was a prose block, and the front matter became the half of the file that grows: measured at
`docs/planning/ledger-budgets-review.md` §13.3, a prose block cost ~6,110 B per trim against ~117 B
for a table row, and by the eighth trim those blocks were 33% of everything a session reads before
it opens a single record. **The rule now: a trim adds one row to the table in the front matter, and
the trim's rationale — what it argued, measured, swept or rejected — goes in that session's own
record instead.** Session 254 applied it backwards as well as forwards, replacing the three blocks
still standing; the ruling is `docs/planning/ledger-budgets-review.md` §13.1 (Option E, ahead of
Option D, on §13.3's arithmetic) and the mechanism is §8 row E. Two consequences worth stating
because they are easy to get wrong. First, **the table IS the routing table**: its `archived` column
tiles the whole session history with no gap and no overlap, so a session is placed by reading the
row whose span contains it, and the prose routing clauses that used to state the same thing were
deleted rather than kept in parallel. Second, **the rule is asserted, not announced** — `R8` in
`docs/architecture-history/SESSION_NOTES-pointer-collapse-S254.verify.sh` reads the WORKING TREE and
goes red if a prose pointer block, or a member of the positional "the N blocks below are frozen"
family, ever reappears in the front matter. That is deliberate: this convention had no enforcement
for eight trims, and every block written under it went stale without a single proof noticing.

**SESSION_RUNNER.md references to `docs/planning/` are unchanged by this convention.** The runner points to `docs/planning/` as the canonical location for *active* plans; the archive move is a retrospective action for plans whose work is done.

---

## 4. Evolution.md update discipline

The Evolution page is rewritten in full on request, not maintained incrementally. This section is the discipline for every rewrite.

### 4.1 Trigger

User-requested only. No scheduled cadence. Typical triggers: sharing the codebase with another developer, preparing a current-state assessment, or reaching a milestone worth narrating.

### 4.2 Full rewrite, not incremental edit

Every rewrite produces the page from scratch. Incremental edits are explicitly not the model — the narrative arc changes as the project evolves, and stitching new sections into an old arc produces a disjointed document.

### 4.3 Source material for each rewrite

- **`CHANGELOG.md`** — the completeness checklist. Every session entry since the prior rewrite (or since project inception on rewrite #1) must be accounted for: either incorporated into the arc, or listed in the deliberately-omitted appendix (see §4.5).
- **`SESSION_NOTES.md`** — the rationale source. Where CHANGELOG says *what*, SESSION_NOTES explains *why*. Use it to recover the design-discussion context behind each decision.
- **The code itself** — authoritative on current shape. When SESSION_NOTES and the code disagree, the code wins.

### 4.4 Banner on every rewrite

Prepend at the top of `Evolution.md`:

```markdown
> *Last updated: YYYY-MM-DD (commit `<short-sha>`, after Session N). This page is a full-rewrite synthesis — not continuously updated. For commits since this date, see `CHANGELOG.md` (maintainer) or `git log`.*
```

Use the 7-character short-sha form. Update all three placeholders (`YYYY-MM-DD`, `<short-sha>`, `Session N`) on every rewrite.

### 4.5 Deliberately-omitted appendix

End every rewrite with a short appendix listing sessions intentionally excluded from the arc. Format: session number, one-line summary, reason for omission. This prevents a reader from wondering *"was Session X forgotten, or left out on purpose?"* — the appendix answers.

### 4.6 Diff-against-prior discipline (rewrite #2 onward)

Before committing rewrite #2 or later, read the prior rewrite end-to-end and note what changed in the arc (not just what's new). The page evolves deliberately; unexplained disappearances of earlier framing are a regression signal.

### 4.7 Review gate

Evolution rewrites use an **explicit review gate**, unlike all other sessions in this project:

- The rewrite session writes the draft, verifies it against §4.3 sources, and **stops before committing**.
- The operator reviews the draft interactively.
- The session commits only after explicit approval.

**Why the gate is here and nowhere else.** Evolution is outward-facing and persistent between rewrites. Errors are audience-visible and can hide for months before the next rewrite catches them. The review cost (one round-trip) is small relative to the audience-visibility risk. Every other session in this project continues the autonomous-commit pattern.

---

## 5. Read budgets for the mandated-read files

**Operator ruling, 2026-09-10 (Session 255) — Option D of `docs/planning/ledger-budgets-review.md`,
widened from `SESSION_NOTES.md` to the mandated-read files; narrowed by the operator on 2026-09-14
(Session 257).** The read budget covers `SESSION_NOTES.md`, `BACKLOG.md` and `PROJECT_LEARNINGS.md`.
It replaces the line-count retention rule, which governed a quantity no session reads by.
`tests/test_read_budget.py` holds budgets 1–4 below, and the satisfiability of budget 5, against
the working tree on every CI run; budget 5's thresholds are enforced at a trim, by that trim's
proof. **Nothing checks the fire threshold between trims**, so a Phase 0 that sees
`wc -c SESSION_NOTES.md` above it knows a trim is due. The guard also requires each sentence
stating a budget to appear exactly once here and once in `CLAUDE.md`, so a budget cannot be
re-tuned by editing prose alone — the hazard that document's §10 names first.

**`CHANGELOG.md` is outside the read budget.** The operator's ruling of 2026-09-14 was *"Rule (c) for
CHANGELOG.md — take it off the read budget"* — remedy (c) of the `BACKLOG.md` item that filed it —
given because the file is never read whole, only searched for something, and even then what is
found is not kept in the session. What a default `Read` of it delivers therefore decides nothing, and
its size is no longer a defect. **The ruling names this file alone:** `PROJECT_LEARNINGS.md` is also
searched rather than read whole, and its own item offers a like remedy, (d), but it stays in scope —
that document's §13.8 ruled it in — until the operator rules on it. `CHANGELOG.md` stays an
append-only log (§3). The synced dashboard still watches it for the read cap (`READ_CAP_CLASS_A`);
under this ruling that flag is expected, and the dashboard is not edited here.

**What one default `Read` delivers — measured in Session 255; harness behaviour, not a contract.**

- More than 262,144 bytes: refused, zero content. A file of exactly 262,144 B still returns a page.
- At most 25,000 tokens: the whole file. Above that: the first `floor(0.85 × 25,000 × L / T)` lines
  of a file of L lines and T tokens — or **0.7** of it when the file's tokens pro-rated to those
  lines' bytes, `T × bytes(page) / B`, exceed the cap. That trigger separated all thirteen probes; a
  head metered over the cap on its own did not. The page is sized by the **whole** file: a dense
  tail shrinks it, and a dense band just past it can trigger the reduced page.
- No tokenizer runs offline, so T is unknown in CI. The guard applies both rules at every ratio from
  its floor up to **2.9 B/token** and keeps the smallest page. Its bytes arm budgets a page as
  **21,250 tokens** at **2.49 B/token**, the lowest whole-file ratio Session 255 measured across the
  four files then in scope (`CHANGELOG.md`'s; the ledger's prose runs ~2.65). That file has left the
  budget and the figure stays: it is below every file still in scope, and a re-tune needs its own
  ruling. The fleet's 2.27 floor was set by another repository's content; here it would have failed
  K=2 at commits where one `Read` delivered two records (that document's §14 has the count).
- The probe runs only inside a session: a default `Read`, whose banner gives the lines delivered and
  the file's tokens; and an explicit `offset`/`limit` `Read` spanning more than the cap, which
  returns the exact token count with zero content, even for a refused file. Reproduction: that
  document's Appendix A and §14. **Re-run it; never quote these figures without it.**

**The budgets.**

1. **Ceiling.** no mandated-read file may exceed **262,144 B** — except `PROJECT_LEARNINGS.md`, declared over it and filed in `BACKLOG.md` as a remediation
   needing its own ruling. The exemption expires by itself: the guard fails the moment the file
   drops under the ceiling, until it is removed from the guard and from this sentence.
2. **Page.** In `SESSION_NOTES.md`, the front matter plus the **2** newest non-stub records must fit in **52,912 B**, and inside the predicted page in lines — a BYTES arm and a LINES
   arm. Both mandated reads (Phase 0, and Phase 3A before the close-out overwrites the claim stub)
   need only the newest non-stub record; K=2 is the operator's ruling, one record of margin and
   context. At all 41 commits since Session 239 two records fit; three fit at a minority (that
   document's §14 has the count). Because the newest records carry the page, this is in effect a
   soft budget on the newest PAIR of records — distinct from the hard per-record cap that
   document's §13.5 declined. **Remedies differ by arm.** A red BYTES arm: the newest records are
   too long — shorten them, moving detail into a planning doc; a trim cannot help, because
   truncation starts at the top. A red LINES arm: the tail is dense (reflowing its long lines widens the page, and so, once the
   file is past the trigger, does the trim that archives it) or the head is (reflow long lines near the top —
   tables, one-paragraph-per-line prose). The guard errs conservative by design, by about 6% on
   this file's prose: a red it raises where a real `Read` would still deliver the records costs a
   shorter record, never a missing one.
   **Every close-out runs `uv run pytest tests/test_read_budget.py --no-cov` before committing**:
   the close-out is the commit that grows the newest record, and the guard models the next
   session's claim stub, at least **1,024 B**, on top of it.
3. **Front matter.** front matter at most **8,192 B** — Session 255's judgment, not part of the
   ruling. It is the part of the page the ledger apparatus writes; at the budget the newest records
   and any claim stub above them keep **44,720 B**, more than the largest such prefix measured at
   those 41 commits, stubs included (44,139 B at `28879a0`). A trim adds one table row to it (§3),
   never prose.
4. **Index.** `BACKLOG.md`'s plain-language index must fit in **52,912 B**, and inside the predicted
   page in lines. Item bodies past the page stay reachable by `offset`/`limit` or `grep`; keeping
   each item's index row current is `BACKLOG.md`'s own rule.
5. **Retention, in bytes.** For `SESSION_NOTES.md`: fire a new trim when the live file exceeds **196,608 B** (192 KiB); cut back to **≤98,304 B** (96 KiB); never retain fewer than **4** non-stub records. This is the canonical trimmer's Class A fire/stop pair — a level with hysteresis.
   The guard checks the rule stays **satisfiable**: that a cut keeping the floor, plus a table row,
   lands under the stop. That document's §3.2 found that failure by hand.

**A stub** is a record with no body, or one whose leading metadata — its run of leading paragraphs
that each open with a `**Field:**` line, read outside fences — still carries a Status line
beginning `Session claimed`: the Phase 1B template in `SESSION_RUNNER.md` §1B, or a variant
(Sessions 193, 226 and 242 each wrote one). It counts toward neither K nor the floor, and the guard
fails if the runner's template is reworded.

**Enforcement is split by when a thing can be checked.** Between trims: `tests/test_read_budget.py`,
which reads files and never git. At a trim: that trim's proof, whose `L11` enforces budget 5 —
fire and target in bytes, the floor in non-stub records, each held against the sentence that states
it. The ninth trim (Session 256) rewrote `L11` to it and re-targeted every inherited operand that
read retired prose, the five `read_cap` sites `BACKLOG.md`'s read-cap item listed among them; later
trims copy that `L11` forward. A budget that changes takes the trim's `L11` with it, and a stale
inherited operand is found the same way: run the proof's declarations against the working tree and
flag each literal present at HEAD and absent now.

**Limits.** The page rules are measured, not documented, and the reduced page rests on six probes of
thirteen. The rule also failed on one real file (an oldest-first table with long head lines), so the
guard predicts a page only for the two files whose head is what a session needs. A default `Read`
that disagrees with the guard is the authority.
