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

**Shards stay write-once.** A twelfth trim writes a twelfth file; it never appends to one of these.
That is also why every shard after the first is named as a range rather than in the first's
open-ended `-through-S216` form — `docs/methodology/PROJECT_CONVENTIONS.md` §3.1 carries the rule
and the reason.

**A shard banner is a snapshot of its own cut; this table is the authority.** Several banners still
route sessions to this live file that have since moved into a shard. Each was true when it was
written, none may be repaired, and no proof can notice: every shard proof reads its prose at its own
trim commit, so from the moment a trim lands its prose is checked by nothing until the next one.
That is this apparatus's largest hole, it is measured rather than suspected, and only three
mechanisms close any of it: the working-tree arms `R6`, `R7`, `R8` and `C6` below;
`tests/test_session_notes_census.py`, which since Session 258 holds this front matter as well as
the four prose files; and `tests/test_read_budget.py`, which holds the read-budget sentences and
this file's size. **What the census guard reads here is exactly:** every table cell but the hash,
the table's shape, each standing rule's headline, every shard filename, every number near shard
vocabulary. **The prose around those is still unread — a paragraph of it deletes green.** Edit
anything above `## ACTIVE TASK` and run `uv run pytest tests/test_session_notes_census.py --no-cov`.

**Nothing is bequeathed to the twelfth trim.** The two instructions that stood here — never
re-open the `L`-numbering collision; publish a sweep result, never repeat its sentence — are
recorded in `CLAUDE.md`, and the list as it stood is embedded in the tenth trim's proof.

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
| 9 | S256 `9342637` | 248 → 242 | 7 | 1,681 | `SESSION_NOTES-S248-through-S242.md` | 1,732 | 256 → 249 | none |
| 10 | S266 `49d23b7` | 257 → 249 | 9 | 1,447 | `SESSION_NOTES-S257-through-S249.md` | 1,498 | 266 → 258 | none |
| 11 | S277 `this commit` | 269 → 258 | 12 | 1,702 | `SESSION_NOTES-S269-through-S258.md` | 1,754 | 277 → 270 | none |

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
that trim's own `L12/row` at its trim commit; between trims the proofs read only its span, via
`R7`, and since Session 258 the census guard composes every other cell on each CI run. `R7` proves the `archived` spans
tile the history with no gap and no overlap, which is what allows the routing clauses to be deleted
rather than kept in
parallel. `R6`, `R7`, `R8` and `C6`
are the only proof assertions that read this file from the WORKING TREE; every other proof reads
this file at a commit that has already passed. That is why the census guard exists — now for this
front matter too — and the read-budget guard for this file's size and the budget sentences. **Run both modes over every proof in `docs/architecture-history/`** — a plain
run proves the world is intact and cannot see a proof that has stopped being able to fail;
`--self-test` proves the proof can fail and is blind to real corruption. `CLAUDE.md` carries the
loop and the reason neither half is sufficient.

**Cutting is by byte position, never by authorship.** This ledger files a handoff evaluation under
its author, so Session N's evaluation of N−1 sits inside N's record, and every cut so far has split
one from its subject. Expect that seam at every boundary. What these eleven trims found, argued and
rejected stays in their own records and, for the blocks that stood here, at the commits above. What
they left BINDING is in `CLAUDE.md`'s `SESSION_NOTES.md`-is-trimmed bullets, which this collapse
updates rather than contradicts.

---

## ACTIVE TASK

### What Session 280 Did
**Deliverable:** **`DataAgent.run` is total: the report is built inside a guard, so a model reply it cannot be assembled from is `EXECUTION_FAILED` with `report assembly failed: <Class>`, not a raise — COMPLETE.** Route 9 of `BACKLOG.md`'s
"Seven more routes" item. Only `self._app.invoke` was guarded; `_assemble_complete_report` runs after it. I reproduced the
symptom through the real script before changing anything: a loopback gateway that answers every question validly except
`expected_row_count_order` gave exit 1, a traceback on stderr that quoted the model's reply (pydantic's `input_value`, the
ESC as `\x1b`), no status line, and no `DataReport.json` in the checkpoint directory. Now the script exits 1 with
`Status:  FAILED_AT_DATA`, the saved report reads `Data Agent run failed: report assembly failed: ValidationError`, it holds
no queries, and nothing the model said is on the screen or in any file. Chosen by the operator at Phase 0 from a picker (first
option, recommended). **The operator also decided:** push at close-out (yes). **Mine, and not put to the operator:** a second
`try` around the assembly rather than "the same `try`" (the status branch sits between the two); the class name through
`db.safe_class_name`, as the graph's site does; adding the assembly as a third arm of the shared `SITES` parametrization (it
inherits all four of the other sites' tests) and testing that no guard swallows an interrupt at all three sites (wider than
route 9); hoisting `message()` into `tests/agents/website/loopback.py`; fixing the review's findings about this diff's own tests
and prose and filing the rest. **Started:** 2026-10-03 22:14. **Completed:** 2026-10-03. **Commits: nine** — `e2e0a16` (claim,
alone), `6a59fa3` (the guard and its unit tests), `ec05df5` (the end-to-end test), `2857a0b` and `e7f5865` (docs, `BACKLOG.md`),
`cf4ced9` (the review's test findings), `a3d359c` (its documentation findings), `9e425a3` (what it found that this change did not
cause) and this close-out. Each carries its own `CHANGELOG.md` entry; the push is recorded in the close-out's.

#### What changed
- **`agent.py:65-75`:** the `_assemble_complete_report(...)` call is in `try`/`except Exception`; the handler returns
  `_execution_failed_report(request, f"report assembly failed: {safe_class_name(e)}")`. Class only: pydantic's message quotes the
  refused value, and the report is saved and written into a committed project.
- **Tests (3,053 → 3,073):** `test_data_agent.py` 51 → 69 (§Session 280, `:1508`): an `"assembly"` arm on `SITES` (+8: the class and
  none of the text, a message that cannot be printed, four class names `type()` can build, two it cannot); `FAULTS` (`:1595`: an
  order outside the vocabulary, a different number of quality-check groups, a summary that is not text) each asserting the failed
  report and, separately, that nothing the model said is in any string; a control that a sound reply still completes; the
  interrupt test (`:1569`, one per site). `tests/scripts/test_run_pipeline_data_bad_reply.py` (new, 2 tests): the real script
  against a gateway answering all five questions, and the premise that pydantic quotes what it refuses. `loopback.py:183`
  `message()`, shared with `test_gateway_error_text.py`.
- **Docs:** `packages/data-agent/USAGE.md` (error contract, the CLI's exit code, a recipe), `TROUBLESHOOTING.md:119` §FAILED_AT_DATA
  (a root-cause entry; the recipe at `:202`, run with a stand-in client; the log level in step 3), `OPERATIONS.md`, `docs/tutorial.md`;
  `docs/wiki/` not touched. **`BACKLOG.md`:** route 9 closed (`:538`), six routes remain (1, 2, 3, 4, 6, 8); a new item, a model reply of
  `[]` is a `COMPLETE` report with no queries (`:711`, index row `:61`); channel 2 of *Three more channels* (`:386`) and the bad
  `--db-url` item (`:345`) gain what the review found. `PROJECT_LEARNINGS.md` #349-351; `CLAUDE.md:122` (351, 396.0 KB).

#### Verification
Full suite with `GITHUB_ACTIONS=true`: **3,073 passed, 9 skipped**, coverage 98.33%; `ruff check src/ tests/ packages/ scripts/` and
`mypy` clean; both ledger guards 82 passed. Before the guard 14 of the 18 new unit cases failed (the control and the three interrupt
tests pass either way). Mutation against the guard, each run's count equal to the unmutated one: no guard, raw `{e}`,
`safe_message(e)`, a bare `type(e).__name__`, `__qualname__`, an unguarded `e.__class__.__name__`, the rule inlined without a `try`,
`except ValueError`, `except BaseException`, a wrong prefix, no prefix, a handler naming a class nothing raises: all caught; and after
the review a handler that keeps the graph's baseline (4 fail) and one that carries the graph's summary (14). The script test catches
the original, raw `{e}` and `safe_message(e)`; a bare class name and `except ValueError` survive it and are the unit tests' to catch.
**Runtime smoke (3E), done:** the fixture pipeline (`--llm none`) exits 0 with `Status:  COMPLETE`; the unassemblable reply through the
real script is the end-to-end test (exit 1, `FAILED_AT_DATA`, no traceback, no quoted text).

#### The review, and what it found
One workflow: five read-only lenses (totality, test faithfulness, callers, docs and ledger, hostile inputs), two skeptics per non-nit
finding. 29 agents, 0 errors, 22.5 minutes, 2.95M subagent tokens, 637 tool uses. 20 findings (8 nits); of the 12 others the
skeptics refuted 4 as older than this change and confirmed 8 (every one reproduced; most rated nit by the skeptics, three low). **The
guard held:** no lens found a way for an exception to leave the new handler or for a model's text to reach the report through it.
What it found was around the fix, and half of it was claims I had written without checking. **Fixed:** the "not quoted" test never
asserted the status, and two of its three arms held no hostile text (a `None` quotes nothing, `zip` quotes nothing); the
`baseline_snapshot is None` assertion could not fail (the request asked for no baseline); the interrupt test's docstring said the
orchestrator saves a FAILED result for a data-stage Ctrl-C (Session 275's save is the website stage's; I wrote it from memory of the
notes); "14 of the 15" and "the other three still pass" in my own ledger; docs that named causes only a custom client can produce
(the shipped ones coerce every field with `str`), said "fewer" for a `zip` that fails for any different number, and said the traceback
"names the field" for a `ValueError`; the recipe re-runs the model and a REPL echoes the reply; `OPERATIONS.md` and the troubleshooting
step still said `agent.error`. **Filed:** a model reply of `[]` gives a `COMPLETE` report with no queries (the website stage accepts
it on purpose); through the pipeline a lone surrogate in a model reply crashes the checkpoint save instead of writing an unloadable
file; the standalone CLI exits 0 for an `EXECUTION_FAILED` report (it used to exit 1 with a traceback for this cause; `USAGE.md` says
so now). **Not filed:** model-authored text is raw in every `DataReport` field by design (route 6 files the template sink). **Observed,
not filed:** `DataAgent.run` is total by enumeration, not by structure: `final_state.get`, the `failure_reason` read and
`_missing_semantics` are outside every `try`, and none is reachable from the shipped graph or clients (a stand-in `invoke` returning
`None` gives `AttributeError`).

### Session 279 Handoff Evaluation (by Session 280)

**Score: 9/10.**
- **+** The first recommendation was the deliverable, exactly: `BACKLOG.md:530`, `agent.py`'s `try`, the two failing inputs (an
  out-of-range `expected_row_count_order`, fewer quality-check groups) and "the TROUBLESHOOTING class list gaining the case" were all
  right, and the key-file line numbers resolved. Gotcha 1 (a mutation harness must compare the test count, not read the last line) paid
  for itself: my new harness read "0 passed" from a doubled `-q`, every mutant "survived", and the count discipline caught it at once.
  Gotcha 3 (copy the helper, change both or neither) and gotcha 5 (`CLAUDE.md:122`) held.
- **−** It said "inside the same `try`", and the status check sits between the graph's `try` and the assembly, so a second handler was
  needed (cosmetic). It did not say that the real-client gateway fixture is private to `test_gateway_error_text.py` and answers four
  calls (I built a five-question one for the script; `loopback.message` is shared now), and it did not mention the standalone CLI's
  exit code for `EXECUTION_FAILED`, which the review showed is part of route 9's before and after. Its "five or six more closing
  records at this size" estimate assumed about 12 KB each; the two records since are 13 KB each, so it is lower now (below).
- **ROI: high.**

### Session 280 Self-Assessment

**Score: 7/10.**
- **+** Claimed first, reproduced through the real script before changing anything, wrote the unit tests first and watched 14 fail for
  the right reason, mutated the guard and then the strengthened tests, kept every commit at five files or fewer, drove the real
  script end to end, ran the review before closing, and fixed or filed every finding.
- **−** Four of the review's eight confirmed findings were claims I wrote without reading the thing they were about (the interrupt
  docstring, two counts in my ledger, a list of causes checked against a test double instead of the shipped client), and two assertions
  could not fail. My ledger-edit script aborted on an `assert` and the next line committed without it (`bb2d477`, no `CHANGELOG.md`
  entry, failure mode #27); I saw the traceback and amended the local commit (`cf4ced9`) before doing anything else. My mutation
  harness repeated #346's bug (a doubled `-q`) before it caught itself. I restored `agent.py` after two scratch mutations with `git checkout --`,
  which is safe only because the guard was already committed (the harnesses restore from a copy).
- **Decay term:** nothing was removed from a mandated-read file. `SESSION_NOTES.md` was 134,739 B before this record (the live trigger
  is 196,608 B); `BACKLOG.md` 153,194 → 157,960 B; `PROJECT_LEARNINGS.md` grows by three rows (393,533 → 395,969 B). **A twelfth trim
  is not due:** about three or four more closing records at this size is an estimate (147,858 B now, so about 49 KB of room to the
  trigger over roughly 13 KB each).

**What's next** (sizes and effort are estimates unless measured; none is blocking).
1. **Small, no ruling, still open:** route 8 (`BACKLOG.md:524`: `scrub_host_text(value)` where `ProjectInfo` and `CommitInfo` are built, or
   at the three prints) and route 2(b) (`:450`: a logging filter on the `sqlalchemy` loggers). `BACKLOG.md`'s own cost line says both
   need no ruling.
2. **Rulings owed, as before, plus one new:** the `[]` reply (`:711`); one named error class per cause for the scripted intake and the
   data stage (`:670`); the discovery log line and its four raw class-name reads (`:649`); the lone-surrogate channels (`:386`) and
   what `run` should exit with for a failed report (`:345`); `L10`'s completeness gap; publish the wiki correction (`:622`) and the
   two `opencode`-version sentences; wire or stop documenting `MPC_LOG_LEVEL` (`:725`); whether the coverage harness from Session 277
   should be committed.
3. **Observed, not filed:** `stash@{0}` (Session 270's claim commit), the branches `worktree-wf_5f96c807-d00-3` and
   `worktree-wf_c93ee390-506-3` with `.claude/worktrees/wf_5f96c807-d00-3`, the root `methodology_dashboard.py` at v2.18.0 against
   v2.19.0, Session 277's `gitleaks` count of 9 (not re-measured), `TROUBLESHOOTING.md` §FAILED_AT_DATA's first root-cause bullet ("a SQL
   query failed against the database": a failing quality check is `ERROR` on that check and the report stays `COMPLETE`), and
   `tests/agents/website/loopback.py`'s module docstring, which still says the module answers every request `200 {}` (it now also holds
   `serving_raw`, a 400 handler and `message()`).

**Key files** (line numbers read off `grep -n` at this close-out).
- `packages/data-agent/src/model_project_constructor_data_agent/agent.py:65-75` (the handler), `db.py:456` (`safe_class_name`).
- `tests/agents/data/test_data_agent.py:1508-1690` (§Session 280; `SITES` at `:1357`, `_crash_report` at `:1281`);
  `tests/scripts/test_run_pipeline_data_bad_reply.py`; `tests/agents/website/loopback.py:183` (`message`).
- `TROUBLESHOOTING.md:119` and `:202`; `packages/data-agent/USAGE.md` (§Error contract, the CLI paragraph near `:71`);
  `BACKLOG.md:61, 345, 386, 524, 538, 711`; `PROJECT_LEARNINGS.md` #349-351.

**Gotchas.**
1. **Chain a script and the commit that follows it with `&&`**, and read `git show --stat` of every commit (#351). A heredoc script that
   fails does not stop the next line.
2. **The shipped clients coerce every model-reply field with `str`**, which is why only two causes reach the assembly's handler through
   them; `FakeLLMClient` returns anything, so a test double is the wrong place to list causes from (#350).
3. **The standalone CLI exits 0 for any report status**, `EXECUTION_FAILED` included; `USAGE.md` says so and `BACKLOG.md:345` holds the
   question.
4. **`DataAgent.run` is total by enumeration**: three statements sit outside every `try` and none is reachable today. A new node that
   puts a non-dict in the state, or a `failure_reason` that is not text, would reach them.
5. Never `git stash` (#316). `uv run pytest tests/test_read_budget.py tests/test_session_notes_census.py --no-cov` before every commit
   that touches `SESSION_NOTES.md`, `CLAUDE.md` or `BACKLOG.md`. Use `uv run python`, never bare `python3`. `CLAUDE.md:122` states the
   learnings count and the file's size (now 351, Sessions 9–280).

### What Session 279 Did
**Deliverable:** **the data stage's report names the exception's class and never its message — COMPLETE.** `DataAgent.run` wrote
`f"graph crashed: {e}"` into `summary` and `data_quality_concerns`, and the baseline collection wrote `f"LLM baseline-query
generation failed: {e}"` into `caveats`. I reproduced the first before changing anything: the real script (`--llm data`)
against a loopback gateway that answers a 400 quoting the `x-api-key` it received put the key into `DataReport.json` (2,258 B,
on disk, not on the screen). Now the summary reads `Data Agent run failed: graph crashed: BadRequestError`, the key appears
nowhere, and the file is 1,966 B (the same script, re-run on the final code). Closes route 5 of `BACKLOG.md`'s "Seven more
routes" item. Chosen by the operator at Phase 0 from a picker (first option, recommended). **The operator also decided:** push
at close-out (yes). **Mine, and not put to the operator:** copying the rule into the standalone package as `db.safe_class_name`
(it cannot import `orchestrator.logging._class_name`) with a parity test, rather than moving it; the class name rather than the
planned `safe_message(e)` (measured: a bare `sk-ant-` token and `Authorization: Bearer <key>` survive it, the `x-api-key:`
header echo does not); hoisting the echoing-gateway handler into `tests/agents/website/loopback.py`; fixing 13 of the review's
17 findings in this session and filing the other four; adding the missing arm to the decoupling guard. **Started:** 2026-10-03 21:19.
**Completed:** 2026-10-03. **Commits: ten** — `2ad0d58` (claim, alone), `0e46e7d` (the helper), `aa95b3a` (the two sites),
`ed0be6f` (end-to-end tests), `a4e08aa` (docs), `48ce1cd` and `0337a50` (tests, from the review), `f9ac4cc` and `da87d37` (docs,
from the review) and this close-out. Each carries its own `CHANGELOG.md` entry; the push is recorded in the close-out's. (I told
the operator at the push picker there were 11 commits. There were nine, and ten with this one.)

#### What changed
- **`db.py:456` `safe_class_name(error)`:** the class name, or `<unprintable>` unless an exact-`str` ASCII identifier of at most 100
  characters; it asks the exception for nothing and reads the name under a `try`. **`agent.py:57`** and **`nodes.py:218`** write it
  in place of `{e}`. `{e}` was also a raise site inside the `except`: an exception whose `__str__` raises made `DataAgent.run`
  raise, against its documented contract.
- **Tests (+34, 3,019 → 3,053):** the two tests that pinned the message as behaviour are inverted; `test_data_agent.py` §Session 279
  (both sites × hostile text with the key bare and as a header echo, every control character and a newline; an exception that
  cannot be printed; four odd names `type()` can build; two it cannot, `NameThatRaises` and `NameThatIsAHostileStr`, now in
  `tests/hostile_text.py`); `TestSafeClassName` and a parity test against the orchestrator's copy (`test_db.py:1076`);
  `tests/scripts/test_run_pipeline_data_error_text.py` (the real script, screen and every file) and
  `tests/agents/data/test_gateway_error_text.py` (the real client and SDK against a socket that answers four calls validly and
  rejects the baseline call; it also pins the SDK premise); a third arm in `tests/test_data_agent_decoupling.py` (the standalone
  package imports nothing from `model_project_constructor`, with a self-check).
- **Docs:** `TROUBLESHOOTING.md` §FAILED_AT_DATA (the classes, a recipe that was run for reading a crash's message, the committed
  project the old baseline leak went into), `OPERATIONS.md`, `packages/data-agent/USAGE.md`, `docs/tutorial.md`; `docs/wiki/` not
  touched. **`BACKLOG.md`:** route 5 closed (`:462`); route 9 new (`:530`); route 6 notes the whole dump is committed; the
  discovery item gains point 2 (`:648`); the data stage's cost joins the intake item (`:674`); the index row counts seven again.

#### Verification
Full suite with `GITHUB_ACTIONS=true`: **3,053 passed, 9 skipped**, coverage 98%; `ruff check src/ tests/ packages/ scripts/` and
`mypy` clean; both ledger guards 82 passed. Mutation, all caught: `{e}` back at each site, `safe_message(e)` at each, a bare
`type(e).__name__` at each, six helper mutants (no length limit, no exact-`str`, no ASCII, no identifier check, unguarded read,
`__qualname__`); and after the review, inline copies of the rule at each site without the `try` and without the exact-`str` check.
Each end-to-end test fails against its own site's mutant and passes against the other's. **Runtime smoke (3E), done:** the fixture
pipeline exits 0 with `COMPLETE`; the failing scripted data stage exits 1, `FAILED_AT_DATA`, key on neither the screen nor any file.

#### The review, and what it found
One workflow: five read-only lenses (leak channels, test faithfulness, compatibility, docs and ledger, hostile inputs), two
skeptics per non-nit finding. 39 agents, 0 errors, 14.7 minutes, 3.79M subagent tokens, 896 tool uses. **17 non-nit findings and
20 nits; none refuted by every skeptic; every one low** (a skeptic called several nits). The fix itself held: the leaks lens
probed the real SDK, the CLI, the script and a fake `opencode` binary, and in every case `DataAgent.run` caught, the key was
absent from the report, the screen and the checkpoint files. What it found was around the fix. **Fixed:** the old-leak advice named
the checkpoint directory and CI logs, and missed that a baseline failure left the report `COMPLETE`, so the website stage
published the message into the generated project (three lenses, independently); "call the same client method yourself" contradicted
"the node is not recorded" and I had not run it; two diagnostics steps still said a data crash reaches the caller's handler; my
CHANGELOG said each helper mutant is caught by "at least two tests" (the `__qualname__` one by one: the parity list held no nested
class); "12 new cases", not 14; "the one place" in a title and a comment (`discovery.py` has four raw reads); my docstring's
"cannot import" was checked by nothing (the decoupling guard forbade only intake tokens). **Filed:** route 9 (`run` guards only
`invoke`, so report assembly can raise on a model reply with a bad enum), `reports/data_report.json` as the whole dump, the four raw
class-name reads in `discovery.py`, and the `opencode` version the report no longer carries (two wiki pages promise it).

### Session 278 Handoff Evaluation (by Session 279)

**Score: 9/10.**
- **+** The first recommendation was the deliverable, exactly: `BACKLOG.md:462`, `agent.py:54`, `nodes.py:211` all resolved as
  written, "reproduced by two skeptics, disk only, not the screen" was true (I reproduced it in one run), and "the sturdier fix is
  the class name, not `safe_message`" proved right when I measured what `safe_message` leaves. The harness pointer
  (`tests/scripts/test_run_pipeline_intake_error_text.py`) was the template for both new end-to-end tests, and gotchas 1 and 2
  (`uv run python`; strip `MPC_*` and `ANTHROPIC_*`, empty working directory) each saved a round trip.
- **−** It did not say the data agent is a standalone package that cannot import `orchestrator.logging._class_name`, which shaped
  the design (a copy, a parity test, and a guard I then found did not exist). And gotcha 4, "`_website_failure` is the one unguarded
  copy left", was a universal: `discovery.py` has four raw reads (#345 again, in the predecessor's prose this time).
- **ROI: high.**

### Session 279 Self-Assessment

**Score: 8/10.**
- **+** Claimed first, reproduced before the change, wrote the tests first and watched 14 fail for the right reason, mutated every
  site and the helper, kept every commit at five files or fewer, drove the second site with the real SDK and a socket instead of
  a stand-in, ran the review before closing, and fixed what it found about this diff's own tests and prose.
- **−** The review found real defects in my own work: advice that stopped where I had looked (the checkpoint directory) although I
  had read that the templates publish the caveat; a recipe and a "recorded nowhere" I wrote without running or checking
  (LangSmith exports it); a CHANGELOG count I never measured per mutant; a test helper that could end the whole pytest session
  (`INTERNALERROR`) if the code regressed. And my own mutation harness printed only pytest's last line, so a run that aborted at the
  failing test read "47 passed", four tests short: I caught it only because the count differed from the unmutated 51. I also told
  the operator the wrong commit count at the push picker.
- **Decay term:** nothing was removed from a mandated-read file. `SESSION_NOTES.md` is 121,644 B before this record (the live
  trigger is 196,608 B), `PROJECT_LEARNINGS.md` grows by three rows (it was 390,757 B), `BACKLOG.md` 149,335 → 153,194 B. **A
  twelfth trim is not due:** about five or six more closing records at this size is an estimate (about 75 KB of room over roughly
  12 KB each); the 262,144 B refusal ceiling is about 140 KB away.

**What's next** (sizes and effort are estimates unless measured; none is blocking).
1. **Route 9: `DataAgent.run` can still raise** (`BACKLOG.md:530`). Small, no ruling: put `_assemble_complete_report` inside the same
   `try`, writing `report assembly failed: ` and `safe_class_name(e)`, with a test (a model reply with an out-of-range
   `expected_row_count_order`, or fewer quality-check groups than queries) and the TROUBLESHOOTING class list gaining the case.
2. **Rulings owed, as before:** one named error class per cause for the scripted intake's stop reasons and the data stage's
   `LLMParseError` (`BACKLOG.md:655`, `:674`; adds names to two agents' surfaces); the discovery log line and the four raw class-name
   reads (`:634`, `:648`; small now that `safe_class_name` exists); `L10`'s completeness gap and second hole (`:938`, `:959`); publish
   the wiki correction (`:607`) and, new, the two wiki sentences about `opencode`'s version (`:674`); wire or stop documenting
   `MPC_LOG_LEVEL` (`:686`); whether the coverage harness from Session 277 should be committed.
3. **Observed, not filed:** `stash@{0}` (Session 270's claim commit), the branches `worktree-wf_5f96c807-d00-3` and
   `worktree-wf_c93ee390-506-3` with `.claude/worktrees/wf_5f96c807-d00-3`, the root `methodology_dashboard.py` at v2.18.0 against
   v2.19.0, Session 277's `gitleaks` count of 9 (not re-measured), `TROUBLESHOOTING.md` §FAILED_AT_DATA's first bullet ("a SQL
   query failed against the database"; a failing quality check is `ERROR` on that check and the report stays `COMPLETE`, so the
   bullet is imprecise: not changed, outside this deliverable), and `tests/agents/website/loopback.py`'s module docstring, which
   still says the module answers every request `200 {}` (it also holds `serving_raw` and now a 400 handler).

**Key files** (line numbers read off `grep -n` at this close-out).
- `packages/data-agent/src/model_project_constructor_data_agent/db.py:456` (`safe_class_name`), `agent.py:57`, `nodes.py:218`.
- `tests/agents/data/test_data_agent.py:1213-1500` (the Session 279 section, `_crash_report` at `:1279`);
  `tests/data_agent_package/test_db.py:1076` (`TestSafeClassName`); `tests/hostile_text.py` (the exotic names, at the end);
  `tests/scripts/test_run_pipeline_data_error_text.py` and `tests/agents/data/test_gateway_error_text.py` (the end-to-end pair);
  `tests/test_data_agent_decoupling.py:70-93`; `tests/agents/website/loopback.py:155` (`echo_the_api_key_in_a_400`).
- `TROUBLESHOOTING.md:115` §FAILED_AT_DATA (the recipe at `:169`); `BACKLOG.md:462, 530, 607, 634, 648, 655, 674, 686, 938`;
  `PROJECT_LEARNINGS.md` #346-348.

**Gotchas.**
1. **A mutation harness must compare the test count, not read the last line.** Against a mutant that made `run()` raise an exception
   whose class name cannot be read, pytest hit `INTERNALERROR` while formatting the failure and its last line read "47 passed".
   `_crash_report` raises its own failure outside the `except` block for that reason; keep it that way (#346).
2. **`DataAgent.run` is still not total** (route 9): the report assembly is outside its `try`, so the new docs' "becomes
   `EXECUTION_FAILED`" is true of the graph and not of the assembly.
3. **The data agent cannot import the main package** and now has a guard that says so; a rule shared with `orchestrator/logging.py`
   is copied and held in step by `test_it_agrees_with_the_orchestrators_copy_of_the_rule`, so change both or neither.
4. **`COMPLETE` is not "nothing was published".** The baseline site leaves the report `COMPLETE`, which sends it to the website
   stage; only `EXECUTION_FAILED` halts before a project exists (#347).
5. **`CLAUDE.md:122` states the learnings count and the file's size**; a close-out that appends learnings edits it (now 348, Sessions
   9–279). `docs/wiki/` was not touched, so no commit this session published the wiki.
6. Never `git stash` (#316). `uv run pytest tests/test_read_budget.py tests/test_session_notes_census.py --no-cov` before every commit
   that touches `SESSION_NOTES.md`, `CLAUDE.md` or `BACKLOG.md`. Use `uv run python`, never bare `python3`.

### What Session 278 Did
**Deliverable:** **the scripted intake runner's failure report names the exception's class and never its message — COMPLETE.**
`scripts/run_pipeline.py::_draft_incomplete_from_exception` wrote `str(exc)` into `missing_fields`; `pipeline.py` copies that
into `failure_reason`, the script prints it as `Failure: ...` and saves it in `IntakeReport.json`. I reproduced it before
touching anything: a loopback gateway that answers a 400 echoing `x-api-key` put the API key on the screen and on disk. Now the
report reads `interview_aborted: BadRequestError` and the key appears nowhere (the gateway did receive it). Closes point 1 of
`BACKLOG.md`'s "Two more places" item (now "One more place": the data agent's discovery log is what is left).
Chosen by the operator at Phase 0 from a picker (first option, recommended). **The operator also decided:** push at close-out
(yes). **Mine, and not put to the operator:** importing the log's guarded `_class_name` rather than copying the rule a third
time or promoting it to a public name (a refactor); fixing the review's eight standing findings in this session because each is
about this diff's own tests and prose; adding the `TROUBLESHOOTING.md` entry and the old-report `grep` recipe (Sessions 273 and
274 set that precedent); filing the diagnosability cost instead of fixing it (it adds exception classes to the intake agent).
**Started:** 2026-10-03 18:49. **Completed:** 2026-10-03. **Commits: four** — `6c69125` (claim, alone), `699331e` (the fix: the
script, two test files, one docstring, the ledger), `1c8c385` (docs and `BACKLOG.md`) and this close-out. Each carries its own
`CHANGELOG.md` entry; the push is recorded in the close-out's.

#### What changed
- **`scripts/run_pipeline.py`:** `reason = _class_name(exc)` (imported from `orchestrator/logging.py`: an exact-`str` ASCII
  identifier of at most 100 characters, else `<unprintable>`, and the read cannot raise) and `missing_fields=[f"interview_aborted:
  {reason}"]`. Reading the name unguarded would have been a raise site inside the `except` block; dropping `{exc}` also removed
  the other one (a `__str__` that raises). `logging.py`'s `_class_name` docstring now names the script as its second caller.
- **Tests (13 net):** the test that pinned the message as behaviour (`test_draft_incomplete_from_arbitrary_exception` asserted
  `"429 too many requests" in missing_fields[0]`) is inverted; 11 new unit cases (an exception that cannot be printed, seven odd
  class names, the 100-character limit, a metaclass whose `__name__` raises, a `str` subclass for a name); and
  `test_run_pipeline_intake_error_text.py`: the real script as a subprocess in an empty working directory against a loopback
  gateway, searching the screen and every file, plus a premise test that the SDK does put the body into its exception.
- **Docs:** `docs/tutorial.md`, `OPERATIONS.md` and `TROUBLESHOOTING.md` (an `interview_aborted:` entry under `FAILED_AT_INTAKE`,
  the leak `grep` for reports saved by earlier runs, and step 3's "where the text is"). `docs/wiki/` untouched.
- **`BACKLOG.md`:** the first point closed; a new item for the cost (`:635`); item 5 (`:462`) notes that `safe_message` leaves a
  bare `sk-ant-` token; the index rows follow.

#### Verification
Mutation: against the original script 14 of the changed and new tests fail (the end-to-end one included); against an unguarded
`type(exc).__name__` without the message, 9; against the guarded name with the message restored, the message tests and the
end-to-end test. CI's `ruff check src/ tests/ packages/ scripts/` and `mypy` clean (`ruff format --check` flags 3 files, two of them
already unformatted at `HEAD`, and CI does not run it, so I formatted only the new file). Full suite with `GITHUB_ACTIONS=true`
on the working tree: **3,019 passed, 9 skipped** (3,006 before), coverage 98.21%. The two changed test files with the run-log tests,
three runs in a row, 100 passed each. Both ledger guards 82 passed. **Runtime smoke (3E), done:** the fixture pipeline completes with exit 0; the failing
scripted intake exits 1 with `Failure: ... missing_fields=['interview_aborted: BadRequestError']` and the key nowhere.

#### The review, and what it found
One workflow: five read-only lenses (leak channels, test faithfulness, compatibility, docs and ledger, hostile inputs), two skeptics
per non-nit finding. 31 agents, 0 errors, 14.4 minutes, 2.67M tokens, 469 tool calls. **13 non-nit findings; 4 refuted by both
skeptics; 9 not refuted by every skeptic, which is 8 distinct (one raised by two lenses), all low** (one skeptic called the flaky
test medium). **None above low, no leak left on the intake path.** All eight are fixed: the `"429"` assertion that flaked about once
in 300 runs on the timestamp's digits; the search that did not cover the working directory; the tutorial listing three of the four
causes; "only these four collide" (`IntakeLLMError` has about eleven sites; every HTTP 400 is `BadRequestError`); a docstring
crediting the website stage with the guarded rule; a test docstring citing a BACKLOG title this diff renames; `TROUBLESHOOTING.md`
step 3 and the missing note on reports already on disk. Refuted, and why: the data stage's `DataReport.json` holds the key too
(true and already filed as item 5, which I annotated; it is not on the screen); model-authored `missing_fields` (the model never
sees the key); `ANTHROPIC_LOG=debug` makes the SDK's own logger print the chain and headers (opt-in, not this change); a fixture with an
integer `stakeholder_id` makes the handler raise (unchanged from `HEAD`).

### Session 277 Handoff Evaluation (by Session 278)

**Score: 9/10.**
- **+** The first recommendation was right and exact: `scripts/run_pipeline.py:206`, `BACKLOG.md:619`, `:614`, `:633` all resolved
  as written, and "with a test through the real script" set the shape of the deliverable. The observed-not-filed list (the stash,
  the two worktree branches and the directory, the dashboard at v2.18.0 against v2.19.0) was still true at Orient, and the size
  estimate (about 107 KB) was within 2 KB of the measured 108,822 B. Gotcha 7 (never `git stash`; both guards before a ledger commit)
  saved two decisions.
- **−** It did not point at a template for a real-script test: `tests/scripts/test_run_pipeline_website_crash_resume.py` and
  `tests/agents/website/loopback.py::serving_raw` were the model, and the fact that the Anthropic SDK honours `ANTHROPIC_BASE_URL`
  (which makes the intake path drivable offline) took a grep and a probe to find. And the item it recommended called the fix
  "small, class name only" without saying the exception is swallowed, so the name is all that survives (filed as the new item).
- **ROI: high.**

### Session 278 Self-Assessment

**Score: 8/10.**
- **+** Claimed first; reproduced the leak end to end before the fix; wrote the tests first and watched them fail; checked the tests
  can fail with three mutants, twice (once more after I changed the end-to-end test); found the existing test that pinned the leak
  and inverted it; kept the commits under the five-file cap; ran the review before committing rather than after; fixed what it found
  and filed, with measurements, what I had not seen (the wider name collision).
- **−** Four statements I wrote were universals that were false or unchecked (the tutorial "lists the four", "only these four
  collide", a docstring crediting the website stage, "cannot import"), each written right after reading code that contradicts it
  (#345). My first unit assertion flaked on a timestamp (#344) and I had not run it enough times to see it. A probe ran under the
  system Python 3.10 (bare `python3` is miniforge's here; `uv run python` is the project's) and cost one round trip. A test docstring
  cited a BACKLOG title my own diff renamed.
- **Decay term:** nothing was removed from a mandated-read file this session: `SESSION_NOTES.md` grew by this record,
  `PROJECT_LEARNINGS.md` by three rows (to 390,757 B), `BACKLOG.md` by about 3 KB net. **A twelfth trim is not due:** the live file
  is about 121 KB (measured with `wc -c` just before the commit) against the 196,608 B trigger, about six more closing records at this
  size (an estimate: about 75 KB of room over roughly 12.5 KB each), and the 262,144 B refusal ceiling is about 141 KB away.

**What's next** (sizes and effort are estimates unless measured; none is blocking).
1. **The scripted intake's four stop reasons now share one class name** (`BACKLOG.md:635`, with the wider `IntakeLLMError` and
   HTTP-status collision the review measured). Small, a choice: one `RuntimeError` subclass per cause at `agent.py:141, 149, 153,
   157`. It adds names to the intake agent's surface, so it is yours to rule on before anyone builds it.
2. **The data stage still writes the key into `DataReport.json`** (`BACKLOG.md:462`, item 5, `agent.py:54` and `nodes.py:211`;
   reproduced by two skeptics this session, disk only, not the screen). Medium. The sturdier fix is the class name, not
   `safe_message`; the harness this session used is the recipe: `tests/scripts/test_run_pipeline_intake_error_text.py`
   with a gateway that answers a few calls validly and then a 400 (the review did this in its scratch directory; it is not kept).
3. **Rulings owed, as before:** `L10`'s completeness gap and its second hole (`BACKLOG.md:927`), publish the wiki correction
   (`BACKLOG.md:593`, point 1), wire or stop documenting `MPC_LOG_LEVEL` (`BACKLOG.md:654`), the discovery log line (`BACKLOG.md:620`),
   and whether the coverage harness from Session 277 should be committed.
4. **Observed, not filed:** `stash@{0}` (Session 270's claim commit), the branches `worktree-wf_5f96c807-d00-3` and
   `worktree-wf_c93ee390-506-3` with `.claude/worktrees/wf_5f96c807-d00-3`, the root `methodology_dashboard.py` at v2.18.0, and
   Session 277's `gitleaks` count of 9 (not re-measured). New: `ANTHROPIC_LOG=debug` prints the SDK's exception chain and response
   headers to stderr (opt-in, refuted as a defect here; worth one sentence in `OPERATIONS.md` if anyone documents that variable).

**Key files** (line numbers read off `grep -n` at this close-out).
- `scripts/run_pipeline.py`: the import (`:97`), `_draft_incomplete_from_exception` (`:182-247`), the `runner()` closure (`:284-301`).
- `src/model_project_constructor/orchestrator/logging.py:58-84` (`_class_name`, now with two callers).
- `tests/scripts/test_run_pipeline_intake_error_text.py` (the template for a real-script, secret-absence test) and
  `tests/scripts/test_run_pipeline_adapter.py:51-172` (the new unit cases).
- `TROUBLESHOOTING.md` §`FAILED_AT_INTAKE`; `BACKLOG.md:462, 593, 620, 635, 654`; `PROJECT_LEARNINGS.md` #343-345.

**Gotchas.**
1. **Use `uv run python`, never bare `python3`** (3.10 here; the project needs 3.11+). A script that imports `datetime.UTC` fails
   under it with an `ImportError` that looks like a project bug.
2. **A real-script test must strip `MPC_*` and `ANTHROPIC_*` from the environment it passes** and run in an empty working
   directory; the script loads no `.env`, but the checkout has one. `ANTHROPIC_BASE_URL` redirects the SDK to a loopback server.
3. **Do not reformat `scripts/run_pipeline.py` or `test_run_pipeline_adapter.py`:** both were unformatted at `HEAD` and CI does not
   run `ruff format`, so a format pass is a whole-file diff in an unrelated change.
4. **`_class_name` is private and two things now depend on it.** `pipeline.py::_website_failure` is the one unguarded copy left
   (`BACKLOG.md:578`); it does not import `logging.py` by that module's own design, so the fix there is the same four lines inline.
5. **`CLAUDE.md:122` states the learnings count and the file's size**; a close-out that appends learnings edits it (now 345, Sessions
   9–278, 390.8 KB). `docs/wiki/` was not touched, so no commit this session published the wiki.
6. Never `git stash` (#316). `uv run pytest tests/test_read_budget.py tests/test_session_notes_census.py --no-cov` before every commit
   that touches `SESSION_NOTES.md`, `CLAUDE.md` or `BACKLOG.md`.

### What Session 277 Did
**Deliverable:** **the eleventh trim of `SESSION_NOTES.md` — COMPLETE.** Sessions 269 → 258 (twelve records, 1,702 lines,
126,395 B, a pure byte slice) are in
[`docs/architecture-history/SESSION_NOTES-S269-through-S258.md`](docs/architecture-history/SESSION_NOTES-S269-through-S258.md)
(1,754 lines, 129,691 B) beside its proof. The live file fell from 221,099 B to 94,821 B and keeps this record plus seven
non-stub ones (276 → 270). The front-matter table gained a row, and the previous row's pending marker resolved to `49d23b7`.
The proof adds **no** assertion (ruling F) and ships 109 mutants, none new. Chosen by the operator at Phase 0 from a picker
(first option, recommended). **The operator also decided, at the commit gate (a two-question picker):** the eight-file commit
is acknowledged (it is over `SAFEGUARDS.md`'s cap of five; a shard proof reads its prose at its own commit, so no subset is
green), and **push at close-out**. **Mine, and not put to the operator:** the cut point (the fewest-records rule the ninth and
tenth used), taking the derived back half over the prototype's, running the coverage loops instead of carrying the tenth's
figures, and filing rather than fixing what the review found outside the trim. **Started:** 2026-10-03 14:18.
**Completed:** 2026-10-03. **Commits: four** — `01a39dd` (claim, alone), `b461d7d` (the trim, **no record edit, eight
files**), `1259116` (the review's filings, `BACKLOG.md` only) and this close-out. Each carries its own `CHANGELOG.md` entry;
the push is recorded in the close-out's.

#### The cut, and the ledger
The byte rule fired at 221,099 B (220,549 B before the claim stub: this stub's own first line said the second figure, the
proof's L11 line prints the first, and both are true of different states). Keeping Session 269 lands at 106,141 B before the
front-matter edits, over the 98,304 B stop, so the fewest-records cut is 269 → 258: twelve headings, none an abandoned stub
this time (the tenth moved one). Front matter 7,569 B → 7,686 B (limit 8,192; the read-budget guard's own model leaves it
about 318 B, so **roughly two more trims** before it binds: an estimate from the guard's constants and the growth per trim).
Probe: an explicit whole-file `Read` of the new shard reports **50,371 tokens** against the 25,000-token cap, so a default
`Read` truncates; the figure is in `BACKLOG.md`'s read-cap item beside the tenth's.
**The sweep, published as a dated fact** (CLAUDE.md asks for it, never the old sentence repeated): at `b461d7d`,
`git grep -l 'SESSION_NOTES-[A-Za-z0-9-]*\.md'` returns **35** files (eleven shards, eleven proofs, two collapse proofs, the
four prose files, this ledger, `PROJECT_LEARNINGS.md`, two planning documents, the census guard, and the two append-only logs
`CHANGELOG.md` and `HANDOFFS.md`); the broad `SESSION_NOTES-` form returns **37**, the extra two being `.github/workflows/ci.yml`
and `docs/architecture-history/evolution-page-plan.md`. Session 266 published 32 and 34; the new shard and proof are two of the
difference and `HANDOFFS.md`, which names the tenth shard in its own receipt, is the third. The seventh re-derivation found no
fifth prose file. `ci.yml` and `evolution-page-plan.md` are outside every proof's reach and the census guard; `ci.yml` states
Session 253's counts in the present tense (filed already, `BACKLOG.md:87`).

#### The proof: carried forward, nothing added, coverage re-measured
Every function but `self_test` is AST-identical to the tenth's (one docstring, `compose_row`'s, was re-dated; measured with
`ast.dump`, 33 functions each). What changed is declaration: the cut key, the routing table, the tenth proof added to
`ANCESTOR_PROOFS` frozen at `49d23b7`, the sizes, the row, the span sentences, the tenth shard's figures in `L14` (44 literals
carrying 63 figures), four front-matter substitutions each anchored on text the tenth trim wrote, and the banner. 0 of the
tenth proof's 111 declared literals were absent at the claim commit; 26 stop matching under this cut (19 required prose strings,
2 size literals, 1 lineage literal, 4 front-matter), exactly the re-declaration worklist.
**The coverage harness, which the proof's header says is described here.** It copies the proof file, neuters ONE statement in
the copy and runs `bash <copy> --self-test` in a clone whose artifacts do not change for the run: (a) each of the fifteen
`fails += Ln(...)` statements in the main flow becomes `pass`; (b) each of the 68 failure-emitting statements inside `L0`-`L14`,
located with `ast` (an `out.append(...)` expression statement, or a `return [...]` of a non-empty list literal), becomes `pass`
or `return []` (type-preserving: learning #191). Every run's exit code must be 0 (every mutant caught) or 2 (survivors, named on
`SURVIVED` lines); anything else is a broken run, never a clean one (learning #190). A mutant that survives a neutered statement
is one that statement alone catches. **It was validated on the tenth proof first**: its fifteen whole-assertion lists matched the
tenth header's published ones exactly. Result for this proof: the same lists, and arm for arm the same 68 arms, **48 with a sole
catcher and 20 without**, 166 runs on the two proofs, none broken. The script is about 80 lines and is not in the repo.

#### Two workflows, and what they found
- **Map** (six read-only scouts, one per surface: 1.59M tokens, 438 tool calls, 40 min, 0 errors). Every FACT I gave was
  confirmed (one trivial miscount: the proof diff is 606 changed lines, not 604). One scout built a whole prototype of the cut in
  a scratch clone although it was told to map; another derived the proof's back half independently. **Diffing the two found a
  false comment in the prototype that no test could see** (#339), and I took the derived one. I rebuilt the chain myself
  with the real prose and measured figures rather than using the prototype's analog placeholders.
- **Review** (five lenses, two skeptics per non-nit finding: 37 agents, 0 errors, 57 min, 3.77M tokens, 980 tool calls): 24
  findings, 8 of them nits; 16 non-nit verified (6 confirmed by both skeptics, 6 refuted by both, 4 split); **none above low after
  verification, no blocker**; 83 clean checks, including a byte-for-byte recomputation of the cut, about fifty perturbations of
  the amended trim commit (each red for the expected arm, except holes already filed or filed below), and a rehearsal of the
  real application (eight files, all 13 proofs in both modes, the full suite). **What it found that mattered:** three comments in the new header were wrong (a count of
  differing labels was 14 not 13 because I measured it before my own label fix; an M58 comparison called "in reverse" that is the
  same direction at the tenth; a carried sentence crediting this trim's review with the tenth's finding): **fixed before the
  commit** (#340). Three `BACKLOG.md` sentences this trim made stale and a quotation item whose records are now archived:
  **fixed in `1259116`**. One gap, **inherited and filed**: `L10`'s hand-typed list of ancestor proofs is checked against
  nothing, so dropping the newest proof's entry leaves every proof and guard green (#342; an operator call, since it adds an
  assertion).

#### Verification
All 13 proofs in both modes green in committed mode in the real tree (the new proof prints `source : the trim commit b461d7d`);
both guards 82 passed; the full suite on a clone of the committed tree, `GITHUB_ACTIONS=true`, Python 3.13.5 with the `agents`,
`ui` and `dev` extras: **3,006 passed, 9 skipped**. `ruff` and `mypy` were not run: no code changed. **Runtime smoke (3E): n/a,
docs and ledger only**; the proofs and guards are this deliverable's runtime and were run above.

### Session 276 Handoff Evaluation (by Session 277)

**Score: 8/10.**
- **+** The first recommendation was the right deliverable, with the figure that triggered it (220,549 B) exact and the
  instruction to say at Phase 0 whether to do it first, which became the picker. The gotchas I used: never `git stash`, both
  guards before each commit that touches the ledger, the shell is zsh, and the observed-not-filed list (the stash, the worktree
  branch and directory, and the stale dashboard copy were all still true at this Orient).
- **−** One wrong figure: it said the file sat under the 262,144 B refusal ceiling by "about 50 KB, roughly four more closing
  records"; the measured margin was 41,595 B, about three records. It also did not say what a trim costs (a full session with a
  mapping and a review workflow); Session 266's record did, and I used that instead.
- **ROI: high.**

### Session 277 Self-Assessment

**Score: 8/10.**
- **+** Claimed first and ran both guards at the claim state (green). Mapped with parallel scouts before building, then built in
  a scratch clone from scripts, never by hand-editing a write-once file, and applied to the real tree only after a review.
  Validated the coverage harness against a published result before trusting it. Verified committed mode in the real tree, and
  asked the operator at the two gates (the cap, the push) rather than assuming the tenth's answer.
- **−** The review caught three defects in text I wrote or carried into a header (#340): one figure measured before my own last
  edit, one comparison I took from a scout without checking it against the tenth proof, one sentence copied verbatim. I also
  wrote the header's pointer to this record before the description existed, the tenth's unkept promise repeated (#341): I
  caught it only because a lens did. The mapping scouts were told to stay read-only and one built a prototype anyway (benign:
  scratch only, and it served as the cross-check).
- **Decay term:** this is the first close-out in some time that removed something from a mandated-read file: `SESSION_NOTES.md`
  221,099 B to 94,821 B at the trim, then this record. `BACKLOG.md` grew 143,640 B to about 146 KB and `PROJECT_LEARNINGS.md`
  384,494 B to 387,823 B. **A twelfth trim is not due:** after this record the live file is roughly 107 KB against the
  196,608 B trigger, about seven more closing records at 12-13 KB (an estimate), and the 262,144 B refusal ceiling is 155 KB away.

**What's next** (sizes and effort are estimates unless measured).
1. **`scripts/run_pipeline.py:206` writes a raw intake exception into the saved report and the printed `Failure:` line**
   (`BACKLOG.md:619`, point 1 of the item at `:614`; two skeptics confirmed it last session, medium). Small: class name only,
   with a test through the real script. Still the one place a secret can reach disk and the screen with a live model.
2. **Rulings owed**, none blocking: `L10`'s completeness gap (`BACKLOG.md:885`, filed this session); publish the wiki
   correction (`BACKLOG.md:587`, point 1); wire or stop documenting `MPC_LOG_LEVEL` (`BACKLOG.md:633`); and the standing list
   in Session 273's record. **Decide whether the coverage harness should be committed**: it is described above and exists
   only in this session's scratchpad.
3. **Observed, not filed:** a `gitleaks detect` of the whole history reports **9 findings** (measured here: 676 commits), all
   fake token fixtures in tests that Sessions 273-276 added (`glpat-` and generic-key shapes under `tests/`); none is from
   this trim. Worth settling (an allowlist, or fixtures that do not match a scanner's shapes) before any scan the
   enterprise-migration plan relies on. Also unchanged: `stash@{0}` (Session 270's claim commit; the operator's call), the
   branches `worktree-wf_5f96c807-d00-3` and `worktree-wf_c93ee390-506-3` and the directory `.claude/worktrees/wf_5f96c807-d00-3`,
   the root `methodology_dashboard.py` at v2.18.0 against v2.19.0 (`bin/sync`'s job), and `ruff format --check` not re-measured.

**Key files** (line numbers read off `grep -n` at this close-out).
- `docs/architecture-history/SESSION_NOTES-S269-through-S258.md.verify.sh`: `:140-141` (the cut key), `:174` (`REACH`), `:247`
  (`ANCESTOR_PROOFS`), `:285` (`WORDS`, which stops at twelve), `:321` (`LINEAGE_CENSUS`), `:393` (`BANNER`), `:450`
  (`FRONT_SUBST`), `:1319` (`self_test`), `:1574` (M58's derived floor). Read its header first.
- `BACKLOG.md:885` (collapse-proof item, now with the `L10` list gap), `:919` (the quotation item), `:946` (table rows
  after the eighth), `:614` (the two older routes), `:633` (`MPC_LOG_LEVEL`).
- `PROJECT_LEARNINGS.md` #339-342. `CHANGELOG.md` the S277 entries under `## 2026-10`.

**Gotchas.**
1. **How the twelfth trim should be built** (the scripts are not kept; this is the recipe): claim; map with scouts (surfaces: the
   proof's declarations, its mutants, the prose copies, the guards, the working-tree readers, the sweep); build in a scratch
   clone from scripts (shard and live file; the prose edits with every anchor asserted unique; the proof by transforming the
   eleventh's declarations, then its back half, then its header); measure every figure the header and prose state **after the
   last edit**; run both modes of every proof, both guards and the full suite in a clone of the committed tree; review; apply.
2. **The twelfth's four front-matter substitutions must be anchored on text this trim wrote:** the write-once ordinal sentence,
   the bequest addressee, the trim count, and the newest table row's pending marker. All four occur exactly once now.
3. **`WORDS` stops at twelve and this cut archived exactly twelve.** A cut of thirteen or more needs the table extended (a
   declaration in the proof's front half) or the size check reports a figure nobody derived.
4. **M58 has zero slack whenever exactly one claim stub is retained**; a second retained stub fails its assertion loudly. Its floor
   must stay derived (non-stub count plus one), never typed.
5. **A record must not quote the newest table row word for word** (four guard tests go red: measured by the review), nor any of
   the older rows or the heading paragraph of the front matter (the collapse proofs count occurrences across the whole file).
   This record paraphrases. Quoting the first 60 characters of a row is green.
6. **The trim commit is eight files by necessity;** ask the operator at the commit gate as this session did.
7. Never `git stash` (#316). `uv run pytest tests/test_read_budget.py tests/test_session_notes_census.py --no-cov` before every
   commit that touches `SESSION_NOTES.md`, `CLAUDE.md` or `BACKLOG.md`. **Any commit that touches `docs/wiki/` publishes it.**
   None of this session's did.

### What Session 276 Did
**Deliverable:** **`agent.error` now carries the exception's class and never what it said — COMPLETE**, closing `BACKLOG.md`'s item
*"The run log records the full text of any exception a runner raises"* (removed; its residue and two further findings filed).
Chosen by the operator at Phase 0 from a picker (first option, labelled "Run-log redaction"). **The choice inside it, drop the
message rather than redact it, was mine** (the default Session 275 had already ruled for the website stage's `failure_reason`,
and a redaction that needs no secret cannot find a bare token); it was not put to the operator. **Push at close-out** and **the
wiki stays filed, not corrected now** were put to the operator (picker). **Started:** 2026-10-02 23:14. **Completed:** 2026-10-02.
**Commits: seven** — `15d59b6` (claim, alone), `4dc186f` (the fix), `04bb807` (operator guides), `bd6f71f` (BACKLOG), `97cd878` (the
review's code and test findings), `29e2f46` (the review's doc corrections) and this close-out. Each carries its own `CHANGELOG.md`
entry; the push is recorded in the close-out's.

#### What changed
- **The fix (`orchestrator/logging.py`).** `make_logged_runner`'s `agent.error` context is `agent`, `run_id`, `correlation_id`,
  `duration_ms`, `error_type`: no `error_message`, no `exc_info`, and the exception's text, repr and arguments are never read.
  `_class_name` (`:58`) is the rule `_website_failure` applies (a name that is not a short ASCII identifier, or is over 100
  characters, becomes `<unprintable>`) and is stricter in two ways: it fails closed if reading the name raises, and it requires an
  exact `str`. The event is emitted **after** the `except` block (`:125-159`, `failure = exc` … `raise failure`), because a log
  handler that fails while writing has the exception being handled chained to its own failure and `logging` prints the chain.
- **Tests: 2,940 to 3,006 passed, 9 skipped, coverage 98.21%** at CI scope (`GITHUB_ACTIONS=true uv run pytest`, Python 3.13.5;
  `logging.py` 100%); `tests/orchestrator` and the end-to-end file, 362 passed on 3.12.13 (CI's interpreter). +66: the new file
  `tests/orchestrator/test_logging_error_text.py` (12 kinds of exception that hold text in the message, a filename, a cause, a
  context, a group, a repr, a real pydantic error and a real `httpx` port error; an exception that cannot print; a 2,000,000-character
  message; six odd class names and two hostile metaclasses; a failing log sink; the cause, context and traceback left alone; the script's
  own `make_measured_runner` + `make_logged_runner` composition inside `run_pipeline`; a test that the capture reaches `DEBUG` records
  on any logger; the premise of the real-exception cases). One assertion in `test_logging.py` changed.
- **Docs.** `OPERATIONS.md` section 3.1 and `TROUBLESHOOTING.md` (the structured-logs step, the unhandled-exception bullet, and Session
  275's own `unexpected_error:` entry, which said the log has the message); `BACKLOG.md` (item closed; residue item; a second item
  for `MPC_LOG_LEVEL`; a third for two older routes the review found; Session 275's residue corrected and given points 7 and 8);
  `PROJECT_LEARNINGS.md` #333-338; `CLAUDE.md` (the count). **The wiki is not edited** (a commit under `docs/wiki/` publishes it).

#### Measured first, then built
- **Scouted inline, no sub-agents** (the surface was one function): the callers (`scripts/run_pipeline.py::instrument`), the docs that
  name `error_message` (`OPERATIONS.md`, `TROUBLESHOOTING.md`, two wiki pages), and that **nothing installs a log handler**: `MPC_LOG_LEVEL`
  is parsed into `settings.log_level` and read by nothing (filed). With no handler Python prints only the bare words `agent.error`.
- **Red first, read:** 32 of the first 49 tests failed on the unchanged handler, each for the leak it was written to catch (the other
  17 pin what must not change; one, `_CannotBePrinted`, shows the old handler let a raising `__str__` replace the runner's exception).

#### The checks, each finding what the last could not
- **Mutation, two passes: 23, then 35 mutants, all caught** — after one survivor of the second pass, `raise failure from None`, which
  overwrites the exception's own `__cause__` and passed every identity check; three tests now pin cause, context and traceback.
- **The review** (4 lenses, 2 skeptics per non-nit finding: **38 agents, 0 errors, 11.6 minutes, 3.18M tokens, 564 tool calls**): 26
  findings, 17 non-nit, **16 confirmed by both skeptics, 1 refuted by both; none rated above medium by a skeptic.** It found what my
  tests could not: **(1)** the emit inside the `except` block leaked the runner's message through `logging`'s own failure report when a
  handler could not write (reproduced); **(2)** `_class_name` could itself raise (a metaclass `__name__`) and accepted a `str`
  subclass; **(3)** my fixture watched one logger at `INFO`, so a `DEBUG` record, the root logger, `stderr`, `print` and
  `warnings.warn` all survived (#336); **(4)** two probes read the checkout path; **(5)** Session 275's `unexpected_error:` entry in
  `TROUBLESHOOTING.md` and its BACKLOG point 1 still said the log has the message, and "the caller's traceback" is not true of a website
  crash; and **(6) the premise was false**: `httpx.InvalidURL` does not quote a project id placed in a URL path (it quotes a refused host
  or port), so Session 275's `echoed-id` case never had the token in the exception's text and I had repeated the claim in six places
  (#333). **Fixed** in `97cd878` and `29e2f46`. **Filed, not fixed:** two older routes (`scripts/run_pipeline.py:206` writes a raw intake
  exception into a saved report; the data agent's probe logs a model failure through a masker that cannot see a bare token),
  `_website_failure`'s unguarded name read, and the website crash's text now being recorded nowhere.
- **Runtime smoke (3E):** the real script in its no-credentials mode, through the real `instrument()`, ran the pipeline to completion
  (five checkpoint files); the real `instrument()` with a JSON handler installed as `OPERATIONS.md` section 3.1 shows, around a runner that
  raises, logged `agent.error` with `error_type` only, and the exception propagated with its message intact.

### Session 275 Handoff Evaluation (by Session 276)

**Score: 7/10.**
- **+** The first recommendation was the right deliverable and its lines were exact (`BACKLOG.md:572`, `logging.py:94-105`). The
  gotchas I used: CI's interpreter and its command (#325: I built the 3.12 environment from it), never `git stash`, both guards before
  each commit. The decay-term disclosure that the eleventh trim is due was accurate. Its test helpers (the odd class names, `_intake()`)
  were reused for the parity test.
- **−** **A premise it handed me was false.** The item, and the `echoed-id` case's comment, said `httpx.InvalidURL` quotes the URL, so
  a host-echoed token reaches the message. It does not for a path (measured, 0.28.1 and 0.27.0); I took it from the handoff and wrote
  it into six places. "Small, no ruling" held for the code but the item hid a real choice (drop or redact). Gotcha 3 ("the
  `agent.error` log context has the message") was made false by this very change, and so were Session 275's `TROUBLESHOOTING.md`
  entry and BACKLOG point 1, which said the same. "Small" understated again: seven commits, a review and two mutation passes.
- **ROI: high.**

### Session 276 Self-Assessment

**Score: 7/10.**
- **+** Scouted proportionately (inline, for one function), red first and read, a real-socket-free but real-composition test, two
  mutation passes, a review whose findings were triaged one by one (what belonged to the change fixed, the rest filed with the line and
  the reproduction), the false premise corrected everywhere it was written including in Session 275's artifacts, tests run on CI's
  interpreter, a runtime smoke through the real script, and the two outward-facing questions (push, wiki) asked rather than assumed.
- **−** **I repeated an unchecked premise into six places before a skeptic ran one line of `httpx`** (#333). **I wrote #329 last session
  and did not apply it to my own fixture** (#336). My first hostile-name test crashed pytest itself (#335). I committed the BACKLOG
  filing while the review was still reading the tree, so it reviewed a tree I was still changing. A wrong figure again, caught on
  re-measuring: `BACKLOG.md` 139,515 B written, 139,616 B true at that commit (corrected in the ledger). "Redaction", in the picker's
  label, was my word for a choice that turned out to be a removal; the operator chose the item, not the removal.
- **Decay term:** nothing removed from a mandated-read file except the closed item. `BACKLOG.md` 136,624 to 143,640 B,
  `PROJECT_LEARNINGS.md` 379,328 to 384,494 B, `SESSION_NOTES.md` 206,863 to 220,549 B against the 196,608 B trigger.
  **The eleventh trim is due, for a second session.**

**What's next** (sizes and effort are estimates unless measured).
1. **The eleventh `SESSION_NOTES.md` trim is due** (its own deliverable: claim, trim, close out; two commits and no record edit in the
   trim commit). Say at Phase 0 whether to do it first; the guards are green, so nothing is red, and the file is under the 262,144 B
   refusal ceiling by about 50 KB, which is roughly four more closing records.
2. **`scripts/run_pipeline.py:206` writes a raw intake exception into the saved report and the printed `Failure:` line**
   (`BACKLOG.md:614`, point 1; two skeptics confirmed, medium). Small: class name only, with a test through the real script. The first
   of the small ones, because a secret can reach disk and the screen with a live model.
3. **Small leftovers, each filed with its line:** `_website_failure`'s unguarded class-name read (`BACKLOG.md:574`); the saved reason and
   project URL printed when `--resume` refuses, and an atomic `CheckpointStore.save_result` (`BACKLOG.md:532`, points 2 and 3).
4. **Rulings owed:** publish the wiki correction (`BACKLOG.md:587`, point 1; it publishes on commit); wire `MPC_LOG_LEVEL` or stop
   documenting it (`BACKLOG.md:633`); a caller-supplied scrubber on `make_logged_runner` (`BACKLOG.md:587`, point 2); a frame in the
   failure reason; a hard-kill marker; a repeated `--run-id`; a Python 3.12 pin or a matrix; and the standing list in Session 273's record.
5. **Observed, not filed:** `stash@{0}` (Session 270's claim commit; the operator's call); the branch `worktree-wf_c93ee390-506-3` and
   `.claude/worktrees/wf_5f96c807-d00-3` (both still present); the root `methodology_dashboard.py` is v2.18.0 against v2.19.0 (`bin/sync`'s
   job); `uv run ruff format --check` was reported by Session 275 to reformat 14 of 20 test files in the touched directories and
   was not re-measured here (CI runs `ruff check` only).

**Key files** (line numbers read off `grep -n` at this close-out).
- `src/model_project_constructor/orchestrator/logging.py:58` (`_class_name`; its docstring is the specification of the rule), `:83`
  (`make_logged_runner`; its docstring says what `agent.error` never carries), `:125-159` (`wrapped`: `failure = exc` at `:136`,
  `raise failure` at `:159`).
- `tests/orchestrator/test_logging_error_text.py:204` (the `log` fixture: root logger at `DEBUG`, `capfd`, recorded warnings),
  `:417` (`_caught`), `:318` (cause, context, traceback), `:452` (the failing sink), `:494` (the premise of the real-exception cases),
  `:512` (the script's composition inside `run_pipeline`).
- `OPERATIONS.md:101-125` (section 3.1, what is and is not logged); `TROUBLESHOOTING.md:165-182` (`unexpected_error:`) and the
  structured-logs step at `:28`; `BACKLOG.md:532` (Session 275's residue, points 7 and 8 at `:574`, `:580`), `:587` (this session's
  residue), `:614` (two older routes), `:633` (`MPC_LOG_LEVEL`); `PROJECT_LEARNINGS.md` #333-338; `CHANGELOG.md` the S276 entries under
  `## 2026-10`.

**Gotchas.**
1. **Do not "simplify" the wrapper back to a bare `raise` inside the `except`.** The failing-sink test
   (`TestAFailingLogSink`) pins the placement and a mutant for it is in the session scratchpad's harness (not kept). `raise failure`
   outside the block keeps cause, context and traceback; `raise failure from None` would not (three tests).
2. **A website crash's text is recorded nowhere now** (the log carries the class, `run_pipeline` saves the class). Session 275's gotcha
   3 ("the `agent.error` log context has the message") is false; so is the same sentence in its `HANDOFFS.md` receipt. To see one, run
   the website stage by itself against a scratch namespace.
3. **`_class_name` and `_website_failure` agree only for ordinary classes** (the parity test); the website copy does not guard a raising
   `__name__` (filed).
4. **A test with a hostile exception class must catch the exception itself** (`_caught`): pytest formats a failure with `type.__name__`
   and an `INTERNALERROR` ends the run (#335).
5. **Check a library's message before writing it into a doc** (#333): `httpx.URL` quotes a refused host or port and not a path;
   a pydantic `ValidationError` quotes its input. `TestTheRealExceptionsHoldTheToken` pins both, so a release that changes either fails
   there with a name instead of making the other cases pass vacuously.
6. A `( cmd ) &` inside a `run_in_background` call completes at once (#338). Never `git stash` (#316).
   `uv run pytest tests/test_read_budget.py tests/test_session_notes_census.py --no-cov` before every commit that touches
   `SESSION_NOTES.md`, `CLAUDE.md` or `BACKLOG.md`. **Any commit that touches `docs/wiki/` publishes it.** None of this session's did.

### What Session 275 Did
**Deliverable:** **a website stage that raises, or is interrupted, now leaves a saved FAILED result, so `--resume` refuses instead of
creating a second project on the host — COMPLETE**, closing `BACKLOG.md`'s item *"A website stage that raises something other than a
`RepoClientError` saves no result"* (removed; its residue and a log item filed). Chosen by the operator at Phase 0 from a picker (the
resume duplicate). **The operator's choices (a two-question picker, then a typed `1`, which I read as option 1 of each; not two
separate rulings):** catch in the orchestrator only; convert an ordinary exception into a clean exit 1. **Push at close-out** (picker).
**Started:** 2026-10-02 20:53. **Completed:** 2026-10-02. **Commits: seven** — `738f836` (claim, alone), `36a4172` (the fix),
`2f5dea7` (the real script against a real socket), `6d989ee` (the review's code and test findings), `13d30c8`, `c5765b9` (docs) and this
close-out. Each carries its own `CHANGELOG.md` entry; the push is recorded in the close-out's.

#### What changed
- **The fix (`orchestrator/pipeline.py:476-505`, `_website_failure` `:644`).** The runner call in the website stage is wrapped.
  `except Exception` builds a FAILED `RepoProjectResult` (`unexpected_error: <ClassName> (the website stage may already have created a
  project on the repository host)`) and falls into the normal save and `FAILED_AT_WEBSITE` halt (exit 1). `except BaseException`
  (`KeyboardInterrupt`, `SystemExit`) saves `interrupted: <ClassName> (...)` and **re-raises**, so Ctrl-C still stops the run. The
  reason names the class and never the message; a class name that is not a short ASCII identifier becomes `<unprintable>`; id, URL and
  commit are empty; governance fields come from the intake report. Nothing before the website stage is caught.
- **Tests: 2,894 to 2,940 passed, 9 skipped, coverage 98.21%** at CI scope (`GITHUB_ACTIONS=true uv run pytest`, Python 3.13.5); the same
  2,940 and 9 on 3.12.13 (CI's interpreter). +46: `tests/orchestrator/test_pipeline_website_failure.py` 41 (seven exception kinds, odd
  class names, two interrupt kinds, saved once and after the runner, the screen and the log captured, a disk-full save) and
  `tests/scripts/test_run_pipeline_website_crash_resume.py` 5 (the real script against a socket: three crashes, a host that echoes the
  token as the project id, a real SIGINT; each then `--resume`, which exits 2 with the host's `POST /projects` count unchanged).
- **Docs.** `TROUBLESHOOTING.md` (`unexpected_error:` and `interrupted:` entries), `OPERATIONS.md` section 5, `BACKLOG.md` (item closed;
  residue and a log item filed; Route 7 and 8 text; the 3.14 note), `PROJECT_LEARNINGS.md` #327-332, `CLAUDE.md` (the count).

#### Measured first, then built
- **Four read-only scouts** (the website agent, the orchestrator and resume, the tests, a reproduction; 630,630 tokens): reproduced on
  the unchanged tree. Run 1 exits 1, no result file, one project; `--resume` prints `RESUMED from: website` and makes project 1002 (with
  real GitLab naming, `-v2`: three POSTs); the SIGINT variant is the same; a `RepoClientError` saves FAILED and `--resume` refuses.
  They also showed that a catch in the nodes cannot cover the scaffold nodes, `build_repo_project_result` (it can fail after a
  successful commit) or an interrupt, and that `determine_resume_point` reads that one file.
- **Red first, read:** 28 of 32 unit tests failed on the unchanged tree (the exception escaped; no file), the other 4 pin behaviour that
  must not change; all 4 end-to-end tests failed on it as well (on the traceback assertion, which is *earlier* than the token one: see #328).

#### The checks, each finding what the last could not
- **Mutation, two passes: 27 mutants, all caught** (17 on the handler; 10 on the leak channels and the class-name guard). A first M16 was
  an equivalent mutant of my own making (`None or ...`) and was redone. Files restored byte for byte (`cmp`).
- **The review** (4 lenses, 2 skeptics per non-nit finding: **30 agents, 0 errors, 25 minutes, 2.84M tokens, 555 tool calls**): 16
  findings (13 checked, 3 nits), **4 confirmed by both skeptics, none above low.** It found what my tests could not: a handler edit that
  `print`ed or logged the exception passed every test (the tests never captured the screen or the log), the end-to-end token assertions
  could not fail (no vector carried the token), the Ctrl-C test waited 120 s for a child that had died, the raw `\x1b` check on a JSON file
  could not fail, and the 100,000-deep JSON case fails on Python 3.14. **Fixed** (`6d989ee`) with the class-name guard, which two skeptics
  rated a nit and I added anyway: the docstring said "a class name is chosen by code" and nothing enforced it. **Filed, not fixed:** the
  stack is gone (confirmed), the non-atomic result write, a hard kill, a repeated `--run-id`, the log context (pre-existing).

### Session 274 Handoff Evaluation (by Session 275)

**Score: 8/10.**
- **+** The first recommendation was the right deliverable and its line numbers were exact (`:528`, `:506`, `:545`). The decay-term
  disclosure of `SESSION_NOTES.md`'s size (195,311 B) was accurate and let me say at Phase 0 that the trim is due. Gotcha 1 (CI's
  interpreter, with the command) was used verbatim and paid off twice; gotchas 4 (never `git stash`; saved copies and `cmp`) and 5 (both
  guards before each commit) were used as written.
- **−** "Small" understated: the change is about 50 lines, but it needed four scouts, a decision, six commits and a review. The
  reproduction recipe omitted that the host must also answer the group lookup and `GET /projects/<id>`, or the commit step fails as a
  `RepoClientError` and the bug is masked. Key files named no file for the fix (`orchestrator/pipeline.py`, `determine_resume_point`); the
  scouts found them in minutes. **Estimate wrong:** the claim stub alone did not pass the trim trigger (196,270 B); the record does.
- **ROI: high.**

### Session 275 Self-Assessment

**Score: 7/10.**
- **+** Scouted before designing, put the one real choice to the operator with a recommendation, red first and read, a real-socket test at
  the real script including a real SIGINT, two mutation passes, a review whose findings were triaged one by one (fixed what belonged to
  the change, filed the rest with reproductions), new tests run on CI's interpreter, and my own mistakes corrected in place.
- **−** **I wrote "operator rulings" in the review prompt for two of my own scoping choices (hard kills; the `--resume` message) and the
  label reached `BACKLOG.md` and the ledger before a re-read caught it** (#332, FM #16). **My first leak assertions could not fail**
  (#328; the same mistake as Session 273's #319, and the review, not I, found it). Wrong figures of mine, again: "eight" commits in the
  push question (seven), 3 confirmed findings (4), 13 reported (16), a test count of 59 (46); all corrected. I read a bare `1` as option 1
  of two questions without asking. Long stretches without narration (the harness prompted me four times).
- **Decay term:** nothing removed from a mandated-read file except the closed item, and the files grew: `BACKLOG.md` 131,511 to
  136,624 B, `PROJECT_LEARNINGS.md` 373,933 to 379,328 B, `SESSION_NOTES.md` 195,311 to 206,863 B against the 196,608 B trigger.
  **The eleventh trim is due.**

**What's next** (sizes are estimates unless measured).
1. **The run log writes `str(exc)` unscrubbed (`BACKLOG.md:572`, `orchestrator/logging.py:94-105`).** Small, no ruling; first because a
   secret can reach a file today with the JSON formatter `OPERATIONS.md` section 3.1 recommends (Session 275's host-echoes-the-token
   vector reproduces the message). Log the class name only, or redact; a test that installs the formatter against that host holds it.
2. **The unruled small parts of the residue item (`BACKLOG.md:530`, points 2 and 3):** print the saved `failure_reason` and
   `project_url` in `_handle_already_complete` (`scripts/run_pipeline.py`), and make `CheckpointStore.save_result` atomic
   (`checkpoints.py:82`) with an unreadable result file treated as a refusal. Then Route 8 (`BACKLOG.md:~513`).
3. **The eleventh `SESSION_NOTES.md` trim is due** (its own deliverable: claim, trim, close out; two commits and no record edit in the
   trim commit). Say at Phase 0 whether to do it first.
4. **Rulings owed:** where the exception was raised (a frame in the reason, or a DEBUG log; `BACKLOG.md:530` point 1, which reopens what
   `failure_reason` holds), a hard-kill marker (point 4), a repeated `--run-id` (point 5), Python 3.12 pin or a matrix (now with a 3.14
   note), a host URL with a password, and the standing list in Session 273's record.
5. **Observed, not filed:** `stash@{0}` (Session 270's claim commit; the operator's call); the branch `worktree-wf_c93ee390-506-3` and
   `.claude/worktrees/wf_5f96c807-d00-3`; the root `methodology_dashboard.py` is v2.18.0 against v2.19.0 (`bin/sync`'s job);
   `uv run ruff format --check` would reformat 14 of 20 test files in the touched directories (CI runs `ruff check` only).

**Key files** (line numbers read off `grep -n` at this close-out).
- `src/model_project_constructor/orchestrator/pipeline.py:400` (`run_pipeline`), `:476-505` (the website block; its comment, `:476-488`, is the
  specification of the choice), `:644` (`_website_failure`; its docstring is the specification of the reason), `determine_resume_point` (reads one file).
- `tests/orchestrator/test_pipeline_website_failure.py:200,309,386` (the three classes); `tests/scripts/
  test_run_pipeline_website_crash_resume.py:38` (`BOOT`), `:46` (the 3.14 probe), `:67` (`Host`), `:214,:241` (the two tests).
- `BACKLOG.md:57-58` (index rows), `:530` the residue, `:572` the log item, `:584` CI's Python; `TROUBLESHOOTING.md:159` (the new entries),
  `:254`; `OPERATIONS.md:342`; `PROJECT_LEARNINGS.md` #327-332; `CHANGELOG.md` the S275 entries under `## 2026-10`.

**Gotchas.**
1. **The end-to-end router must answer the group lookup, `POST /projects`, `GET /projects/<id>` and the commit.** Leave one out and the
   commit step fails as a `RepoClientError`, the agent saves FAILED, and a test that only checked for a saved file would pass for the
   wrong reason; the `unexpected_error:` prefix assertion is what prevents it.
2. **Do not "fix" the asymmetry.** The `Exception` branch saves after the handler (the disk error has no `__context__`; pinned by
   `test_a_result_that_cannot_be_saved_is_not_hidden`), the interrupt branch saves inside it (the context is the interrupt; pinned).
3. **A website crash reports only the class.** To debug one: the `agent.error` log context has the message (if a handler shows it), or
   reproduce with `scripts/run_pipeline.py --live` against `serving_raw`.
4. **Run new tests on CI's interpreter** (#325): `UV_PROJECT_ENVIRONMENT=<scratch>/venv312 uv sync --frozen --python 3.12 --extra agents
   --extra ui --extra dev`. This session's scratch environment is not kept. The deep-JSON end-to-end case skips itself on 3.14.
5. Never `git stash` (#316); the mutation harness (saved copy, one anchor per mutant, `cmp` after) and the review's scripts are in the
   session scratchpad and are not kept.
6. `uv run pytest tests/test_read_budget.py tests/test_session_notes_census.py --no-cov` before every commit that touches
   `SESSION_NOTES.md`, `CLAUDE.md` or `BACKLOG.md`. **Any commit that touches `docs/wiki/` publishes it.** None of this session's did.

### What Session 274 Did
**Deliverable:** **a repository host's failure text can no longer put the access token, a terminal control code or an
unbounded body on a terminal, in the result JSON, in the `-o` file or in the pipeline checkpoint — COMPLETE**, Route 7 of
`BACKLOG.md`'s item *"Seven more routes can still put database, driver or exception text on a terminal or in a report"*
(marked closed; Route 8 filed beside it). Chosen by the operator at Phase 1 from a two-step picker (area: secrets still on
screen; item: Route 7). **Ruling (operator, by picker):** push at close-out (asked while the review ran).
**Started:** 2026-10-02 17:31. **Completed:** 2026-10-02. **Commits: twelve** — `2b99f9d` (claim, alone); the build,
`043af67`, `b4480e3`, `b5d7ee7`, `f18639d`, `0f3508b`, `32292f0`; `a50fe6b` (docs); the review's fixes `69303d1`, `58b21ba`;
`d1098dc` (docs) and this close-out. Each carries its own `CHANGELOG.md` entry; the push is recorded in the close-out's.

#### What changed
- **The design: scrub where an error leaves, not where its message is built.** Route 7 had 21 message-building sites in two
  adapters (16 interpolate an exception, 5 a response body; counted at `2b99f9d`). `agents/website/_host_text.py` (new):
  `scrub_host_text(text, secret, *, limit)` removes the secret by value (case-insensitive; as written, and as JSON, `h11`'s
  `bytearray(b'...')`, the repr of a longer message, HTML and percent encoding, two levels deep, longest first), turns each
  control character into a space, makes one line, cuts to 1,000 characters plus a notice, and fails closed (`<unprintable>`);
  `scrubbed_errors` decorates `create_project` and `commit_files` of both adapters and re-raises a `RepoClientError` scrubbed,
  **after the handler**, so nothing is behind it (#320); `response_text` reads a body without a crash. The adapters keep
  `self._secret` (`gitlab_adapter.py`, `github_adapter.py`).
- **Tests: 2,788 to 2,894 passed, 9 skipped, coverage 98.20%** at CI scope (`GITHUB_ACTIONS=true uv run pytest`, Python 3.13.5);
  the same suite on 3.12.13 and 3.11.15: 2,894 passed, 9 skipped and 98.20% on each (the 3.12 run is CI's interpreter). +106: `test_host_text.py` 53, `test_host_failure_text.py` 43 (every request of
  GitLab's sequence and of GitHub's two, organisation and personal account, answered in turn by eight hostile replies on a
  real socket, plus a transport error in three classes, plus two registry-wide gates), `test_host_failure_end_to_end.py` 10
  (the real command and the real script; stdout, `-o`, the checkpoint directory). `loopback.py` gains `serving_raw`.
- **Docs.** `BACKLOG.md` (Route 7 closed, Route 8 filed, two new items: a non-`RepoClientError` in the website stage leaves no
  result so `--resume` makes a second project; CI tests one Python and not the one sessions run), `TROUBLESHOOTING.md` (an
  advisory for a token a host echoed in an earlier run, what the removal does not cover, a table row, and the leak-hunt
  commands corrected: the script does not read `MPC_CHECKPOINT_DIR`), `PROJECT_LEARNINGS.md` #321-326, `CLAUDE.md`.

#### Measured first, then built
- **Three read-only scouts** (sinks, an 80-reply httpx matrix against a raw-socket server, the existing tests' expectations):
  one string, `failure_reason`, reaches exactly three places; only `RemoteProtocolError` was seen to quote server bytes; every
  adapter-message test pins a prefix only, and the one-letter test token `"t"` would have put a replaced letter inside 34 of the
  75 message assertions. The matrix also found a crash no one had thought of: `response.text` raising inside the message.
- **Red first, read:** 15 then 16 of 25 tests failed on a no-op stub (one toothless test found: `json.dumps` escapes a surrogate to
  ASCII); 10 of 17 adapter tests failed on the unwired adapters, each for the leak it was written to catch, and my first
  malformed-header reply failed on the chain, not the token (`h11` quotes only the FIRST illegal line).

#### The checks, each finding what the last could not
- **Two mutation passes** (32, then 43 live mutants; the second on Python 3.12): all caught after two survivors were dealt with
  (the second replace pass had no test; the `str`-repr escaper was dead code for ASCII and was removed).
- **The review** (6 lenses, 2 skeptics per non-nit finding: **98 agents, 0 errors, 66 minutes, 9.3M subagent tokens, 2,022 tool
  calls**): 46 findings, 32 confirmed by both skeptics, 6 by one, 8 by none; none rated high. **It found what I could not:**
  CI runs CPython 3.12.3 and I worked on 3.13.5, where a UTF-16 body with no BOM raises a plain `UnicodeError` and not
  `UnicodeDecodeError`, so **7 of my 66 new tests were red on CI and the crash they guard stayed open there** (reproduced on a
  scratch 3.12 environment; #325); nine more codecs raise other classes, so my "total function" was not; the registry gate
  accepted any `functools.wraps` decorator; no test covered the C1 controls; 48 of the files' 54 s was idle shutdown waiting;
  the new tests did not clear proxy variables; and the leak-hunt command in `TROUBLESHOOTING.md` (and Session 273's) grepped a
  variable the script never reads. All fixed or filed. **Found and filed, not fixed (pre-existing):** the resume duplicate above;
  host-URL userinfo is a second credential an echo returns as base64; Route 8.

### Session 273 Handoff Evaluation (by Session 274)

**Score: 8/10.**
- **+** The first recommendation was the right deliverable, correctly sized ("small, no ruling") and pointed at exactly: the
  sites named were right, and "rebuild from `loopback.py`" was the right instruction. Gotchas 1 to 3 and 5 were used as written
  (the `loopback` fixture, never `git stash`, both guards before every commit, re-derive a count) and the measured baseline
  (2,788 tests, 98.16%) was right.
- **−** **Missing, and it cost the most:** that CI runs Python 3.12.3 while the work is done on 3.13.5 (learning #303 said to run
  the other interpreters; nothing said which one CI has). **Understated:** "small" took nine commits and a review. The loopback
  fixture clears proxies, but a new helper has to do it itself.
- **ROI: high.** Orientation was nearly free.

### Session 274 Self-Assessment

**Score: 6/10.**
- **+** Scouted before designing and chose the exit over 21 sites; red first against a stub and read for which assertion failed;
  a real-socket test at every request position, derived from the happy run; two mutation passes; a proportionate review whose
  findings were triaged one by one, with in-scope ones fixed and the rest filed with reproductions; every correction of my own
  claims made in place and recorded.
- **−** **I shipped a fix that did not work on CI's interpreter and only the review caught it**, with learning #303 in the repo;
  "total function" and "answered in turn" were over-claims; wrong figures of mine: 19 sites (21), "about 30" assertions (34 of 75
  flagged), 34 confirmed findings (32), 11 GitHub requests (10), a worked example that dropped the second `t`, and a ledger
  sentence about which gap the second replace pass was. Fixture mistakes (even-length parity inside a server thread). Tests that
  took 50 s. Long stretches without narration (the harness prompted me repeatedly).
- **Decay term:** nothing was removed from a mandated-read file: `BACKLOG.md` grew 124,312 to 131,511 B (Route 7 rewritten, Route 8
  and two items added), `PROJECT_LEARNINGS.md` +7,625 B (373,933 B now). `SESSION_NOTES.md` is 195,311 B against the 196,608 B trim
  trigger: just under it, so **the eleventh trim is due as soon as the next record lands** (Session 275's claim stub and record will pass the trigger; an estimate).

**What's next** (sizes are estimates unless measured).
1. **The resume duplicate (`BACKLOG.md:528`): a website stage that raises something other than a `RepoClientError` saves no result,
   and `--resume` then creates a second project on the host.** Small, one choice (catch in the nodes, or in the orchestrator's website
   stage, which also covers an interrupt). It is the item with a real side effect, which is why it is first; the Route 8 pointer
   below is the quieter one. Reproduce with `scripts/run_pipeline.py --live` against `serving_raw` (`tests/agents/website/loopback.py`):
   answer `POST /projects` 201 and the commit with `201 {}`.
2. **Route 8 (`BACKLOG.md:506`): the host's project address, commit id, project id and default branch are printed raw** (`cli.py:266,268`,
   `run_pipeline.py:663,403`). Small, no ruling, one choice: `scrub_host_text(value)` in the adapters where `ProjectInfo` and
   `CommitInfo` are built (it also cuts to 1,000 characters and adds a notice).
3. **`SESSION_NOTES.md` is 195,311 B against the 196,608 B trigger: the eleventh trim is due as soon as the next record lands. It is its own deliverable per `CLAUDE.md` (claim, trim, close out: two commits and no record edit in the trim commit), so say at Phase 0 whether to do it first.**
4. **Rulings owed to the operator:** where to catch for the resume duplicate; pin Python 3.12 or add a matrix (`BACKLOG.md:545`); refuse
   a host URL with a password or scrub its base64 form (`BACKLOG.md`, the API-key item); and the standing list in Session 273's record
   (refuse versus client for the API keys; catch versus environment variable for the parser echo; `--db-url` option (c); the two
   guard-design calls; a CI job installing the dependency minimums; the saved inventory names; whether `safe_message` should cap).
5. **Observed, not filed:** `stash@{0}` ("WIP on (no branch): 022e6de", Session 270's claim commit; the operator's call), and the branch
   `worktree-wf_c93ee390-506-3` with `.claude/worktrees/wf_5f96c807-d00-3`, not this session's; the root `methodology_dashboard.py` is
   v2.18.0 against v2.19.0 (`bin/sync`'s job); `test_a_password_of_many_short_tokens_does_not_stall_the_scrub` took 5.6 s against its 5.0 s
   bound once, with three agents running, and 3 s alone (it passed in all four full runs since); `tests/` is outside the mypy gate.

**Key files** (line numbers read off `grep -n` at this close-out).
- `src/model_project_constructor/agents/website/_host_text.py:99,128,155,184` (`scrub_host_text`, `response_text`, `scrubbed_errors`,
  `_scrubbed_message`; the docstring of the module and of `response_text` are the specification), `:56` `_ESCAPERS`, `:70` `_rewrites`;
  `gitlab_adapter.py:77,88,132` and `github_adapter.py:91,104,177` (the secret, the two decorated methods).
- `tests/agents/website/test_host_text.py`, `test_host_failure_text.py` (`REQUESTS` `:110`, `HOSTILE` `:188`, the two gates `:382,:401`),
  `test_host_failure_end_to_end.py`, `loopback.py:44,86` (`without_proxies`, `serving_raw`).
- `BACKLOG.md:423` (the item), `:479` Route 7 closed, `:506` Route 8, `:528` the resume duplicate, `:545` CI's Python;
  `TROUBLESHOOTING.md` ("A token the repository host echoed back", "What the removal does not cover", the table row);
  `PROJECT_LEARNINGS.md` #321-326; `CHANGELOG.md` the S274 entries under `## 2026-10`.

**Gotchas.**
1. **Run new tests on CI's interpreter before pushing** (#325): `UV_PROJECT_ENVIRONMENT=<scratch>/venv312 uv sync --frozen --python 3.12
   --extra agents --extra ui --extra dev`, then `<scratch>/venv312/bin/python -m pytest`. 3.11 and 3.12 raise `UnicodeError` where 3.13
   raises `UnicodeDecodeError`.
2. **The registry gate looks for `__scrubs_host_text__`, not `__wrapped__`.** A new adapter, a new protocol method or a new request in
   an adapter's sequence turns `test_host_failure_text.py` red on purpose (its routers and `REQUESTS` are pinned): update them.
3. `serving_raw` sets proxy variables aside itself and raises a handler's exception from its `finally` with the client's error as
   context; a premise belongs in a plain test, not in the handler.
4. Never `git stash` (#316); the mutation scripts used saved copies and `cmp`. The scouts' and the review's scripts are in the session
   scratchpad and are not kept.
5. `uv run pytest tests/test_read_budget.py tests/test_session_notes_census.py --no-cov` before every commit that touches
   `SESSION_NOTES.md`, `CLAUDE.md` or `BACKLOG.md`. **Any commit that touches `docs/wiki/` publishes it.** None of this session's did.

### What Session 273 Did
**Deliverable:** **a website token that is not printable ASCII is refused once, before it can reach a header, and the
HTTP library's protocol-error text can no longer reach a message — COMPLETE**, closing `BACKLOG.md`'s item *"A website
token with a trailing carriage return or tab is printed in full in the result and the `-o` file"* (removed). Chosen by
the operator at Phase 1 from a two-step picker (area: secrets still on screen; item: the website token). **Rulings
(operator, by picker):** reject, never strip (Phase 1); push at close-out (Phase 3).
**Started:** 2026-10-01 23:40. **Completed:** 2026-10-02. **Commits: nine** — `132117c` (claim, alone), `1b9ab5e`,
`5ce4241`, `eba2858` (the three fix layers), `11d4734`, `011ba17` (the review's fixes), `f1af728`, `185e12f` (docs) and
this close-out. Each carries its own `CHANGELOG.md` entry (the four after midnight are dated 2026-10-02); the push is
recorded in the close-out's own entry.

#### What changed
- **The rule.** `protocol.py:82` `InvalidRepoTokenError` (a `ValueError`; its constructor takes no argument, so it cannot
  carry a value; `__reduce__` so it pickles), `:102` the regex `[\x21-\x7e]+`, `:105` `validate_repo_token` (`fullmatch`).
  Called first by **both adapter constructors** (`gitlab_adapter.py:69`, `github_adapter.py:83`), the choke point for
  **both** routes to a token: the website CLI and `scripts/run_pipeline.py` (`GITLAB_TOKEN`/`GITHUB_TOKEN` through
  `REPO_PLATFORMS[host].adapter_factory`). `cli.py:211-219` checks first (`--fake` skips it) and prints
  `ERROR: --private-token: <the sentence>` on stderr, exit 2.
- **The second line.** `website/_http.py` `RepoHttpClient(httpx.Client)`: `send` runs under
  `contextlib.suppress(httpx.LocalProtocolError)` and the fixed-text replacement is raised after the handler, so it has no
  `__context__`; both adapters build it; `agents/website/__init__.py` exports the error.
- **Tests: 2,713 to 2,788 passed, 9 skipped, coverage 98.16%** (under `GITHUB_ACTIONS=true`); CI-scope `ruff` and
  `uv run mypy` (69 files) clean. `tests/agents/website/test_repo_token.py` (53), `test_repo_http_client.py` (20),
  `loopback.py` + a `conftest.py` fixture (a real socket, proxies set aside), one pipeline-route test appended to
  `tests/scripts/test_run_pipeline_adapter.py`.
- **Docs.** `OPERATIONS.md`, `TROUBLESHOOTING.md` (a row, and **a rotate-and-scrub advisory: the pipeline route also saved
  the token in the checkpoint file**), `BACKLOG.md` (item removed; Route 7 rewritten and no longer a nit; a new sibling
  item for API keys), `PROJECT_LEARNINGS.md` #317-320, `CLAUDE.md`.

#### Measured first, then built
- Through the real adapters against a loopback server, every code point 0-255 (and two more) in three positions, both
  header styles: `h11` refuses NUL, LF, VT, FF, CR anywhere and a space or tab at the ends, and **quotes the whole value**
  (the filing named "carriage return or tab"); it accepts and sends U+0001-U+0008, U+000E-U+001F and DEL; non-ASCII fails at
  construction. A sweep of **27 real httpx 0.27.0-0.28.1 x httpcore 1.0.0-1.0.9 x h11 0.13.0/0.14.0/0.16.0 combinations**
  (21 requested pairs cannot be installed together): 0 of the accepted tokens refused, the refusal set identical.
- **Red first:** 42 of the 70 tests run failed on a no-op validator, and **my first CLI tests passed the leak assertion**
  (with `-o` the leak went to the file, which they never read): found by reading the failure, not the count (#319).

#### The checks, each finding what the last could not
- **Three mutation passes** (20, 6 and 10 mutants), all caught, files restored byte for byte.
- **The review** (5 lenses, 2 skeptics per non-nit finding: **67 agents, 0 errors, about 26 minutes, 5.87M subagent tokens,
  1,126 tool calls**): 31 judged, 20 confirmed, 10 contested, 1 refuted, **none high.** It changed: the replacement was raised
  inside the handler, so the original quoting exception stayed on `__context__` (#320); the error could not be pickled; the
  wire test failed under `HTTP_PROXY`; five CLI mutants survived; the client's kwargs were unpinned; **the docs were silent
  and nothing told an operator that tokens an earlier run printed are still on disk**; and **five of my own ledger claims
  were wrong** (fourteen sites, not fifteen; 20 mutants, not 19; 282 tokens, not 564; "a stricter `h11` cannot reopen the
  leak" does not follow; the first commit's figures were a later tree's), all corrected in place.
- **Found and filed, not fixed (pre-existing):** a host that echoes request headers puts a **valid** token in `failure_reason`
  (Route 7 of `BACKLOG.md:421`, `:475`); API keys for Anthropic and Bedrock are quoted in the exception chain (`:526`);
  `MPC_HOST_URL` with userinfo is printed and saved (inside `:526`).
- The repository was checked clean after the review (the harness reported its safety classifier timed out for two
  subagents): `HEAD`, the stash and the worktrees as before.

### Session 272 Handoff Evaluation (by Session 273)

**Score: 8/10.**
- **+** The first recommendation was the right deliverable and its pointer (`BACKLOG.md:514`) was exact. Gotchas 1, 2, 5 and
  6 were used as written (`GITHUB_ACTIONS=true`; learning #315's sweep one-liner; both guards before every commit that
  touched `SESSION_NOTES.md`, `CLAUDE.md` or `BACKLOG.md`), and the measured baseline (2,713 tests, 98.15%) was right.
- **−** **Understated:** "validate once at the CLI" — the route that matters is the adapter constructors, because the
  pipeline script is a second route to the same sink; "a carriage return or tab" — line feed, space, NUL, vertical tab and
  form feed leak too; "small" — it took three layers and a review. **Missing:** that the pipeline route *saved* the token in
  a checkpoint, which is why a rotation advisory was owed. The `stash@{0}` warning was accurate and I left it alone.
- **ROI: high.** The orientation was nearly free; the three understated points were each cheap to re-measure.

### Session 273 Self-Assessment

**Score: 7/10.**
- **+** Measured the whole character space instead of building on the filing's example, and swept the admitted range, not the
  lock (#315, #317, #318); red first, and read the red run closely enough to find a hole in my own test; three mutation
  passes with byte-for-byte restores; a proportionate-to-the-stakes review that changed eight things and was triaged finding
  by finding, with in-scope fixes made and out-of-scope ones filed with their reproductions; every correction of my own
  claims made in place and recorded.
- **−** **Five wrong claims in my own ledger entries** (above), all caught by the review's claims lens and not by me; the
  `from None` design flaw (#320) and a proxy-sensitive test, both found only by the review. **I touched six files before
  my first commit** (the cap is five per commit; I split the commits by file, but the tree held six). Several long
  stretches without narration (five "the user hasn't heard from you" prompts). Scope: the rule covers the pipeline route
  and library callers, wider than the filing said; stated in the ledger.
- **Decay term:** removed one `BACKLOG.md` item and its row (net `BACKLOG.md` 122,247 to 124,312 B: Route 7 grew, a sibling
  item was added); `PROJECT_LEARNINGS.md` +4,280 B (four rows, now 366,308 B). **`SESSION_NOTES.md` is 183,023 B against the
  196,608 B trim trigger: the eleventh trim will probably fire at Session 274 or 275 (an estimate).**

**What's next** (sizes are estimates unless measured).
1. **Route 7 of `BACKLOG.md:421` (rewritten at `:475`): a repository host's error text is printed raw, and can carry a valid
   token.** Small, no ruling: one helper per adapter that builds the message from the status and a truncated, control-stripped
   body and replaces the token (and `Bearer <token>`); the sites are `gitlab_adapter.py:113,187`, `github_adapter.py:123,156,271`
   and the `{exc}` ones beside them (a malformed response is `httpx.RemoteProtocolError`, which `RepoHttpClient` passes
   through on purpose). Needs a real-socket test with a raw-socket server (the review's scripts are not kept: rebuild from
   `tests/agents/website/loopback.py`).
2. **`BACKLOG.md:526`, API keys quoted in the exception chain.** Small; **needs the operator's choice** (refuse such a key where
   each provider reads it, moving the rule to a shared module, or hand the SDK a client that withholds the message).
3. **Residue routes 2(b) and 5 of "Seven more routes ..."** (`safe_message(e)` at `nodes.py:211` and `agent.py:54`; the pool
   logger's filter), and the two items that need no ruling: the Click 8.2 declaration (`BACKLOG.md`, "The test suite needs
   Click 8.2") and the `langgraph` floor.
4. **Rulings owed to the operator:** refuse versus client for the API keys; catch versus environment variable for the parser
   echo; whether the connect error should say to percent-encode an `@`; whether to take the declined smaller design;
   `--db-url` option (c), one per channel for the three channels, the two guard-design calls, a CI job installing the dependency
   minimums, whether the website should sanitise report text, the saved inventory names, whether `safe_message` should cap its
   input; and new: whether `docs/tutorial.md` Options B and C should strip a carriage return (they keep it; the refusal's row
   in `TROUBLESHOOTING.md` says so).
5. **Observed, not filed:** `stash@{0}` ("WIP on (no branch): 022e6de", Session 270's claim commit; provenance unrecorded; the
   operator's call); `scripts/run_pipeline.py` shows a bad `GITLAB_TOKEN` as a traceback (exit 1) that names no variable, like
   every `ConfigError` at that step (one of two skeptics refuted it as a defect); the root `methodology_dashboard.py` is v2.18.0
   against v2.19.0 (`bin/sync`'s job); `.claude/worktrees/wf_5f96c807-d00-3` and the branch `worktree-wf_c93ee390-506-3` are not
   this session's; `tests/` is outside the mypy gate.

**Key files** (line numbers read off `grep -n` at this close-out).
- `src/model_project_constructor/agents/website/protocol.py:82,102,105` (the rule); `_http.py` (the client); `cli.py:211-219`
  (the check); `gitlab_adapter.py:69-70`, `github_adapter.py:83-84` (the constructors); `src/.../orchestrator/config.py`
  (`PlatformSpec`'s docstring); `tests/agents/website/test_repo_token.py`, `test_repo_http_client.py`, `loopback.py`,
  `conftest.py` (the `loopback` fixture); `TROUBLESHOOTING.md` (the row and "A token leaked by a run before Session 273");
  `BACKLOG.md:421,475,526`; `PROJECT_LEARNINGS.md` #317-320; `CHANGELOG.md` the S273 entries under `## 2026-10`.

**Gotchas.**
1. **A test that talks to a socket takes the `loopback` fixture, which clears the proxy variables** and sets `NO_PROXY`;
   `httpx.MockTransport` cannot see anything in `h11` (#317).
2. **Never `git stash`** (#316); use saved copies and `cmp` for a temporary revert. This session's mutation scripts did, and
   restored every file byte for byte.
3. `uv run pytest tests/test_read_budget.py tests/test_session_notes_census.py --no-cov` before every commit that touches
   `SESSION_NOTES.md`, `CLAUDE.md` or `BACKLOG.md`. **Any commit that touches `docs/wiki/` publishes it.** None of this
   session's did.
4. The rule is U+0021-U+007E, **not** "what `h11` accepts" (it accepts DEL and most controls): do not loosen it to match a
   library, and do not move the check out of the adapter constructors without a registry-wide test (one exists).
5. A review's claims lens found five wrong numbers in my entries: **re-derive a count before writing it** (`grep -c`, the
   suite's delta), and write "run" and "new" separately.

### What Session 272 Did
**Deliverable:** **none of the three Typer apps prints its parameters' values in a traceback — COMPLETE**, part (2)
of `BACKLOG.md`'s item *"Two more surfaces print the raw `--db-url`: the argument parser's error and Typer's locals"*.
Typer 0.16 to 0.22 (which `typer>=0.16.0` admits) printed `db_url` with its password in a locals box under every
frame of an uncaught exception; **the website agent's `--private-token` leaked the same way and nobody had filed
it**, so all three apps carry the fix (it is one argument per app, and the setting is per app). The item's other
half stays open, retitled *"The argument parser prints a mistyped `--db-url` or `--private-token`, value and all"*.
Chosen by the operator at Phase 1 from a two-step picker (area: secrets still on screen; item: Typer shows the
address in tracebacks). **Ruling (operator, by picker, Phase 3):** push at close-out.
**Started / completed:** 2026-10-01. **Commits: four** — `20cc72c` (claim, alone), `44d2029` (the fix and its test),
`8dfa451` (docs) and this close-out. Each carries its own `CHANGELOG.md` entry; the push is recorded in the
close-out's own entry.

#### What changed
- `pretty_exceptions_show_locals=False` on the three `typer.Typer(...)` calls: `packages/data-agent/.../cli.py:64`,
  `src/.../intake/cli.py:27`, `src/.../website/cli.py:38`.
- `tests/test_typer_locals.py` (238 lines, 5 tests). **Structural arm** (`_scan` `:79`; `test_every_known_app_is_found`
  `:126`, `test_every_typer_app_hides_locals_in_a_traceback` `:131`): an AST scan of `src/`, `packages/`, `scripts/`
  requiring the literal `False` on every `Typer(...)`, `typer.run(...)` and `Typer` subclass; it fails on the unfixed
  code under the lock's Typer, which is what holds the fix in CI. **Behavioural arm** (one parametrized test `:229`):
  the three real apps under `python -m`, an uncaught error forced while the secret is a local; it requires the named
  exception and the app's own `run` frame, so a run that dies earlier cannot pass. The docstring lists what the scan
  cannot see.
- **Tests: 2,708 to 2,713 passed, 9 skipped, coverage 98.15%** (under `GITHUB_ACTIONS=true`); CI-scope `ruff` and
  `uv run mypy` (68 files) clean. `BACKLOG.md` (item retitled and halved, one item and one index row added),
  `PROJECT_LEARNINGS.md` #312-316, `CLAUDE.md` (count and size).

#### Measured first, then built (the real apps under `python -m`, a Typer overlay per release)
- **All 38 non-yanked, non-pre-release Typer releases from 0.16.0 to 0.27.2** (the filing had stopped at 0.24.1; the
  range has no ceiling): unfixed, the 18 from 0.16.0 to 0.22.0 print a box and the 20 from 0.23.0 do not; **36 of 114
  runs printed a secret (the data agent's password 18, the website's token 18) and 54 a box** (the intake agent,
  which takes no secret, 18). Fixed: **0 of 114** printed a secret or a box, none failed to import, all still print a
  traceback and exit 1. The review re-ran both sweeps from scratch: 0 differing rows. Long values are cut by rich, so
  "printed the password" is exact for a 44-character address and conditional on length.
- **A first probe read two of three apps as clean** (a single-command Typer app has no command name; both died on a
  usage error). A two-release smoke run against a known leaker caught it before the sweep (learning #312).

#### The checks, each finding what the last could not
- **Red first, verified per surface.** With the fix reverted: the lock fails the structural arm only; 0.16.0, 0.21.0 and
  0.22.0 fail four; 0.23.0 (the first clean release) fails the structural arm only. Fixed: 5 passed on 0.16.0, 0.21.0,
  0.24.1 and 0.27.2, with and without `GITHUB_ACTIONS=true`. **The first version of the test failed whenever
  `GITHUB_ACTIONS` was set, alone or in the suite** (I met it in the suite; the review corrected my "in the full suite"):
  Typer forces terminal output there and style codes split the strings asserted on, which could also have hidden a
  real leak (learning #313). Four mutants of the structural arm, all caught.
- **The review** (3 lenses, 2 skeptics per non-nit finding: **21 agents, 0 errors, about 28 minutes, 1.76M subagent
  tokens, 316 tool calls**): 9 non-nit findings, 8 not refuted by both skeptics (two of those split 1 to 1) and 1 refuted by both,
  plus 9 nits. **It changed the test:** the behavioural arm **passed vacuously when the app died at an import** (reproduced on
  unfixed code under 0.22.0: all three arms passed) **while its docstring claimed otherwise**; the intake arm passed on
  leaking code when the child's stdout was not UTF-8; the structural arm missed an alias, a subclass, `typer.run`,
  `scripts/` and a package without `src/`; and `TERMINAL_WIDTH`, source encoding, a dangling symlink and a missing
  timeout were fixed as nits. Each was re-reproduced as caught. **It found a leak outside the diff:** a website token
  ending in a carriage return or tab is printed in full (below). Re-running the reviewer's `LC_ALL=C` environment on
  the finished test caught a regression my own hardening had introduced (the parent decoded the child's forced UTF-8
  as ASCII), now fixed.
- **Filed, not fixed** (`BACKLOG.md:488`, `:514`): the website token (reproduced by me directly against `GitLabAdapter`
  for CR and TAB; the CLI chain and the LF case by the review) and the parser echo's three further shapes, with the
  measured fact that **`redact_secrets` masks an address's password but not a bare token**.
- **An error of mine, recorded in the ledger:** a failed `git stash push` (zsh does not split an unquoted variable)
  was followed by an exit trap's `git stash pop`, which applied **a stash that is not this session's** (`stash@{0}`,
  from Session 270's claim commit) and conflicted in two test files. I restored exactly those two files to `HEAD`
  (neither was touched this session); the stash is intact. The checks were redone with saved copies and `cmp`.

### Session 271 Handoff Evaluation (by Session 272)

**Score: 8/10.**
- **+** The first recommendation was the right deliverable and its pointer (`BACKLOG.md:487`) was exact. Gotcha 5 (use
  `uv run --with ... python -m`, because the console script runs the project venv's copy) was used as written, and gotcha
  6 (both guards before any commit touching `SESSION_NOTES.md`, `CLAUDE.md` or `BACKLOG.md`) was followed. The measured
  baseline (2,708 tests, 98.15%) was right to the digit.
- **−** **What was wrong, mildly:** "small, needs no ruling" understated it: it named one app where there are three (the
  website agent's token leaked too), and "measured from 0.12.0 to 0.24.1" was stale: fourteen later releases existed.
  **What was missing:** the `stash@{0}` left by Session 270 is not in "Observed, not filed", which listed the two
  worktrees. A `git stash list` at orientation would have named it before it bit.
- **ROI: high.** It saved the orientation, and the two unmeasured premises were cheap to re-measure.

### Session 272 Self-Assessment

**Score: 7/10.**
- **+** Re-measured the filing instead of building on it (38 releases, three apps; found the unfiled website leak);
  caught my own false-negative probe with a smoke run; wrote the test red first and verified it per surface, with the
  fix reverted and restored byte for byte; an independent review that was proportionate (1.76M subagent tokens against
  Session 271's 9.1M) and changed the test in four ways; reproduced the website-token leak myself before filing it;
  every figure in the ledger was audited by a lens before it was written.
- **−** **Three errors of mine of the kinds this project warns about:** I wrote a docstring claim ("asserts the failure is
  the one provoked") with no assertion behind it, caught only by the review (#312); I ran an unchecked undo in a trap
  and applied someone else's stash (#316); and my first hardening broke the parent's decode under `LC_ALL=C`, found only
  by re-running the reviewer's environment (#313). Four "the user hasn't heard from you" prompts: the long
  background waits and runs were not narrated.
- **−** Scope judgment: I widened from the filed data agent to all three apps. It is the same one-argument fix and the
  operator's picker named the area, but it is a judgment call; it is stated here and in the ledger.
- **Decay term:** none removed except the closed half-item's text. `BACKLOG.md` 118,805 to 122,247 B (one item halved,
  one added, one index row reworded, one added); `PROJECT_LEARNINGS.md` +5,103 B (five rows, now 361,984 B).

**What's next** (sizes are estimates unless measured).
1. **`BACKLOG.md:514`, the website token ending in a carriage return or tab.** A live secret in a shipped command's
   output with a reproduction; small (validate once at the CLI with a fixed sentence, and stop interpolating `{exc}` for
   `httpx.LocalProtocolError` at `gitlab_adapter.py:87,103,131,154` and in `github_adapter.py`). **Needs the operator's
   ruling on rejecting versus trimming** (a one-question picker; reject is the recommendation, since trimming edits a
   credential).
2. **`BACKLOG.md:488`, the argument parser's echo.** Needs a choice (catch and mask, or take the address and token from an
   environment variable). **Do not call `redact_secrets` on a token message: it leaves a bare token untouched** (measured).
3. **Residue routes 2(b) and 5 of "Seven more routes ..."** (carried from Session 270's list): `safe_message(e)` at
   `nodes.py:211` and `agent.py:54`, and the pool logger's filter. No ruling.
4. **Two items still need no ruling:** the Click 8.2 declaration (31 of 87 CLI tests fail under Click 8.1, `BACKLOG.md:604`)
   and the `langgraph` floor.
5. **Rulings owed to the operator:** reject versus trim for the token; catch versus environment variable for the parser
   echo; whether the connect error should say to percent-encode an `@`; whether to take the declined smaller design; and,
   unchanged, `--db-url` option (c), one per channel for the three channels, the two guard-design calls, a CI job
   installing the dependency minimums, whether the website should sanitise report text, the saved inventory names, and
   whether `safe_message` should cap its input.
6. **Observed, not filed:** `stash@{0}` ("WIP on (no branch): 022e6de", Session 270's claim commit; 360 lines of test
   additions to `tests/agents/data/test_data_agent.py` and `tests/data_agent_package/test_cli.py`; provenance unrecorded;
   I did not drop it and it is the operator's call); the root `methodology_dashboard.py` is v2.18.0 against canonical
   v2.19.0 (`bin/sync`'s job); two clean worktrees remain that are not this session's (`.claude/worktrees/wf_5f96c807-d00-3`
   and the branch `worktree-wf_c93ee390-506-3`); `tests/` is outside the mypy gate.

**Key files** (line numbers read off `grep -n` at this close-out).
- `packages/data-agent/src/model_project_constructor_data_agent/cli.py:64`, `src/model_project_constructor/agents/intake/cli.py:27`,
  `src/model_project_constructor/agents/website/cli.py:38` (the three apps); `tests/test_typer_locals.py` (`:79`, `:126`,
  `:131`, `:140` `_environment`, `:159` `_run`, `:229`); `BACKLOG.md:488` and `:514`; `PROJECT_LEARNINGS.md` #312-316;
  `CHANGELOG.md` the S272 entries under `## 2026-10`. For the token leak: `gitlab_adapter.py:66-70` (the header),
  `:83-88` (the `{exc}`), `website/nodes.py:107-111` (`failure_reason`), `website/cli.py:258-263` (the print; the file grew 6 lines when the
  setting was added).

**Gotchas.**
1. **The behavioural arm cannot fail under the lock** (0.24.1's default is already off); the structural arm is what holds
   the fix in CI. To watch the behavioural arm bite: save the three `cli.py` files, `git checkout HEAD --` them, and run
   `uv run --no-sync --with typer==0.21.0 pytest tests/test_typer_locals.py --no-cov -q`, then copy the saved files back and
   `cmp`. **Never `git stash` for this** (learning #316).
2. **Run any output-asserting test with `GITHUB_ACTIONS=true`** (learning #313); `tests/test_typer_locals.py` strips the
   style codes and pins `COLUMNS`, `TERMINAL_WIDTH`, UTF-8 and `TYPER_STANDARD_TRACEBACK`.
3. **Single-command Typer apps (website, intake) take no command name**: `python -m ...website --intake ...`; only the data
   agent has `run`. A probe that adds `run` dies on a usage error and reads as clean.
4. `redact_secrets` masks a URL's userinfo, not a bare token (measured). `safe_message` is the database-text route.
5. The sweep and matrix scripts were scratch and are gone; learning #315 gives the one-liner to rebuild the sweep.
6. `uv run pytest tests/test_read_budget.py tests/test_session_notes_census.py --no-cov` before every commit that touches
   `SESSION_NOTES.md`, `CLAUDE.md` or `BACKLOG.md`. **Any commit that touches `docs/wiki/` publishes it.** None of this
   session's did.

### What Session 271 Did
**Deliverable:** **a password in a database address no longer reaches the connect error, the report or the
dialect warning — COMPLETE**, closing `BACKLOG.md`'s item *"A password can still reach the connect error, the
report and a warning"* (removed; the four S271 ledger entries are the record). `redact_db_url` reads an address
SQLAlchemy cannot be trusted to have split as the operator typed it; `safe_message(url=)` removes the password's
tokens from the RAW driver text. The residue is filed. Chosen by the operator at Phase 1 from a two-step picker
(area: passwords in database text; item: the password-leak item only; the slow-masker item needs a ruling on a
length cap and stays open). **Ruling (operator, by picker, Phase 3):** push at close-out.
**Started / completed:** 2026-10-01. **Commits: seven** — `73837b2` (claim, alone), `9b936f0` (the redaction),
`c70a076` (13 route tests), `26cac7b` (a mutation pass), `cf65f58` (the review's fixes), `028eae8` (docs) and
this close-out. (The push question said eight; it is seven.) Each carries its own `CHANGELOG.md` entry.

#### What changed
- `db.py`: `redact_db_url` (`:208`); the trigger `_untrusted_userinfo` (`:184`): the address does not parse, or
  holds an `@` the parse does not account for (`_unaccounted_at` `:155`: not the userinfo separator, a user name,
  a password, or a query value after a host); SQLite is exempt only with no user or password; a `URL` object is
  read as the string it renders. `_split_userinfo` (`:131`) masks from the user's colon to the LAST `@`.
  `_password_patterns` (`:241`) and `_scrub_address_password` (`:293`): ASCII and Unicode alphanumeric tokens, chains
  of up to six with a gap of up to six non-alphanumerics, the tails after the first four `@`, a bytes-repr form for
  non-ASCII; `safe_message(url=)` (`:370`) scrubs RAW text before it flattens; `connect` (`:595`) and the dialect
  warning (`:538`, now `safe_message`) pass the address. `_USERINFO_URL` is gone. `redact_secrets` is as before.
- **Tests: 2,432 to 2,708 passed, 9 skipped, coverage 98.15%** (under `GITHUB_ACTIONS=true`); CI-scope `ruff`
  and `uv run mypy` (68 files) clean. `tests/data_agent_package/test_db_url_secrets.py` (263), `tests/hostile_text.py`
  (`EchoingDialect` = `fakeecho`, which echoes every field SQLAlchemy parsed, and the `leaked_run` oracle), 13 route
  tests (`test_cli.py:1277,1296`, `test_data_agent.py:1177`). `USAGE.md`: how to write a password (percent-encode).

#### Measured first, then built (real unless marked)
- Fifteen driver setups in throwaway environments: the unencoded-`@` password reaches the connect error as
  `failed to resolve host 'ssw0rdXYZ@127.0.0.1'` and in `redact_db_url`'s own output. **Two routes the item did
  not name:** an `@` and a `:` make `make_url` raise `invalid literal for int() ... '123@h:5'`, and **SQLAlchemy
  2.0.40, which `sqlalchemy>=2.0,<3` admits, puts the whole address in its parse error** (2.0.41 and later do not;
  the lock's 2.0.49 hides it from CI).
- The real console script, a real psycopg 3, a refused port, before and after: **2, 3, 2 and 3 lines containing the
  password (error line, report, warning) became 0, 0, 0, 0**. The error is one line and still names the host.
- **The design departs from the item once:** it said print a fixed `<unparseable URL>`; Session 260's
  `test_connect_error_names_the_cause_without_the_password` requires the host and `$DB_PORT` (learning #308).

#### The checks, each finding what the last could not
- **Prototype + five attackers** (a workflow: 1.25M subagent tokens, every claim run) changed the design three
  times: a raw `@` count over-fired (`bob:***@nightly`); typed-text matching failed on 168 of 2,484 driver rows
  (re-escape, bracket, strip, comma, `#`), so it matches tokens; the first scrub was cubic. I implemented in a
  separate worktree so their baseline stayed still.
- **My own enumeration and fuzz** found four more (a one-slash-scheme skip that printed `bob:/pw`; a chain
  outranking the whole password; short-segment passwords; a `://` inside a password). **A mutation pass** left 23 of 46
  mutants alive after 157 tests; the final pass is 59 of 59 killed.
- **The review** (5 lenses, 2 skeptics per finding, a critic: **96 agents, 0 errors, 80 minutes, 9.1M tokens**):
  45 lens findings, 29 confirmed by both skeptics, 16 partly or mixed, **0 refuted**, plus 4 from the critic (all
  outside the diff). It changed the code: non-ASCII passwords leaked (three lenses), a `sqlite+pysqlcipher`
  passphrase leaked past the SQLite exemption, a short token before punctuation leaked, **two bounds I deleted as
  "redundant" were not (an address of 100,000 `@` took 8.6 s)**, a URL object bypassed the trigger, and a raw
  `odbc_connect` lost its host. **Both mutants I had argued "equivalent" were not** (learning #305).
- **Final measurements:** real-driver matrix 0 leaking rows of 1,242 (899 today); the 4-to-6-character enumeration
  0 except 81 scheme-less passwords that begin `//`; 59,977 random passwords x 6 templates, 0 in the plain class
  (one oracle artifact: `hoSt` in `host`).
- **Declined:** the simplicity lens's smaller design (withhold driver text when the parse is untrusted). **Filed:**
  the argument parser prints a mistyped `--db-url`; Typer 0.16 to 0.22 print it in a traceback's locals; the
  message does not say to percent-encode (`USAGE.md` does); SQLAlchemy 2.1 fails one older test.

### Session 270 Handoff Evaluation (by Session 271)

**Score: 7/10.**
- **+** The first recommendation was the right deliverable and every line number it gave was right when read.
  Gotcha 1 (apply `safe_message` once; the masker mangles a composed message) and gotcha 3 (re-measure before
  trusting a server's wording) were followed, and learning #300's fake-dialect technique was reused as written.
  The backlog item named both shapes with a reproduction.
- **−** **What was wrong:** the item's recommended fix, a fixed `<unparseable URL>`, contradicts a standing test
  (Session 260); and "small, no ruling" sized a deliverable that took the whole session. **What was missing:** two
  more routes in the same item (the `@`-and-`:` port error and SQLAlchemy 2.0.40's whole-address echo), and that
  `redact_db_url`'s tests had no password-bearing case of any kind beyond the `$DB_PORT` ones.
- **ROI: high.** It saved the orientation; it did not save the discovery.

### Session 271 Self-Assessment

**Score: 7/10.**
- **+** Measured every route on real drivers before writing a fix, found three routes the item did not name, and
  ran a before/after on the real console script. Tests red first at each layer; **four staged snapshots verified in
  a clean worktree with the passed-test count predicted first (2,589, 2,602, 2,644, 2,708: all matched).** An
  attack before the build (design changed three times), then four different checks after it; the review found
  five real leaks and I fixed them all with a test each. 59 of 59 mutants killed. Corrected my own claims by ledger
  entry, except one figure I amended into an unpushed commit.
- **−** **I committed two wrong "equivalent" arguments** and **deleted two live bounds as redundant**; both were
  caught only by the review (learnings #305, #310). **I wrote unsupported figures into the ledger three times** ("14
  decisions" for 17, "28 decisions", "333,000 passwords" for 59,977; each corrected by a later entry). My first
  trigger and first scrub were each redesigned by someone else's measurement. The push question said eight commits.
- **−** It was a long session: about 10.4M subagent tokens in two workflows (1.25M, then 9.12M), for a change whose
  shipped size is `db.py` +252 −20 and 939 lines of tests. The yield (five leaks, two corrected claims) justified the
  review; the first workflow, the attack on a prototype, was cheaper per finding.
- **Decay term:** none removed except the closed item. `BACKLOG.md` 117,729 to 118,805 B (one item and one row
  out, two items and two rows in); `PROJECT_LEARNINGS.md` +6,266 B (seven rows, now 356,881 B).

**What's next** (sizes are estimates; the previous handoff's "small" was not).
1. **`BACKLOG.md`'s "Two more surfaces print the raw `--db-url`".** Part (2), Typer 0.16 to 0.22 printing `db_url` in
   a traceback's locals, is one argument (`pretty_exceptions_show_locals=False`) and a test, needs no ruling, and
   is a secrets matter. Part (1), the argument parser echoing an address typed without `--db-url`, needs a choice
   (catch the error, or take the address from an environment variable).
2. **Residue routes 2(b) and 5 of "Seven more routes can still ..."** (S270's list): a `safe_message(e)` at
   `nodes.py:211` and `agent.py:54`, and the pool logger's filter.
3. **Two items still need no ruling:** the Click 8.2 declaration (now 31 of 87 CLI tests fail under Click 8.1) and
   the `langgraph` floor.
4. **Rulings owed to the operator:** whether the connect error should say to percent-encode an `@` (a fixed
   sentence when `_untrusted_userinfo` fires), and whether to take the declined smaller design (both in "Smaller
   follow-ups"); and, unchanged, `--db-url` option (c), one per channel for the three channels, the two guard-design
   calls, a CI job installing the dependency minimums, whether the website should sanitise report text, the saved
   inventory names, and whether `safe_message` should cap its input.
5. **Observed, not filed:** the root `methodology_dashboard.py` is v2.18.0 against canonical v2.19.0 (`bin/sync`'s
   job); two clean worktrees remain that are not this session's (`.claude/worktrees/wf_5f96c807-d00-3`, Session
   269's, and a branch `worktree-wf_c93ee390-506-3`); `tests/` is outside the mypy gate.

**Key files** (line numbers read off `grep -n` at this close-out).
- `db.py:75` `_USERINFO_TEXT`; `:108-130` the constants and their bounds; `:131` `_split_userinfo`; `:155`
  `_unaccounted_at`; `:184` `_untrusted_userinfo`; `:208` `redact_db_url`; `:241` `_password_patterns`; `:293`
  `_scrub_address_password` (its docstring is the specification: the limits, the order); `:370` `safe_message`;
  `:538` the warning; `:595` `connect`.
- `tests/data_agent_package/test_db_url_secrets.py`; `tests/hostile_text.py` (`EchoingDialect`, `leaked_run`);
  `test_cli.py:1277,1296`; `test_data_agent.py:1177`. `BACKLOG.md` the two new items above "`redact_secrets` is
  quadratic ..."; `PROJECT_LEARNINGS.md` #305-311; `CHANGELOG.md` the S271 entries under `## 2026-10`.

**Gotchas.**
1. **The scrub removes by value ONLY when the parse is untrusted.** A correctly parsed password is never removed
   from driver text: no measured driver echoes one, and an unconditional scrub turns `user "postgres"` into
   `user "***"` for `postgres:postgres`. Do not widen it.
2. **The scrub runs on RAW text, before the flatten.** After it, `ab<TAB>c` leaves `ab`; a test holds the exact output.
3. **Read `_scrub_address_password`'s docstring before touching a threshold.** The limits are measured and
   written there; tokens are ASCII and Unicode; a chain's gap is six non-alphanumerics. The mutation harness
   (59 mutants) and the attack scripts were scratch and are gone; learnings #305-311 say how to rebuild them.
4. **SQLAlchemy 2.0.40 echoes the whole address in a parse error and the lock hides it**; the tests simulate it
   by monkeypatching. Run new tests under `uv run --no-project --with sqlalchemy==X` for the range's edges.
5. **`uv run --with 'psycopg[binary]' model-data-agent` runs the project venv's script, which has no overlay.**
   Use `uv run --with ... python -m model_project_constructor_data_agent`; I compared the wrong objects once.
6. `tests/hostile_text.py` registers both `fakeesc` and `fakeecho` on import. `uv run pytest tests/test_read_budget.py
   tests/test_session_notes_census.py --no-cov` before every commit that touches `SESSION_NOTES.md`, `CLAUDE.md` or
   `BACKLOG.md`. **Any commit that touches `docs/wiki/` publishes it.** None of this session's did.

### What Session 270 Did
**Deliverable:** **database and driver text reaches the operator's terminal and the report only through one
redact-and-scrub function — COMPLETE** for routes 1 to 3 of `BACKLOG.md`'s item *"Seven more routes put
database or driver text on a terminal or in a report unscrubbed"*: `discover`'s connect error, `run`'s
"database unreachable" concern, and the quality-check and baseline driver errors. `discovery._safe_message`
became `db.safe_message` (`db.py:147`) and each route went through it. **The residue is filed**, among it a
secrets matter. Chosen by the operator at Phase 1 from a two-step picker (area: database-text safety; item:
routes 1 to 3 as one session). **Ruling (operator, by picker, Phase 3):** push at close-out.
**Started / completed:** 2026-10-01. **Commits: ten** — `022e6de` (claim, alone), four green layers
(`e60ab3c`, `5332aad`, `e29eb94`, `eaa0434`), two review fixes (`0dc50a4`, `6da5399`), `df6cf71` (docs), `b5fbd56`
(backlog, learnings) and this close-out. Each carries its own `CHANGELOG.md` entry. The push is recorded in
the close-out's own ledger entry.

#### What changed
- `db.py`: `safe_message(error, *, redact=True)` (`:147`, pattern `_CONTROL_CHARACTERS` `:144`); `ReadOnlyDB.connect`
  builds `DBConnectionError`'s text with it and falls back to the exception's type name when the cause has no
  text (`:361`). `cli.py:240-251` `discover` catches `DBConnectionError`, prints one `error:` line, exits 1.
  `agent.py:152` and `nodes.py:146,237` use it; `discovery.py:292,305,322` import it. The sinks (`cli.py`,
  `agent.py`) call it with `redact=False`: see the review.
- **Tests: 1,995 to 2,432 passed, 9 skipped, coverage 98.09%** (the same under `GITHUB_ACTIONS=true`); CI-scope
  `ruff` and `uv run mypy` (68 files) clean. New: `tests/hostile_text.py` (shared hostile input, a simulated
  failing dialect `fakeesc`, `database_with_a_dangling_view`); `TestSafeMessage`, `TestConnectError`,
  `TestSafeMessageWithoutRedaction`, `TestTheSharedHelpers` (`test_db.py:735-1007`); six `discover` tests
  (`test_cli.py:992-1099`); nine route tests (`test_data_agent.py:900-1116`). `USAGE.md`, the `nodes.py` and `state.py`
  `db_error` comments, `BACKLOG.md` (one item replaced by three), `PROJECT_LEARNINGS.md` #301-304.

#### Measured first, then built (the real Typer app in a subprocess; a real SQLite file; a simulated driver)
- **Route 1, `discover` on a failed connect: 418 non-blank lines, 6 ESC, `hunter2`, a traceback; after, 1 line,
  no control character, no secret, exit 1, no file.** The item had said scrubbing the message alone would not
  help because of the chained `__cause__`; it had not recorded that the chain is **unredacted**, so the secret was
  on stderr too (learning #302).
- Route 2, the "database unreachable" concern: 2 ESC and 1 BEL; after, none. Route 3, `result_summary` and the
  baseline caveat: 2 ESC, 1 BEL and a newline for a hostile table name, and **`PWD=hunter2` unmasked for a table
  named like a DSN fragment** (the item's secrets claim, first measured here on real SQLite); after, none and `PWD=***`.
- **Tests first, red against the old sites** (12 of the first batch), then **two mutation passes: 30 of 30 killed on
  the first four layers, 41 of 41 on the final code** (the second adds `redact` ignored or inverted, the
  `redact=False` branch weakened, the empty-cause fallback, `discover` catching `Exception`, and a missing newline,
  the classes the review said survived). The harness was scratch and is gone; the classes are in the ledger by id.

#### The review, and what it changed
Seven lenses over `022e6de..eaa0434`, two skeptics per finding told to refute it, a completeness critic: **86
agents, 0 errors, about 47 minutes, 79 clean checks. 42 lens findings, 39 re-checked (the claims lens reported 13,
the cap was 10): 11 confirmed, 28 partly, 0 refuted; no skeptic rated one above minor; 30 in scope, 9 adjacent. The
critic added 3 (one `major`, adjacent) and 5 gaps.** What changed the code:
- **My layering was wrong.** I re-applied the full `safe_message` at `discover`'s echo and `agent.py`'s concern as a
  belt. The masker over the composed `cannot connect to '<url>': <cause>` ate the `':` after a URL ending in
  `password=***` and the exception type after a path ending in a key word, where the old concern kept its text. The
  idempotence test passed because it tested `safe_message(safe_message(x))`, not the composed message (learning #301).
  Fix: `redact=False` at the sinks (`6da5399`); redaction stays where the text is built. **That gives up one
  accidental protection and the record says so:** the second pass had masked an unencoded-`@` password's tail in
  the URL half; the driver's own echo of that tail leaks either way (`BACKLOG.md`, the secrets item).
- **My test helper broke from SQLite 3.50.4** (even `SELECT 1` fails on a file whose `sqlite_master` I had overwritten;
  two tests failed on the uv-managed interpreters on this machine; CI's SQLite was never measured). Replaced by a
  view over a dropped table, probed on SQLite 3.47.1, 3.50.4, 3.53.3 and 3.54.0 (learning #303). One assertion was
  SQLAlchemy-2.0-specific; two loops could pass over nothing; `connect` printed a bare colon for an empty cause.
- **`safe_message`'s docstring claimed idempotence and "the masker is idempotent"**: false (`password=''hunter2`
  becomes `password=***hunter2`, then `password=***`). Reworded, with the second masker limit named.
- **Corrected by a ledger entry, not an edit:** layer 3's "all seven red" (six against its own parent); "418 lines"
  (non-blank); the mutation prose; "three more places" (seven); layer 1's "the exception a library caller prints is
  safe" (`str(e)` only; `__cause__` is raw).
- **Filed, not fixed** (adjacent, pre-existing): two password shapes `redact_db_url` misses (an unencoded `@`, a
  mistyped `://`: **a secrets matter**), `redact_secrets` quadratic on some text and `safe_message` unbounded,
  SQLAlchemy's pool logger printing a raw driver traceback, LLM and graph-crash text raw at `nodes.py:211` and
  `agent.py:54`, the website templates as an unguarded sink, repo-host failure text.

### Session 269 Handoff Evaluation (by Session 270)

**Score: 8/10.**
- **+** Route list with line numbers, each measured and labelled real or simulated, and an exact ordering ("route 3
  first, the secrets half"): Phase 1 needed no rediscovery. Gotcha 1 (redact, scrub, redact: do not simplify) and
  gotcha 3 (re-measure before writing a fix that depends on a server's wording) were followed. Learning #300's
  fake-dialect technique was reused as written. Every line number it gave for open items was right when read.
- **−** **What was wrong:** "the masker is idempotent" sat in its docstring, its ledger entry and the reasoning for the
  three-pass order, and was never measured; I had to correct it (and the test that leaned on it). It sized routes 1 to
  3 as "one helper, used by the sites": the helper was, and the sites turned out to compose text from text the
  helper had already cleaned, which the sketch could not have shown.
- **−** What was missing: that route 1's chain carries the secret; that `safe_message`'s callers feed it a composed
  message (the question I should have asked at Research).
- **ROI: high.**

### Session 270 Self-Assessment

**Score: 7/10.**
- **+** Measured every route before writing it, including the claimed secrets half and route 1's chain; tests red first;
  41 of 41 mutants killed; the work is committed as ten commits, four layers each verified as its own snapshot in a
  clean worktree with the passed-test count predicted first (1,995, 2,340, 2,347, 2,350; 2,427, 2,432: all matched).
  Fixed the in-scope review findings and filed the rest with their measurements; the review was proportionate.
- **−** **I let 11 files accumulate over the five-per-commit cap** and split afterwards (learning #304).
- **−** **I shipped a design the review had to fix** (the second masking pass), and my idempotence test tested the
  wrong string (learning #301). **I trusted "real SQLite" without running the other SQLite builds on the machine**
  (learning #303): a helper that failed on 3.50.4 for the whole of the build.
- **−** Four written claims were overstated and corrected by a ledger entry (red-first count, the mutation prose,
  "418 lines", a commit title saying the baseline errors were done).
- **−** The review used about 7.9 million subagent tokens and 47 minutes; the ultracode setting authorised it, the
  yield (3 design or test fixes, 8 claim corrections, 4 filed items) is not a lot per token.
- **Decay term:** none removed. This record is growth: `BACKLOG.md` grew by 7,075 B (110,654 to 117,729: one item
  became three), `PROJECT_LEARNINGS.md` by 3,939 B (four rows).

**What's next** (sizes are estimates, not measurements; the last three sessions each found "small" understated the work).
1. **`BACKLOG.md`'s secrets item, "A password can still reach the connect error, the report and a warning".** It is
   the only open item that leaks a secret, it needs no ruling, and its fix is described: do not echo a URL that does
   not parse, and treat an `@` in the parsed host as part of the password (or scrub the parsed password's fragments
   from the cause). Add a URL-borne-password case to the route tests: none has one.
2. **Residue routes 2(b) and 5 of the new item**: a `safe_message(e)` at `nodes.py:211` and `agent.py:54` with tests
   (one token each), and the pool logger's filter. The review's AST guard idea would stop new raw interpolations.
3. **Two items still need no ruling:** the Click 8.2 declaration (now 26 of 77 CLI tests fail under Click 8.1) and
   the `langgraph` floor.
4. **Rulings owed to the operator, unchanged:** `--db-url` option (c), one per channel for the three channels, the
   two guard-design calls, a CI job installing the dependency minimums; **new:** whether the website should sanitise
   report text itself, the saved inventory names, and whether `safe_message` should cap its input.
5. **Observed, not filed:** the root `methodology_dashboard.py` is v2.18.0 against canonical v2.19.0 (`bin/sync`'s
   job); the clean leftover worktree `.claude/worktrees/wf_5f96c807-d00-3` at `40b1c4a` is Session 269's review's
   (`git worktree remove` it); `tests/` is outside the mypy gate; `tests/hostile_text.py` duplicates helpers
   `test_discovery.py` and `test_cli.py` already hold, on purpose.

**Key files** (line numbers read off `grep -n` at this close-out).
- `db.py:144,147` `_CONTROL_CHARACTERS`, `safe_message` (its docstring is the specification: order, `redact=False`,
  why it is not a fixed point, the masker's limits); `:361` the connect error. `cli.py:240-251`, `agent.py:152`,
  `nodes.py:146,237`.
- `tests/hostile_text.py:71,96` the dialect and `database_with_a_dangling_view`; `test_db.py:735-1007`;
  `test_cli.py:992-1099`; `test_data_agent.py:861-1116`. `BACKLOG.md` the three items under "Seven more routes can
  still ..."; `PROJECT_LEARNINGS.md` #301-304; `CHANGELOG.md` the S270 entries under `## 2026-10`.

**Gotchas.**
1. **Apply `safe_message` once, to raw text. Do not re-add the masker at a sink.** A message composed from text it
   already cleaned is mangled by it; pass `redact=False` there. Both orders of redaction and the scrub are still
   needed inside the function (learning #298).
2. **`tests/hostile_text.py` registers the `fakeesc` dialect on import** and `database_with_a_dangling_view` is not a
   corrupt-schema helper any more. A test that depends on a library's behaviour should be run on the other
   interpreters here (`ls ~/.local/share/uv/python`; SQLite 3.50.4 and 3.53.3 are among them).
3. **The routes were reproduced on SQLite or a simulated dialect; the review's `@` shape on psycopg 3 against a
   fake server. Never a live PostgreSQL, MySQL, Oracle or SQL Server.** Re-measure before writing a fix that depends
   on a server's wording.
4. **The harness is gone** (the mutation script, the before/after measurement, the layer verifier lived in the
   session scratchpad); the technique is in learning #304 and the mutant classes are in the ledger by id.
5. `uv run pytest tests/test_read_budget.py tests/test_session_notes_census.py --no-cov` before every commit that
   touches `SESSION_NOTES.md`, `CLAUDE.md` or `BACKLOG.md`.
6. **Any commit that touches `docs/wiki/` publishes it.** None of this session's did.

