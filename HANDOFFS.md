# Handoff Receipts — durable close-out proof

The cumulative, append-only record of **each session's close-out handoff**, distilled into a
machine-checkable block. It is the durable answer to *"was close-out actually performed, and what
did the session hand its successor?"* — the part of close-out that otherwise lives only in the
transient `SESSION_NOTES.md` (overwritten every session) or the spoken report (which leaves no file
at all).

One `handoff` block per **session** (not per commit), newest on top. The canonical-only
`bin/check-handoff` (copy it into your `bin/` if you want the structural check) asserts each block is
present and structurally complete; the next session's Phase 0 reconcile greps this file for a missing
or still-`pending` receipt and backfills it — that reconcile, not the checker, is the dependable
backstop, so the discipline needs no tooling. Together — a write-step at close-out **and** a
reconcile-on-read backstop — this makes a skipped handoff *detectable* rather than silent.

> **A green `bin/check-handoff` is not a good handoff.** The check verifies presence and structure,
> never semantic quality. Faithfulness is still scored 1–10 by the next session (Phase 3A). A
> well-formed but hollow receipt passes the check and is caught only by that human judgement.

## How to write a receipt

**At Phase 1B (claim the session)** — write the stub block below with `status: pending`, filling what
you can, and commit it with your session-claim commit. This committed `pending` block is the crash
breadcrumb: if the session ends before close-out, the next session's Phase 0 reconcile sees it.

**At Phase 3D (close-out)** — overwrite that block in place to `status: complete` and fill every
field. The block must satisfy all six Minimum Handoff Requirements (`SESSION_RUNNER.md` §3D).

**Naming the acting model (optional).** No new key — `REQUIRED_KEYS` is unchanged, and the fenced
block below stays exactly as documented. When a one-line summary is useful, especially for a
single-tier session where it saves a reader a cross-reference into `CHANGELOG.md`'s per-action
**Model:** bullet (see that file's format section), name the model in this receipt's free-text
prose area — the Format section below documents that area as *"the durable proxy for the Phase 3G
spoken report."* This formalizes what a capability-tiered session already does organically when it
states which tier built which layer and which tier reviewed it; this fork's own first receipt
(root `HANDOFFS.md`, session S1) is the worked precedent. `CHANGELOG.md`'s **Model:** bullet
remains the structured, per-action record; this is a convenience pointer for the session-level
view, not a second schema — and it is fine for both to name the same model on a single-tier
session, since they answer different questions ("what happened, action by action" vs. "which model
ran this session"). A canonical-only `bin/model-report` (copy it into your `bin/` if you want it,
same as `bin/check-handoff`) reads this free-text convention back alongside `CHANGELOG.md`'s
**Model:** bullets and git's `Co-Authored-By` trailers, keeping all three visually separate.

## Format — a fenced `handoff` block

````
```handoff
session: S<N>
date: YYYY-MM-DD
status: <pending | complete>
self_score: <1-10>
predecessor_score: <1-10>
active_task: <current state>
what_was_done: <what you did, including a commit sha — or the literal `pending`>
next_steps: <specific and actionable; never "pick next from backlog">
key_files: <each entry carries a path:line token, e.g. SessionManager.java:245>
gotchas: <traps the next session should watch for>
runtime_smoke: <a run result, or "n/a — docs-only", or "impossible: <reason>"; where .quality-gates.json declares gates, the `quality_ratchet: N/M pass · …` summary line of this session's --run>
changelog_ref: <PR #N, a short-sha, or CHANGELOG.md "<its ### heading>" — never a bare line number, which decays once the ledger is trimmed>
commit: <short-sha — or the literal `pending`>
```
<free-text prose: the durable proxy for the Phase 3G spoken report, plus the +/- self-score breakdown>

Write clean `key: value` lines — no inline `#` comments (a `#` is a literal value character,
as in `changelog_ref: PR #52`). The keys are the six Phase 3D Minimum Handoff Requirements (the sixth
*is* `self_score`) plus `predecessor_score` (the Phase 3A evaluation) and a little metadata. `status`
is `pending` at the Phase 1B claim and `complete` at
close-out; a third value, `reconciled`, is written *only* by a later session's Phase 0 reconcile
when it reconstructs a receipt a crashed session never completed — you never write it yourself.
````

`self_score` and `predecessor_score` are distinct keys so one can never stand in for the other; omit
`predecessor_score` on Session 1 (there is no predecessor to score). `commit: pending` and
`what_was_done: pending` are legal at write time (the receipt ships in the very commit whose sha it
would name); no future session is assigned to fill either in later, so `pending` is a legitimate
resting value for both, not a promise a later session owes.

**A receipt's identity is `session` + `date`, not `session` alone.** `S<N>` is a per-sequence
counter, and one ledger may legitimately merge more than one sequence — a fork and its upstream each
running their own, so two distinct sessions share an `S<N>` by construction. Keep `S<N>` unique
within a sequence if you can (never renumber an already-written receipt to do it — a visible gap
that closes on merge is the lesser defect), but do not treat a repeated id across sequences as
corruption. `bin/check-handoff --all` keys on the pair for this reason.

## Size, and when to archive

handoffs-format: 2 — keep this marker, and bring it across with this section; `bin/status` reads it.

This file gains a receipt every session and nothing removes one, so it grows without bound. The
protocol never asks a session to read it whole: Phase 0 reconciles it against `git log` and checks
the newest receipt, and a session reads that receipt at the top — past the harness's default-read
refusal, with an offset and a limit. Archive it when the trimmer's trigger fires. The tool states the
trigger, and this file names no size of its own.

**Run this rather than estimating it:**

```sh
python3 methodology_trim.py --file HANDOFFS.md --check
```

`--check` evaluates the trigger and never writes. `--write` performs the trim, refuses unless it
can prove the split lossless, and **neither commits nor stages** — it leaves this file modified and
the new shard *untracked*, and leaves the commit to you (`git add HANDOFFS.md docs/archive/`).

An archive is a **shard**: a new frozen file, same format, same newest-on-top order.

- **Path: `docs/archive/HANDOFFS-through-<CUT-KEY>.md`.** Both halves are load-bearing — the
  directory keeps the shard from shadowing this file, and the `HANDOFFS-` prefix is what the
  trigger's own glob looks for. A shard named otherwise is silently invisible to it.
- **This file keeps one short pointer** naming each shard, the span it covers and how many receipts
  it holds — with the command that recomputes those counts, never a hand-maintained number.
- **The shard back-links here and states only facts about itself.** It must not restate a
  forward-looking rule: a shard is frozen, so a rule copied into one cannot be corrected when the
  live rule moves.
- **After a split, anything that enumerates receipts must span both** — `HANDOFFS.md
  $(git ls-files 'docs/archive/HANDOFFS-*.md')` — or it silently counts a shrunken
  population. Enumerate the shards with `git ls-files`, never as a bare glob: zsh aborts a
  command whose glob matches nothing, so before the first split the bare form counts nothing
  at all — the same reason the ledger's audit is written that way.

The reasoning this file shares with `CHANGELOG.md` — how a ledger is read, why the tool is the only
statement of its trigger, and what a split must conserve — is in the *Reading and archiving*
subsection of [§The Action Ledger](docs/methodology/FRAMEWORK_APPARATUS.md#the-action-ledger).
That subsection makes archiving optional for `CHANGELOG.md`; this file keeps its own rule, above —
archive it when the trimmer's trigger fires. Everything needed to *act* is here.

What is specific to *this* file, and gets receipts wrong if assumed:

- **A record is a `handoff` block *plus the prose beneath it*, not the fence alone.** The self-score
  and predecessor-score paragraphs sit outside the fence and belong to the receipt above them. A
  fence-only cut severs every receipt from its own scoring.
- **Archive oldest-first by position, never by sorting on `session:`.** Two independent `S<N>`
  sequences can share one ledger — a fork and its upstream each running their own counter — and
  their numbers collide. The record's identity is **session + date**.
- **A trim leaves the newest-receipt check alone and moves what the older-receipt checks see.**
  Phase 0 reconcile is frontier-based and a structural checker applies the full schema to the newest
  receipt only, so neither is disturbed. Its other passes are not so confined — an answer-slot rule
  reads every receipt below the newest, and a locator-form rule reads every receipt in the file. So
  after a trim, **run the checker against each shard as well**, and recompute any "all N older
  receipts" count from the files rather than carrying it forward.
- **Never trim to zero receipts.** An empty receipt ledger is indistinguishable from a broken one.
- **A shard freezes, with one exception this file needs:** a `commit:` answer slot may still be
  reconciled inside an archived receipt, because that field was always going to be filled by a later
  session. Nothing else in a shard is rewritten.

## Three files, three questions, one shared key

- **`SESSION_NOTES.md`** — the *transient scratchpad*: rich working notes, overwritten every session.
- **`HANDOFFS.md`** (this file) — the *durable receipt*: the distilled, machine-checkable proof that
  the handoff was written. Nothing is ever deleted; when the file is archived, the oldest receipts
  move to a frozen shard (see **Size, and when to archive** above).
- **`CHANGELOG.md`** — the *cumulative action ledger*: *"what was done here, ever?"*, append-only.

The shared key across all three is the commit sha (`changelog_ref` / `commit` here). This file
**distills** the handoff; it does not copy the scratchpad. The belongs-here test: *would the next
session need this block to continue the work without re-reading the whole repo?*

## Citing the gate run — honesty made countable

Where the project declares quality gates (`.quality-gates.json` with at least one gate), a
`status: complete` receipt cites the session's own gate run: paste the summary line
`quality_ratchet.py --run` prints (`quality_ratchet: N/M pass · F fail · U unmeasured · results
<sha12> · manifest <sha12>`) into `runtime_smoke` (or `what_was_done`). The canonical-only
`bin/check-handoff` lints the **newest** receipt for that token when a manifest with gates is present;
the next session's Phase 0 reconcile compares the cited `results` hash and counts against the current
`.quality-gates-results.json` (or re-runs `--run`) and treats a contradiction — a receipt claiming
`6/6 pass` over results that say otherwise — as the same class of finding as an unrecorded commit.
Ceiling, stated as v3.3 stated it: the lint checks the citation's **structure**, the reconcile checks
its **counts**; neither reaches the truth of anything no gate expresses. Receipts written before the
manifest existed are not re-judged.

---

<!-- Receipts go below, newest on top. Delete the seed-sentinel line above when you add the first one. -->

```handoff
session: S265
date: 2026-09-22
status: complete
self_score: 8
predecessor_score: 9
active_task: One unreflectable view no longer empties the whole inventory -- COMPLETE, closing BACKLOG.md "One unreflectable view empties the whole inventory" (filed Session 261; the operator's pick from a two-step picker). Two operator rulings, taken by picker with the HEAD measurements: (1) skipped entities are reported in the existing ProducerMetadata.notes (no contract change); (2) discover still exits 1 on a partial inventory, and a new --allow-skipped flag accepts skipped tables alone with exit 0. The item and its index row are removed.
what_was_done: Seven commits, pushed at close-out on the operator's ruling (0adc8ae..this close-out). 340139b claims. 4cd881b: get_information_schema(skipped=list) collects a frozen SkippedEntity per table/view whose reflection raises SQLAlchemyError and carries on; the default (no list) still raises. 31b4c8b: the probe writes a skip note (SKIPPED_NOTE_PREFIX, up to ten names with exception types, one WARNING per skip, cause never persisted, skip part before any ranking part), and cli.discover gains --allow-skipped (exit 0 only when skips are the sole fault and something was reflected). A four-lens adversarial review (correctness, mutation, security, stale docs) found no blocker; its medium defect, found by two reviewers independently on PostgreSQL 17, was that a lost connection read as skipped tables, so --allow-skipped exited 0 over an outage. 5a27874 fixes it: a connection_invalidated error is retried once, and any other error is skipped only while a fresh SELECT 1 still succeeds; SkippedEntity hides its error from repr. c61aea6: skipped names are written in full (they were cut to 80 characters), no false ranking failure without --rank-with-llm, and the mutation pass's 9 real gaps are closed. 1beebca: USAGE.md, BACKLOG.md (item removed, a precedent sentence on the --db-url item), README census (445 / 1,587 / 98.07%). The last commit is this close-out: record, receipt, learnings #284-#286, the CLAUDE.md count and size, and the ledger entry recording the push.
next_steps: The tenth trim of SESSION_NOTES.md is due: 198,514 B at this close-out, past the 196,608 B trigger. Run it as its own session (claim, trim, close out). Before it, and only with the operator's go-ahead, restore Session 262's record heading: a one-line insert above the line starting "**Deliverable:** **`redact_secrets` stops failing open" (SESSION_NOTES.md:520 at this close-out; find it with grep -n). Rulings still owed: the --request-context item (BACKLOG.md:366, reject or scrub) and --db-url option (c) (BACKLOG.md:327, whose precedent paragraph at :361 now names discover's opt-in-flag shape). Observed, not filed: _safe_message passes terminal control characters from driver messages to stderr and the probe-failed note (pre-existing; a table name is embedded in its SQL; fix by escaping non-printables there); a duck-typed db can put an unescaped entity_kind in the note; discover --db-url sqlite:///<typo> creates an empty file and exits 0; cli.py's module docstring says only anthropic exists; BACKLOG.md's README-counts index row states a stale sum of 1,347.
key_files: packages/data-agent/src/model_project_constructor_data_agent/db.py:141 (SkippedEntity), db.py:229 (_answers_select_1), db.py:281 (get_information_schema), db.py:344 (reflect; :350 disconnect retry, :357 SELECT 1 gate), discovery.py:59 (SKIPPED_NOTE_PREFIX), discovery.py:64 (_SKIPPED_NAMED), discovery.py:251 (skip note inside the stage-1 try), discovery.py:260 (WARNING loop), discovery.py:294 (_skipped_note), discovery.py:375 (_fqn), cli.py:172 (--allow-skipped), cli.py:254 (unranked), cli.py:268 (acceptable), tests/data_agent_package/test_db.py:467 (skip section), test_db.py:606 (_outage_at), test_db.py:629 (outage test), test_db.py:663 (retry test), tests/data_agent_package/test_discovery.py:148 (_SkippingDB), test_discovery.py:174 (_skip_note), test_discovery.py:666 (TestUnreflectableEntitiesAreSkipped), tests/data_agent_package/test_cli.py:537 (_seed_stale_view_db), test_cli.py:587 (view named like a ranking failure), packages/data-agent/USAGE.md:217, USAGE.md:260, USAGE.md:489, BACKLOG.md:361
gotchas: get_information_schema's default (no list) must stay strict: tests/eval/eval_corpus.py relies on the first error propagating. Every duck-typed test DB must accept the skipped= keyword, or the probe's TypeError becomes a probe-failure note; test_cli's _boom fakes take **kwargs. To simulate an outage on SQLite, call inspector.bind.dispose() and then rename the database's directory; pooled connections survive a rename, so dispose first. The shell is zsh, which does not word-split an unquoted $var, so run measurement loops through bash (#286); a SQLite URL to a missing file silently creates it. To verify a partial commit against the 5-file cap, git stash push --keep-index, run the suite, commit, pop; editing a staged file after stashing makes the pop conflict. Real-dialect checks: postgres:17-alpine is local, mysql:8.4 was pulled this session; drivers via uv run --with 'psycopg[binary]' or --with pymysql --with cryptography.
runtime_smoke: RAN the real model-data-agent discover, previous code (archived copy via PYTHONPATH or sys.path) against the fix, at $0. SQLite (4 tables, a good view, a stale view): before, 0 entries and exit 1; after, 5 entries and exit 1, or exit 0 with --allow-skipped; two stale views are both named; stale-only exits 1 even with the flag; a healthy db with the flag exits 0 with nothing on stderr. MySQL 8.4 in Docker: the drop is allowed and reflection raises UnreflectableTableError (error 1356); before, 0 entries naming one view; after, 3 entries naming both; the password is in neither stderr nor the file. PostgreSQL 17 in Docker: the drop is refused (DependentObjectsStillExist); a table dropped mid-walk is skipped as NoSuchTableError. With --allow-skipped, login refused after the first view gave exit 0 and two good views "skipped" before, and gives exit 1 and a probe failure now; the probe's backend killed while reading t2 gave exit 0 and t2 "skipped" before, and gives exit 0 with all 5 entries now. Mechanical: full suite 1,587 passed / 9 skipped / 98.07%; ruff and mypy (68 files) clean; census and read-budget guards green. .quality-gates.json declares no gates, so quality_ratchet.py has nothing to run.
changelog_ref: CHANGELOG.md "### 2026-09-22 · [ad hoc] S265 — close out: one unreflectable view no longer empties the inventory; pushed to origin"
commit: pending
```

Session 265 was run by Claude Opus 5.5 on a single tier. It delegated four read-only review lenses to subagents and verified every finding it acted on itself, at runtime on PostgreSQL 17. Self-score 8: the rulings were taken with measurements, there was real-dialect runtime evidence, and the review's medium defect was fixed with evidence for both of its forms. The first design missed that defect (#284), the first picker hid open items (#285), and three runtime runs measured the wrong object (#286).

```handoff
session: S264
date: 2026-09-22
status: complete
self_score: 8
predecessor_score: 6
active_task: A ranking that cannot be applied is a ranking failure -- COMPLETE, on BACKLOG.md "A ranking that matches no entry is silent, and scores are not range-checked" (filed Session 261, operator's pick at Phase 1). Two operator rulings before code: (1) a score that is NaN, +/-inf or outside [0.0, 1.0] on an entry it is applied to is REJECTED (whole ranking fails), never clamped; (2) close the lone-surrogate ranking and reflection channels, leave request_context filed. So the item is NARROWED, not closed: it now holds only the --request-context channel (BACKLOG.md:392), re-measured through the real CLI.
what_was_done: Five commits, none pushed (operator ruling at start). 5e17330 claims. 959c452 is the fix: discovery._ranked raises RankingMatchedNoEntryError when no entry is named exactly, InvalidRelevanceScoreError when an applied (validated) score is not finite in [0.0, 1.0], and -- via the faaf334 refactor -- UnwritableEntryError when a reason cannot be written; stage 1 runs the same writability check on every built entry so reflected text is a probe failure; 19 tests red at HEAD then green, plus a CLI exit-1 test. faaf334 fixes what a 10-agent adversarial review (wf_3680318a-548; 39 findings, all held, no blocker) found: bad values were always LAST and the reflection test always had an LLM, so a dedented check and an llm-gated check survived -- now first/middle/last and ranking on/off; failures name the entry; the no-match WARNING is bounded with reprlib; a shipped-client end-to-end test. 31b46b6 narrows the BACKLOG item and its index row, updates USAGE.md Example 4 and the error contract, re-measures README's census (404 collected in data_agent_package; 1,546 passed; 98.04%). The last commit is this close-out: record, receipt, learnings #281-#283, CLAUDE.md count and size.
next_steps: Pushing is the operator's call (seven local commits: Session 263's two, this session's five including this close-out). Restore Session 262's record heading, which Session 263's close-out 6360c2c deleted -- a one-line insert above SESSION_NOTES.md:382 -- before the tenth trim; it was a picker option this session and was not chosen, so ask first. The narrowed item (BACKLOG.md:392) needs a reject-vs-scrub ruling; "One unreflectable view empties the whole inventory" (BACKLOG.md:364) needs a reporting decision. Observed and not filed: duplicate ranking names are last-wins; a None score on a named entry is now rejected (an extension of ruling 1, disclosed in the ledger); LLM-returned names can carry a Bearer shape into the stderr WARNING (pre-existing via LLMParseError, never persisted).
key_files: packages/data-agent/src/model_project_constructor_data_agent/discovery.py:56 (RankingMatchedNoEntryError; :65 InvalidRelevanceScoreError; :73 UnwritableEntryError), discovery.py:84 (_BRIEF), discovery.py:90 (_check_writable), discovery.py:221 (stage-1 check), discovery.py:256 (_ranked; :288 no-match raise, :301 score check, :308 reason check), tests/data_agent_package/test_discovery.py:474 (stage-1 test), test_discovery.py:804 (AT) and :807 (_one_scored), test_discovery.py:849 (TestRankingThatCannotBeApplied), test_discovery.py:1019 (_CannedAnthropic) and :1046 (shipped-client test), tests/data_agent_package/test_cli.py:416 (CLI exit-1 test), packages/data-agent/USAGE.md:235 and :446, BACKLOG.md:55 and :392, PROJECT_LEARNINGS.md:287 (#281-#283)
gotchas: pytest's pythonpath ini option (pyproject.toml) is inserted ahead of PYTHONPATH, so a scratch-copy mutation harness silently tests the unmutated tree -- pass -o pythonpath=<scratch> src and always run a baseline plus a must-die control (#281). Workflow agents with isolation worktree start at origin/master, not local HEAD, and lack the dev extra -- brief them to check out the SHA and uv sync --all-extras (#283). --fake-llm ranks every table validly, so it reaches none of these failures; use _CannedAnthropic in tests or a local HTTP stand-in with ANTHROPIC_BASE_URL. math.isfinite in the score check is an equivalent mutant -- not a test gap. `and entries` in the stage-2 guard is now load-bearing (without it an empty DB under --rank-with-llm exits 1). The ranking note persists the type only, so a new ranking failure deserves its own exception class; PydanticSerializationError no longer appears in notes.
runtime_smoke: RAN the real `model-data-agent discover --rank-with-llm` through the real AnthropicLLMClient over real HTTP to a local stand-in for the Messages API (ANTHROPIC_BASE_URL, $0), parent 959c452^ (via PYTHONPATH to an archived copy) against the fix, on a two-table SQLite warehouse. Parent: bare names, [], NaN, a 0-10 scale and a surrogate reason all exit 0; NaN writes a non-RFC literal; the surrogate file fails model_validate_json. Fix: each exits 1 naming RankingMatchedNoEntryError / InvalidRelevanceScoreError / the serialization failure, every file reloads and is RFC-clean; a good ranking and a partial ranking with an invented NaN-scored name still exit 0. The unfixed --request-context channel re-measured through the real CLI: exit 0, a file adapters.py:220 rejects. Mechanical: full suite 1,546 passed / 9 skipped / 98.04%; ruff and mypy (68 files) clean; 18 of 18 non-equivalent mutants killed on faaf334 (baseline passes, control killed). .quality-gates.json declares no gates, so quality_ratchet.py has nothing to run.
changelog_ref: CHANGELOG.md "### 2026-09-22 · [ad hoc] S264 — close out: a ranking that cannot be applied is a ranking failure; the item is narrowed to the channel left open"
commit: pending
```

Session 264 ran on Claude Opus 5. Score 8/10:
- **+** Every failure class was measured at HEAD before the rulings were asked, and runtime-verified parent-vs-fix through the real client over HTTP.
- **+** Every skeptic verdict of the 10-agent review was read; its three medium gaps were fixed and the survivors re-run to confirm they die.
- **+** A control mutant exposed a broken mutation harness before any result was reported.
- **−** The first-draft tests had position and mode bias (#282); the review found it, not the author.
- **−** One test docstring carried an underived, backwards claim (`nan-as-text`), and `959c452`'s ledger entry needed two corrections in the next.

```handoff
session: S263
date: 2026-09-21
status: complete
self_score: 6
predecessor_score: 8
active_task: Readiness verdict on migrating the repository into a private environment (the plan's one-time git clone --mirror of the public origin into an enterprise host) -- answered, not ready, one blocker, cleared the same session by the operator's push. The operator asked it as a question, not a migration request; no migration step was performed. The five before-fork fixes, the C4-time facts the plan omits, and the never-started Phase C2 are now in BACKLOG.md's Enterprise migration item.
what_was_done: A 13-agent read-only workflow (wf_a5108b71-83a: six dimension auditors, one adversarial verifier each, one synthesis; 0 failed), with the headline claims re-derived first-hand before reporting. On the operator's instruction, pushed master to origin f987a6f..0adc8ae (a non-commit action; CI run 35683413293 green on all six jobs, 1481 passed / 9 skipped in its log; publish-tutorial and the wiki hook did not fire; feat/bedrock-mantle-migration deliberately not pushed). 26e84d9 files the punch list into BACKLOG.md's Enterprise migration item and index row, and records the push in CHANGELOG.md. The last commit is this close-out: the record, learning #280, this receipt, CLAUDE.md's learnings count and size. Phase 1B was skipped (no stub, no pending receipt) -- a deviation, stated in the record.
next_steps: Two commits (26e84d9 and this close-out) are unpushed again, which reopens the blocker in its trivial form -- pushing is the operator's call. Then the five before-fork fixes in BACKLOG.md's Enterprise migration item: (1) docs/methodology/README.md's superseded licence text plus three NOTICE corrections -- needs a ruling first, see gotchas; (2) push or deliberately drop local-only 4795c29; (3) tag v0.3.0; (4) refresh audits/2026-07-28-b2-import-readiness.md; (5) add a local-vs-origin parity pre-flight to Phase C4. (2) and (3) are operator actions, not sessions. Session 262's carried items are unchanged.
key_files: BACKLOG.md:53 (the rewritten index row), BACKLOG.md:787 (the Session 263 audit block, through :819), docs/planning/enterprise-migration.md:1266 (Phase C4, through :1391), docs/methodology/README.md:361 (the superseded licence, through :369), NOTICE:28 and NOTICE:40 (the two wrong statements), scripts/publish_wiki.sh:48 (the WIKI_CLONE fallback to the personal wiki)
gotchas: docs/methodology/README.md is an orphan inside the do-not-edit synced set -- the methodology repository has no docs/methodology/README.md (only a root README.md), so bin/sync can never refresh it; deleting or rewriting it changes a file NOTICE section 1 and CLAUDE.md count among the 13 synced docs/methodology/ files, so rule on that first. Never execute scripts/publish_wiki.sh to test "fails closed" -- with WIKI_CLONE empty it falls back to the personal public wiki (:48), and the plan's own C4/C5 check runs it. The plan's C4/C5 figures are stale (wiki 44 commits / 25 pages, 188 intra-wiki links) -- re-derive by running the commands. Readiness for this fork is readiness of origin (learning #280): git ls-remote origin before any claim about what the clone will contain. Python runtime deps are copyleft-free, but gh-pages and mkdocs-material bundle wordcut.js, which upstream licenses LGPL-3.0 -- do not say "no copyleft anywhere".
runtime_smoke: n/a -- docs-only; no runtime behaviour changed. Evidence for the verdict: the audit's own run of the full suite (1,481 passed / 9 skipped / 98.02%), ruff, mypy (68 files) and all 11 proofs in both modes; CI run 35683413293 green on 0adc8ae after the push. Census and read-budget guards 82/82 before each commit. .quality-gates.json declares no gates, so quality_ratchet.py has nothing to run.
changelog_ref: CHANGELOG.md "### 2026-09-21 · [ad hoc] S263 — close out: the repository is one push from fork-ready; the punch list is filed"
commit: pending
```

Session 263 ran on Claude Opus 5. Score 6/10:
- **+** The headline claims were re-derived first-hand before reporting.
- **+** The push was proven unable to fire a deploy, then watched to green in CI.
- **+** The punch list was filed rather than carried in a what's-next list.
- **−** Phase 1B was skipped.
- **−** The Phase 0 report was compressed to one line.
- **−** A copyleft claim reached the operator with its qualifier dropped (#257). It was corrected at close-out.

```handoff
session: S262
date: 2026-09-21
status: complete
self_score: 8
predecessor_score: 8
active_task: redact_secrets stops failing open on shapes inside its own claimed coverage -- COMPLETE, closing the BACKLOG item filed in Session 261. _SECRET_KEY widens the key list and drops the \b word-boundary assumption; _SECRET_VALUE adds quoted/braced/lookahead-guarded-bare value forms; _mask_kv percent-decodes a copy of the text to find matches while editing the original untouched outside a matched span. redact_db_url and redact_secrets both route through it. Still blind by design: a key outside _SECRET_KEY, and a bare-key/header/Bearer/SigV4 shape with no key=/key: form at all.
what_was_done: Six commits. 0d76da2 claims the session. 69c5aba is an incidental fixture repair found at the claim commit: tests/test_read_budget.py's M08 mutant held byte length fixed but not line density when swapping a ledger's tail for a pad, so in the wide-close-out-then-claim state the page estimate fell below a K-prefix boundary and check_k_lines co-fired; now the swap removes whole tail lines and pads with exactly that many lines summing to the same bytes. 1e53c20 is the fix and its tests: db.py's _SECRET_KEY/_SECRET_VALUE/_SECRET_KV/_mask_kv, both userinfo patterns dropping their '@'-exclusion; test_db.py gains the item's leak table (11 shapes), its four further classes (7 shapes), two field-boundary tests, a false-positive guard, and idempotence -- 22 new tests, all secret-ABSENCE assertions. 1fac1dd is a test-quality repair mutation testing found: the quoted-value tests all used a spaceless secret, so a bare-only mutant passed them by accident; introduced SPACED_SECRET = "hunter two" for the rows that need quoting. 3505ce9 is docs: BACKLOG.md item removed with its index row, discovery.py's _safe_message docstring and test_discovery.py's ranking-note test comment corrected (the widened key list now masks 2 of 3 named shapes, not 0), README.md's census re-measured (316->339 collected, 1,458->1,481 passed, 98.01%->98.02%), PROJECT_LEARNINGS.md gains #278-#279, CLAUDE.md's counts re-measured. The last commit is this close-out: the record, the receipt, and CHANGELOG.md entries for the three commits above that each omitted their own entry at commit time (a process gap caught only at this close-out).
next_steps: Pushing is the operator's call -- this session's six commits plus the four inherited from Session 261 are unpushed. Session 261's two other filed items are still open and cheap: BACKLOG.md "One broken view empties the whole table inventory" (needs a reporting decision before code) and "A ranking that matches nothing is silent" (one function, discovery._ranked). The --db-url status-exit-0 item is still open, an operator ruling, unrelated to this session. redact_secrets' remaining named gaps (bare-key/header/Bearer/SigV4 shapes, keys outside the fixed list) are recorded in SESSION_NOTES.md rather than filed as a new item, because nothing currently reaches those shapes with a secret in them -- filing one without a live reach would be manufacturing work.
key_files: packages/data-agent/src/model_project_constructor_data_agent/db.py:21 (module comment, through :71 for _SECRET_KEY/_SECRET_VALUE/_SECRET_KV), db.py:73 (_mask_kv, through :97), db.py:99 (redact_db_url/redact_secrets, through :113), discovery.py:67 (_safe_message's corrected redaction docstring, through :72), tests/data_agent_package/test_db.py:265 (the Session 262 test block, through :360), tests/data_agent_package/test_discovery.py:624 (the corrected ranking-note comment, through :634), tests/test_read_budget.py:684 (M08's exact-swap repair, through :719), BACKLOG.md's plain-language index (closed item's row removed)
gotchas: --fake-llm never reaches redact_secrets -- FakeCLIClient.summarize returns a hardcoded data_quality_concerns: [] regardless of db_executed; verify redaction at discover instead, which calls connect() directly. A redaction test needs a secret that CONTAINS the character its new support protects -- a spaceless secret cannot tell a quote-aware value class from a bare one that swallows quotes by accident (see SPACED_SECRET). Never git checkout -- a file mid-mutation-testing unless the real fix is already committed -- mutate a scratch copy or restore from a checksum-verified snapshot taken after committing. A commit's own CHANGELOG.md entry goes in that SAME commit, not a later one -- verified against how Sessions 260 and 261 actually did it, not assumed. The ranking note is type-only unconditionally, a design choice, not because redact_secrets happens to be blind. _SECRET_KEY's widened list can now match inside an unrelated word (api-key inside x-api-key) -- intentional, but means "is this shape covered" must be checked against the CURRENT key list.
runtime_smoke: RAN against the real console script. model-data-agent discover against postgresql://claims_ro:hunter two@warehouse.invalid:5432/claims (unreachable host, psycopg2 not installed) and the same with $DB_PORT unexpanded (unparseable) -- both EXIT 1, both name the real cause in stderr, neither leaks "hunter", "two", or "hunter two" anywhere in stderr or any written file. --fake-llm mode checked and set aside as the wrong surface (never reaches redact_secrets). Mechanical evidence: full suite 1,481 passed / 9 skipped / 98.02% against the 95% gate (1,458 before); ruff check src/ tests/ packages/ scripts/, uv run mypy (68 files), tests/test_data_agent_decoupling.py and the census and read-budget guards clean throughout. Six hand-built mutants (narrow key list, bare-only value class, old tail-stop, no percent-decoding, @-excluding userinfo, bare-=-only separator), each applied to a scratch-snapshotted copy and restored by checksum-verified copy -- all six caught. .quality-gates.json declares no gates, so quality_ratchet.py has nothing to run.
changelog_ref: CHANGELOG.md "### 2026-09-21 · [ad hoc] S262 — close out: `redact_secrets` stops failing open inside its own claimed coverage"
commit: pending
```

```handoff
session: S261
date: 2026-09-21
status: complete
self_score: 8
predecessor_score: 9
active_task: probe_information_schema's "never raises" promise is true, closing the BACKLOG item filed in Session 223. The probe now guards two stages separately -- reflection plus entry building (failure -> empty inventory, note names the exception type and its redacted one-line message) and LLM ranking (failure -> the reflected tables are KEPT, all unranked, note names the type only). Two operator rulings taken by picker mid-session govern the `discover` command: any DEGRADED inventory, ranking-failed or reflection-failed, is still written and the command exits 1. The item is removed from BACKLOG.md with its index row, and three defects the reviews found are filed in its place.
what_was_done: Four commits through this close-out. 62da800 claims the session. ae20310 is the fix and its tests: discovery.py gains PROBE_FAILED_NOTE_PREFIX / RANKING_FAILED_NOTE_PREFIX, _safe_message (guarded str, surrogate scrub, best-effort redaction, flattened), a stage-1 try that now includes entry building under `except Exception`, a separate stage-2 try with the ranker looked up inside it, and _ranked (deep copies to the ranker, all-or-nothing, revalidated from a dict because model_validate(<instance>) and model_copy(update=) both skip validation); cli.py writes the file and then exits 1 with one stderr line echoing the note whenever the inventory carries a note; test_discovery.py gains two classes, a load-bearing `notes is None` in the shared _probe helper, recorders in place of two in-fake asserts, and tightened degradation tests; test_cli.py gains three exit-status tests. 2a38d00 updates USAGE.md Example 4 and the Error contract, re-measures README.md's census (316 / 1,458 / 98.01%), removes the BACKLOG item and its row, files three new items with rows, records the rulings as precedent on the open --db-url item, and carries a correction to ae20310's ledger entry (8 skeptics, not 9). The last commit is this close-out: the record, five learnings (#273-#277), this receipt, CLAUDE.md's learnings count.
next_steps: Pushing is the operator's call; nothing from this session is pushed. The cheapest engineering on the board is the three items this session filed, each with its measurement in the item -- BACKLOG.md "One unreflectable view empties the whole inventory" (db.py's reflection loop; needs a decision on how a skipped entity is reported BEFORE code, because get_information_schema returns list[dict] with no side channel), "A ranking that matches no entry is silent, and scores are not range-checked" (one function, discovery._ranked: raise when the ranking map matches no entry; rule on NaN/range; model_dump_json each rebuilt entry to catch lone surrogates), and "redact_secrets fails open on shapes inside its own claimed coverage" (one regex in db.py plus a parametrized secret-absence table). The --db-url option-(c) ruling is still open and now has a precedent recorded beside it, ruled for `discover` only.
key_files: packages/data-agent/src/model_project_constructor_data_agent/discovery.py:50 (the two note prefixes), discovery.py:54 (_safe_message), discovery.py:158 (stage 1, through :167), discovery.py:170 (stage 2, through :190; ranker lookup at :174), discovery.py:195 (_ranked), packages/data-agent/src/model_project_constructor_data_agent/cli.py:223 (the exit-1 rule and the rulings comment, through :241), tests/data_agent_package/test_discovery.py:72 (_probe and its load-bearing assertion), test_discovery.py:138 (_Ranker, a recorder), test_discovery.py:407 (TestProbeNeverRaises), test_discovery.py:530 (TestRankingFailureKeepsEntries), tests/data_agent_package/test_cli.py:356 and :398 and :447 (the three exit-status tests), packages/data-agent/USAGE.md:217 (the degraded-outcome contract), BACKLOG.md:54 (three new index rows, through :56), BACKLOG.md:358 (the precedent), BACKLOG.md:365 and :393 and :420 (the three filed items)
gotchas: Never signal "should not be called" by raising from a fake on the probe's path -- the probe absorbs Exception, AssertionError included; record the call and assert outside. A healthy-path probe test must assert notes is None (use _probe): a degraded inventory also has entries == []. The CLI's rule is "any note -> exit 1", and the probe sets notes only when it degraded, so a future producer that writes an informational note would make discover exit 1 -- give it another field. notes is None does NOT mean ranked: a ranker that returns [] or names no entry raises nothing (filed, not fixed). The two notes carry different things on purpose -- reflection: type plus redacted message; ranking: type only, message to the WARNING, because redact_secrets is blind to 6 of the 7 LLM-side secret shapes measured -- do not harmonise them. Revalidate from a dict; model_validate(entry) is a no-op. A committed ledger entry is never edited: ae20310's entry says "9 skeptics" and 2a38d00's carries the correction.
runtime_smoke: RAN against the real console script, after the second ruling. `env -u ANTHROPIC_API_KEY -u ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL=http://127.0.0.1:9 uv run model-data-agent discover --db-url sqlite:///<db> --output <f> --rank-with-llm` -> EXIT 1, file written with one unranked entry and the note "LLM relevance ranking failed (TypeError); all 1 entries are unranked...", stdout the one "wrote" line, stderr the WARNING carrying the SDK's message plus the `error:` line. A SQLite DB with a stale view -> EXIT 1, file written with 0 entries, the view named in the note and on stderr. `--rank-with-llm --fake-llm` -> EXIT 0, ranked, notes null. At HEAD the first case was exit 1, a traceback and NO file (measured before any code). Mechanical evidence: full suite 1,458 passed / 9 skipped / 98.01% against the 95% gate; ruff check src/ tests/ packages/ scripts/, uv run mypy (68 files), tests/test_data_agent_decoupling.py and the census and read-budget guards clean; 40 mutants of discovery.py and cli.py with 0 survivors. .quality-gates.json declares no gates, so quality_ratchet.py has nothing to run.
changelog_ref: CHANGELOG.md "### 2026-09-21 · [ad hoc] S261 — close out: `probe_information_schema` never raises; a degraded `discover` exits 1"
commit: pending
```

Model: Claude Fable 5.1, single tier. Self-score 8 and predecessor score 9 are argued in this
session's record in `SESSION_NOTES.md`. Two multi-agent reviews bracketed the code: a design attack
before any of it was written (5 lenses, 5 skeptics) and a diff review after (4 lenses, 3 skeptics).
Both exit-status problems, the disarmed test tripwire, the no-op revalidation and the type-only note
came from the first; the mislabelled "unchanged" test and a false numeral came from the second. Every
blocker was re-measured by the session before it was accepted, and both behaviour changes went to the
operator as pickers.

```handoff
session: S260
date: 2026-09-20
status: complete
self_score: 9
predecessor_score: 9
active_task: The silent --db-url failure is closed for options (a) and (b): the DataReport now names the cause of a DB connect failure instead of a fixed string, with any password masked, and a URL that fails to PARSE additionally logs a WARNING so it is distinguishable from one that parses and cannot be connected to. Option (c) -- a DataReport status that makes the orchestrator halt -- is NOT done and is an operator ruling; BACKLOG.md's item is narrowed to it rather than removed, and its plain-language index row rewritten to match.
what_was_done: Eight commits, the last three landing AFTER this receipt was first written -- 640d199 (the close-out this receipt belongs to), 3545d08 (recording the push and correcting the two sentences it falsified) and one repairing the counts in this very field, which 3545d08 had in turn falsified. 2a648ef claims the session; 945b316 is the fix (nodes.py binds the DBConnectionError it had been catching unbound and returns it as a new db_error state key, declared on DataAgentState because langgraph silently drops an undeclared node return key; agent.py appends the cause to the canned concern rather than replacing it, flattened to one line because SQLAlchemy puts a help URL after a newline on every DBAPIError; db.py gains redact_db_url and redact_secrets and applies both in connect(), and sql_dialect_from_url binds its exception and warns); 6350fda adds 25 tests; 8054a13 corrects two test-file warnings the fix falsified; e6a9edc narrows the BACKLOG item, updates USAGE.md and re-measures README.md's three test-census numerals; 640d199 closes out; 3545d08 records the push; the last commit repairs the counts here and in SESSION_NOTES.md and adds learning #272. Also one non-commit action with its own ledger entry: the inherited 25-commit backlog was pushed to origin/master at Phase 1 on the operator's instruction (5f173f8..159e739), and CI run 35479804135 went green on it.
next_steps: Option (c) is the only part of this item left and it is an operator ruling -- BACKLOG.md:326 states three shapes in ascending blast radius, and notes that the same question governs nodes.py's baseline branch ("database not reachable at baseline-collection time"), which should be ruled with it rather than separately. After that the cheapest engineering item on the board is the sibling defect: probe_information_schema promises it "never raises" and can, one file, same defect class -- but re-locate it by content, because this session's review measured that item's own _reflect_entity line citations wrong at HEAD. All six commits were pushed after close-out (159e739..640d199) and CI run 35485626427 is green on 640d199 across all five jobs, ledger proofs in both modes included; nothing is left unpushed.
key_files: packages/data-agent/src/model_project_constructor_data_agent/db.py:21 (the redaction helpers, through :70), db.py:92 (the rewritten Session 223 docstring paragraph), db.py:134 (the option-(b) warning), db.py:167 (connect() redacting both operands), state.py:39 (db_error and the comment saying what guards it), nodes.py:124 (the one-line root cause), agent.py:137 (the cause appended to the canned concern), tests/data_agent_package/test_db.py:184 (redaction + option (b)), tests/agents/data/test_data_agent.py:682 (discriminator, one-line, credential, db-is-None), BACKLOG.md:55 (index row) and BACKLOG.md:326 (the narrowed item), README.md:95 and :100 and :155 (the re-measured census)
gotchas: redact_db_url and redact_secrets are two functions on purpose -- the URL form matches greedily to the LAST '@' because a password may contain one, and the text form must NOT or a single pass would span from a URL to an unrelated '@' later in a driver's message. Assert a secret's ABSENCE, never that a '***' marker is present: a marker assertion passes on a partial leak, which is the exact mistake an adversarial review caught here. _SECRET_KV is a fixed key list, so a secret under a key not in it is unmasked -- the structural path covers the userinfo password regardless. Adding a DataAgentState key is two edits and mypy catches neither, because langgraph drops an undeclared key silently and both ends are typed dict[str, Any]; the discriminator test is the only guard, verified by deleting the declaration. The canned concern PREFIX was kept rather than replaced -- four existing assertions and docs/tutorial.md:535 depend on it.
runtime_smoke: RAN, and it is what demonstrates the item closed. `uv run model-data-agent run -r tests/fixtures/sample_request.json -o <out> --fake-llm --db-url <url>` for both `postgresql://user:hunter2@warehouse.internal:$DB_PORT/claims` and `sqlite:////nonexistent/path/does/not/exist.db`: the two reports now carry DIFFERENT data_quality_concerns naming the actual causes ("invalid literal for int() with base 10: '$DB_PORT'" vs "unable to open database file"), the option-(b) WARNING appears on stderr for the unparseable URL only, "hunter2" is absent from both serialized reports, and status stays COMPLETE with exit 0 -- exactly the shape option (c) is deliberately left in. Mechanical evidence: full suite 1,420 passed / 9 skipped / 97.99% against the 95% gate; ruff check src/ tests/ packages/ scripts/, uv run mypy (68 files) and tests/test_data_agent_decoupling.py (the C4 job, run because this diff added a stdlib logging import to the package) all clean; census and read-budget guards 82 passed. .quality-gates.json declares no gates, so quality_ratchet.py has nothing to run. Four mutants against the new tests, each caught by its intended test and no other.
changelog_ref: CHANGELOG.md "### 2026-09-20 · [ad hoc] S260 — close out: the silent --db-url failure reports its cause"
commit: pending
```

Model: Claude Opus 5 (1M context), single tier. Self-score 9 and predecessor score 9 are argued in
this session's record in `SESSION_NOTES.md`. The design was mapped and adversarially verified by a
9-agent workflow (five mapping lenses, a synthesizer, three skeptics): 13 findings, 2 blockers, and
both blockers plus the partial-leak finding were re-measured in this repo before being accepted.
All three were against this session's own draft redaction, not against the filed item.

```handoff
session: S259
date: 2026-09-19
status: complete
self_score: 8
predecessor_score: 9
active_task: BL-57 phase P11 — COMPLETE. CHANGELOG.md follows the methodology's ledger rules, the framework files are synced from fork main a69ef73, and this project's runner customizations live in CLAUDE.md. Nothing of P11 is left in this repository; the only remaining step, reporting the phase back to the methodology fork, happens there.
what_was_done: Nine commits, one ledger entry each — bb91fda claim, 5935288 ignores for the three tool run logs, 3d96eb6 the runner's seven task rows and Wiki sync paragraph moved into CLAUDE.md with step 5 retired (operator decision (a)), 8da685f bin/sync --force writing exactly the 26 files its dry run listed, 886945a NOTICE and CLAUDE.md attribution enumerating what the sync brought, 8b32939 the ledger header to the seed's rules pointer and ledger-format 2 marker, 3f35793 PROJECT_CONVENTIONS.md §2 superseded plus the CLAUDE.md ledger adaptations, 7e575ba three corrections an adversarial review caught, and this close-out. CHANGELOG.md lost exactly two lines across the whole phase; its ### count went 156 to 164 and the anchored audit 0 to 8.
next_steps: Report P11 back to the methodology fork's recording session — commit list, bin/status before and after, the sync's source version v3.7-975-ga69ef73, the ### and audit counts, the §9.8 outputs, each trimmer check, the gate results, and the facts that measured differently (the trimmer archives 143 of 156 back to 2026-04-16, not all 156 back to 2026-04-10; the fork had moved to a69ef73; context_budget.py has no --status flag). Then the operator's call on pushing: 25 commits ahead of origin/master, this close-out included.
key_files: CLAUDE.md:79 (the new CHANGELOG.md adaptations, five bullets to :85), CLAUDE.md:106 (the seven task-to-workstream rows), NOTICE:8 (the enumerated attribution), docs/methodology/PROJECT_CONVENTIONS.md:29 (the supersession banner over §2), CHANGELOG.md:5 (the seed's rules pointer and format marker), BACKLOG.md:569 (the ledger-order item, narrowed to its order question)
gotchas: Never run methodology_trim.py --write on CHANGELOG.md — it parses the file now and its trigger fires, and at three tagged entries its dry run would carry 143 of the 156 legacy entries into the oldest tagged record, back to 2026-04-16, leaving the last 13 live as the footer; CLAUDE.md:83 holds the measurement. A Verified bullet about its own commit is measured before that entry exists, so name the scope or measure after staging — 8b32939's entry said 3 insertions when the commit is 9, and the ledger forbids editing it, so the repair cost a whole entry. The synced runner is 400 lines, not 304, and its Phase 3E/3F are now 3F/3G. A bare ruff check reports 294 errors in the four synced root tools while CI's scoped form stays clean; do not "fix" it with a hand-copied exclude list, which was measured and rejected.
runtime_smoke: n/a — docs and framework files only, no runtime behavior changed. .quality-gates.json declares no gates, so quality_ratchet.py has nothing to run here. Mechanical evidence instead: full suite 1,395 passed and 9 skipped at 97.98% coverage, ruff check src/ tests/ packages/ scripts/ clean, uv run mypy clean over 68 files, all 11 docs/architecture-history proofs green in both plain and --self-test modes, and the census and read-budget guards 82 passed.
changelog_ref: CHANGELOG.md "### 2026-09-19 · [ad hoc] S259 — close out BL-57 P11"
commit: pending
```

Model: Claude Opus 5 (1M context), single tier. Self-score 8 and predecessor score 9 are argued in
this session's record in `SESSION_NOTES.md`; the review that gated this close-out ran five lenses and
a skeptic per finding, confirming 3 distinct defects of 35 findings, all of them this session's own.
