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

**Shards stay write-once.** A thirteenth trim writes a thirteenth file; it never appends to one of these.
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

**Nothing is bequeathed to the thirteenth trim.** The two instructions that stood here — never
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
| 11 | S277 `b461d7d` | 269 → 258 | 12 | 1,702 | `SESSION_NOTES-S269-through-S258.md` | 1,754 | 277 → 270 | none |
| 12 | S287 `this commit` | 279 → 270 | 10 | 1,299 | `SESSION_NOTES-S279-through-S270.md` | 1,352 | 287 → 280 | none |

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
one from its subject. Expect that seam at every boundary. What these twelve trims found, argued and
rejected stays in their own records and, for the blocks that stood here, at the commits above. What
they left BINDING is in `CLAUDE.md`'s `SESSION_NOTES.md`-is-trimmed bullets, which this collapse
updates rather than contradicts.

---

## ACTIVE TASK

### What Session 291 Did
**Deliverable:** **push the 8 unpushed commits (Session 289's `46f928f` and `daef416`, Session 290's six) to `origin/master` and read the CI result: do they verify on Linux? (IN PROGRESS)**
**Started:** 2026-10-31 18:06
**Status:** Session claimed. Work beginning. Chosen by the operator at Phase 0 from an area picker (first option, recommended; the opening message was only "go"). Computed at the claim, not taken from the handoff: the 13 files in `origin/master..HEAD` match none of Publish Tutorial's path filter (`docs/*.md`, `mkdocs.yml`, its own workflow file, `pyproject.toml`, `uv.lock`, the two `scripts/check_*`) and none is under `docs/wiki/`, so the push runs CI only. The push is still confirmed with the operator immediately before it runs.
**Ledger:** `CHANGELOG: pending` — the claim commit's `CHANGELOG.md` entry says (in progress); Phase 3F records the rest. Until close-out, this line is the crash breadcrumb for the next session's reconcile.

### What Session 290 Did
**Deliverable:** **Larkspur point (2): the project the tool scaffolds passes its own tests — COMPLETE** (`BACKLOG.md`'s item *Running the pipeline on a made-up company…*, narrowed to what is left). A generated project failed 8 of 8 of its own tests (9 of 9 with protected attributes), its README and both CI files ran a bare `uv sync` that installs neither `pytest` nor `ruff`, and its pre-commit hook would have rewritten four test files. Now `pytest`, `ruff check` and `ruff format --check` pass after `uv sync --extra dev` on a clean `PATH`, and a test runs all three on every suite run. **The operator decided,** by two pickers at Phase 0 (area, then item; the recommended first option both times) and a three-question picker before any code: the stub tests are **green** (each calls its stub inside `pytest.raises(NotImplementedError)`), the tools are installed with **`--extra dev`** (not a PEP 735 dependency group), and the scope is **tests, CI and format only** (the "Phase 4B" prose, Jupyter for notebooks 02 to 05 and the GitLab stage order stay filed). **Mine, not put to the operator:** the stub-call table and the shape of the generated tests, the new test file, the review fixes, the example, README and backlog wording, learnings #376 to #379, and leaving the push to them. **Started:** 2026-10-31 16:40. **Completed:** 2026-10-31 (close-out about 18:00). **Commits: six** (`git rev-list --count daef416..HEAD` after this one lands): `66fbd6f` claim, `60f5db9` the generated tests, `3f478b9` the install line, `2ed8454` the review's fixes, `5da9fc6` the documentation and this close-out; each has its own `CHANGELOG.md` entry. **None is pushed** (7 commits ahead of `origin/master` before this one, 8 after).

#### What was wrong, measured before planning
Three read-only scouts (0.48M subagent tokens, 144 tool calls, 6.7 min) generated a scaffold from HEAD, which equals Session 286's output byte for byte, and ran it. Three separate failures: **(1)** with `uv sync --extra dev`, 8 of 8 tests fail (four import a module literally named `<project_slug>`, four put `pass` inside `pytest.raises`; fixing only the name leaves four red); **(2)** a bare `uv sync` installs neither `pytest` nor `ruff`, so on a clean `PATH` `uv run pytest` and `uv run ruff` die with "Failed to spawn" (on this Mac a miniforge `pytest` on `PATH` made `uv run pytest` run, and fail the 8, which hid it); **(3)** `ruff format --check` rewrites the four test files. They also found two things the backlog did not say: the fairness test (protected attributes) has the same unrendered name, and **ruff 0.17 fails the generated lint job with RUF100** on a `# noqa: F401` in the fairness package (the name is in `__all__`). Nothing in the suite executed a rendered scaffold: `FakeRepoClient` stores the text and the template tests compare strings.

#### What changed
`templates.py`, `governance_templates.py`: the package name is rendered into the generated tests and the qmd comments; each stub test calls every stub it names (`_STUB_CALLS`) inside `pytest.raises`; the tests import the package with `import <slug>.<module> as module`, a statement `ruff format` cannot wrap; `_str_list_literal` writes an empty list as `[]`; the `noqa` is gone; the README and both CI files run `uv sync --extra dev`. `tests/agents/website/test_scaffold_runs.py` (new) drives the real `WebsiteAgent` against the fake client for four variants (tier 3 on GitLab, tier 1 on GitHub with protected attributes, a 106-character slug, empty metric and query lists), writes what it committed to a directory and runs that project's own `pytest`, `ruff check` and `ruff format --check` in a child process, sweeps every slug length from 1 to 130 through the formatter, and checks the install line per CI job by parsing the YAML. The example's notice and README findings 7 and 8, and `BACKLOG.md` point (2), now say what is true (`5da9fc6`).

#### The review, and what it changed
A workflow of four lenses (correctness, the new tests, inputs beyond the variants, and an inventory of what the change made false) over the committed tree, two skeptics per finding above nit: 56 agents, 4.94M subagent tokens, 1,094 tool calls, 34 minutes, no errors. 26 findings: 12 stood both skeptics, 5 split, 9 were refuted by both. **My own claim was false:** layer 1 said the output is format-stable "whatever the slug's length" and tested slugs of 16, 21 and 106 characters; `ruff format` wraps the constant I used for slugs of 77 to 82 only (learning #376). Fixed in `2ed8454` with the import statement and the sweep, with the empty-list case, a child `ruff --isolated`, `pytest --color=no`, a per-job CI check, a derived tool list and the narratives' package name asserted. **Filed, not fixed** (point (2) in `BACKLOG.md`): a slug equal to `tests` or a standard-library module name (`json`, `email`, `os`…) fails all its generated tests (older than the session, no reserved-name list in `derive_project_slug`). **Two errors of mine caught before commit:** I first wrote the review tally as 4 split and 10 refuted (it is 5 and 9) and said no wiki page names the install line (the Development Workflow page does, and now agrees with the scaffold); both fixed after recounting from the printed votes and grepping.

#### Verification
Red first: the new file failed 16 of 19 on the unchanged templates (tier 3: 8 generated tests fail; tier 1: 9). Mutants written against the code at each stage: 13, 7 and 22; every one caught but a docstring wording (unguarded on purpose), after one mutant that only looked caught (a syntax error with no test named; learning #379) was redone. Faithfully, on a clean `PATH` (`env -i`) after `uv sync --extra dev --python 3.11`: the Larkspur scaffold 8 passed, the tier 1 one 9, and **the example's own `out/project/`** 8 passed, with `ruff check` and `ruff format --check` clean under ruff 0.17.3 and `ruff@0.5.0`; `pre-commit run --all-files` on the tier 1 scaffold passes all three hooks. Full suite with the coverage gate (`GITHUB_ACTIONS=true`): **5,367 passed, 9 skipped, 98.46%**, 55 more tests than Session 289's CI run (5,312); `ruff check src tests packages scripts examples` and `mypy` clean. **CPython 3.14.8** (CI's interpreter last time), lock frozen, ruff 0.15.10: the three affected test files 131 passed. Both ledger guards 82 passed with the `BACKLOG.md` edit and again at this close-out with a Session 291 claim stub above this record. **Runtime smoke (3E):** `run_example.py` run keyless ends `COMPLETE`, 55 files plus the notice, 14 quality checks, 11 passed, 3 failed. **Not verified:** a real GitLab or GitHub pipeline, the `python:3.11` image (the clean-`PATH` run stands in), a Linux CI run of these commits, the `model-registry-schema` pre-commit hook on a machine where `python` is not on `PATH` (unchanged), and the rendered README.

### Session 289 Handoff Evaluation (by Session 290)

**Score: 9/10.**
- **+** Its pointers were exact and I used them: `BACKLOG.md:696` was the Larkspur item's heading and `:748` the `ReadOnlyDB` follow-ups, so the Phase 0 picker could name the areas without a search; "no file they touch matches Publish Tutorial's filter" held, and I computed the same for this session's files before relying on it; "put the next claim stub above the close-out and run the read-budget guard" is what this record was sized by. "Nothing in the ledger is due" was true.
- **−** It offered areas but not the one fact that would have shaped the choice: point (2) of the Larkspur item had an "operator call" inside it (are red stubs intended), which the item's text said and the handoff did not. It also left a stash I did not make in `git stash list` unmentioned (`stash@{0}`, "WIP on (no branch): 022e6de"); its gotcha "never `git stash`" was right and I left it alone.
- **ROI: high.**

### Session 290 Self-Assessment

**Score: 8/10.**
- **+** Measured the failures with scouts before planning, which showed the work was three defects and not one and found two the backlog did not name; asked the operator only the three design questions that were theirs; wrote the new test first and watched it fail 16 of 19; verified each layer on the path a user takes (clean `PATH`, the real install, the example's own output, the pre-commit hook) and not only in the suite; had the work reviewed adversarially before the documentation layer, fixed what stood in the same session and filed what did not; kept every commit at five files or fewer with its own entry.
- **−** Layer 1 shipped a claim ("whatever the slug's length") that I had tested on three values; the review found it, not I. The review cost 4.94M tokens and 34 minutes, and 9 of 26 findings were refuted and 5 split, so a good share of that spend bought confirmation. I inserted a test class in the middle of another class with an edit and found it only by reading the result; I miscounted a tally and made one wrong "no page says" claim, both caught before commit.
- **Decay term:** `SESSION_NOTES.md` 122,460 B at this point (196,608 B trigger); `BACKLOG.md` 201,855 → 202,572 B (the Larkspur item narrowed but gained the slug-collision line and a longer index row); `PROJECT_LEARNINGS.md` 422,830 → 426,702 B (four learnings, #376 to #379). Nothing could be removed from a mandated-read file.

**What's next** (estimates unless measured).
1. **The operator decides whether to push** the 8 commits (`46f928f`, `daef416` from Session 289 and this session's six). Computed: none of the 13 files they touch matches Publish Tutorial's filter (`docs/*.md`, `mkdocs.yml`, `pyproject.toml`, `uv.lock`, the two `scripts/check_*`, the workflow file), and none is under `docs/wiki/`, so a push runs CI only. CI has not seen the new test on Linux; read the run before calling it verified (learning #375).
2. **Operator calls, advice only:** the other Larkspur points in `BACKLOG.md:696` (point (3), the `--host` and `MPC_HOST` token mismatch, is the smallest and the only one that touches a secret; then (5) with (7), the report content; then (6) with (9), the bridge and an example smoke test; (4) needs a live GitHub account); what point (2) still lists (stale "Phase 4B" prose, Jupyter, the governance job's stage); the `ReadOnlyDB` follow-ups (`:748`); the CI interpreter item; and the front-matter limit before a thirteenth trim.
3. **Nothing in the ledger is due.**

**Key files.** `templates.py` (`:216` `_str_list_literal`, `:675` `_STUB_CALLS`, `:683` `render_test_stub`); `governance_templates.py` (`:628` `render_gitlab_ci`, `:666` `render_github_actions_ci`, `:801` `render_fairness_test_stub`), both under `src/model_project_constructor/agents/website/`; `tests/agents/website/test_scaffold_runs.py` (`:66` `VARIANTS`, `:125` `_child_env`, `:156` `_ruff`, `:186` the slug-length sweep, `:202` the install checks); `tests/agents/website/test_templates.py` (`TestScaffoldedStubTests`, the stub drift guard); `BACKLOG.md:696` and `:706` (point (2), narrowed); `examples/larkspur_mutual/README.md` findings 7 and 8; `PROJECT_LEARNINGS.md` #376 to #379.

**Gotchas.**
1. **A new stub in a scaffolded module needs an entry in `_STUB_CALLS`;** `test_every_scaffolded_stub_is_called_by_its_test` fails when the two disagree. `render_qmd_data`, `render_qmd_feature_engineering`, `render_qmd_initial_models` and `render_fairness_audit_qmd` now require `project_slug`.
2. **Python text written into a scaffold must already be `ruff format`-clean** (double quotes, blank lines, `[]` for an empty list); `test_scaffold_runs.py` fails on four variants if it is not. It runs the suite's own `pytest` and `ruff` in a child process and fails, not skips, if `ruff` is missing from the dev environment.
3. **Do not put a number in a template and claim it holds for every value without sweeping it** (learning #376).
4. Session 289's gotchas stand: the wiki still says the code filters nothing on three pages and any `docs/wiki/` edit publishes on commit; do not run `ruff format` on `db.py`, `test_data_agent.py`, `cli.py` or `scripts/run_pipeline.py`; never `git stash` (a stash that is not this session's sits in the list; leave it). `examples/larkspur_mutual/out/` is gitignored and was regenerated by this session's run.
5. Before committing a close-out, put the next claim stub above it and run the read-budget guard; do not edit `SESSION_NOTES.md`, `BACKLOG.md` or `CLAUDE.md` while a proof loop or the suite runs.

### What Session 289 Did
**Deliverable:** **Session 288's 11 commits pushed to `origin/master` and their CI result read — COMPLETE: they verify on Linux.** The push was `a7fbedf..e361047` (12 commits: Session 288's 11 and this session's claim), a fast-forward with no force, at 15:54 on 2026-10-31; both workflows it started finished green. **The operator decided,** by two pickers: the area (the first option, recommended) and, immediately before the push, "Push now" — asked because the push also deploys the public tutorial site (`be57a68` edits `docs/tutorial.md`). **Mine, not put to the operator:** reading the runs' logs and not only their status, correcting the `BACKLOG.md` item the logs contradicted, learning #375, leaving the two commits made after the push unpushed, and running no review workflow (no code changed, so there was nothing to review). **Started:** 2026-10-31 15:53. **Completed:** 2026-10-31 (close-out about 16:15). **Commits: three** (`git rev-list --count 2b53616..HEAD` after this one lands): `e361047` (claim, pushed), `46f928f` (the `BACKLOG.md` correction) and this close-out; each has its own `CHANGELOG.md` entry. **The last two are not pushed.**

#### What the runs showed
CI `41241062531`: success, 5 of 5 jobs (Data Agent decoupling, Tests, Ledger proofs in both modes, ruff, mypy). Tests: **5,312 passed, 9 skipped, coverage 98.38%, 7,351 warnings, pytest 136 s, CPython 3.14.4.** That is every test collected (5,321 locally); the one more than Session 288 recorded (5,311, run before its layer-2 commit) is `test_the_refusal_is_importable_from_the_package`, added in a later layer-3 commit. Publish Tutorial `41241062505`: success through its build, its "every linked asset exists" assertion, the `gh-pages` deploy and its "published site serves what it links" assertion; `pages-build-deployment` `41241080492` succeeded, and the live `tutorial/` page serves the new `ReadOnlyDB` paragraph (two fragments of it fetched). No `docs/wiki/` path was touched, so the wiki did not publish.

#### What the previous run showed, set beside this one
Run `41132134289` (Session 287's close-out) used `ubuntu-24.04` and CPython 3.12.3 and printed no warnings; this one used **`ubuntu-26.04` and CPython 3.14.4**. `ubuntu-latest` moved between two pushes a day apart, with no change in this repository, and the suite passed on both, so Session 288's work is not what made the warnings: the 7,351 are nearly all dependency `DeprecationWarning`s on 3.14 (langgraph, `asyncio.iscoroutinefunction`, `punycode`), and the 5 `ResourceWarning`s (unclosed SQLite connections) are the 5 recorded locally on 3.13.5. `pyproject.toml` sets no `filterwarnings`, so none fails the run. `BACKLOG.md`'s item *CI tests one Python* said "3.12.3 at the last run", "(what CI uses)" and "about 75 s"; all three were false by the push and are corrected from the logs (`46f928f`), its fix options (pin 3.12, or a matrix) unchanged and still an operator call. Learning #375.

#### Verification
Read, not recalled: every figure above is from the runs' logs (the runner group's "Image:" line, `uv sync`'s "Using CPython" line, pytest's summary line) or from `gh run view`. Both ledger guards 82 passed at the claim and before the `BACKLOG.md` commit, and again at this close-out with a Session 290 claim stub put above this record in the working tree and then removed. **Runtime smoke (3E): n/a** — no code, test or workflow file changed; the runs are this deliverable's verification. **Not verified:** any of Session 288's work on a live PostgreSQL, MySQL or MariaDB (CI has no server; unchanged), and the new tutorial paragraph's layout (its text was fetched, not looked at in a browser). **A correction to my own claim entry** (already pushed, so not rewritten): it says the dashboard's one High+ risk has no stated cause; the dashboard states it — the size flags of `CHANGELOG.md` (1.1 MB, ruled outside the read budget in Session 257), `BACKLOG.md` and `SESSION_NOTES.md` — and Session 288's entry had said so.

### Session 288 Handoff Evaluation (by Session 289)

**Score: 9/10.**
- **+** Its first item was this deliverable with the facts that mattered, each exact: 11 commits ahead, the push fires Publish Tutorial because `be57a68` edits `docs/tutorial.md`, CI had never seen the commits on Linux, "read the run before calling the work verified". Its "Not verified" list told me what a green run could and could not close. "Nothing in the ledger is due" was true.
- **−** It recorded the suite as 5,311 passed with "5 warnings" and no interpreter, so the CI figures needed a comparison before they could be read; and its gotchas did not say that CI's interpreter is whatever `ubuntu-latest` has (the backlog item it cited did, with a figure that was a day from being false).
- **ROI: high.**

### Session 289 Self-Assessment

**Score: 8/10.**
- **+** Asked before the push, as the picker option I offered said I would; read the logs and not the badge; set the run against the previous one before calling 7,351 warnings anything; traced the one-test difference to its commit; corrected the stale backlog item from evidence and kept the edit to the three sentences that were false; checked the dashboard's risk against its own output once I saw I had left it unexplained.
- **−** My claim entry says the dashboard's High+ risk has no stated cause, and the dashboard states it; Session 288's entry said so and I had not read it before writing mine. I misspelled `VALUES` in the push question the operator saw. No workflow was used in a session where the standing instruction is to use them for substantive work: this one was a push and a log read, with no code to review, and I judged a workflow would have had nothing to do.
- **Decay term:** `SESSION_NOTES.md` 113,948 B at the claim, 121,351 B now (196,608 B trigger); `BACKLOG.md` 201,209 → 201,855 B; `PROJECT_LEARNINGS.md` 421,797 → 422,830 B (one learning, #375). Nothing could be removed from a mandated-read file.

**What's next** (estimates unless measured).
1. **The two unpushed commits** (`46f928f` and this close-out). Computed: no file they touch (`BACKLOG.md`, `CHANGELOG.md`, `CLAUDE.md`, `HANDOFFS.md`, `PROJECT_LEARNINGS.md`, `SESSION_NOTES.md`) matches Publish Tutorial's filter (`docs/*.md`, `mkdocs.yml`, `pyproject.toml`, `uv.lock`, the two `scripts/check_*`, the workflow file), so a push runs CI only. The operator's call whether to push now or with the next session's work.
2. **Operator calls, advice only:** the CI interpreter item (`BACKLOG.md:1061`: pin 3.12, or a matrix that now includes 3.14, whose pytest time is measured at 136 to 180 s); then the areas the Phase 0 picker offered and this session did not take: the Larkspur defects (`BACKLOG.md:696`), the `ReadOnlyDB` follow-ups (`:748`), the smaller hardening items; and the front-matter limit before a thirteenth trim.
3. **Nothing in the ledger is due.**

**Key files.** `BACKLOG.md:1061` (the corrected item) and its index row `:67`; `PROJECT_LEARNINGS.md:381` (#375); CI runs `41241062531`, `41241062505`, `41241080492` and, for comparison, `41132134289` (`gh run view <id> --log`); `.github/workflows/ci.yml:16,27,38,56,106` (all five jobs say `runs-on: ubuntu-latest`).

**Gotchas.**
1. **A red CI after a change that cannot explain it may be the runner image.** Read the "Image:" and "Using CPython" lines before the traceback (#375). Dependency `DeprecationWarning`s on 3.14 are not failures.
2. **A later commit that touches `docs/*.md`, `mkdocs.yml`, `pyproject.toml` or `uv.lock` publishes the tutorial site on push**; the two pending commits touch none of them.
3. Session 288's gotchas stand: the wiki still says the code filters nothing on three pages and any wiki edit publishes on commit; do not run `ruff format` on `db.py`, `test_data_agent.py`, `cli.py` or `scripts/run_pipeline.py`; never `git stash`.
4. Before committing a close-out, put the next claim stub above it and run the read-budget guard; do not edit `SESSION_NOTES.md`, `BACKLOG.md` or `CLAUDE.md` while a proof loop or the suite runs.

### What Session 288 Did
**Deliverable:** **`ReadOnlyDB` is read-only — COMPLETE** (`BACKLOG.md` item 1 of the Larkspur-found defects, now removed from it). Three layers, each with its own `CHANGELOG.md` entry: **(1)** `read_only_gate.py`, a hand-written fail-closed scanner that accepts exactly one `SELECT`, `WITH` or `VALUES` statement (`fbf1cbf`); **(2)** `ReadOnlyDB.execute` calls it before a connection is borrowed, and `connect` installs per-dialect read-only hooks and fails rather than run writable (`4c20ccf`); **(3)** the documentation around it (`283de94`, `5cee3cd`, `7bc4996`, `0bfbb47`, `be57a68`) and a follow-up item in `BACKLOG.md` (`032e6fb`). A gate fix (`36d5039`) came out of the layer-2 review. **The operator decided** at Phase 0, after a two-step picker, three questions: a strict allowlist, connection-level read-only per dialect where one exists, and `validate_sql` out of scope; and, when this work resumed with layer 2 uncommitted in the tree, to continue it (a picker, because `SAFEGUARDS.md` says to ask before touching uncommitted work). **Mine, not put to the operator:** the fixes the review found, the test design, the documentation text, what to file, a passage in the tutorial (a push of it publishes the site; flagged), leaving the wiki alone and not pushing. **Started:** 2026-10-30 17:22. **Completed:** 2026-10-30 (close-out about 22:45). **Commits: eleven** (`git rev-list --count a7fbedf..HEAD` after this one lands): `8f3e947` claim, `fbf1cbf`, `36d5039`, `4c20ccf`, `283de94`, `5cee3cd`, `7bc4996`, `0bfbb47`, `be57a68`, `032e6fb` and this close-out; each has its own entry. **Nothing is pushed.**

#### What it does now
`execute` raises `ReadOnlyViolation` (a `ValueError` with a constant rule code, never the SQL) before the database is touched, so EXECUTE_QC records a refused quality check as `ERROR` and the baseline path as a `FAILED` snapshot and the run goes on. `connect` registers hooks before its first round trip: SQLite `PRAGMA query_only = ON` on `connect` and `checkout`, read back; PostgreSQL `SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY`, read back and committed, plus the engine option `postgresql_readonly`; MySQL and MariaDB `SET SESSION TRANSACTION READ ONLY` on `connect` and `checkout`. If a hook cannot be installed `connect` raises `DBConnectionError`; on any other dialect it logs a WARNING that names the dialect and only the gate applies. The two layers are needed: `query_only` alone does not stop `ATTACH` or `VACUUM INTO` creating a file (the gate does), and the gate alone let a quoted `pragma_optimize` write `sqlite_stat1` (fixed; `query_only` also stops it).

#### The review, and what it changed
The layer-2 diff was reviewed in a scratch copy by a workflow of five lenses (dialect mechanics, callers and regressions, mutation of the tests, a red team of gate, connection and both on real SQLite, and a documentation inventory) and two skeptics per claim: 51 agents, 4,987,897 subagent tokens, 900 tool calls, 33.6 minutes, no errors (the layer-1 scouts spent 871,304 more). Of 23 claims 4 were refuted by both skeptics, 2 split and 17 stood; none was above medium and **nothing got through the shipped configuration**. **Fixed:** the quoted `pragma_*` bypass of the gate and `ReadOnlyViolation` not surviving `copy` or `pickle` (`36d5039`); a `connect` hook that raises leaked the raw connection, which SQLAlchemy does not close (it put a sixth `ResourceWarning` in the suite); the docstring's per-transaction claim, true for psycopg and psycopg2 but not pg8000; the warning's wording; and every test gap the mutation lens found, by a second test file that runs SQLAlchemy's real PostgreSQL and MySQL dialects on a stand-in driver module. **Filed, not fixed** (`BACKLOG.md`, the item after the Larkspur one): three wiki pages that say the opposite (editing publishes), no CI job on a real server and MariaDB never run, the quality-check prompt never saying SELECT, the eval's "executable" metric counting a refusal, and five small things. **One of my own errors, caught before commit:** I extended the scout's "measured on PostgreSQL 17 and MySQL 8.4" to MariaDB in `USAGE.md`; re-reading the layer-1 entry corrected it.

#### Verification
Full suite on the working tree before the layer-2 commit, `GITHUB_ACTIONS=true`: **5,311 passed, 9 skipped, 5 warnings, coverage 98.46%** (layer 1: 5,197, 9, 5, 98.39%); `ruff check` and `mypy` clean; 25 mutants of `db.py` in a scratch copy, 24 caught and one equivalent survivor; three gate mutants caught. **Runtime smoke (3E):** the Larkspur example, run keyless in a scratch copy of the committed tree, ends `COMPLETE` with 14 quality checks run, 11 passed, 3 failed, none refused. **Not verified:** any of it on a live PostgreSQL, MySQL or MariaDB (none is installed; the tests use a stand-in driver and the PostgreSQL 17 and MySQL 8.4 behaviour is the scout's), the rendered tutorial page, and a Linux CI run of the session's commits (nothing is pushed).

### Session 287 Handoff Evaluation (by Session 288)

**Score: 8/10.**
- **+** Its gotchas held and I used them: put the next claim above the close-out in a scratch copy and run the read-budget guard (done below), and do not edit `SESSION_NOTES.md`, `BACKLOG.md` or `CLAUDE.md` while a proof loop or the suite runs (done: the suite ran while I edited nothing). "Nothing is due" was true, which let the operator choose from a picker without a clock.
- **−** It named only operator calls, so the deliverable came from the picker and `BACKLOG.md`, not from the handoff. And no handoff, mine included, could have told this work's resume what layer 3 was: the claim stub did not list the layer set (see below).
- **ROI: medium.**

### Session 288 Self-Assessment

**Score: 8/10.**
- **+** Asked before touching the uncommitted diff; reviewed before committing it, with skeptics on every claim and a red team that measured each layer alone, so "defence in depth" is a measurement; mutation-checked my own fixes (25 and 3 mutants); caught my MariaDB overstatement by re-reading the source; kept each commit under the five-file cap with its own entry; ran the example for a runtime check.
- **−** The claim stub did not record the layer set or the operator's decisions; they lived in one ledger entry, and the resume reconstructed layer 3 from it, so a crash would have cost more. A stray `cat` with no input hung a command for two minutes. The review cost about 5M tokens to find one gate gap and a set of test gaps, and its largest class of finding was in the tests I had written. I did not run the shard-proof loop at the layer commits (it runs at this close-out).
- **Decay term:** `SESSION_NOTES.md` is 113,269 B against the 196,608 B trigger (104,927 B before this record); `BACKLOG.md` 196,283 → about 201.2 KB (one item removed, one filed); `PROJECT_LEARNINGS.md` 416,756 → 421,797 B (five learnings, #370 to #374). Nothing could be removed.

**What's next** (estimates unless measured).
1. **The operator decides whether to push.** The branch is 11 commits ahead of `origin/master`; the push fires Publish Tutorial (`be57a68` edits `docs/tutorial.md`, a trigger path) and the CI, which has never seen these commits on Linux. Read the run before calling the work verified.
2. **Operator calls, advice only:** the item in `BACKLOG.md` after the Larkspur one (the wiki edit with its replacement text, a real-server CI job, the quality-check prompt, the eval metric); the Larkspur points (2) to (4); the second tutorial and the live pass; the front-matter limit before a thirteenth trim.
3. **Nothing in the ledger is due:** the file is far from its trigger.

**Key files.** `packages/data-agent/src/model_project_constructor_data_agent/db.py` (`:626-690` the three hooks, `:694` `_close_when_it_raises`, `:715` `_install_read_only`, `:756` `connect`, `:791` `execute`); `.../read_only_gate.py` (`:157` `check_read_only_sql`, `:208` the `PRAGMA_` word rule, `:190` the quoted rule); `tests/data_agent_package/test_db_read_only.py`, `test_db_read_only_dialects.py`, `test_read_only_gate.py`; `BACKLOG.md:748`; `PROJECT_LEARNINGS.md` #370 to #374.

**Gotchas.**
1. **The dialect tests stand on a fake `psycopg2` or `pymysql` that lists what SQLAlchemy 2.x imports from each**; a SQLAlchemy release that imports more fails them with a missing-attribute error that is the stand-in's, not the code's.
2. **A push publishes the tutorial site** (see What's next 1). The wiki still says the code filters nothing, on three pages, and the commit hook publishes any wiki edit: do not edit them without the operator.
3. **Do not run `ruff format` on `db.py`, `test_data_agent.py`, `cli.py` or `scripts/run_pipeline.py`:** each already fails `--check` at `HEAD` in code this work did not touch, and CI runs `ruff check` only.
4. **The gate refuses 47 bare words and the prompt does not say so**, so a live run may show more `ERROR` checks than before; no live run was made (no key).
5. **Any harness that runs a scratch copy must print the module's `__file__`** and not use `python -I` (learning #373). Never `git stash` (#316); the shell is zsh.

### What Session 287 Did
**Deliverable:** **the twelfth trim of `SESSION_NOTES.md` — COMPLETE.** Sessions 279 → 270 (ten records, 1,299 lines, 126,485 B, a pure byte slice) are in `docs/architecture-history/SESSION_NOTES-S279-through-S270.md` (1,352 lines, 129,852 B with its 53-line banner) beside its proof (2,108 lines). The live file fell from 219,635 B to 93,278 B at the trim and keeps this record plus Sessions 286 → 280; the front-matter table gained a row and the previous row's marker resolved to `b461d7d`. The proof adds **no** assertion (ruling F) and ships 109 mutants, none new. Chosen by the operator at Phase 0 from a picker (first option, recommended), as Session 286's addendum had planned. **The operator also decided:** at a three-option picker when the claim turned a guard red, to fix the guard's mutant in its own commit and then trim; at the commit gate (a two-question picker), that the eight-file commit is acknowledged (over `SAFEGUARDS.md`'s cap of five; a shard proof reads its prose at its own commit, so no proper subset is green) and that the push happens at close-out. **Mine, not put to the operator:** the cut (the fewest-records rule), the six-scout map and the five-lens review, building in a scratch clone from scripts, keeping the proof header's history sentences true rather than re-dating them, filing (not fixing) what the review found beyond the header and the ledger, and the rehearsal of the next claim. **Started:** 2026-10-30 14:05. **Completed:** 2026-10-30 (close-out 16:31). **Commits: five** (`git rev-list --count cbf185e..HEAD` after this one lands): `eed6901` (claim, knowingly red on one read-budget test), `3ef1a1b` (that test's mutant fixed), `60e9901` (the trim: no record edit, eight files), `dbd688c` (the review's filings, `BACKLOG.md` and the ledger) and this close-out; each has its own `CHANGELOG.md` entry. The push follows this commit and is not recorded here: a record cannot name a result that postdates its own commit.

#### The claim turned a guard red
The claim stub alone made `test_next_state[after-a-trim-then-its-close-out]` fail ("check_k_bytes is the sole catcher of no mutant"), with two ledger guards at 82 passed one commit earlier. I measured per mutant instead of reading the message: that test models a trim that keeps the floor of four records and then closes out the claim, and in that state mutant M04 (a ledger whose newest records outgrow the page in bytes only) also fired `check_k_lines`, because the predicted Read page for its file was 93 lines against a K prefix ending at line 102 and the three earlier claims (277, 285, 286) had 24, 49 and 90 lines to spare. The cause was the density of the four newest records (Session 286 holds 10,972 B in 41 lines), not the stub. I prototyped a fix on a scratch copy, asked the operator (a guard is theirs), then committed the claim as it was, red on that one test and saying so, and `3ef1a1b` pads M04's tail with blank lines until the predicted page keeps pace with the prefix; no threshold, check or other mutant changed. It was run on the committed trees of three earlier claims (47 passed each) and on the parent. The review found the twin mutant M01 has the same shape and is not fixed; it is filed.

#### The cut, the ledger and the sweep
The byte rule fired at 219,635 B. Keeping Session 280 lands at 93,150 B before the front-matter edits and keeping 279 as well at 106,359 B, over the 98,304 B stop, so the fewest-records cut is 279 → 270: ten headings, none a stub, and the retained side is this record's stub plus seven non-stub records (floor four). The front matter is 7,814 B against its 8,192 B limit (it was 7,686 B). **That leaves room for one more trim:** measured with the guard on a padded copy, 7,935 B (a thirteenth trim) passes and 8,056 B (a fourteenth) turns three next-state tests red; filed as an operator call. A whole-file `Read` of the new shard reports **51,663 tokens** against the 25,000 cap (the scouts' inference from bytes was about 50.4K), so it truncates, and the figure is in `BACKLOG.md`'s read-cap item. **The sweep, published as a dated fact** (the proof's header promises it here): at `60e9901`, `git grep -l 'SESSION_NOTES-[A-Za-z0-9-]*\.md'` returns **37** files and the broad `SESSION_NOTES-` form **39**, the extra two being `.github/workflows/ci.yml` and `docs/architecture-history/evolution-page-plan.md`; Session 277 published 35 and 37, the difference is the new shard and its proof, and the file set is otherwise identical, so the eighth re-derivation found no fifth prose file. It also found one unread stale count, `all 11 ledger proofs` in `BACKLOG.md`, reworded in `dbd688c`.

#### The proof, the harness and the two workflows
The proof is the eleventh carried forward with 94 asserted-unique edits in a script (never a hand edit of a write-once file): 31 of its 33 functions are AST-identical, `compose_row` differs in its docstring alone and `self_test` in its fixtures; the first plain run was green and `--self-test` caught 109 of 109, its listing differing from the eleventh's in exactly the three lines (M16, M24, M55) and fourteen labels the scouts predicted. **The coverage harness** exists only in a scratchpad and its recipe lived only in Session 277's record, which this trim archived, so the recipe is now in the proof's header. A scout rebuilt it, I ran it on both proofs the same day (83 variants each, none broken, the survivors identical on every variant), and the header's lists are asserted equal to the measured ones. Whether to commit the script is still the operator's call. **Map** (six read-only scouts: 1.38M tokens, 327 tool calls, 18 minutes): every fact in my brief held, and I reproduced their figures with my own scripts before using them. **Review** (five lenses and two skeptics per non-nit finding: 39 agents, 3.83M tokens, 893 tool calls, 71 minutes, 0 errors): 21 findings (1 high, 2 medium, 14 low, 4 nit), 17 judged, none kept above low, no blocker. **What it found that mattered:** my header's harness recipe had two errors I took from a scout without running it (a count of 70 appends where 64 exist, and a marker spelled in a comment that the harness itself would have matched first), fixed before the commit with the proof's code unchanged (AST equal to the measured one); the header said six strings are read by no guard and a perturbation battery of about 880 runs measured at least eight; a draft ledger sentence said the claim was green on M04 (it was red); and the close-out window below.

#### Verification
The real commit's tree hash equals the reviewed scratch commit's (`b2a7ab7`), so what was proven is what was committed. In the real tree all 14 proofs in both modes print nothing red, the new proof reads `source : the trim commit 60e9901` with L0 to L14 holding, and both guards give 82 passed (the close-out re-runs them). The full suite on a clone of the committed tree (`GITHUB_ACTIONS=true`, before the amend, which changed a proof comment and the ledger): **3,942 passed, 9 skipped**, the pre-session figures. `ruff` and `mypy` were clean at `3ef1a1b` and no code changed after it. **Runtime smoke (3E): n/a**, docs and ledger plus one test mutant; the proofs and guards are this deliverable's runtime. Session 286's push CI (`41111501708`) finished green, 5 of 5 jobs. Not run: a Linux CI run of this session's commits, the first being the push.

### Session 286 Handoff Evaluation (by Session 287)

**Score: 9/10.**
- **+** Its first recommendation was exactly this deliverable, with the figure that triggered it (217,610 B) within a kilobyte of the 218,628 B I met (its own addendum accounts for the difference), and it pointed at the procedure, not a recipe: the Session 277 record's gotchas were the recipe and held. "Both ledger guards before every commit touching the three files" saved the session: it is how the red claim was seen before it was pushed. Its CI note ("read it first") was right, and the run was green.
- **−** It could not know the claim would turn a guard red, and it said nothing about the density of its own record (Session 286's 41 lines for 10,972 B is what set M04's margin); a handoff that names the guard's margin in lines would have saved a diagnosis. It also gave a push-affects-nothing check (path filters) I re-derived because the filter's non-recursive globs matter.
- **ROI: high.**

### Session 287 Self-Assessment

**Score: 8/10.**
- **+** Measured the red guard per mutant, prototyped before asking, and asked before changing a guard; built every artifact from scripts and asserted each anchor; reconciled each scout figure against my own scripts; verified the real commit by tree hash rather than by eye; kept the proof header's history sentences true when a scout's mapping would have re-dated one; and read all 21 review findings and fixed the ones that were mine before the commit.
- **−** Two errors reached the reviewed proof because I took a scout's recipe text on trust (the append count and the marker), and an arithmetic slip (a margin of 89 that measured 90) reached a draft, both caught on re-derivation or by a lens; my first background launcher mis-quoted its log path and cost a run; a sanity check of mine located the proof's code by a string the new header had begun to mention. The claim commit was knowingly red, on the operator's say. 5.2M subagent tokens across two workflows for a deliverable that adds no assertion.
- **Decay term:** `SESSION_NOTES.md` fell from 219,635 B to 93,278 B at the trim (this record brings it to about 105 KB); `BACKLOG.md` 190,149 → 196,283 B (the filings); `PROJECT_LEARNINGS.md` 413,600 → 416,756 B (three learnings, #367 to #369).

**What's next** (estimates unless measured).
1. **Nothing is due.** The file sits near 105 KB against the 196,608 B trigger, about seven more closing records at 11 to 13 KB (an estimate), and the front matter's room for one more trim is the real clock: see the filed operator call.
2. **Operator calls, advice only as the plan in Session 286's addendum said:** the second tutorial and the live pass (still undiscussed this session); whether to commit the coverage harness; the front-matter decision before a thirteenth trim; the guard's M01 twin and the close-out window (`BACKLOG.md`, the read-budget item), small.
3. **The next claim:** run both guards at the claim state before committing it; a red from the record sizes alone is the known hole, not a regression.

**Key files.** `docs/architecture-history/SESSION_NOTES-S279-through-S270.md.verify.sh` (header `:1-124`; the harness recipe at `:78-92`); `tests/test_read_budget.py` (`_m04_the_newest_records_outgrow_the_page`, near `:627`); `BACKLOG.md` (the read-budget item, the front-matter item above it, the collapse-proof item); `PROJECT_LEARNINGS.md` #367 to #369.

**Gotchas.**
1. **The thirteenth trim must append this proof to `L10`'s hand-typed list, as the last entry, frozen at `60e9901a79443a0776e923dcd32736a2aeaf486f`.** Until it does, a one-byte edit to this proof is invisible to every proof and guard (measured by the review; filed).
2. **Four sentences in `BACKLOG.md` that name row ordinals are pinned by nothing**; the thirteenth trim advances them by hand (they are named in the ledger-table item).
3. **Before committing a close-out, put the next claim stub above it in a scratch copy and run the read-budget guard**: this record was sized and wrapped that way. A hard-wrapped record of about 12 KB is red at its own commit.
4. Do not edit `SESSION_NOTES.md`, `BACKLOG.md` or `CLAUDE.md` while a proof loop or the suite runs; the collapse proofs and the guards read them.
5. Never `git stash` (#316); the shell is zsh, so quote a redirect target built from a variable with care (a mis-quoted one cost a run here). Any commit that touches `docs/wiki/` publishes it; none of this session's did.

### What Session 286 Did
**Deliverable:** **a worked example of the pipeline on a made-up company, run keyless onto the fake repository — COMPLETE** (`examples/larkspur_mutual/`, 8 tracked files). Asked for as "the 2nd planned tutorial" (`docs/tutorial.md:5`), then **re-scoped once by the operator**: after a read-only audit found that tutorial's planned scope unwritable, they asked "can we develop an actual model project for a hypothetical company?" and chose reading A (run this tool on a made-up company) and "keyless first with the fake repo". **The second tutorial is NOT delivered; `docs/tutorial.md:5` still says "forthcoming".** **Started:** 2026-10-30 10:30. **Completed:** 2026-10-30 (close-out 13:50). **Commits: ten** (`git rev-list --count ec23bc7..HEAD` after this one lands): `540b7a3` (Phase 0 reconcile: a `reconciled` `HANDOFFS.md` receipt for the fork's BL-101 P11 span, which left three commits and none), `afecbd0` (claim), `d7ed920` (re-scope), `24629e6`, `a9bb137`, `efca54b` (layers 1 to 3), `c46de69`, `e56f41e` (the review's fixes), `2dc1175` (`BACKLOG.md` item and a README line) and this close-out; each has its own `CHANGELOG.md` entry. **Nothing is pushed.**

**Who decided what.** The operator: the task, the re-scope, reading A, "keyless first with the fake repo"; they declined two pickers to clarify and answered in prose. **Mine, not put to the operator:** the company and its idea (flag total losses at first notice of loss), that I write the stakeholder's answers, `examples/` as the home, keeping the 55 generated files out of git (the per-commit cap is 5), driving the UI over real HTTP, not pushing, FILING the tool's defects and fixing none, and the 78-agent review.

**Changed.** `examples/larkspur_mutual/`: `intake_fixture.yaml` (the interview), `serve_intake.py` and `drive_interview.py` (the shipped intake web UI with a fixture model behind it, driven over HTTP: the UI writes no file, so the driver saves `/report.json`), `make_synthetic_db.py` (40,000 fictitious claims on the real total-loss rule, three problems planted at known counts), `scripted_data_llm.py` (a stand-in for the data agent's model; its checks and baseline run for real), `run_example.py` (the shipped orchestrator, `DataAgent` and `WebsiteAgent` on a `FakeRepoClient`; writes the project to `out/project/`), `README.md`, `.gitignore`. `BACKLOG.md:694` (nine points) and its index row `:58`; one line in the root `README.md`; learning #366; `CLAUDE.md:122` (366, 413.6 KB). **No source or test file changed, and `docs/` is untouched.**

**Verified.** `run_example.py`: exit 0 in 2.01 s, `COMPLETE`, 14 quality checks of which 11 pass and 3 fail, and the 3 are exactly the three planted problems; 55 files plus `EXAMPLE_NOTICE.md`. **The generated project's own tests: 8 failed, none passed.** Full gate on the final tree: **3,942 passed, 9 skipped, coverage 98.34%** (`GITHUB_ACTIONS=true`), `ruff check src/ tests/ packages/ scripts/` and `mypy` clean: the pre-session figures, as no source or test file changed; both ledger guards 82 passed before each ledger commit. Measured on the database: 8.96% total losses of closed claims, median 4.98 days to the decision (75th percentile 8.06), 173 / 1,226 / 9 planted rows, 37,600 training rows, 3,517 closed total losses, 760 open; single-feature AUCs of the training set 0.855 (vehicle age), 0.873 (value), 0.501 (photos), 0.494 (report lag). Re-checked against the code before relying on four of the audit's claims: `model-intake-agent --anthropic` exits 2; `run_pipeline.py` has 12 flags and none takes an `IntakeReport`; the token variable follows `MPC_HOST` while the adapter follows `--host`; the GitHub adapter has no `auto_init` and reads a ref. **Not run:** a live model, a real repository host, the revision loop; the GitHub path is inferred from the code.

**The two workflows.** (1) Understand: 7 read-only agents, 1.99M subagent tokens, 18.6 min; it found the tutorial's scope could not be written truthfully. (2) Adversarial review of the example and the project it generated: 6 lenses and their skeptics, 78 agents, 6.28M tokens, 14.5 min, 59 findings judged (44 upheld, 3 contested, 12 refuted) plus 16 nits not judged. **I fixed what was mine** (an AI-written fixture header saying no model wrote it; a generated project with no fictional or scripted marker; "the pipeline finds what is there"; datasheets that omitted the scale-down and the engineered separability; storage days computed from the blanked flag; a check filed under the wrong query; hand-typed figures pinned to nothing) and **filed the tool's** in `BACKLOG.md:694`: `ReadOnlyDB` lets `DROP TABLE` through and it persists on SQLite, the scaffold fails its own tests 8 of 8 (an unrendered `<project_slug>`), `--host github --live` can send a GitLab token to GitHub, the GitHub path probably fails on an empty repository, the interview's data concerns and time range are not passed on, no route from a finished interview into `run_pipeline.py`.

### Session 285 Handoff Evaluation (by Session 286)

**Score: 9/10.**
- **+** Every pointer I used held (`BACKLOG.md:693`, the sizes, "both ledger guards before every commit touching the three files", the per-commit cap); its prediction that the twelfth trim stays due was exact; gotcha 6 (no `cd` into a subdirectory) was right and I broke it at least five times (below).
- **−** It could not know about the tutorial (`docs/tutorial.md:5`) or the fork's BL-101 P11 commits that landed after it closed: its "What's next" named only ledger and operator-call work, so the operator's request met no pointer. Not its fault; a line saying what the published docs promise would have saved me an audit.
- **ROI: high.**

### Session 286 Self-Assessment

**Score: 8/10.**
- **+** Checked the audit's claims against the code before building on them; the run is real (shipped orchestrator and agents, a real database, real HTTP); an independent review found real faults in my own work and I fixed or filed all of them; the datasheet pin was negative-tested with the number I had first got wrong; every finding in the README says whether it was run, read or reviewed; no source file was touched (the defects are filed, per the one-deliverable rule); a clean gate.
- **−** **Figures typed from memory three times** (datasheet counts "about 36,000" and "about 1,000", the review tally "40 upheld, 10 refuted" for 44 and 12, a nearly quoted AUC): caught by measuring, by the tally, and by running the pin, but learning #365 says measure where it is written. **My fixture header and README were false until the review** (an AI-written file that said no model wrote it). **At least five `cd`s into a subdirectory** despite the gotcha (the harness reported the working directory changing each time). A mistyped edit parameter (it landed correctly; I checked), two scratch files in `/tmp` and not the scratchpad. 8.3M subagent tokens in all, of which the first 2.0M served a tutorial scope the operator then replaced (its findings were reused). The tutorial the operator first asked for is not written.
- **Decay term:** nothing removed from a mandated-read file. `SESSION_NOTES.md` 207,656 B at Phase 0, 217,610 B now (**the twelfth trim is due and every close-out grows it**); `BACKLOG.md` 184,075 → 190,149 B; `PROJECT_LEARNINGS.md` 411,884 → 413,600 B.

**What's next** (estimates unless measured).
1. **The twelfth trim of `SESSION_NOTES.md`**, its own session (claim, trim, close-out: three commits; `CLAUDE.md`'s "`SESSION_NOTES.md` is trimmed" is the procedure; run both modes of every proof). Overdue and growing.
2. **Operator calls.** (a) **Push?** Ten commits are unpushed; none touches a path that fires `publish-tutorial.yml` (checked against its filter) or `docs/wiki/`, so a push deploys nothing; `BACKLOG.md`'s enterprise-migration item says unpushed commits reopen its blocker. (b) **The second tutorial:** write it as a narration of the example with its live parts marked unverified, or keep it "forthcoming" until a live run exists. (c) **The live pass the operator's "keyless first" implies:** needs an `ANTHROPIC_API_KEY` and a throwaway GitLab group and token exported in their own shell (never pasted); cost unknown, since the docs' figures have no evidence behind them (the recorded data stage took 318 to 696 s); GitHub is best skipped until `BACKLOG.md:694` point 4 is settled. (d) **`BACKLOG.md:694`**: point 1 (`ReadOnlyDB`) first.

**Key files** (read off `grep -n` at close-out). `examples/larkspur_mutual/run_example.py:44` (`DATASHEET_FIGURES`), `:53` (`NOTICE`); `scripted_data_llm.py:52` (`PRIMARY_QUERIES`), `:143` (`CHECKS`), `:300` (`DATASHEETS`), `:402` (`ScriptedDataLLM`); `make_synthetic_db.py:203` (`_claim_row`), `:245` (`_outcome_row`); `drive_interview.py:42`; `serve_intake.py:42`; `BACKLOG.md:694` and `:58`; learning #366 (`PROJECT_LEARNINGS.md:372`).

**Gotchas.**
1. **Never `cd` into a subdirectory** (the harness reports the working directory changing): start every command with `cd /Users/rmsharp/Development/model_project_constructor &&` and use `uv run --no-sync`.
2. `examples/larkspur_mutual/out/` is gitignored and every run deletes and rewrites it: never run the example while anything is reading it (I told the reviewers so), and do not keep work there.
3. The datasheets quote hand-typed counts. Change the generator or its seed and `run_example.py` stops and names each stale figure: update `scripted_data_llm.py` and `DATASHEET_FIGURES` together.
4. A workflow's `.output` file is about 400 KB: parse it with Python (`result` is a string or an object); parsed copies sit in this session's scratchpad.
5. Do not edit `SESSION_NOTES.md`, `BACKLOG.md` or `CLAUDE.md` while the full suite runs: tests read them.
6. Write every count LAST, from the command that produces it, and run a design claim before it goes in a document (#365, #366). Both ledger guards before every commit touching the three files.

**Addendum after the close-out (13:59 onward, at the operator's instruction).** **Pushed:** the ten commits `ec23bc7..e46228f` went to `origin/master` at 13:59, a fast-forward with no force; no touched path matches `publish-tutorial.yml`'s filter or `docs/wiki/`, so nothing was deployed or published. CI run `41111501708` was queued when this was written and **its result is unread: read it first** (`gh run list --limit 3`). "Nothing is pushed" and "Ten commits are unpushed" above are no longer true; this addendum's own commit is one ahead of origin and not pushed. **The operator's plan, for the next session (a separate one; they said not to start it in this one):** call 4, the twelfth trim, as its own session; and calls 2 and 3 (the second tutorial; the live pass) to be DISCUSSED, advice only, nothing built or run. A Session 287 claim for the trim was committed locally and withdrawn before any push (`git reset --mixed HEAD~1`), so no stub or receipt for it exists; the `CHANGELOG.md` push entry says so.

### What Session 285 Did
**Deliverable:** **a reply of the wrong shape from the repository host fails as a `RepoClientError` that names the field, at all nine places an adapter reads a `2xx` reply, and a failure to read the reply to the request that CREATES a project says a project may exist — COMPLETE.** Points 1 and 3 of `BACKLOG.md`'s item *A reply of the wrong shape ends as a raw `KeyError` or `TypeError` out of the adapter*, now retitled *Smaller follow-ups from the wrong-shape fix* (`:693`). Chosen by the operator at Phase 0 from two pickers (area, then item; both the first option, recommended) and **three more questions put to them:** check each field and name it (not a catch of the two classes); a wrong shape on the commit path is RETRIED as invalid JSON is (no new error class); push at close-out (yes). **Mine, not put to the operator:** the helper API and its rule (`reply_object`, `reply_string`, `reply_id`, `_host_text.py:264-318`: a non-empty string, and for GitLab's ids a non-empty string or an int that is not a bool); the note as a context manager (`reading_a_creation_reply`, `:333`) placed LAST in the message; refusing `NaN` and an infinity by field name; leaving `default_branch` unchecked; holding Session 275's net by injecting a bug into the real script (`BUGGY_BOOT`) now that a host cannot cause one; an AST guard that every `_parse_json` read goes through a helper; filing, not fixing, what the review found beside the change. **Started:** 2026-10-04 17:20. **Completed:** 2026-10-04 (close-out 20:03). **Commits: eight** (`git rev-list --count 22ba61e..HEAD` after this one lands): `f02fabb` (claim), `c32c255` (source and 331 tests, a knowingly red checkpoint: the five-file cap), `fca8c12` (the 26 older tests it broke), `b9eca14` (docs), then the review's fixes `7873fe1` (source), `814b0c6` (tests), `80d3965` (docs) and this close-out; each has its own `CHANGELOG.md` entry, and the push is recorded in the close-out's.

**Changed.** `_host_text.py`: `reply_object`, `reply_string(body, first, *rest, context)`, `reply_id`, `PROJECT_MAY_EXIST`, `reading_a_creation_reply` (a `RepoNameConflictError` and any non-`RepoClientError` pass through). Both adapters read all nine replies through them (`gitlab_adapter.py:125,148-153`, `github_adapter.py:142-148` and the five commit-path reads) and `_parse_json` returns `object`, so a subscript is a mypy error. `test_host_reply_shape.py` new, 396 tests (191 wrong-shape cases over ten routes, 36 unreadable bodies, controls, no host word in a message, the note absent at refused lookups and lost connections, ids and shas back on the wire as sent, the retry and the stop through the real graph, the AST guard, the helpers); `test_host_reuse_text.py` and `test_host_reply_nesting.py` say what the field check now refuses first; `test_run_pipeline_website_crash_resume.py` 9 → 12 (the net via `BUGGY_BOOT`, wrong shapes at the creation and the commit, and a GitHub-shaped host through `--host github`). Docs: `BACKLOG.md` (points 5 to 9 filed, the nesting item's sentences corrected), `TROUBLESHOOTING.md` (a new `repo_error: ... no usable "<field>"` entry), #364 and #365, `CLAUDE.md:122` (365, 411.9 KB). `docs/wiki/` untouched.

**Verified.** Red first: 197 of the 267 first-written tests failed on the unchanged adapters, every one of the 150 first wrong shapes (`KeyError('id')` and the like). **Runtime smoke (3E), done:** the real `scripts/run_pipeline.py --live --host github` against a socket host answering the creation `201` with `{}`, `[]` or `not json`: the OLD tree (`22ba61e`, exported with its own script) says `unexpected_error: KeyError` / `TypeError (... may already have created a project ...)` and, for not-JSON, `invalid JSON body` with no warning; this tree says `repo_error: create_project failed ...: the reply has no usable "full_name"` / `is not a JSON object` / `invalid JSON body`, each followed by `(the host answered with a success status, so a project may already exist on it)`; an honest host is identical; all exit 1, no traceback, one `POST`. **Final tree:** 3,942 passed, 9 skipped, coverage 98.34% (`GITHUB_ACTIONS=true`; was 3,540), `ruff check src/ tests/ packages/ scripts/` and `mypy` clean; the six touched test files 676 passed on 3.11.15, 3.12.13 and 3.14.6 and 668 passed with 8 skipped on `httpx` 0.27.2 (the lone-surrogate body cases; the new `NaN`/infinity ones run there); both ledger guards 82 passed.

**The review** (one workflow: 5 lenses, 2 skeptics per non-nit finding, a completeness critic: **42 agents, 0 errors, 124 min, 4.96M subagent tokens, 1,210 tool uses**; `git status` empty after). **Behaviour:** no blocker: 1,000,000 bodies per tree, same seed, 0 raw escapes from the new code (the old: 366,846 bare exceptions) and 0 disagreements with an independent oracle; 209,305 bodies the old code accepted are refused, none a shape a real host sends; 500,000 marker bodies, 0 host words in a message; the same on 3.11, 3.12, 3.14 and `httpx` 0.27.2; real sockets match. **Real findings, all but two confirmed by both skeptics, and what I did:** (major, mutation) six mutants that wrapped the note around steps that make no project survived 859 tests: pinned; (minor) 13 mutants of each message's own words, and of what goes back to the host (a numeric-string group id sent as an int, a stripped sha): pinned on the wire; (major, docs) **"the narrower design is one catch away" is false on 3.14** (a 100,000-deep reply parses there and `str()` of it raises `RecursionError`, which both name-conflict checks and the default branch run): corrected in `BACKLOG.md`, the source comment and #364; the figures I typed from memory in three ledger entries (150 → 172, "four new ones" → three, "4 in the crash-resume file" → 3 and 1): a Corrections bullet; `_parse_json` typed `object`; the shim imported the adapter before the script's own tree was first on the path; the docstring that said a `5xx` "made none"; stale comments. **Filed, not fixed:** (8) the note covers an unreadable `2xx` only (a gateway `504`, a lost connection, a cut-off `201` body and a name of ~850 characters carry none); (9) the standalone website command exits 0 on a `FAILED` result with no `--resume` guard (the critic's, which I read in `cli.py`). Left: six assertions no mutant reaches (the skeptics split on four of them; two are structural: `scrubbed_errors` cleans every message first).

### Session 284 Handoff Evaluation (by Session 285)

**Score: 9/10.**
- **+** Every pointer held (`github_adapter.py:300,320-321`, `BACKLOG.md:683,721`); "put the rest of that item to the operator first" was right and saved a wrong guess at all three choices; its prediction that the next claim would cross the trim trigger was exact (196,591 → 197,728 B at the claim); gotchas 3 and 4 (no formatter; restore a mutated file from a byte copy) were used.
- **−** It priced points 1 and 3 as "a choice" with no size: they were a vertical slice, 26 older tests in three files and a seven-commit change, which a sentence ("expect the tests that pinned `NaN` at `httpx` and the `{}` crash triggers to change") would have said. Gotcha 6 (no `cd`): I broke it once into a subdirectory, early, and returned.
- **ROI: high.**

### Session 285 Self-Assessment

**Score: 7/10.**
- **+** Red first (197 of 267); the real script on the old and new tree; nothing deleted from the 26 older tests, each rewritten for its layer; Session 275's net kept held; a review that found a major hole and a false design claim, all fixed or filed, eight surviving mutants re-run against the fixes in place with a byte-copy restore (`git status` clean).
- **−** **Three figures typed from memory into ledger entries were wrong** (the "150", "four", "4"), the same failure #361 names, and I wrote "one catch away" about a design without running it on 3.14 (#365). My tests had holes the review found, not I: nothing pinned the note ABSENT at the steps before the creation, and a numeric-string id could be turned into an int unseen. I committed a red checkpoint on purpose (the five-file cap) and did not mark its entry `(in progress)`. A zsh `$FILES` string for a file list (the matrix ran against nothing the first time). Long silences: the harness prompted me about six times while the 2-hour review ran.
- **Decay term:** nothing removed from a mandated-read file. `BACKLOG.md` 179,168 → 184,075 B; `PROJECT_LEARNINGS.md` 407,945 → 411,884 B; `SESSION_NOTES.md` 196,591 B at Phase 0, **over the 196,608 B trigger since this session's claim**.

**What's next** (estimates unless measured).
1. **The twelfth trim of `SESSION_NOTES.md`**, its own session (claim, trim, close-out: three commits; `CLAUDE.md`'s "`SESSION_NOTES.md` is trimmed" is the procedure; run both modes of every proof). It is due now and every further close-out grows the file.
2. **Operator calls**, each small, in `BACKLOG.md:693`: (4) delete the dead loop in `_is_name_conflict`; (5) a GitLab commit whose reply cannot be used is retried and the retry may be refused for creating files that exist (an inference, not measured); (6) the default branch is read, not checked; (7) a text of only spaces counts as non-empty; (8) widen the may-exist note or read the creation reply as a stream; (9) the website command's exit code on `FAILED`.
3. **Rulings owed**, as Session 283 listed; the 64-level limit's ruling now needs a guard at three more places, not one catch (`BACKLOG.md:644-657`). BACKLOG headings after `:683` moved again (`### A website crash now leaves a result` is `:779`): grep the headings.

**Key files** (read off `grep -n` at close-out). `_host_text.py:210` (`MAX_REPLY_NESTING`, its comment), `:264,291,307` (the helpers), `:327,333` (the note and its manager); `tests/agents/website/test_host_reply_shape.py:110` (`SITES`), `:160` (`context_of`), `:860,908` (the AST guard); `tests/scripts/test_run_pipeline_website_crash_resume.py:55` (`BUGGY_BOOT`), `:275,304,461`; `BACKLOG.md:693`; `TROUBLESHOOTING.md` (the entry after `unexpected_error`); learnings #364, #365 (`PROJECT_LEARNINGS.md:370,371`).

**Gotchas.**
1. `_parse_json` returns `object` on purpose: read through `reply_*`, never a subscript; the guard counts nine reads against `SITES`, so a tenth needs a site there.
2. The may-exist note is for an unreadable `2xx` and is the LAST words of the message: do not move or widen it without the operator (point 8).
3. Session 275's net (`orchestrator/pipeline.py:_website_failure`) is held only by `BUGGY_BOOT` now; a host cannot make a bare exception, so keep that test.
4. zsh does not word-split a `$FILES` string: use an array and `"${FILES[@]}"`. The version matrix is Session 283's gotcha 5.
5. Write every count LAST, from the command that produces it (`pytest --collect-only -q | grep -c ...`), and run a design claim on 3.14 before it goes in a document (#365).
6. Both ledger guards before every commit touching `SESSION_NOTES.md`, `CLAUDE.md` or `BACKLOG.md`. No `cd` into a subdirectory. `CLAUDE.md:122` states 365 learnings, Sessions 9–285, 411.9 KB.

### What Session 284 Did
**Deliverable:** **GitHub's `_is_name_conflict` answers a `422` whose `errors` is not a list and no longer raises a bare `TypeError` out of `create_project` — COMPLETE.** Point 2 of `BACKLOG.md`'s item *A reply of the wrong shape ends as a raw `KeyError` or `TypeError` out of the adapter* (`:683`). Points 1 and 3 need a choice and stay open. Chosen by the operator at Phase 0 from two pickers (area, then item; both the first option, recommended); **the operator also decided:** push at close-out (yes). **Mine:** the guard as filed and not the deletion of the loop in front of which it sits (dead code, below; filed as point 4, `:721`); the eight extra tests the review asked for. **Started:** 2026-10-04 16:00. **Completed:** 2026-10-04 (close-out 16:55). **Commits: six** (`git rev-list --count 10904d8..HEAD` after this one lands): `84e13aa` (claim), `eb7e9b3` (fix and 71 tests), `1fcc6ad` (docs, #363), `c82a891` (the review's 8 tests), `3eaf34d` (its doc corrections) and this close-out; each has its own `CHANGELOG.md` entry, and the push is recorded in the close-out's.

**Changed.** `github_adapter.py:300-330`: `errors` is read once (`:320`) and walked entry by entry only if it is a list (`:321`); any other shape is left to the whole-body "already exists" match after it. `or []` replaces a falsy value, and `5`, `-1`, `1.5` and `true` are truthy and cannot be iterated. `test_github_adapter.py` 42 → 121: 20 shapes of `errors` (`:155`, the four that crashed first) through `_is_name_conflict` and `create_project` (exactly `RepoClientError`, not its subclass), a conflict in a sibling field, 4 shapes with the wording INSIDE a non-list (`:178`), 7 non-object bodies. Docs: `BACKLOG.md` (`:683` point 2 closed, point 4 at `:721`, the index row), `TROUBLESHOOTING.md:275`, #363, `CLAUDE.md:122` (363, 407.9 KB). `docs/wiki/` untouched.

**Verified.** Red first: 16 of the first 71 tests failed on the old adapter (the four shapes in four tests). Same-seed fuzz of 60,000 random 422 bodies: the old source raised `TypeError` for 4,934, the new for none, and they never disagree where the old answered; `create_project` over 20,000 ended only as `RepoClientError` (11,430) or `RepoNameConflictError` (8,570). Of 10 mutants, 8 are killed on 121 tests; **2 survive (the loop stops after one entry; never reports a match) and are equivalent**: a loop-deleted variant agreed on 60,000 bodies, the review found no disagreement in 200,000 more and 69,075 Unicode variants of the phrase, and both survive the old 42 tests on the pre-fix source. **Runtime smoke (3E), done:** the real `scripts/run_pipeline.py --live --host github` against a socket host that answers every repo creation `422`: `errors` of `5`, `true`, `1.5` was `unexpected_error: TypeError (the website stage may already have created a project ...)`, a false warning since a `422` made nothing, and is `repo_error: create_project failed ...: 422 {...}`; a real conflict (5 POSTs) and a list `errors` are byte-identical. **Final tree:** 3,540 passed, 9 skipped, coverage 98.32% (`GITHUB_ACTIONS=true`; 3,461 + 79), `ruff check src/ tests/ packages/ scripts/` and `mypy` clean, the four adapter files 245 passed on 3.11.15, 3.12.13, 3.14.6 and `httpx` 0.27.2 (main: 3.13.5), both ledger guards 82 passed.

**The review** (read-only `Explore`, 3 lenses and a skeptic per non-nit finding: **5 agents, 0 errors, 22.6 min, 488k subagent tokens, 139 tool uses**; `git status` clean after). Behaviour lens: nothing found (260,000 random bodies agree old against new; about 40 raw socket replies and a 33-status by 45-body by 23-charset grid ended only as the two repo errors). **Two real, both reproduced by their skeptic, both fixed:** no test put the conflict wording inside a non-list `errors`, so mutants that strip it from the whole-body text or make that match case-sensitive passed all 113 (#363); and a BACKLOG sentence said the loop mutants survive "all 113 tests ... on the code from before" when 16 fail there. Five nits taken; three not (the docstring still reads as if the loop works, which is filed; `type(...) is RepoClientError` beside `match=`; `ids=repr`).

### Session 283 Handoff Evaluation (by Session 284)

**Score: 9/10.**
- **+** Item 1 was the deliverable and held on every point: file and line (`github_adapter.py:317`), fix shape, the three test inputs, the BACKLOG point, and "put the rest of that item to the operator first". Gotcha 5's command ran on three interpreters; the "observed, not filed" list matched Phase 0; its size estimate (about 189 KB) was right.
- **−** It priced the fix as a guard ("no choice in it") without knowing the loop is dead, so the cheaper fix, a deletion, was a choice; it did not say that the pipeline saved a false "a project may exist" for this crash. Gotcha 6 (no `cd`): I broke it once. The record is 15 KB, most of what moved the file toward the trigger.
- **ROI: high.**

### Session 284 Self-Assessment

**Score: 8/10.**
- **+** Red first, same-seed fuzz, the real script on the old and the new tree, mutants, and proof (not a test) that the two survivors are equivalent; filed the dead loop instead of deleting it; ran a bounded review and fixed both real findings; asked the operator about the push.
- **−** My mutants changed the guard and not what it hands on, so two real holes passed 113 tests until the review (#363). I wrote a BACKLOG sentence false of the old code, cited `:317` for a guard at `:320`, and **committed a ledger line saying `awk` found no over-wide line after `awk` had printed one** (129 characters; three rewraps, then an `--amend` of the unpushed commit). I first ran `ruff check` on two of CI's four directories. One `cd`. Long silences: the harness prompted me about seven times, as in 282 and 283.
- **Decay term:** nothing removed from a mandated-read file. `BACKLOG.md` 177,724 → 179,168 B; `PROJECT_LEARNINGS.md` 406,347 → 407,945 B; `SESSION_NOTES.md` 188,730 B at Phase 0, trigger 196,608 B.

**What's next** (estimates unless measured).
1. **Operator calls first:** delete the dead loop in `_is_name_conflict` (`BACKLOG.md:721`; a refactor, tiny, and the existing tests stay valid); the rest of the wrong-shape item (`:683`, points 1 and 3: check each field or catch the two classes, the "a project may exist" text, whether a wrong shape is retried).
2. **Rulings owed**, as Session 283 listed; BACKLOG headings after `:683` moved +14 lines (`### A website crash now leaves a result` was `:717`, is `:731`), so grep the headings, not the old numbers.
3. A twelfth trim is due when `SESSION_NOTES.md` exceeds 196,608 B; the next claim and close-out will cross it unless the record is small.

**Key files** (read off `grep -n` at close-out). `github_adapter.py:300` (`_is_name_conflict`), `:320-321` (the guard); `tests/agents/website/test_github_adapter.py:155,156,178,186,374,392,408`; `BACKLOG.md:683,721`; `TROUBLESHOOTING.md:275`; learning #363 (`PROJECT_LEARNINGS.md:369`).

**Gotchas.**
1. The entry loop in `_is_name_conflict` is dead code: do not write a test to kill its two surviving mutants, and do not delete it without the operator.
2. `{"errors": 5, "message": "... already exists"}` on a `422` is a NAME CONFLICT (5 POSTs, `project_name_conflict`), on purpose and pinned (`test_github_adapter.py:408`).
3. CI runs `ruff check src/ tests/ packages/ scripts/` and no `ruff format`; the touched files are not format-clean at HEAD, so do not run it.
4. A mutation harness that rewrites the repo source must restore from a byte copy in `finally` (never `git stash` or `checkout`); check `git status` after. Check line widths with `awk` BEFORE writing that they are fine.
5. Both ledger guards before every commit touching `SESSION_NOTES.md`, `CLAUDE.md` or `BACKLOG.md`. No `cd`. `CLAUDE.md:122` states 363 learnings, Sessions 9–284, 407.9 KB.

### What Session 283 Did
**Deliverable:** **the adapters turn three inputs a host or the caller chose, which used to leave them as raw exceptions, into a clean failure: a reply nested too deeply (`RecursionError`), a redirect `httpx` cannot build (`InvalidURL`, `ValueError`, `idna`'s errors), and a lone surrogate in the GitLab namespace (`UnicodeEncodeError`) — COMPLETE, with a limit on how the first was done and one claim corrected.** Points 3 to 5 of `BACKLOG.md`'s item *The id and the branch go into request paths unquoted, and one wiki sentence is now imprecise* (`:610`; filed by Session 282). **The deliverable's name over-promises, and the review proved it:** "the adapters raise only `RepoClientError` for any host reply" is still false for a reply of the wrong shape (a bare `KeyError`/`TypeError` at nine places, plus GitHub's name-conflict check on a `422`), filed as its own item (`:683`). Chosen by the operator at Phase 0 from two pickers (the area, then the item; both the first option, recommended). **The operator also decided:** push at close-out (yes; I had written "13 commits" in that question without counting, and there are twelve). **Mine, and not put to the operator:** a LIMIT of 64 levels on every reply (`reply_json`) in place of catching `RecursionError` at each end, which refuses a reply whose deep part nothing reads (a cost, below); the helper in `_host_text.py` and not a copy per adapter; overriding the PRIVATE `httpx` method `_build_redirect_request` and converting `InvalidURL` and `ValueError` there, with a canary; `RemoteProtocolError` and not `LocalProtocolError`; the namespace catch in the adapter and not at the command; rewriting Session 275's deep-reply crash case; filing, not fixing, what the review found beside it. **Started:** 2026-10-04 13:46. **Completed:** 2026-10-04 (close-out 15:40). **Commits: twelve** (counted with `git rev-list --count 6075853..HEAD` after this one lands): `17ca079` (claim), `e265f8c` (the nesting fix) and `8cde06f` (its tests), `f445c5d` (namespace), `ee8fec0` (redirect), `cdb1080` (docs), then the review's corrections `fdf9cb1`, `8ff2adc`, `eaa9285`, `a7270f3`, `760bdaf` (the by-hand counts brought to the final tree), and this close-out. Each carries its own `CHANGELOG.md` entry; the push is recorded in the close-out's.

#### What changed
- **`_host_text.py`:** `MAX_REPLY_NESTING = 64` (`:197`, with the measured interpreter table), `_nests_deeper_than` (`:200`, a level at a time over arrays and objects only), `reply_json` (`:227`: `response.json()` with `RecursionError` turned into a `ValueError`, and a reply nested past the limit refused as the same; raised after the handler so nothing is chained). **`github_adapter.py:294,313` and `gitlab_adapter.py:222,239`** read every reply through it (`_parse_json` and `_is_name_conflict`, which the filing did not list). **`gitlab_adapter.py:100`**: the namespace is quoted before the `try` and the `UnicodeEncodeError` becomes a `RepoClientError`.
- **`_http.py`:** `_build_redirect_request` (`:104`) and `UNBUILDABLE_REDIRECT_TEXT` (`:67`); the module docstring says what `httpx` builds a redirect request for (301, 302, 303, 307, 308 only), what it raises (three classes, one of them for `mailto:x`), why the override is where it is and the alternative not taken (a response hook).
- **Tests (3,369 passed + 9 skipped → 3,461 passed + 9 skipped, +92):** `test_host_reply_nesting.py` new, 52 (the helper; each of the nine reply sites and the two name-conflict checks against a real socket that RECORDS what reached it; a value one level past the limit refused and the request that would carry it absent; a stub for the `RecursionError` handler; the message holds none of the host's words); `test_repo_http_client.py` 87 → 124 (the redirect section with its canary, all five statuses, `mailto:x`, 300/304/305 untouched, a transport's `ValueError` untouched; the namespace for both adapters); `test_host_failure_text.py` +2 (the adapters call `.json()` nowhere); `test_run_pipeline_website_crash_resume.py` 5 → 6 (the deep case rewritten, and a `201` variant).
- **Docs:** `BACKLOG.md` (the item closed down with the corrected facts; the new wrong-shape item `:683`; point 4 of the channels item `:388`; the CI-Python item; two index rows), `TROUBLESHOOTING.md`, `PROJECT_LEARNINGS.md` #359-362, `CLAUDE.md:122` (362, 406.3 KB). `docs/wiki/` not touched.

#### Verification
Red first on every fix: 17 of the 40 first nesting tests failed on the unchanged adapters (a bare `RecursionError` at all 11 reply sites, a value one level past the limit sent on at six); 13 of 20 redirect tests (the raw `InvalidURL`, `ValueError` and `idna` errors); GitLab's namespace alone. **Fuzz, same seed before and after:** 60,000 hostile `Location` values gave 85 raw escapes (`InvalidURL` 38, `idna` 38, `ValueError` 9) and, through `RepoHttpClient`, 31,481 returned and 28,519 `RemoteProtocolError` (28,434 + 85), none raw. **24 mutants** of the four fixes all killed with each run's total equal to the unmutated 200; the review then found two that survived (the `RecursionError` handler deleted, which no test noticed on 3.14, and a message that appended `response.text[:40]`), I added a third (a walk that always answers no), and all three are killed. **Interpreters, on the final tree:** the five touched or neighbouring files 295 passed on 3.11.15, 3.12.13 and 3.14.6 (3.13.5 is the main environment), `httpx` 0.27.2 251 passed, 44 skipped. Final tree: **full suite 3,461 passed, 9 skipped, coverage 98.32%** (`GITHUB_ACTIONS=true`), `ruff check` and `mypy` clean, both ledger guards 82 passed. **Runtime smoke (3E), done:** the real pipeline script against a real socket host that answers every request `302 Location: mailto:x` ends, on the old tree, `unexpected_error: InvalidURL (the website stage may already have created a project ...)` and, on HEAD, `repo_error: group lookup failed for ...: the host's reply redirected the request, and the HTTP library could not build ...`, both exit 1 and no traceback; the fixture pipeline (fake host) exits 0 with `Status:  COMPLETE` and `--resume` prints the address; the new end-to-end tests drive the real script at a socket host for a `400` and a `201` 100,000 levels deep.

#### The review, and what it found
One workflow: five read-only lenses (hostile inputs, compatibility and callers, test faithfulness, docs and ledger, design and scope) and two skeptics per non-nit finding: **51 agents, 0 errors, 56.8 minutes, 4.84M subagent tokens, 918 tool uses.** 23 non-nit findings (20 confirmed by both skeptics, 2 split, 1 refuted by both) and 9 nits. **Fixed:** the walk allocated a tuple per scalar (10M scalars: 928 MB and 1.22 s, now 409 ms and no extra); my interpreter claims were wrong in five places (`json` fails at **995, 9,998, 9,999 and 116,211** levels on 3.11 to 3.14, not "about 10,000 on 3.11 to 3.13 and none on 3.14"); the `RecursionError` handler ran for no input on 3.14; nothing pinned that the message holds none of the host's words; the redirect text blamed the address when a cookie can cause it; "a `Location` is read on every 3xx" (five statuses); `mailto:x` was missing from the canaries, and is the cheapest member of the class; my replacement test served a `400`, where no project exists. **Corrected and filed, not fixed:** **the namespace fix is unreachable from the website command and the pipeline script** (reproduced: `--namespace $'a\xffb'` is a `TypeError: string contains surrogates` out of LangGraph's checkpointer before the adapter is reached), so three documents saying the run "now fails cleanly" were true of a direct call only (BACKLOG `:388` point 4); GitHub's `_is_name_conflict` raises a bare `TypeError` for a `422` whose `errors` is a number (the only raw escape at a non-2xx in a 30,000-reply fuzz) and an unusable `2xx` is a clean error that does not warn a project may exist (both in `:683`); the limit refuses a reply whose deep part nothing reads (at `6075853` a `201` with an unused field 100 levels deep completed; real replies nest at most 5). **Not taken:** the response hook as the redirect fix (split 1 to 1; recorded in `_http.py` as the fallback if a release renames the private method); a different message for a `RecursionError` a deep caller stack caused (split; documented in `reply_json`); `invalid JSON body` for a valid deep body; a `UserWarning` out of the standard library's cookie jar under `-W error`.

### Session 282 Handoff Evaluation (by Session 283)

**Score: 7/10.**
- **+** Item 1 of "What's next" was the deliverable and its pointer held (`BACKLOG.md:596`, points 3 to 5, and `gitlab_adapter.py:99`). Gotcha 1 (keep a canary that the plain library still raises what the client converts) is the pattern I used for the redirect, and it is what made the private-method override defensible. Gotcha 4 gave the working `httpx` 0.27.2 command; gotcha 5 (the recording router) was reused as it was; gotcha 3 held.
- **−** The three filed fixes were each a symptom-shaped prescription. Point 5 said "also catch `InvalidURL` in the `send` override", which names one class of three and a hook that would also hide the transport's `ValueError`; point 4 said "the fix is in `_parse_json`", which leaves a window between what the parser reads and what a body can hold; its depths ("9,998", "9,992 to 9,997") were one interpreter's and stated as general. "Make the adapters raise only `RepoClientError` for any host reply" over-promised: the wrong-shape reply at nine places was in the code, documented in `TROUBLESHOOTING.md` and filed nowhere. Gotcha 6 (do not `cd` into a subdirectory) was right and I broke it twice, once with my own `cd` and once through parallel Bash calls.
- **ROI: high.**

### Session 283 Self-Assessment

**Score: 7/10.**
- **+** Reproduced all three before designing, found by fuzz that the filed redirect fix named one class of three, chose the hook by where the traceback shows the raise, wrote every test red first, held the namespace and redirect fixes to a mutation check and to the interpreters I had installed, ran the review before closing and acted on it: fixed what it proved, corrected earlier entries by a "Corrections" bullet instead of editing them, and filed what it found beside the change instead of fixing a fourth capability.
- **−** I wrote "now fails cleanly" for a surrogate namespace in three documents after testing the adapter alone, when both shipped entry points die earlier (#359). I stated one interpreter's `json` depths as a range in five places and let a test input stay under 3.14's failing depth, so a handler ran for no input there (#361). I chose a limit that refuses replies that used to work and first wrote only its benefit. My replacement for Session 275's deep-reply case served a `400`, the one variant where no project exists (#362). I wrote "13 commits" in a question to the operator without counting (eleven). I went long stretches without saying what I was doing and the harness prompted me several times, as it did Session 282.
- **Decay term:** nothing was removed from a mandated-read file. `SESSION_NOTES.md` 173,804 B before this record (trigger 196,608 B); `BACKLOG.md` 168,449 → 177,706 B; `PROJECT_LEARNINGS.md` 402,079 → 406,347 B. **A twelfth trim is not due at this commit** (this record is about 15 KB, leaving the file near 189 KB), **but the next close-out of this size is an estimate that crosses the trigger.**

**What's next** (sizes and effort are estimates unless measured; none is blocking).
1. **Small, no ruling, one capability:** GitHub's `_is_name_conflict` iterates a truthy non-list `errors` (`github_adapter.py:317`, the loop over `body.get("errors", []) or []`): `isinstance(errors, list)` before it, plus a test where `{"errors": 5}` and `true` and `1.5` on a `422` give a `RepoClientError` (BACKLOG `:683`, point 2). The rest of that item needs a choice (check the field and name it, or catch the two classes; whether a wrong shape is retried; the project-may-exist wording): put the choice to the operator first.
2. **Rulings owed:** the new ones: the wrong-shape item (`:683`); the namespace channel (`:388` point 4: reject at the command or at `RepoTarget`, and the exit status); the 64-level limit's cost (a narrower design, catch at the read and check the six values written back, is the alternative). As Session 282 listed: the `[]` reply (`:863`); one named error class per cause (`:822`); the discovery log line (`:774`); what `run` exits with for a failed report (`:347`); `L10`'s completeness gap; the wiki corrections (`:610` point 2 and `:774`); `MPC_LOG_LEVEL` (`:877`); the Session 277 coverage harness.
3. **Observed, not filed:** as Session 282 listed (`stash@{0}`, the two `worktree-wf_*` branches, the dashboard at v2.18.0 against v2.19.0, the `gitleaks` count, `TROUBLESHOOTING.md` §FAILED_AT_DATA's first bullet, `loopback.py`'s module docstring, `README.md:97`'s "199 website agent tests", `nodes.py:243`'s "(1s, 2s, 4s)"); and that `pytest` on a fresh `UV_PROJECT_ENVIRONMENT` is whatever is first on the `PATH` unless `--extra dev` is given.

**Key files** (line numbers read off `grep -n` at this close-out).
- `src/model_project_constructor/agents/website/_host_text.py:197,200,227`; `_http.py:67,97,104,114`; `gitlab_adapter.py:100,222,239`; `github_adapter.py:294,313` (and `:317`, the unguarded `errors` loop).
- `tests/agents/website/test_host_reply_nesting.py:121,128,221,263` (the stub, the sites); `test_repo_http_client.py:428,449,468,531` (the namespace test, the redirect section, `HOSTILE_REDIRECTS`, the statuses); `tests/scripts/test_run_pipeline_website_crash_resume.py:221,248` (the `400` and the `201`); `BACKLOG.md:388,610,683,893`; `TROUBLESHOOTING.md` (the `unexpected_error` paragraph and the limit paragraph under "A project address, id, branch or commit id with terminal control codes"); learnings #359-362.

**Gotchas.**
1. **`reply_json` measures the whole reply, not the values read.** A reply nested past 64 levels is refused even where nothing reads the deep part, and the limit must stay far below 995 (3.11's failing depth). Raising it needs the interpreter table in `_host_text.py:184` and the test that writes a value of that depth into a body, a path and a message.
2. **The redirect conversion sits on a PRIVATE `httpx` method.** Keep `test_the_installed_httpx_still_raises_what_this_client_converts_for_a_redirect` green on a library bump; if a release renames `_build_redirect_request` the conversion goes inert and that test fails (a response hook that drops the `Location` is the recorded fallback). A reviewer measured `httpx` 1.0.dev6 as a rewrite with no `send`, `build_request` or `_build_redirect_request` (I did not re-check), so the existing overrides break there too.
3. **A namespace with a lone surrogate is refused by the ADAPTER only.** Do not write a run-level "fails cleanly" for it (#359); the command and the script die earlier.
4. **A `2xx` that cannot be used as JSON carries no "project may exist" warning**, where a wrong-shape `2xx` gets it from the net; both are in `:683`. `--resume` refuses either way.
5. **Run a file on another Python with** `UV_PROJECT_ENVIRONMENT=<scratch dir> uv run --frozen --extra agents --extra ui --extra dev --python 3.X python -m pytest <files> --no-cov` (never a bare `uv run --python`, which replaces `.venv`). The `httpx` 0.27 half: `uv run --with "httpx==0.27.2" pytest <files> --no-cov`.
6. **Do not `cd` into a subdirectory in a Bash call, and do not run two Bash calls in parallel when either has a `cd`:** the working directory drifted twice. Never `git stash` (#316). Both ledger guards before every commit touching `SESSION_NOTES.md`, `CLAUDE.md` or `BACKLOG.md`. `CLAUDE.md:122` states the learnings count and size (362, Sessions 9–283).

### What Session 282 Did
**Deliverable:** **`RepoHttpClient.build_request` turns a request `httpx` cannot build into an `httpx.LocalProtocolError`, so a value the host sent and an adapter writes into its next request fails the call as a `RepoClientError` and no longer ends the run in a traceback — COMPLETE.** Items 1 and 2 of `BACKLOG.md`'s
*An adapter puts a value the host sent into its next request* (filed by Session 281; now retitled *The id and the branch go into request
paths unquoted, and one wiki sentence is now imprecise*, with the two points that were never part of the fix and four new ones). `httpx`
raises `InvalidURL` (a C0 control or DEL in a path) and `ValueError` (a lone surrogate, as `UnicodeEncodeError`, in a path or, from 0.28,
a body; a `NaN` or an infinity in a body) while it BUILDS a request; none is an `httpx.HTTPError`, so no adapter `except` caught it.
**The filed fix said to extend the client's `send` override. That cannot work:** the error is raised in `build_request`, before `send`
(a probe of the plain client and its traceback), so the override is `build_request`. Chosen by the operator at Phase 0 from two pickers
(the area, then the item; both the first option, recommended). **The operator also decided:** push at close-out (yes). **Mine, and not
put to the operator:** `build_request` and not `send` (the evidence decided it); converting `ValueError`, not two class names (the
review found `NaN`); leaving `RecursionError` out (a deeper nest bypasses it); reusing `LocalProtocolError` with a second fixed text;
rewriting the four strict expected failures instead of unmarking them (the run now FAILS, it does not complete); filing, not fixing,
what the review found beside it. **Started:** 2026-10-04 07:55. **Completed:** 2026-10-04. **Commits: eight** (counted with
`git rev-list` after this one lands): `13fec02` (claim), `e5ebd40` (fix), `64c8124` (adapter, agent and end-to-end tests),
`c1688a4` (docs), `8f7fb72`, `818853a`, `78792f3` (the review's findings: client, tests, docs) and this close-out. Each carries its own
`CHANGELOG.md` entry; the push is recorded in the close-out's.

#### What changed
- **`_http.py`:** `UNBUILDABLE_REQUEST_TEXT` (`:40`), `RepoHttpClient.build_request` (`:66`, `suppress(httpx.InvalidURL, ValueError)`,
  raised after the handler so nothing is chained), class and module docstrings that record what the library's message holds and the
  three build-time causes (a path, a body, a host's non-ASCII `Set-Cookie`, which refuses every later request). `send` (`:73`) unchanged.
- **Tests (3,232 passed + 4 xfailed → 3,369 passed, 9 skipped):** `test_repo_http_client.py` 20 → 87 (a canary that the plain library still
  raises what the client converts; every method, `request`, `stream`, `build_request`; a body; headers compared as well as the address
  and body; a caller's `TypeError` passes through; the cookie; an adapter turns it into its own error). `test_host_reuse_text.py` new, 68
  (a real socket that RECORDS what reached the host, so a refused request is shown ABSENT and not sent cleaned: GitHub's `parent_sha` and
  four body shas, GitLab's group id, controls that the sequences complete on ordinary values, the agent over each adapter).
  `test_host_success_end_to_end.py` 6 → 8 (the real command and the real script at a GitHub host whose parent sha holds an escape
  sequence). `test_host_success_text.py` 121 → 117 (`GITHUB_REUSES_THE_SHA` gone). `success_hosts.py`: `recording` (`:154`), `shas` and
  `group_id` overrides (`:78`), a prefix match for GitHub's parent commit, `HTTPX_WRITES_JSON_AS_UTF8` (`:30`, moved).
- **Docs:** `BACKLOG.md` item at `:596` (points 1 to 6) and its index row (`:57`) and route 8's cross-reference; `TROUBLESHOOTING.md` (the
  limit paragraph, the `unexpected_error` causes); `_host_text.py` docstring; `PROJECT_LEARNINGS.md` #356-358; `CLAUDE.md:122` (358,
  402.1 KB). `docs/wiki/` not touched.

#### Verification
Red first: with only the text constant added, **56 of the new tests failed, each at the crash** (`InvalidURL`, `UnicodeEncodeError`, or
`isinstance(..., RepoClientError)` false); one `KeyError` was my own test's premise (GitLab percent-encodes the namespace, so a control
code there builds) and was fixed in the test. Final tree: **full suite 3,369 passed, 9 skipped, coverage 98.34%** (`GITHUB_ACTIONS=true`),
`ruff check` and `mypy` clean, both ledger guards 82 passed. **16 mutants** of the client and the fixtures (no override, one class only,
the former two-class catch, catch everything, catch `TypeError` too, raise inside the handler, wrong text, quote the original, send
something else, not an `HTTPError`, `send` override removed, a header dropped, `recording` records nothing, the parent prefix route
removed, a cleaned value sent) all caught, each run's total equal to the unmutated run's (368). **`httpx` 0.27.2** (overlay, which
`pyproject.toml` admits and CI never runs): the focused files 336 passed, 44 skipped (the JSON-body cases), on 0.28.1 376 passed.
**Runtime smoke (3E), done:** the two end-to-end tests drive the real command and the real script as subprocesses (they fail without
the fix: 2 failed, 6 passed); the fixture pipeline (`run_pipeline.py`, fake host) exits 0 with `Status:  COMPLETE`, and `--resume` of it
prints the address.

#### The review, and what it found
One workflow: five read-only lenses (hostile inputs, completeness and callers, test faithfulness, docs and ledger, behaviour and
compatibility) and two skeptics per non-nit finding: 39 agents, 0 errors, 32.8 minutes, 3.68M subagent tokens, 643 tool uses. 28 findings
(11 nits, not put to skeptics); of the other 17, 11 confirmed by both skeptics, 3 split, 3 refuted by both. **Fixed:** a host reply of
`{"sha": NaN}` (or an infinity) ended in a bare `ValueError` after the project existed (three lenses; I reproduced it); my premise that
the library's error "quotes the value" was false for a path (one character and its position; #333 had refuted it, and my own red run
had printed it); I had written GitLab's group-id failure as "a retried commit with the project already created" in three documents, and
it fails at `create_project`, before anything is made, with no retry; the "built exactly as before" test ignored headers (a
`build_request` that dropped `Accept` passed 668 tests); two stale docstrings; a wrong retry comment of mine. **Filed (older, not
caused):** GitLab's raw `UnicodeEncodeError` for a surrogate in the namespace (`quote` raises it before `httpx`); the deep-nesting
`RecursionError`; a 3xx with a very long `Location` (raised in `send`; I reproduced it, the skeptics ruled it out of scope for this
change); CI never runs `httpx` 0.27. **Not changed:** `RecursionError` in the catch; the website command exiting 0 for a `FAILED` result
(the ruling already owed at `BACKLOG.md:346`); that a deterministic failure still costs three attempts and 3 s of waiting.

### Session 281 Handoff Evaluation (by Session 282)

**Score: 8/10.**
- **+** Item 1 of "What's next" was the deliverable and its pointer (`BACKLOG.md:596`) held; "no ruling" held. Gotcha 1 (route a fixture on
  the parsed path) is exactly what `success_hosts.serve` does and I built on it; gotcha 3 (`GITHUB_REUSES_THE_SHA` applies from `httpx`
  0.28 only) held, and I measured the other side on 0.27.2; gotcha 5 (never `git stash`, both guards) held.
- **−** The item's fix line named the wrong hook ("have `RepoHttpClient` turn ... into an `httpx.HTTPError`" reads as an extension of the
  existing `send` override, and the error is raised in `build_request`) and called the fix "one place, it covers a value added later",
  which `NaN` shows was only as wide as the classes it listed. "Remove `GITHUB_REUSES_THE_SHA` (its four strict cases go red the moment
  it works)" was half right: they go red, but because the run now fails cleanly, so removing the mark was not the fix (#357).
- **ROI: high.**

### Session 282 Self-Assessment

**Score: 7/10.**
- **+** Claimed first, measured the premise (a traceback frame) before choosing the override, wrote the tests red first and read why each
  failed, found my own test premise wrong (the namespace) from the red run, drove a mutation check to 16 mutants with totals compared,
  measured `httpx` 0.27.2 instead of guessing, ran the review before closing and fixed or filed every finding, corrected earlier
  ledger entries by a "Corrections" bullet instead of editing them, counted the new test cases before writing a number (31 became 47).
- **−** I wrote "both quote the value" into six places after #333 had refuted it and after my own red run printed the opposite; I wrote
  GitLab's outcome from the GitHub flow without running it; I chose the catch list from the filed item (two class names) when the claim was
  "a request it cannot build" (#356). I went long stretches without saying what I was doing, and the harness had to prompt me for it
  several times.
- **Decay term:** nothing was removed from a mandated-read file. `SESSION_NOTES.md` 160,370 B before this record (trigger 196,608 B);
  `BACKLOG.md` 165,622 → 168,449 B; `PROJECT_LEARNINGS.md` 398,801 → 402,079 B. **A twelfth trim is not due:** 172,828 B now against the trigger at 196,608 B, and this record is about 13 KB, so one or two more
  closing records at this size is an estimate.

**What's next** (sizes and effort are estimates unless measured; none is blocking).
1. **Small, no ruling, one capability: make the adapters raise only `RepoClientError` for any host reply.** Three gaps filed by this
   session (`BACKLOG.md:596`, points 3 to 5): catch `UnicodeEncodeError` where GitLab quotes the namespace (`gitlab_adapter.py:99`); catch
   `RecursionError` in both `_parse_json`; also convert `InvalidURL` in `RepoHttpClient.send` for a redirect's long `Location`. Route 2(b)
   (`BACKLOG.md:451`, a logging filter on the `sqlalchemy` loggers) is the other small one.
2. **Rulings owed, as Session 281 listed (line numbers are current):** the `[]` reply (`:795`); one named error class per cause (`:754`);
   the discovery log line (`:706`); the lone-surrogate channels (`:387`) and what `run` exits with for a failed report (`:346`);
   `L10`'s completeness gap; the wiki corrections (`:596` point 2 and `:706`); `MPC_LOG_LEVEL` (`:809`); the Session 277 coverage harness.
3. **Observed, not filed:** as Session 281 listed (`stash@{0}`, the two `worktree-wf_*` branches, the dashboard at v2.18.0 against
   v2.19.0, the `gitleaks` count, `TROUBLESHOOTING.md` §FAILED_AT_DATA's first bullet, `loopback.py`'s module docstring, `README.md:97`'s
   "199 website agent tests"), and `nodes.py:243`'s docstring "Delay doubles each attempt (1s, 2s, 4s)", where three attempts sleep twice (1 s, 2 s).

**Key files** (line numbers read off `grep -n` at this close-out).
- `src/model_project_constructor/agents/website/_http.py:40,48,66,73`; `github_adapter.py:204-258` (the values read from one reply,
  `:204,213,226,239,253`, and written into the next request: the parent into a path at `:208`, the rest into bodies); `gitlab_adapter.py:99` (the namespace, `quote`), `:113` (the group id into a body);
  `_host_text.py:15-36` (the docstring).
- `tests/agents/website/test_host_reuse_text.py:50,61,80,97,110,224`; `test_repo_http_client.py` (from "A request `httpx` cannot build");
  `success_hosts.py:30,78,154`; `test_host_success_end_to_end.py` (the last two tests); `BACKLOG.md:57,596`; `TROUBLESHOOTING.md`
  (`unexpected_error` causes, and the limit paragraph under "A project address, id, branch or commit id with terminal control codes");
  learnings #356-358.

**Gotchas.**
1. **The error is raised in `build_request`, not `send`.** Keep the canary test (the plain library still raises what the client
   converts) green on a library bump, or the fix goes inert silently (#356).
2. **The catch is `InvalidURL` and `ValueError`.** A `TypeError` passes through on purpose (a caller's type JSON cannot hold, which a JSON
   reply cannot produce); `RecursionError` is deliberately not caught. Widening either needs a test that says why.
3. **GitLab's group-id failure is at `create_project`: nothing made, not retried.** GitHub's commit sites are attempted three times with a
   1 s and a 2 s wait, with the repository already made. Do not write one outcome for both (#358).
4. **The `httpx` 0.27 half is run by hand:** `uv run --with "httpx==0.27.2" pytest <files> --no-cov` (the overlay replaces the locked
   version; check with `python -c "import httpx; print(httpx.__version__)"`). The JSON-body cases skip there; the path and cookie cases run.
5. **A "never sent" claim needs the recording router.** A request sent with something cleaned out also fails cleanly; only the list of what
   reached the host tells the two apart (`success_hosts.recording`, routing on the parsed path).
6. **Do not `cd` into a subdirectory in a Bash call**: the working directory carried over twice this session and I used absolute paths
   from then on. Never `git stash` (#316). Both ledger guards before every commit touching `SESSION_NOTES.md`, `CLAUDE.md` or
   `BACKLOG.md`. `uv run python` for anything that imports the package. `CLAUDE.md:122` states the learnings count and size (358,
   Sessions 9–282).

### What Session 281 Did
**Deliverable:** **the repository host's success values are scrubbed where they leave the adapters — COMPLETE.** Route 8 of
`BACKLOG.md`'s "Seven more routes" item. A host's 2xx reply carries the project address, id, default branch and commit id; they
reached the website command's `Project:`/`Commit:` lines and the script's `Project:` line raw, were saved in
`RepoProjectResult.result.json`, came back raw on `--resume`, and the id and branch went back to the host in a request path,
where a control character made `httpx.InvalidURL` escape from `commit_files`. I reproduced all of it first through the real command
and the real script against a socket (OSC title and `ESC c` on stdout; an id with ESC: a traceback after the host had made the
project). Now both adapters' `create_project` and `commit_files` leave through `scrubbed_values` (`_host_text.py`), the return-side
twin of `scrubbed_errors`, with the adapter's own token; `--resume` scrubs the address it reads back. Chosen by the operator at Phase 0
from a picker (first option, recommended). **The operator also decided:** push at close-out (yes). **Mine, and not put to the
operator:** the adapters as the layer, not the nodes or the three prints (the token is the adapters', and Session 275's crash-resume
fixture modelled a host echoing it as the project id); U+FFFD for a lone surrogate (after the review); filing, not fixing, the values an
adapter sends back in its next request; replacing Session 275's `echoed-id` case, whose `InvalidURL` the fix removes. **Started:**
2026-10-03 23:17. **Completed:** 2026-10-04. **Commits: ten** (counted with `git rev-list`): `55b179e` (claim), `ab71441` (fix),
`d132f1e` (adapter and agent tests), `24e6091` (`--resume`), `71c5ff8` (end-to-end tests), `9456ae3` (docs), `1f205ea`, `2e759ae`,
`4ea8a07` (the review's findings) and this close-out. Each carries its own `CHANGELOG.md` entry; the push is recorded in the
close-out's. (I told the operator 11 at the push picker. There were nine, ten with this one: learning #355.)

#### What changed
- **`_host_text.py`:** `scrub_project_info` (`:225`), `scrub_commit_info` (`:252`), `scrubbed_values` (`:267`, marker
  `__scrubs_host_values__`), `_secret_of` (`:294`, a guarded read: no secret means every field `<unprintable>`), `NOTICE_ROOM` (`:64`),
  `REPLACEMENT` (`:72`, U+FFFD: `scrub_host_text` used to write `?`). Applied under `@scrubbed_errors` at `gitlab_adapter.py:90,135`
  and `github_adapter.py:106,180`. `scripts/run_pipeline.py:417` (`_handle_already_complete`). `protocol.py` docstrings.
- **Tests (3,073 → 3,232 passed, 4 strict expected failures):** `tests/agents/website/success_hosts.py` (new: the hostile table and
  routers for GitLab's sequence and GitHub's two, routed on the parsed path, `serve` at `:156`); `test_host_success_text.py` (new, 121:
  every field and kind on all three sequences, the token, the agent over each adapter, a stub showing the limit, the registry marker at
  `:298`; `GITHUB_REUSES_THE_SHA` at `:56`); `test_host_success_end_to_end.py` (new, 6: the real command and script, `--resume`, an id
  with a control code, a token echoed as the id); `test_host_text.py` 53 → 79; `tests/scripts/test_run_pipeline_resume.py` 7 → 17;
  `test_run_pipeline_website_crash_resume.py` (`echoed-id` replaced by a non-object body, a vestigial assertion removed).
- **Docs:** `BACKLOG.md` route 8 closed (`:525`), the count words, index row (`:56`) and cost paragraph (`:593`) moved together, a new
  item *An adapter puts a value the host sent into its next request* (`:596`, index row `:57`); `TROUBLESHOOTING.md:355` (the
  guarantee) and `:278` (a stale cause); `PROJECT_LEARNINGS.md` #352-355; `CLAUDE.md:122` (355, 398.8 KB). `docs/wiki/` not touched.

#### Verification
Full suite with `GITHUB_ACTIONS=true` on the final tree: **3,232 passed, 9 skipped, 4 xfailed**, coverage 98.34%; `ruff check src/
tests/ packages/ scripts/` and `mypy` clean; both ledger guards 82 passed. Red first: the first agent-level file (43 tests, nodes
design) 42 failed for the right reasons; the end-to-end file's first five failed on the control codes and `InvalidURL`; the resume
tests 7 of 9; the surrogate fix 4 (with the realistic router). The rebuilt adapter-level tests came after the fix and are held by
mutation instead: **21 mutants** (each decorator removed, each field unscrubbed, paths scrubbed, the secret dropped or ignored or read
unguarded, the marker removed, the type guard removed, the identity scrub, `?` for a surrogate, no notice room, and three of the resume
print) all caught, each run's total equal to the unmutated run's. **Runtime smoke (3E), done:** the fixture pipeline (`run_pipeline.py`,
fake host) exits 0 with `Status:  COMPLETE`, and `--resume` of it prints the address and exits 0; the hostile runs are the end-to-end tests.

#### The review, and what it found
One workflow: five read-only lenses (completeness, test faithfulness, callers, docs and ledger, hostile inputs), two skeptics per
non-nit finding: 37 agents, 0 errors, 26 minutes, 3.48M subagent tokens, 642 tool uses. 31 findings (15 nits); every non-nit one was
confirmed by both skeptics except one (1 to 1). **No host text reached a terminal from the shipped adapters.** **Fixed:** my `?` for a
lone surrogate started a query in a request path, so a GitHub id named the real repository and crashed with `KeyError` (my router
matched the raw target, `?` included, and hid it); `--resume` re-scrubbed a cut address and printed a false count; the secret read was
unguarded; strict expected failures that `httpx` 0.27 would turn into passes; docstrings that said an id "names nothing the host has"
(false at the ends) and "at most 1,000 characters"; two end-to-end assertions that could not fail as written; the docs crediting the
end-to-end file with the resume print's scrub. **Filed (older, not caused):** a lone surrogate in any value an adapter sends back
(GitHub's base-tree, blob, new-tree and commit shas and `parent_sha`; GitLab's group id) crashes with `UnicodeEncodeError`, each
reproduced by me over a real socket. **Not changed:** the `or "main"` fallback runs before the scrub (a branch of only control codes
is sent empty; older; documented). A reviewer's harness overwrote my `mutate.py` in the shared scratch directory (not the repository).

### Session 280 Handoff Evaluation (by Session 281)

**Score: 8/10.**
- **+** "What's next" item 1 was the deliverable and its pointer (`BACKLOG.md:524`) and "no ruling" held. Gotcha 1 (chain a script and
  its commit; read `git show --stat`) I followed for every commit; gotcha 5 (never stash, both guards, `CLAUDE.md:122`) held.
- **−** It passed on route 8's own fix line ("`scrub_host_text(value)` (no secret) ... or at the three prints") without the facts that
  decided it: Session 275's crash-resume test depends on an `InvalidURL` from a control-coded id, a host can echo the token, and
  `--resume` reads a file the adapters cannot reach. The item's script line numbers were stale (`:663`, `:403` for `:672`, `:412`).
  "Small" held for the code, not for the session. Its gotcha 5 said never bare `python3`; I used it for text-editing scripts
  that import nothing from the package, which the rule's reason does not reach but its words do.
- **ROI: high.**

### Session 281 Self-Assessment

**Score: 7/10.**
- **+** Claimed first, reproduced through the real command and script before changing anything, ran a read-only scout in parallel with
  writing the first tests, moved the design when its evidence (the token, the crash-resume fixture) said to, kept every commit at five
  files or fewer with its own ledger entry, drove a mutation check to 21 mutants with counts compared, ran the review before closing and
  fixed or filed all of it.
- **−** The first test file was built around the nodes before the scout's harness lens returned, then rebuilt. The `?` bug was mine and
  my fixture hid it: I did not ask what the replacement character means in the place the value goes next (#352). I wrote a ledger claim
  about evidence I had not produced ("run red against the unfixed adapters") and caught it only on re-reading the entry (#355), and I
  told the operator 11 commits when there were 9, Session 279's exact mistake. Two assertions could not fail as written, and three
  docstrings overstated; the review found each.
- **Decay term:** nothing was removed from a mandated-read file. `SESSION_NOTES.md` 148,539 B before this record (trigger 196,608 B);
  `BACKLOG.md` 157,960 → about 165 KB; `PROJECT_LEARNINGS.md` 395,969 → 398,801 B. **A twelfth trim is not due:** about two or three
  more closing records at this size is an estimate.

**What's next** (sizes and effort are estimates unless measured; none is blocking).
1. **Small, no ruling:** the new item *An adapter puts a value the host sent into its next request* (`BACKLOG.md:596`): have
   `RepoHttpClient` (`_http.py`) turn `InvalidURL` and `UnicodeEncodeError` into an `httpx.HTTPError`, then remove
   `GITHUB_REUSES_THE_SHA` (its four strict cases go red the moment it works). Route 2(b) (`:451`, a logging filter on the `sqlalchemy`
   loggers) is the other small one.
2. **Rulings owed, as Session 280 listed:** the `[]` reply (`:773`); one named error class per cause (`:732`); the discovery log line
   (`:711`); the lone-surrogate channels (`:387`) and what `run` exits with for a failed report (`:346`); `L10`'s completeness gap; the
   wiki corrections (`:684`, and now `Extending-the-Pipeline.md:106`); `MPC_LOG_LEVEL` (`:787`); the Session 277 coverage harness.
3. **Observed, not filed:** as Session 280 listed (`stash@{0}`, the two `worktree-wf_*` branches, the dashboard at v2.18.0, the
   `gitleaks` count, `TROUBLESHOOTING.md` §FAILED_AT_DATA's first bullet, `loopback.py`'s module docstring), and `README.md:97`
   ("199 website agent tests"; the scout counted 378 before this session added more).

**Key files** (line numbers read off `grep -n` at this close-out).
- `src/model_project_constructor/agents/website/_host_text.py:64,72,225,252,267,294`; `gitlab_adapter.py:90,135`;
  `github_adapter.py:106,180` (and `:204,213,226,239,253` for the filed reuse); `protocol.py` (`ProjectInfo` docstring);
  `scripts/run_pipeline.py:399,417`.
- `tests/agents/website/success_hosts.py:156`; `test_host_success_text.py:56,298`; `test_host_success_end_to_end.py`;
  `tests/scripts/test_run_pipeline_resume.py`; `BACKLOG.md:56,57,525,593,596`; `TROUBLESHOOTING.md:278,355`; learnings #352-355.

**Gotchas.**
1. **Route a fixture on the parsed path, never the raw request target** (`success_hosts.serve`): matching the target hid a `?` that a
   real server reads as the start of the query (#352).
2. **A second scrub needs `limit=MAX_HOST_TEXT + NOTICE_ROOM`** to leave once-scrubbed text alone; with the default it cuts the notice
   and counts again. A lone surrogate is U+FFFD now, in failure text too; no test pins `?`.
3. **`GITHUB_REUSES_THE_SHA` applies from `httpx` 0.28 only** (the lock has 0.28.1; `pyproject.toml` admits 0.27, which escapes the
   surrogate). Remove the marks with the fix for the filed item.
4. **Review agents share the session's scratch directory** and may overwrite a harness there; give each harness its own name, and
   count commits with `git rev-list --count` before stating a number (#355).
5. Never `git stash` (#316). Both ledger guards before every commit touching `SESSION_NOTES.md`, `CLAUDE.md` or `BACKLOG.md`. `uv run
   python` for anything that imports the package. `CLAUDE.md:122` states the learnings count and size (355, Sessions 9–281).

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

