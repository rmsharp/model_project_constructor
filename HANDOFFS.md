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
session: S262
date: 2026-09-21
status: pending
self_score: pending
predecessor_score: pending
active_task: Close the BACKLOG item "redact_secrets fails open on shapes inside its own claimed coverage" (filed Session 261). db.py's _SECRET_KV misses prefixed keys (DB_PASSWORD=x, PGPASSWORD=x), quoted values (password='x y'), ':' and spaced '=' separators, JSON/dict repr, and four further classes (userinfo with '@' in the username, tail leaks on '&' and '{...}', percent-encoded odbc_connect, camel-cased keys). Fix in db.py plus parametrized secret-ABSENCE tests in tests/data_agent_package/test_db.py.
what_was_done: pending
next_steps: pending
key_files: pending
gotchas: pending
runtime_smoke: pending
changelog_ref: pending
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
