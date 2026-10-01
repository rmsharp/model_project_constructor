# Backlog

**Open work only.** Completed items move to `CHANGELOG.md` (chronological, session-numbered). Milestone-grouped summaries live in `ROADMAP.md`. **Do not leave checked-off `[x]` items here** — remove the line on completion and record the work in `CHANGELOG.md` per `docs/methodology/README.md` §templates (v2.1 three-file split).

---

## Plain-language index — read this to the operator in Phase 0

**Why this exists.** In Session 223 the operator read a Phase 0 report that listed the open items by
their headings and said: *"I do not understand any of the 9 listed items."* That was a fair
complaint — the items below are written by sessions for sessions, and their headings are opaque
without the shared vocabulary. This section is the translation, **written once so no future session
has to regenerate it**, at the operator's explicit instruction (2026-08-17).

**Maintain it.** When you open, close, or materially change an item below, update its row here in the
same commit. A row that disagrees with its item is worse than no row.

### The vocabulary the headings assume

The pipeline's agents call a **large language model (LLM)**. Three routes to one are wired:
`anthropic` (the direct API — **the default, and what actually runs**), `bedrock` (Amazon's hosting),
and `opencode` (a command-line program fronting ~75 vendors, added so an enterprise standardising on
a different AI CLI is not a rewrite). Before any route becomes the default it must pass a **gate**:
eight measurements against real live calls, costing real money. The code that runs them is the
**eval harness** (`tests/eval/`) — test scaffolding, not shipped product. A **sweep** is one batch
run of it. A **transient** is a momentary glitch (timeout, dropped connection, one garbled reply) as
opposed to the model genuinely being bad at the task.

The eight gate measurements: valid JSON emitted; SQL syntactically valid; SQL actually executes;
agreement with reference answers on claim cycle-time; **never** rating a risk less severe than the
reference (zero tolerance); quality-check queries structurally correct; the interview reaches a
complete picture; **never** ending an interview early (zero tolerance).

### The items, in plain terms

**Five of these are one complaint** — *the measuring instrument cannot reliably tell "the model is
bad" from "something hiccuped."* That is what cost `opencode` its recorded verdict. The largest of
them — four surfaces applying three different glitch policies — **closed in Session 225**; the two
rows below it are the smaller residue that closing it exposed.

| Item (heading below) | In plain terms | Cost / note |
|---|---|---|
| Re-measure `opencode` | `opencode` was recorded NO-GO on a single glitch in 15 samples. Session 220 re-ran 45 samples and it never recurred; Sessions 221 and 225 then fixed the harness to retry a glitch before scoring it — and deliberately did **not** re-run the measurement, because changing your instrument after seeing a number you dislike is how a gate stops being a gate. The verdict on the books rests on an instrument since repaired, now in both halves. | **~$16.40, ~130 min.** The only item that costs real money. Source `.env` first. |
| Two sweeps stay silent about a dropped sample | Closing the transient-policy item (Session 225) left two smaller siblings. The live interview gate is the one measurement surface that still passes the sweep no place to log to, so every retry and exclusion note it produces — including the error text that makes a failure attributable — is discarded. And the driver reports how many samples the governance and SQL sweeps dropped, but not the interview one, so that denominator can shrink invisibly in the report. | Two one-line changes. No money. |
| A glitch means different things per provider | The harness decides "network blip" vs "the model is bad" by looking at the *type* of error raised. Only the two direct-API providers raise the network types; `opencode` runs as a subprocess and reports a spawn failure, a crash and a timeout as the same error a garbled reply produces. So the identical real-world event is discounted for one provider and counted against another. | Pre-existing, affects all three sweeps. Fixing it means changing the adapter's error mapping, not the harness. |
| A bare `KeyError` aborts the whole sweep | If the model returns valid JSON with the *wrong field names*, the code dies on an unhandled error that no part of the harness catches — killing a run that may be an hour in, instead of recording one failure and moving on. | Small. Mirrors a convention the intake agent already ships. |
| No circuit breaker | A run failing for a systemic reason grinds on sample after sample. The retry added in Session 221 tripled the SQL/QC worst case to **~7.5 hours of billed nothing**, and Session 225 added the same tripling to the governance block — so the figure in the item below now **understates** it. | Small. Should abort after ~5 consecutive total failures. |
| Unset `ANTHROPIC_API_KEY` scores as 45 failures | Without the key, every call fails with a generic "Unexpected server error" naming neither authentication nor the variable — and the harness faithfully scores that as *"this model cannot write SQL, 0%."* A misconfiguration is indistinguishable from a bad model. Actually happened; voided a run. | Half-fixed in Session 221 (the cause is now in the log). The message still names nothing. |
| The gate measures only ONE of three dialect prompts | Session 217 told the model which SQL dialect to write for in three places. The gate checks the effect of exactly one of them. | Closing it needs a **new scorer and a new gate key** — a design change, not a wiring fix. |
| `SESSION_NOTES.md` shards past the read cap | Session 222 moved 24,564 lines of history into an archive. When an agent reads a file past the cap it gets an **announced partial view** — the notice names the overage and the next page — and past a separate byte ceiling the read is refused outright. Nothing is dropped in silence. (This item said *“silently stops at 2,000 lines — no error, no marker”* until Session 249; that was measured and is false.) The dashboard has a watch-list for exactly this, but it is a list of exact filenames and the archive is not on it. **Session 224 made it two archives, Session 228 a third, Session 231 a fourth, Session 235 a fifth, Session 239 a sixth, Session 242 a seventh, Session 245 an eighth, Session 256 a ninth and Session 266 a tenth** (804, 933, 790, 976, 1,057, 644, 792 and 1,732 lines for the second through ninth, 1,498 for the tenth) — not all of the nine newer ones read whole either (measured Session 249 by probing each, Session 256 for the ninth and Session 266 for the tenth, never by line count; the count and the per-shard result are in the item below); all are equally unwatched, and every future trim adds one more. | **Operator call.** The fix is one line in shared fleet tooling at `~/Development/methodology`, synced to 13 projects — not this repo's to edit. |
| A clean `git merge` still publishes nothing | Closing the two items above (Session 241) showed the filed diagnosis was incomplete. `post-commit` now reads merge commits correctly, but git only runs `post-commit` for a merge **you** finish with `git commit` after a conflict. For a clean `git merge` or `git pull` git runs **`post-merge`**, and this repository installs no such hook — so a merge or pull that carries a wiki change still publishes nothing, silently. | Small: a `post-merge` hook using `ORIG_HEAD..HEAD` (a fast-forward pull moves many commits, so inspecting `HEAD` alone is not enough). Verified, and pinned red-if-git-changes by `test_a_clean_merge_never_reaches_this_hook`. |
| Two finished plans still sit in the active-plans folder | `httpx-adapter-migration.md` was fully executed but never archived — and `repository-rename.md` went EXECUTED in the very commit that filed this item, which is the identical case and the heavier one. | Small, but moving either re-points every citation of its path — sweep first, and rule on both together. |
| Enterprise migration | Handing the project to an enterprise as a one-time copy of the public GitHub repository. Landing the branch, closing public exposure, removing LGPL dependencies, and the legal packet are **done**. **Session 263 audited readiness: not ready yet, but close.** Its one blocker — unpushed commits the copy would have dropped — was cleared by the operator's push that session, and reopens whenever a session leaves commits unpushed. Five small fixes should land on the original first (a leftover licence text, a local-only commit, a missing tag, a stale secrets report, a missing pre-flight check). The runtime-readiness phase was never started: not a gate, but "only the fork remains" was wrong. | The fork itself still waits on five decisions only the operator can make: destination host, import strategy, contributor agreement, wiki destination, and what happens to existing releases. The punch list is in the item. |
| Three more channels can still write a file that will not reload | Session 267 closed the one this backlog had named, `--request-context`. Its review then found three siblings with the same defect: the `run` command's request file, a model's reply, and the interview's stakeholder and session ids can each carry half an emoji or a stray byte that is accepted, written with exit 0, and refused when the next step loads it. | **Operator call** per channel (reject or degrade; what `run` should exit with). The fixes are small once ruled. |
| `run` crashes at the very end if a database check returns binary data | After the whole run — every model call made and paid for — writing the report fails on a sample row that is a binary value that is not valid UTF-8 (or a PostgreSQL `bytea`). Exit 1, and no report. | **Small**, but a choice: hex-encode the value, or record that check as errored. |
| Seven more places can still put database, driver or other error text on the screen or in a report | Sessions 269 and 270 closed the routes that mattered most: the schema probe's messages, a failed connection (it ended in a traceback), the "database unreachable" note, and the SQL errors the `run` command copies into its report (one of which let a secret-looking string through unmasked). Seven remain: an unparseable `--db-url` echoed as typed, warnings and log lines SQLAlchemy prints itself, the table and column names saved in the inventory, the output path, the *language model's* error text (not the database's) copied into a report, the website generator copying report text into files without a check of its own, and a repository host's error page printed raw. | **Small** for the SQLAlchemy lines and the language-model text, no ruling. **Operator call** on the saved names and on whether the website should check for itself. |
| A password can still reach the connect error, the report and a warning | Two spellings of a database address slip past the code that hides passwords: a password containing an unencoded `@` (the part after it is read as the host, and a driver quotes the host back), and a mistyped `://` (the whole address is printed with the password in it). Both print a password or most of one in the `error:` line `discover` now shows, in the report, and in a warning. Neither is new (the old code printed them in a traceback), and no test puts a password in the address. | **Small**, no ruling: stop printing an address that does not parse, and treat an `@` in the parsed host as a password. **A secrets matter, so worth doing before the rest.** |
| `redact_secrets` is slow on some text, and nothing limits how much text `safe_message` reads | A message made of thousands of `://x:` runs with no spaces takes seconds to minutes (4x longer each time the text doubles), and a 10-million-character message uses 1 to 2 GB. No database driver normally produces either. | **Small**, but a choice: a cap on the length shortens a very long `[SQL: ...]` that is now shown whole. |
| Only `typer`'s minimum version has ever been checked | Session 268 closed the `typer` item (the minimum is now `>=0.16.0`, and a test holds it) and, doing it, found that nothing installs ANY declared minimum, because the lock pins every package far above it. Asked of the others, `langgraph>=0.2` fails at once: at 0.2.0 the intake command cannot even start, and the first release that works is 0.2.57. The rest started, but only `--help` was run. | **Small** to raise `langgraph` (measure the data agent's own tests at its minimum first). **Operator call** for a CI job that installs the minimums, the only thing that would have caught either. |
| The tests need Click 8.2 and nothing says so | Under Click 8.1, 26 CLI tests fail because they read the error stream separately and Click 8.1 does not capture it that way; the program itself runs fine there. And one test imports Click directly although no file declares it: it arrives by accident through other packages, and newer Typer stops bringing it. | **Small** — declare `click>=8.2` in the dev extras. |
| A bad `--db-url` still exits 0 | **Two thirds of this closed in Session 260.** The run used to throw away the message naming the cause, so a typo'd port, an unexported shell variable and a genuine warehouse outage produced byte-identical reports; now the cause is in the report (with any password masked) and a URL that fails to *parse* also logs a warning. What is left: the run still reports `COMPLETE` and exits 0 with **every quality check unexecuted** — the cause is reported, but nothing gates on it. | **Operator call.** Making it halt turns runs that succeed today into failures, which is the point of it, and changes `DataReport` status semantics across two packages. Three shapes are in the item. |
| CLI-adapter portability (`opencode` spec) | Not a bug — the umbrella record of the four-phase `opencode` adapter build. **All four phases are DONE.** It stays here as the provenance trail for the measurement items above. | Nothing to execute. |
| `sql_exec` — CLOSED | Historical marker, kept deliberately. Nothing to do. | Nothing to execute. |
| The docs toolchain has no version ceiling | `pyproject.toml` bounds the tutorial site's theme from below only (`>=9.0`), so a major Material release could be resolved into the public site. Deliberately deferred when the renderer landed. Session 243 made such a bump fail as a red job instead of a silent unstyled publish; the ceiling would stop it being resolved at all. | Small — 2 lines + `uv lock`. Non-binding today: Material 10.x does not exist. |

| `README.md`'s test counts are hand-typed and will drift again | Session 247 found three per-directory rows in `README.md`'s repo map stale by a combined 131 tests. **Session 250 fixed the numerals** — each re-measured against `pytest --collect-only`, not pasted from the filing — and every count in that block now agrees with the collection: the rows sum to the 1,347 collected, and the headline's 1,338 passing plus 9 live-skipped is the same figure. What remains is the design question the filing raised: nothing derives any of those counts, so the next test added re-opens the drift. | **Operator call.** Either accept periodic hand re-measurement (the verification command is in the item below), or build a sibling of the census guard that composes the rows from a collection pass — a design change, not a typo fix. |
| The wiki's `Contributing.md` carries a second, older test census | The contributors' wiki page states how many test **functions** each `tests/` directory holds — a different measure from `README.md`'s collected-test counts, since one parametrized function collects as many tests, and the page says so. Measured in Session 250 with the page's own command: `data_agent_package/`, `eval/`, `scripts/` and the top-level files are stale, its total is (997, now 1,167), and its "1110 passed plus 12 skip" sentence is (now 1,338 and 9); it also names four top-level test files where five exist. Filed, not fixed: the wiki publishes to GitHub on commit, so this is an outward-facing edit the operator did not ask for. | **Small**: one paragraph and a table, plus the same derive-or-accept decision as the `README.md` row above. Anything under `docs/wiki/` publishes via the post-commit hook. |

| Are the ledger budgets worth what they cost? | **Operator question, 2026-08-26.** The trim trigger (>1,500 lines), target (≤1,050) and floor (4 records) were each derived as a fraction of an agent read cap nobody had re-derived since Session 222. Measured at Session 247: **3 of the last 10 sessions were lossless trims, 5 of 10 were ledger-apparatus work, and the last 3 consecutively were.** Filed here rather than left in a handoff, because an item that lives only in a what's-next list gets carried ([#180](PROJECT_LEARNINGS.md)). | **ANSWERED — Session 248.** The analysis is [`docs/planning/ledger-budgets-review.md`](docs/planning/ledger-budgets-review.md): the read-cap premise was measured and is false, the retention rule is unsatisfiable as declared, and the options are laid out with mechanisms and costs. **What remains is an operator ruling**, then one session per option ruled. Re-tuning anything is still a SEPARATE session. **And the target is INSUFFICIENT, not merely unjustified** — measured Session 249, a trim that hits ≤1,050 lines exactly still produces 80,349 bytes against a one-`Read` budget of ~56,750, so no value the floor permits can deliver a one-pass file. **Option A landed in Session 249.** **RULED by the operator, Session 252 (2026-09-07)** — see [`§13`](docs/planning/ledger-budgets-review.md): **E retroactive first, then D (widened to the four mandated-read files, K expressed in bytes), then a CI step running `--self-test`; F ruled with that CI step as its substitute; B, C, G and H declined.** Three sessions, in that order. **The `--self-test` repair that came ahead of all three LANDED in Session 253, E in Session 254, and D, widened, in Session 255** (`PROJECT_CONVENTIONS.md` §5, `tests/test_read_budget.py`): the ruling is fully executed, and this row can close once read — except that F's own completion criterion — `CLAUDE.md`'s trim bullet saying no assertion is owed per trim and naming its substitute, and `L15`'s deferral recorded as a decision — was left undone until Session 256 recorded both there. Session 255 measured two more premises moved — every K figure in circulation, this row's old `K = 4` included, had counted claim stubs (one `Read` delivers two non-stub records), and the page is sized by the whole file, not the front matter alone (review §14). |

| The NO-OP guard cannot see a partially inert mutant | Session 253 repaired the broken proof and added a guard: a mutant that corrupts nothing is now reported as a broken *fixture* rather than a missed *assertion*. The guard compares the whole argument list, so it catches a mutant that has gone completely inert — and misses one that mutates three things and loses one of them. Measured: 7 of 46 are exposed, all of them reading frozen inputs that cannot drift, so nothing is broken today. | **Small.** Compare slot-by-slot, or accept the seven and say so. |
| Neither collapse proof is guarded by anything | `L10` enforces write-once over the ancestor *shard* proofs by a hand-declared list; `R4/GONE` covers every shard the table declares, and its proof. Nothing covers `SESSION_NOTES-pointer-collapse.verify.sh` or `SESSION_NOTES-pointer-collapse-S254.verify.sh` — and the second is the declared second custodian of the 276 deleted lines, the reason "nothing was lost" does not rest on git alone. Delete either file and the remaining proofs pass; CI errors only when *zero* proofs are found. | **Small.** Add both to a write-once list, or have each assert the other exists. |
| A quotation can defeat the S254 collapse proof's self-test | Two of that proof's self-test mutations find the oldest live record by searching for the text `### What Session `, which matches the LAST place that text appears anywhere, not the last heading. A record that quotes it lands the search inside the quotation, the mutation edits nothing, and the proof reports a surviving mutant, which turns CI red. Session 266's trim would have hit it; rewording one quotation avoided it. Session 264's record holds another, so a later trim can hit it again. | **Operator call.** Small — anchor both searches at a line start — but it edits a custodian proof that nothing guards, in the session that needs it green. |
| The ledger table's rows after the eighth are guarded only in form | The table at the top of `SESSION_NOTES.md` names, for each trim, the commit that added its archive. A proof checks the first eight commit hashes against git; row 9's and every later one are not checked: the guard accepts any seven to forty hex digits, so a wrong hash, an extra trailing cell or trailing spaces on a later row stay green (each measured in a clone by Session 266's review). That trim typed row 9's hash by hand, after measuring it, and the next trim will copy the pattern for row 10. A related trap found the same way: a session record that quotes the newest row word for word turns four guard tests red at its own commit. | **Small; operator call.** The guard reads no git on purpose (CI checks out shallow), so deriving the hash belongs in the trim's own proof, which does read git. |
| The read-budget guard cannot model "claim, then a wide close-out" from a close-out state | The guard tests each next commit by modelling what the following session will write. One of its models starts only when the newest record is still a claim stub, so from a finished close-out it never runs. Session 266's review measured the consequence with short lines: a close-out of about 19.7 to 19.9 KB, or of about 22 KB, passes at its own commit and turns the NEXT session's claim commit red. Behind it is a recurring cause: the mutant that isolates one check has been repaired five times in four sessions, each time for the quantity the last red named (learning #287). | **Small.** Add the missing model, and an assertion inside that mutant. Until then, before committing a close-out, put the next claim stub above it in a scratch copy and run the guard. |
| The bequest list is the front matter's remaining growth seam | Session 254's record claimed the new standing block is "fixed-size by construction". Measured, one region is not: the bequest list was 12 lines / 1,013 B at Session 254, **14% of the front matter**, and it is per-trim by content. Session 256 resolved one item into its own record and carried the rest to the tenth trim (8 lines / 0.7 KiB); Session 266, that trim, retired the rest into a three-line "nothing is bequeathed" paragraph, with both instructions recorded in `CLAUDE.md`, so the list is empty today. Nothing asserts its size and nothing stops a trim appending rather than rewriting. | **Small**, and it is a discipline rather than code: a session that resolves a bequest moves it into its own record. Or assert a byte ceiling on that region. |
| `PROJECT_LEARNINGS.md` is refused, and newest-last | A default `Read` of the project's learnings file returns nothing at all: it is past the 256 KiB size at which the agent's file reader refuses outright. It is also ordered oldest-first, so even a smaller copy would show the oldest learnings and cut the newest. Sessions reach it by search, which still works. | **Operator call** — four remedies in the item, each a session. The read-budget guard tolerates it only while it stays over the limit. |
| `CHANGELOG.md`'s top is out of order | Four July entries sit above the September ones, so the newest entry of that stretch is not at the top of it. Since Session 259 new entries no longer go there at all — they go above the whole legacy part, under the newest `## YYYY-MM` heading. Its size stopped being a defect in Session 257, when the operator ruled this file — and only this one — outside the read budget. | **Operator call** — reorder the four (a provable pure move), or accept the order. |
| CI runs the proofs, but this repo pushes in bursts | The new CI job runs both proof modes on every push. When it was filed, this clone was 7 commits and 4 sessions ahead of `origin/master` — so CI would have caught the Session 249 breakage about four sessions late, which is exactly how late it *was* caught. The per-session command now lives in `CLAUDE.md`. | **Operator call.** Accept CI as a backstop, add a `pre-push` hook, or push every session. |
**Also standing, not an item below:** `tests/eval/README.md` has three stale statements (`:49`, `:51-52`, `:86`), unfixed for a seventh session. $0, no risk. Two more of the same kind, found by Session 266's review: `.github/workflows/ci.yml:62` and `:70` state Session 253's measurements in the present tense (a proof count and a set count), and two docstrings in `tests/test_session_notes_census.py` (`:245`, `:741`) were written when nine table rows existed and now read ambiguously.

---

## Open Items

### CLI-adapter portability — spec the `OpenCodeLLMClient` adapter

**Decision accepted by the operator, 2026-08-01:** extend the LLM provider seam (`LLMProvider` in both agents'
`factory.py` modules — currently `"anthropic"` | `"bedrock"`) with a new `"opencode"` branch, shelling out to the
`opencode` CLI (`github.com/anomalyco/opencode`) rather than calling an SDK directly. OpenCode is itself a
vendor-agnostic multiplexer (75+ model providers via the Vercel AI SDK / Models.dev), so one adapter unlocks many
underlying vendors through OpenCode's own config — the actual goal being prepared for is an enterprise environment
that may standardize on a different AI CLI than Anthropic's. Full research (four candidates compared: OpenCode,
Codex CLI, Gemini CLI, GitHub Copilot CLI — headless-mode syntax, structured-output support, auth mechanics,
portability verdicts, citations) and the decision record live in
`docs/wiki/model_project_constructor/AI-Dependencies.md` §9 and `docs/wiki/model_project_constructor/Architecture-Decisions.md`
AD-11 — read both before starting, so the next session doesn't re-derive the comparison.

**The spec is DONE (Session 211, 2026-08-01): `docs/planning/opencode-adapter-spec.md`.** It specifies
`OpenCodeLLMClient` for both packages as a **transport-method override** — subclass each package's
`AnthropicLLMClient` and replace only `__init__` plus `_call_json` (intake) / `_call_claude` (data agent), so every
prompt, dataclass builder, and `_extract_json` is inherited and prompt drift across providers is structurally
impossible. It carries the full interface contract, the error-mapping table (spawn failure / non-zero exit /
timeout / no-assistant-text / malformed JSON → `IntakeLLMError`/`LLMParseError`), a grep-based file inventory with
line numbers at `a3f33d8`, the test plan (including the drift guard C4 forces for the *new* duplicated helper
pair), a risk register, and four build phases. **AI-Dependencies.md §9.2's prerequisite is discharged:** the
`--format json` event stream is JSONL of shape `{type, timestamp, sessionID, ...payload}` with types
`text`/`reasoning`/`tool_use`/`step_start`/`step_finish`/`error`, pinned from OpenCode's own emitter source at a
recorded commit — see spec §3.2.

**Phase 1 (the live verification spike) is DONE (Session 212, 2026-08-01)** — `opencode` **v1.18.11** installed
(`npm i -g opencode-ai`), all seven probes run, six verbatim fixtures committed to `tests/fixtures/opencode/`, and
findings recorded as spec **§13 Appendix A** with §3/§4 annotated inline. Cost: $0.1295 over 16 billed calls. All
four `[unverified]` markers resolved — notably the replace-vs-append question behind the spec's largest design
risk: **partial replace**, a custom agent's prompt drops ~4,720 tokens of built-in persona but a constant
**~4,830-token scaffold survives** every call. D2 (folding the system prompt into the user message) was validated
end-to-end: the real `next_question` payload produced schema-valid output that parses with the project's own
unmodified `_extract_json`.

**⚠ Phase 1 also produced seven corrections to the spec (Appendix A.4), one of them a safety defect.** Hazard
H4's claim that "the default is already safe" is **false**: without `--auto`, a live run listed the sandbox, **read
a file and disclosed its contents**, exit 0. The tool-denying agent definition (with `read: deny`) is therefore
**mandatory, not defence-in-depth**, and the "caller supplied their own agent ⇒ adapter writes nothing" escape
hatch in §4.4 must be removed or hard-gated. Also corrected: stderr is empty on the error path (so §4.7's
`{stderr_tail}` message yields `""` — build it from the stdout `error` event's `name`/`message`/`ref`);
`step_finish` exposes `reason`/`tokens`/`cost`, which restores the truncation guard §3.3 declared impossible;
blind concatenation of `text` events picks up narration on multi-step runs; a malformed agent file fails as
usage-help-on-stderr with empty stdout; the sandbox needs a **runtime npm install** (so npm reachability is a
deployment prerequisite, sharpening §11 Q3); and sessions persist prompt/response text in a **global SQLite DB**
that survives sandbox deletion.

**Phase 2 (both clients, both factory branches, the registry entry, the deterministic tier) is DONE (Session 213,
2026-08-01)** — `"opencode"` is a live provider in both packages, shipped with all seven Appendix A corrections
applied. See `CHANGELOG.md`'s 2026-08-01 entry. Gate: **1100 passed + 8 live-skipped @ 97.79%**, mypy and ruff
clean. **Two as-built deviations**, both recorded in the spec: §4.4/§5.1's `agent=` escape hatch was **removed**
(not merely hard-gated) in favour of `agent_name`, which renames the generated tool-denying definition rather than
substituting a caller-owned one — so no constructor path reaches an unlocked agent; and §5.3's twin helpers take
the parsed event list rather than raw `stdout`.

**⚠ The adapter is wired but entirely unmeasured.** `anthropic` remains the default everywhere, and it must stay
that way: spec risk #1 (parses fine, quality silently degrades under the D2 prompt-role change) is untouched, and
no data-agent method has been exercised against OpenCode at all.

**Phase 3 (eval wiring + documentation) is DONE (Session 214, 2026-08-01)** — `"opencode"` is a candidate in the
Phase E cutover gate with all eight thresholds PENDING, and thirteen wiki pages plus `README.md`, `OPERATIONS.md`,
`.env.example` and the published `docs/tutorial.md` now describe a shipped third provider. Gate: **1110 passed + 12 live-skipped @ 97.79%**, mypy and ruff clean. **One deliberate
deviation from spec §7.4, chosen by the operator before implementation:** the credential probe requires the
`opencode` binary **and** `OPENCODE_EVAL_MODEL`, not the binary alone. Binary-only was unsafe — the binary is
installed globally on this machine and `addopts` carries no `-m 'not live'`, so it would have turned every
`uv run pytest -q` here into a billable live run while CI still looked hermetic. The same variable is the pinned
model id (new `provider_eval_model`, threaded through `test_eval_live.py` and `shadow_run.py`), which makes D6's
"every evaluated run passes an explicit model" true and discharges Phase 4's "operator names the model to pin"
pre-flight. Both the spec's §7.4 and its Phase 3 entry carry the correction inline.

**Phase 3b (unplanned — the eval harness could not drive the provider at all) is DONE (Session 215, 2026-08-01)**
— `a0c3930`. Phase 4 was blocked and nobody knew, because the live tier skips so no test could see it. The
stakeholder simulator reached through to `intake_client._client.messages.create`, which for this provider is the
`_UNUSED_SDK_CLIENT` placeholder that raises by design; the resulting bare `AttributeError` is not in
`interview_sweep._TRANSIENT_ERRORS`, so a shadow run would have **billed ~31 live calls and then aborted with no
report**, leaving `interview_convergence` and `interview_premature` unmeasurable. A second defect on the same path
would have run the simulated-stakeholder half of every interview on **no model** while the interviewer half ran
pinned. Fixed with a transport-shape-resolved `TextCompleter` seam; no production code touched; +11 hermetic
tests. Gate: **1121 passed + 12 live-skipped @ 97.79%**, mypy and ruff clean. See `CHANGELOG.md`'s 2026-08-01
entry and spec §9 Phase 3b.

**Phase 4 (the live shadow run + cutover decision) is DONE (Session 216, 2026-08-02) — verdict NO-GO,
`anthropic` stays primary.** 451 live calls pinned to `anthropic/claude-sonnet-4-6` (the baseline's own model id,
so the A/B isolates the transport change per §11 Q2), $13.99, 99.5 min, plus a 31-call same-session `anthropic`
governance+SQL refresh. **7 of 8 thresholds PASS; `sql_exec` FAILs at 42.9%.**

**The result that matters: spec risk #1 did not materialize.** The D2 prompt-role fold degraded nothing
measurable — `opencode` ties the baseline on governance (`cycle_time` 100%, laxer 0), `qc_structural` (100%),
`sql_parse` (100%), and **both interview thresholds** (`convergence` 100% at 20/20, `premature` 0). Cost profile
now quantified (risk #12): mean $0.0310/call, p99 latency 105.8 s, 4.4% of calls >60 s taking 14% of spend, only
8.4% of calls getting any prompt-cache read. See `tests/eval/PHASE_E_AGREEMENT_REPORT.md` §"Update — Session 216".

### `sql_exec` — CLOSED (Session 218): cause fixed S217, re-measured S218, both providers PASS

**Resolved.** Session 218 re-measured under the dialect fix at an N≥5-sampled denominator:
**`anthropic` 18/18 and `opencode` 34/34 executable, zero execution errors** — no `DATEDIFF`,
`PERCENTILE_CONT ... WITHIN GROUP`, `MEDIAN` or `ILIKE`. The entire S216 failure class is gone.
`SQL_EXECUTABLE_MIN` was never lowered; the SQL block simply got the same N≥5 sampling every other
capability already had (`4e2c8ec`, extracted to `tests/eval/sql_sweep.py`). 60 live calls, $0.63
measured + ~$1.00 estimated, 24 min. **The `opencode` cutover verdict flipped NO-GO → GO** — but
five of its eight cells are carried forward from S216, and **no production default was changed**.
See `tests/eval/PHASE_E_AGREEMENT_REPORT.md` §"Update — Session 218", including its six explicit
non-establishments. **What remains open is the cutover *decision*, not the measurement:** if the
swap is going to be taken, one session should measure all eight thresholds fresh.

The original entry follows as the historical record.

#### (historical) dialect cause FIXED (Session 217); the re-measure is what remains

**The root cause is closed.** Session 216 diagnosed `sql_exec` as a SQL *dialect* mismatch — both providers
emit competent *warehouse* SQL (`DATEDIFF(...)`, `PERCENTILE_CONT(...) WITHIN GROUP`, `MEDIAN(...)`), the eval
runs it on SQLite, and nothing in the data-agent prompt named the dialect. **Session 217 fixed it at the source
(`9c9fe35`), choosing the prompt fix over the warehouse-target-DB alternative:** the dialect is derived from the
database the caller configured (`ReadOnlyDB.dialect` / `sql_dialect_from_url`, parse-only, no connection) and
injected into the three SQL-emitting prompts. This also fixes **production**, where the same silence shipped —
the CLI and `scripts/run_pipeline.py` now derive it from `--db-url`. A 6-call live A/B on `anthropic` measured
**2/5 executable dialect-blind vs 4/4 dialect-aware**, and surfaced a fourth offender S216 had not seen:
**`ILIKE`**. Parse-validity was 100% in both arms — which is why it failed silently.

**What remains open — the re-measure, which this session deliberately did NOT do.** The probe is a diagnostic,
not a re-score: tiny n, model-chosen denominator, `anthropic` only, single run. **`SQL_EXECUTABLE_MIN` stays
0.95, the recorded 60.0% / 42.9% rates stand, and the `opencode` NO-GO stands.** Re-scoring means a full
`shadow_run.measure_provider` sweep (S216's cost `anthropic` + `opencode`: $13.99 / 99.5 min) and is a separate,
operator-authorized session. **Do not "fix" this by lowering `SQL_EXECUTABLE_MIN`** — the §5 rule is encoded in
`evaluate_cutover` and must not be relaxed to produce a green report.

**Still note when re-measuring:** the metric's denominator is model-chosen (how many queries the model writes),
so the rate moves run to run and the provider ordering *reverses* — sweep `anthropic` 3/5 = 60.0% vs `opencode`
3/7 = 42.9%; diagnostic re-run `anthropic` 2/4 = 50.0% vs `opencode` 4/7 = 57.1%. Report numerator and
denominator, never a bare rate. Reopening the `opencode` cutover decision is downstream of the re-measure.

**Still open on the adapter:** spec §11 Q1 (`DEFAULT_MODEL` shipped as `None`) — reversible in one line. The
non-Anthropic measurement that discharges `AI-Dependencies.md` §6.7's model-family diversification is a **second**
run and is now unblocked, since the transport itself is cleared on 7/8.

### The gate measures only ONE of the three dialect-injected prompts

**Found Session 218**, recorded rather than fixed (scope). Session 217 injected the dialect note into three
methods — `generate_primary_queries`, `generate_quality_checks`, `generate_baseline_query`. The Phase E gate
exercises the effect of exactly one:

| method | called by the gate? | scored how |
| --- | --- | --- |
| `generate_primary_queries` | yes | `sql_parse` + `sql_exec` — SQL is parsed **and executed**, so a dialect miss is visible |
| `generate_quality_checks` | yes | `qc_structural` only, which is `len(qc_lists) == n_primary_queries` — the QC SQL is **never parsed or executed** |
| `generate_baseline_query` | **never called** | no gate key exists |

`grep -rn "generate_baseline_query" tests/eval/` returns zero hits in any `.py`. The `kind: baseline` corpus case
(`subrogation_recovery_rate`, `corpus/sql_cases.yaml`) is filtered out of every live path by
`if case.kind != "primary": continue`; its only consumers are two deterministic oracle self-tests that score the
**human-authored** `reference_sql`, no LLM involved. So baseline-query dialect correctness is unmeasured, and QC
dialect correctness is unmeasured. Closing either means a new scorer (parse/execute the QC SQL) and, for the
baseline case, a gate key that does not exist yet — a design change, not a wiring fix.

### Re-measure `opencode` under the fixed (retry-symmetric) harness

**Unblocked by Session 221**, which closed the retry asymmetry that produced the S219 NO-GO. That
session deliberately **did not re-score** the verdict — a harness change made after seeing a disliked
number is how a gate stops being a gate (learning #86) — so the recorded verdict is still **NO-GO** and
the two failing cells in `tests/eval/PHASE_E_AGREEMENT_REPORT.md` are pre-fix numbers.

A GO produced by the fixed harness would be the first one resting on eight same-session cells **and** a
symmetric retry policy. Cost at S219's measured rates: **~$16.4, ~130 min** for the full eight-cell
`opencode` sweep (the SQL block alone is ~$1.78 / ~18 min per 5-sample pass — cost it at $0.0593/call,
not the $0.0318 global mean). **Its own session**, and read these before quoting anything it produces:

1. **Post-fix numbers are not comparable with S219's or S220's.** Best-of-3 turns a per-sample failure
   rate `p` into `p³` against unchanged bars. Quote `transient_retries` alongside every rate — it is
   what bounds the first-attempt rate. **Session 225 widened this**: the governance block now retries
   too, so the governance cells are non-comparable with **S216-S220**, a different span from the
   SQL/QC cells' S219-S220. Do not quote one rule for both. The same session added
   `governance_excluded_transient`, `governance_seam_failures` and `governance_transient_retries` to
   the driver's output — record all three, and remember that an exclusion can only move the
   zero-tolerance `governance_laxer_miss` **count** toward PASS.
2. **Do not lower `SQL_PARSE_VALID_MIN` or `QUALITY_CHECKS_STRUCTURAL_MIN`** (learning #82). Four
   sessions running have refused to calibrate a bar to a number.
3. **Source `.env`** — `set -a && . ./.env && set +a`. Without it every sample fails at $0 in ~36 s and
   the harness scores that as 45 model-quality failures (see the item below).

### Two live surfaces stay silent about a dropped or retried sample

**Filed Session 225**, found by the adversarial review of that session's own change and deliberately
not fixed there — the deliverable was the governance transient policy, and both of these are the
*interview* block, which the closed item pinned byte-stable. Two one-line changes, no money, no
threshold.

1. **`test_eval_live.py`'s interview gate passes no `on_event`.** `sweep_interview_convergence(
   load_interview_cases(), run_one)` at `tests/eval/test_eval_live.py:221` leaves `notify` at its
   no-op default, so every retry and exclusion note the sweep produces is discarded inside the gate
   that most needs them. This is the *identical* defect Session 221 fixed for the SQL test and
   Session 225 fixed for the governance test — the same file now has two call sites with a sink and
   one without. `shadow_run` has always passed `_warn` here (`shadow_run.py:157-159`), so only the
   assertion gate is blind.
2. **`shadow_run` reports no interview exclusion counter.** `measure_provider`'s returned mapping
   carries `sql_excluded_transient` and `governance_excluded_transient` but nothing for the
   interview sweep, even though `InterviewSweepResult.excluded_transient` exists and is populated.
   The interview denominator can therefore shrink invisibly in the agreement report — the exact
   condition `tests/eval/README.md` tells readers to check for. (The live *assertion* already prints
   it in its failure message; the *report* does not.)

**Both are diagnosability, not correctness:** no rate or count changes, and no verdict turns on
either. They are filed because a sink-less call site is how the Session 219 event became permanently
unattributable.

### The transient tiers key on exception class, so a glitch means different things per provider

**Filed Session 225** (reproduced by two independent refuters during that session's review, then
ruled out of scope by the panel — the mechanism is real, the severity ruling was "not this session's
defect"). **Pre-existing and wider than any one sweep: all three apply it.**

Every sweep splits transients into a *scored* tier (a seam error — the model produced something
unusable) and an *excluded* tier (a transport error — no model output exists to judge). The split is
made on the **exception class**, and only the SDK-backed providers (`anthropic`, `bedrock`) raise the
transport classes: `AnthropicLLMClient` lets `APITimeoutError` / `APIConnectionError` out of
`_call_json` unwrapped, which is what the excluded tier catches.

`OpenCodeLLMClient` is a subprocess adapter. Per the adapter spec's error-mapping table it converts
**spawn failure, non-zero exit, timeout, no-assistant-text and malformed JSON** all into
`IntakeLLMError` / `LLMParseError`. So for `opencode` a dropped connection or a killed process is
**scored a model-quality miss**, where the same real-world event on `anthropic` is *excluded*. Two
providers are judged by different rules on the same corpus against the same thresholds — and
`opencode` is the provider whose recorded verdict is NO-GO.

**This is not a reason to distrust the S216-S220 numbers on its own** — no measured event has been
attributed to it, and the exhaustion path requires three consecutive failures. It is a reason not to
compare a scored-tier count across providers without saying so.

**Sketch:** the fix belongs in the adapter, not the harness — give the subprocess client a distinct
exception for transport-shaped failures (spawn/exit/timeout) so the existing tier split can see them,
rather than teaching each sweep about provider internals. That changes shipped package code under
`mypy --strict`, so it is its own session. Until then, any surface quoting a scored-exhaustion count
should name the provider.

### A bare `KeyError` from a well-formed-but-wrong-keyed model response aborts the whole sweep

**Filed Session 221** (found while pricing the exception taxonomy), **not fixed** — it is shipped
package code under `mypy --strict`, out of scope for a harness session.

`packages/data-agent/src/model_project_constructor_data_agent/anthropic_client.py:203-215` builds
`PrimaryQuerySpec(name=str(item["name"]), sql=str(item["sql"]), purpose=…, expected_row_count_order=…)`
with **no guard**. A model that returns a well-formed JSON array of objects with the wrong keys raises a
bare `KeyError` — not an `LLMParseError` — so it is caught by no tier of the sweep's transient taxonomy
and **kills the run mid-sweep** instead of scoring one miss. The same gap sits at `:401-407`
(`rank_candidate_tables`) — since Session 261 `probe_information_schema` absorbs that one into a
labelled, unranked inventory, but the client itself still raises the bare `KeyError`.

**The intake twin already does this correctly:** `src/model_project_constructor/agents/intake/anthropic_client.py:439-440`
wraps the identical pattern in `_build_draft`. So the fix is to mirror an existing, shipped convention —
wrap in `try/except KeyError` and re-raise as `LLMParseError` — not to invent one. Add a regression test
per call site; the wheel's error-mapping tests live in `tests/data_agent_package/test_anthropic_client.py`.

### A bad `--db-url` still exits 0 and reports `COMPLETE` — option (c), and it needs a ruling

**Filed Session 223 as three options. Session 260 shipped (a) and (b); this is the residue.**
What closed: `execute_qc` binds the `DBConnectionError` instead of discarding it, `agent.py` appends
the cause (password-masked) to `data_quality_concerns`, and `sql_dialect_from_url` logs a WARNING
naming a *parse* failure. A typo'd port, an unexported shell variable and a genuine warehouse outage
no longer produce byte-identical reports — pinned by
`tests/agents/data/test_data_agent.py::test_two_different_db_failures_produce_different_concerns`.

**What is left is option (c): give the report a status that makes the pipeline halt.**
`agent.py`'s `_assemble_complete_report` returns `status="COMPLETE"` unconditionally, and
`src/model_project_constructor/orchestrator/pipeline.py`'s halt fires only
`if executed and data_report.status != "COMPLETE"`. So the data-agent CLI still prints
`wrote report.json (COMPLETE)` and exits 0, and the full pipeline still generates every project file
and exits 0, with **every quality check unexecuted**. The cause is now *in* the report; nothing
*gates* on it.

**Why it was not done with (a) and (b).** It is an operator-visible behaviour change, not a bug fix:
runs that succeed today would start failing, and that is the point of it. It also changes
`DataReport` status semantics, which the orchestrator's `FAILED_AT_DATA` halt keys on — a design
change across two packages. The filed recommendation was explicitly "(a) + (b), leaving (c) as a
separate decision."

**Operator call.** Three shapes, ascending blast radius: leave it (the cause is reported and a human
reads the concerns); add a non-halting signal the pipeline surfaces more loudly; or give `DataReport`
a status that halts, which means deciding whether an unreachable DB is a *failed* run or a
*degraded* one. Note the same question governs `nodes.py`'s baseline branch, whose
`"database not reachable at baseline-collection time"` caveat is the parallel case.

**A precedent now exists, and it is not this ruling.** In Session 261 the operator ruled twice on the
sibling command, `model-data-agent discover`: a **degraded** `DataSourceInventory` — reflection failed
so it is empty, or ranking failed so it is unranked — is still **written**, and the command **exits
1**. That is the third shape above, in the form "keep the artifact, fail the status". It was ruled
for `discover` only; it does not decide `run` or the orchestrator's halt, whose blast radius is the
reason this item is still open. Session 265 added a variant, also for `discover` only: a *partial*
inventory (tables the database could not reflect were skipped) exits 1 too, but an opt-in flag,
`--allow-skipped`, accepts it with exit 0. That is "fail by default, let the operator accept a known
degradation", a shape option (c) could borrow.

### Three more channels can still write a file that will not reload

**Found by Session 267's adversarial review while it closed the `--request-context` item; each was
reproduced through the real command, and none is a defect of that change.** The operator's rulings so
far (Sessions 261 to 267) cover `discover`'s own channels: ranking, reflected text and
`--request-context`. Three siblings have the same shape: a `str` holding a surrogate code point
validates, is written with exit 0, and then fails to load.

1. **`model-data-agent run --request`** (`cli.py:331`). `_load_request` uses `json.loads` and then
   `DataRequest.model_validate`, so a JSON escape for half an emoji anywhere in the request — the
   target description, a feature name, an embedded inventory's `request_context` — passes. `run`
   exits 0 and writes a `DataReport` that `DataReport.model_validate_json` and the website agent
   refuse (`ValidationError: Invalid JSON`). Reproduced with `--fake-llm`.
2. **A model reply** carrying the same escape is written into the `DataReport` unchecked
   (`cli.py:164`, `json.dumps(report.model_dump(mode="json"), indent=2)`): exit 0 and an unloadable
   file. Reproduced by making the fake client's `summarize` return one.
3. **`intake_qa_pairs_to_inventory`** (`orchestrator/adapters.py:197-199`) builds `request_context`
   from `IntakeReport.stakeholder_id` and `session_id`, which accept the same text, and
   `model_dump_json` then raises. `merge_inventories` embeds only counts, so it is not affected.

**Sketch, once ruled.** For 1, `DataRequest.model_validate_json(path.read_text())` rejects it before
any work runs (it changes the exception type for malformed JSON); a usage error, exit 2, is
`discover`'s shape. For 2, serialise with `report.model_dump_json(indent=2)` inside a `try` and exit 1
without writing, or check each model-returned string at the `DataAgent` boundary. For 3, a field
validator on the two ids, or `validate_request_context` on the f-string. **Needs an operator ruling
per channel** (reject or degrade; the exit status for `run`), which is why none was done inside
Session 267's one deliverable. The library check that exists now is
`discovery.validate_request_context`, and the CLI wires it as an option callback (`cli.py`,
`_check_request_context`).

### `run` crashes at the very end when a quality check returns a binary value that is not valid UTF-8

**Found by Session 267's review; reproduced; not fixed.** `ReadOnlyDB.execute` rows go into
`QualityCheck.raw_result["sample_rows"]` unsanitised (`nodes.py:159`). A BLOB that is not valid UTF-8
(`SELECT x'ff'` on SQLite) makes `report.model_dump(mode="json")` raise `UnicodeDecodeError` at
`cli.py:164`, after every LLM call has been made and billed: exit 1, no report written. A
`memoryview`, which is what psycopg2 returns for a PostgreSQL `bytea`, fails the same dump with
`PydanticSerializationError` even when its bytes are valid UTF-8 (that second case was reproduced
against the model, not against a live PostgreSQL). `bytes` that are valid UTF-8, and `inf`, dump
fine. **Sketch:** make the sample rows JSON-safe in `make_execute_qc` before the `QualityCheck` is
built (hex for `bytes` and `memoryview`), or build it, try the dump, and on failure record the check
as `ERROR` with the reason, the way the existing `db.execute` failure path does. **Small, but a
choice between the two, so an operator call.**

### Seven more routes can still put database, driver or exception text on a terminal or in a report

**Routes 1 to 3 of Session 269's list closed in Session 270** (the connect error `discover` let escape as a
traceback; the "database unreachable" concern; the quality-check and baseline SQL errors): all go through
`db.safe_message` now, and the review of that change filed the rest. **Each was reproduced by a lens and
re-checked by two skeptics; none is fixed.** What each was reproduced on: a real SQLite file where the
route allows it, otherwise a **simulated** driver (a fake SQLAlchemy dialect whose DBAPI error carries what
PostgreSQL echoes of a role name), so no route below was reproduced against a live PostgreSQL, MySQL,
Oracle or SQL Server.

1. **An unparseable `--db-url`** (`db.py:311`, in `sql_dialect_from_url`'s WARNING). `redact_db_url(url)`
   goes through `%s` and its regex fallback replaces nothing: 1 ESC and 1 BEL on stderr from the operator's
   own argument, exit 0. **Nit** for the control codes. **Its secrets half is its own item below.**
2. **SQLAlchemy's own emissions.** (a) The reflection warnings ("Did not recognize type '%s' of column
   '%s'" in the PostgreSQL, MySQL, Oracle and SQL Server dialects; SQLite's foreign-key-signature
   warning) go through Python's `warnings`, not the logger, so nothing in this package touches them.
   Reproduced end to end on SQLite (a case-mismatched foreign key on a table with a control-character
   name: 2 ESC and 1 BEL, exit 0); the unrecognised-type warning only at the `PGDialect` level. (b)
   **Found by Session 270's review:** when a driver raises on rollback or close at pool return, SQLAlchemy
   logs the whole exception, traceback included, on its pool logger ("Exception during reset or
   similar"). No handler is configured anywhere in the repository, so Python's last-resort handler prints
   it to stderr raw: the probe's own WARNING and `discover`'s `error:` line are clean and the same text
   appears a second time unredacted beside them (simulated, with a `PWD=hunter2` in the message).
   **Fix for both:** a `warnings` filter or `catch_warnings` around the probe, and a logging filter on the
   `sqlalchemy` loggers that runs the record through `safe_message` and drops `exc_info`.
3. **The persisted inventory** carries table, namespace and column names and `relevance_reason`
   verbatim. The file is safe to `cat` (`json.dumps` escapes them), but a consumer that loads it and
   prints them gets live ESC and BEL (6 ESC and 3 BEL measured). Nothing in the repository prints
   them, and no test pins `ensure_ascii`, so a later `ensure_ascii=False` would write raw DEL and C1
   characters. **A design call:** scrub names (changing identifiers a consumer joins on) or record them
   faithfully and say so.
4. **The operator's own `--output` path** is echoed raw by `cli.py:165,268,311,323`. Not database text.
   **Nit**, arguably not a defect.
5. **Exception text that is not the database's, written to the same sinks raw.** *Found by Session 270's
   review (measured; not database text, so outside the class `safe_message` was written for, and the
   same defect on the same sinks).* `nodes.py:211`, `caveats=[f"LLM baseline-query generation failed:
   {e}"]`, sits 20 lines above the fixed SQL half: a raw LLM or SDK exception, which `templates.py`
   writes into `analysis/06_implementation_plan.qmd` (a probe with an ESC, a BEL and `password="hunter2"`
   in the exception came out with all three). `agent.py:54`, `f"graph crashed: {e}"`, puts any exception
   that escapes the graph into `data_quality_concerns` **and** the summary. The realistic carriers are an
   SDK `APIError` and `opencode`'s error event. **Fix:** `safe_message(e)` at both (one token each, plus a
   test mirroring the route-3 baseline test). The review's guard idea: a small AST test that fails on any
   f-string interpolating a bare exception name in `nodes.py`, `agent.py` and `cli.py` unless allow-listed,
   which would have flagged both and would stop new routes arriving raw.
6. **The website templates are an unguarded sink.** *Found by Session 270's review.* Routes were fixed at
   the producer, and `templates.py` (around `:421`, `:530-533`, `:758`, `:767`) writes the summary, the
   confirmed and unconfirmed expectations, the caveats and the concerns raw into committed markdown, so
   the guarantee holds only for a `DataReport` made by the fixed producer: a checkpoint written before
   Session 270 and resumed (`determine_resume_point` returns the website stage for a `COMPLETE` report,
   inferred, not run), a report from another producer (`website run --data <any DataReport JSON>`), and
   the LLM-written fields, which are always raw. A raw ESC and BEL in a report's concerns, caveats and
   summary reached `analysis/02_data.qmd`, `analysis/06_implementation_plan.qmd` and
   `reports/data_report.md` (measured). **Fix:** either say the guarantee is the producer's, or a one-line
   sanitiser in the templates for report-derived strings, which makes the producer fixes defence in depth.
7. **Repo-host failure text** (`website/nodes.py:110` and `:219-225`; `gitlab_adapter.py:183`,
   `github_adapter.py:266`). A `RepoClientError` is built from the raw HTTP response body, becomes
   `failure_reason`, and `scripts/run_pipeline.py:665` prints it unmodified (measured through the agent,
   the `print` is a code citation). Server-controlled text, not database text. **Nit.**

Left out on purpose: the Unicode format characters (`Cc`'s neighbour `Cf`: bidirectional marks,
zero-width characters, the tag block; 170 on Python 3.13) are not scrubbed. They are not the escape
and control codes this was about, and scrubbing them would split Persian and emoji sequences. Whether a
given terminal reorders text on them was not measured.

**Cost:** routes 5 and 2(b) are small and need no ruling; 6 is one decision then one function; 3 is an
operator call; 1, 4 and 7 are nits.

### A password can still reach the connect error, the report and a warning

**Found by Session 270's critic and a lens; reproduced; pre-existing, and not fixed.** `ReadOnlyDB.connect`
redacts the URL with `redact_db_url`, and two shapes get past it. **A secrets matter.** (1) **A password
with an unencoded `@`** (`bob:P@ssw0rdXYZ@host`): SQLAlchemy ends the password at the first `@`, parses
`P` as the password and `ssw0rdXYZ@host` as the host, the driver echoes that host in its error, and neither
redaction path sees it: `redact_db_url` takes the `make_url` branch, so its regex that matches to the
LAST `@` (the comment at `db.py:69-74` says this exact case must not leak) never runs, and the driver's
text has no `://` and no `key=`. Measured with psycopg 3 against a refused port: `discover --db-url
'postgresql+psycopg://bob:P@ssw0rdXYZ@127.0.0.1:1/claims'` printed `failed to resolve host
'ssw0rdXYZ@127.0.0.1'`, and `run --fake-llm` left `ssw0rdXYZ` in the report's `data_quality_concerns`. Before
Session 270 it reached the traceback, the concern and the warning, and it still reaches the `error:` line and
the concern **through the driver's own text, which no version of the sinks masks** (the URL half measured
at the Session 270 close with the `fakeesc` dialect: `fakeesc://bob:P@ssw0rdXYZ@127.0.0.1:1/claims` keeps
`ssw0rdXYZ` in `str(DBConnectionError)` and in `discover`'s line; the driver's echo of the host measured by
the review with psycopg 3). `test_redact_db_url_masks_every_secret_shape`
covers `p@ss@host:$DB_PORT` (the unparseable path) and not the parseable `p@ss@host:5432`
(`redact_db_url` returns `user:***@ss@host:5432/claims`). (2) **A mistyped scheme separator**
(`postgresql//bob:hunter2@h/db`, `postgresql:/bob:...`, `bob:hunter2@h/db`): `make_url` fails, the fallback
regex needs `://`, and the whole URL, password included, is echoed in the `error:` line, the concern and
route 1's warning above. SQLAlchemy 2.0.49's own `ArgumentError` does not echo the URL. **Fix:** when
`make_url` fails, do not echo the URL at all (a fixed `<unparseable URL>`: the operator knows what they
typed), and for the first shape treat an `@` in the parsed host or username as an unencoded password, or
scrub the parsed password's known fragments from the cause by exact match, which is stronger than
patterns. Add a URL-borne-password case to the route tests: none of them has one. **Two limits of the
masker belong with this** (`db.safe_message`'s docstring states both): a control between the separator
and an opening quote or brace leaves the rest of a multi-word secret, and a quoted value glued to
following text is read as the whole value. And one consequence of Session 270's own choice, stated so it is
not rediscovered: the sinks no longer run the masker over the composed message (it ate the `':` after a
URL ending in `password=***` and the exception type after a path ending in a key word), which had
accidentally masked this first shape's tail in the URL half; the cause half leaked it either way.

### `redact_secrets` is quadratic on some text and `safe_message` has no input bound

**Found by Session 270's review; reproduced; pre-existing, and not fixed.** `_USERINFO_TEXT`
(`db.py:76`, `(://[^:/\s]*:)[^\s]*(@)`) is tried at every `://x:` and scans to the end of the
whitespace-free run: `safe_message('://a:' * n)` takes 0.15 s at 10,000 characters, 2.3 s at 40,000, 37 s at
160,000 (x4 per doubling, so about 25 minutes extrapolated for 1 MB), and it runs twice per call. A
comma-joined list of 4,000 URLs with no whitespace (71 KB) takes about 2 s; with a space after each it is
linear. No driver normally emits that, which is why it is a nit. Separately `safe_message` has no bound on
its input: about 85 to 230 bytes of memory per character (a 10 MB message peaked at 0.8 to 2.3 GB, 1 to 4
s), linear in time. `redact_db_url`'s `_USERINFO_URL` fallback (`.*(@)`) has the same shape on the
operator's own argument. **Fix:** make the userinfo pass linear (within a whitespace-free token only the
first `://x:` matters and it pairs with the last `@` in that token: a per-token `rfind('@')`, or skip
tokens with no `@`); and a cap on the text `safe_message` processes (8 to 64 KB with a visible
`...[truncated]`) before it redacts, which also bounds the quadratic case. A cap changes what a long
`[SQL: ...]` shows, which is why it is a choice.

### Only `typer`'s dependency floor has ever been measured — `langgraph>=0.2` cannot start the intake CLI

**Found by Session 268's review while closing the `typer` floor; reproduced by a skeptic;
pre-existing.** `uv.lock` pins every package far above the minimum the project declares, so no job
ever installs a declared minimum. Session 268 measured `typer`'s (now `>=0.16.0`, held by
`tests/test_dependency_floors.py`). Asked of the rest, on Python 3.11,
`uv pip install --resolution lowest-direct '<repo>[agents]' '<repo>/packages/data-agent'`:
**`langgraph>=0.2` resolves 0.2.0 and `model-intake-agent --help` dies with `ModuleNotFoundError: No
module named 'langgraph.types'`** (`agents/intake/agent.py:17`, then `nodes.py:14`). Bisected over
langgraph 0.2.0 to 0.2.76 with the lock's other pins held: the import first works at 0.2.47, but the
website agent's graph still fails (`InvalidUpdateError: Expected node scaffold_analysis to update at
least one of ...`) until **0.2.57**, where the intake, website and data-agent test directories pass.
So the working floor is `>=0.2.57`, not the 0.2.47 a first bisect suggests. The other direct floors
(pydantic 2.6.0, anthropic 0.94.0, sqlalchemy 2.0.0, httpx 0.27.0, sqlparse 0.5.0, pyyaml 6.0)
installed and `model-data-agent` ran, but only `--help` was exercised, not the tests. Two limits on
any such check: `pyyaml` 6.0 has no wheel for Python 3.12 and its source build fails
(`cython_sources`), so lowest-direct installs only on 3.11 as the floors stand; and resolving every
transitive package to its minimum (`--resolution lowest`) fails building a `greenlet` source
distribution, independent of any floor here.
**Fix, two sizes.** (1) **Small:** run the data agent's own tests at langgraph 0.2.0, then raise
`langgraph` in `pyproject.toml:19` (and `packages/data-agent/pyproject.toml:13` if its tests need it)
to `>=0.2.57`, with a drift guard shaped like the `typer` one. (2) **Operator call:** a CI job that
installs `--resolution lowest-direct` on Python 3.11 and runs the CLI test files, which is the only
thing that would have caught either floor; it adds a job and may need `pyyaml` raised to install on
anything newer. **The method that worked for `typer`** (Session 268's harness was session-local and is
not committed; rebuild it from this): `uv export --frozen --no-hashes --all-extras --all-groups
--no-emit-workspace --no-emit-project`, drop the lines for the packages under test, then for each
candidate version `uv venv` a fresh environment, `uv pip install` the rest plus the candidate, run with
`PYTHONPATH=src:packages/data-agent/src`, and for each CLI build the app, render `--help` for it and
every command, and run the three CLI test files with `--no-cov -p no:cacheprovider`. Launch the jobs
with `nohup setsid` and print each environment's resolved versions before reading a result
(learnings #296 and #297).

### The test suite needs Click 8.2 or later, and nothing declares it

**Found by Session 268's matrix and review; reproduced by a skeptic; pre-existing.** (1) Under Click
8.1.8, 26 of the 77 CLI tests fail (**measured at the close of Session 270 with Typer 0.17.0**; it was
18 of 69 at Session 268, and every test that reads `result.stderr` adds one: Session 269 added two and
Session 270 six) for every Typer from 0.12.4 to 0.17.0, all
`ValueError: stderr not separately captured`: they read `result.stderr`, and Click 8.1's `CliRunner`
mixes stderr into stdout unless told otherwise. The CLIs themselves build and render `--help` there.
(2) `tests/agents/intake/test_cli.py:10` does `import click` (used at `:21`, `click.unstyle`) while no
`pyproject.toml` declares Click: it arrives through Typer up to 0.25, `uvicorn` (the `ui` extra) and
`mkdocs` (the `docs` extra). **Typer 0.26 and later vendor Click and require none**, so when the
lock's Typer (0.24.1) moves past 0.25, an environment synced with `--extra agents --extra dev` only,
which is the CI decoupling job's shape and a developer's, has no Click and that file fails at
collection. **Fix:** declare `click>=8.2` in the `dev` extra (it is a test dependency), or drop the
direct import. **Small**; do both halves in one commit and re-run the three CLI test files under
Click 8.1.8 to see what the declaration changes.

### No circuit breaker on a systematically-failing live sweep

**Filed Session 221. Arithmetic revised Session 225 — the original figure now understates it.**
The S221 retry tripled the SQL/QC block: a sweep's 30 calls become up to 90 when every sample
exhausts. Against `DEFAULT_TIMEOUT_S = 600.0` (`opencode_client.py`), a timeout-shaped systematic
failure goes from ~2.5 h to ~7.5 h before the run reports anything. **Session 225 gave the governance
block the same retry**, so its 25 calls (5 cases x N_SAMPLES) become up to 75 on the same failure —
the worst case is now the sum over three blocks, not one. Note the ceiling is bounded by the timeout,
not by the retry count alone; the point stands either way and the number in this paragraph should be
re-derived, not quoted, when the breaker is built. The cheap, already-diagnosed signature to break on is the one from the item below —
a run whose calls are failing at $0 is an environment fault, not a measurement. **Sketch:** abort the
sweep with a named error after K consecutive exhausted samples (K ≈ 5), so the operator gets the
diagnosis in one minute instead of seven hours of billed nothing.

### An unset `ANTHROPIC_API_KEY` scores as 45 model-quality failures (`opencode` diagnosability)

**Found Session 220**, cost $0 to find and voided one probe run; **filed, not fixed** — that session was
measurement-only. Not a blocker: every committed live path already sources `.env`.

Running the SQL sweep against `opencode` **without `ANTHROPIC_API_KEY` in the environment** returns
**0/45 on `sql_parse`, `sql_exec` and `qc_structural` in 36 seconds at $0**, with every sample logging
`LLMParseError on primary queries -> parse+exec+qc fail`. Three facts combine:

1. `opencode auth list` reports **0 stored credentials** — the CLI has no auth of its own here.
2. `packages/data-agent/.../opencode_client.py:174` shells out via `subprocess.run(argv, **kwargs)` with
   **no `env=`**, so the child inherits the parent environment; `ANTHROPIC_API_KEY` is the only way an
   `anthropic/…` model authenticates.
3. Unauthenticated, the CLI exits 1 with
   `UnknownError: Unexpected server error. Check server logs for details. (ref=…)` — **a message that
   names neither auth nor the missing variable**, and which reads like a provider-side outage.

**Why it matters:** a misconfigured environment and a provider that genuinely cannot write SQL produce
**the same 0% on the same three gate keys**, and the fast-and-free signature (36 s, $0, 45/45) is only
obvious if someone thinks to check call count and spend. This is the same diagnosability class as the
retry asymmetry closed in Session 221 (see that `CHANGELOG.md` entry) — the harness cannot tell a seam
failure from a quality failure.

**Half-fixed, Session 221.** The cheap interim landed: both `sql_sweep.py` `notify(...)` calls now carry
`str(exc)`, so the `ref=…` reaches the log and the cause is searchable. **The item stays open** — the
message still names neither auth nor the variable, so a reader must already know what they are looking
at. Session 221 also **worsened the cost profile of this exact scenario**: the doomed run's call count
rises 45 → 135 as every sample burns its full retry budget (still ~$0 and fast, since the CLI fails in
under a second — but see the circuit-breaker item above, which this scenario is the motivating case for).

**Sketch:** have `OpenCodeLLMClient.__init__` (or the eval credential probe in `tests/eval/`) fail fast
with a named error when the selected model's provider prefix has neither a stored credential nor the
corresponding key in the environment.

### The NO-OP guard cannot see a PARTIALLY inert mutant — 7 of 46 are exposed

**Filed Session 253**, by the session that built the guard, because the header of
`docs/architecture-history/SESSION_NOTES-pointer-collapse.verify.sh` states this limitation and a
statement of a limitation should resolve to a filing.

Session 253's `--self-test` driver compares each mutant's whole 10-tuple of arguments against the
pristine tuple and reports `NO-OP` when they are equal. That catches a mutant whose *only* mutation
has become a no-op — the Session 249 failure exactly. It is structurally blind to a mutant that
mutates **two or more** slots and loses only one of them: the tuple still differs, so the guard
stays silent, and whether the survivor is caught then depends on the mutation that still lands.

**Measured, not estimated** (instrumented copy printing which slots differ, repo untouched):

| slots changed | mutants | which |
|---|---|---|
| 1 | 39 | (unexposed — inertness is total, and the guard sees it) |
| 2 | 3 | `M27`, `M28`, `M44` (`before`, `after`) |
| 3 | 4 | `M38`, `M39`, `M40`, `M41` (`after`, `live_wt`, `new_table`) |

**Lower risk than the bug it follows, and the reason is structural.** All seven derive their
operands from frozen sources — `M27`/`M28`/`M44` from `before` (read at `ddd5660`) plus the pinned
`OLD_BLOCKS`/`FRONT_SUBST`; `M38`–`M41` from `NEW_TABLE.replace(...)` fed through `with_table()`,
which rebuilds `after` and `live_wt` from `before`. None reads the working tree, so none can drift
out from under its needle the way `live_wt` did at `5243242`. This is a gap to close on purpose,
not a fire.

**Not audited in the other eight proofs.** A generic detector exists — instrument each mutant's
argument tuple, or scan for `.replace()`/`re.sub()` call sites whose every execution returns its
input unchanged. Session 253's review ran the latter across all nine and found **zero** totally
dead replace sites today, so nothing is currently broken; the item is that nothing *watches*.

**DONE** = either the guard compares slot-by-slot and reports which slot went inert, or a documented
decision that whole-tuple comparison is sufficient with the seven named above accepted as residual.
**VERIFY:** re-run the slot census; every mutant is either 1-slot or explicitly accepted.

### Neither collapse proof is guarded by anything

Filed Session 254, same review.

`L10` enforces write-once over the ancestor shard proofs from a hand-declared list. `R4/GONE`
asserts every shard the table declares, and its `.verify.sh`, are on disk. **Nothing covers either collapse
proof.** `SESSION_NOTES-pointer-collapse.verify.sh` and
`SESSION_NOTES-pointer-collapse-S254.verify.sh` are not shards, are not in any declared list, are
not matched by the census guard's `SESSION_NOTES-*.md` glob, and CI's loop errors only when it finds
**zero** proofs — so deleting one leaves the gate green.

This matters most for the S254 proof, which the front matter names as the **second custodian** of the
276 replaced lines: *"the retired prose is readable byte-for-byte in three places … embedded verbatim
inside the proof named below."* If that file can vanish silently, one of the three custodians is
unasserted. (Nothing is actually at risk today: the pre-collapse commit `8c9bb35` and each shard's
own banner both survive independently.)

**Small.** Either add both files to a declared write-once list in the style of `L10`, or have each
collapse proof assert the other exists and matches its add-commit blob. The second is symmetric and
needs no new list to maintain.

### A quotation can defeat the S254 collapse proof's self-test

**Filed Session 266. Operator call — it changes a custodian proof.**

`SESSION_NOTES-pointer-collapse-S254.verify.sh` builds its oldest-record mutations with
`rfind("### What Session ")` (`:1091` and `:1158`). That is the LAST occurrence of the literal
anywhere in the text, not the last record heading, so a record that quotes the literal after its own
heading moves the anchor into the quotation. The mutation then changes nothing, the mutant survives
and `--self-test` exits 2. Measured by Session 266's mapping analyst on a simulation of its trim:
the cut retained Session 258's record, whose line 1149 quoted `### What Session N Did`, and M43
survived (50 of 50 were caught at HEAD). Session 266 avoided it by rewording that one quotation to
"everything above the first record heading", the operator's ruling at Phase 1, which left both
proofs byte-identical.

**It comes back.** Session 264's record quotes `### What Session 262 Did` in its handoff evaluation
(`SESSION_NOTES.md:313` when this was filed). Whenever the oldest record a trim retains holds such a
quotation after its heading, the same red returns, and the workaround is another reword.

**Small.** Anchor both searches at a line start (`rfind("\n### What Session ") + 1`); the analyst
verified that gives 50 of 50 caught. **Operator call** because it edits a custodian proof that
nothing guards (the item above) in the session that needs it green, which reads as gate erosion
(failure mode 17) even though the anchor is stricter, not looser. Best done together with the item
above, since both are about what protects those two files.

### The ledger table's rows after the eighth are guarded only in form

**Filed Session 266 (the tenth trim's adversarial review). Operator call — it is a guard design question.**

`SESSION_NOTES-pointer-collapse-S254.verify.sh` pins rows 1 to 8, and its `R4` checks each of those
hashes against the git history of its archive. Rows 9 and 10 have no such custodian. The census guard
(`tests/test_session_notes_census.py:422`) composes every cell of every row except the hash, and its
hash slot is only the form `[0-9a-f]{7,40}` or the words `this commit`. Session 266's review committed
each perturbation into a clone and ran every proof and both guards: row 9's hash changed to a wrong
one (7 hex digits) passes all 82 guard tests and every proof; so does `this commit` replaced by a
made-up hash in row 10, an extra trailing cell on a row, and trailing spaces on a row.

The tenth trim resolved row 9's `this commit` with a declared substitution in its proof, typing the hash
after measuring it with `git log --diff-filter=A`. L2 compares the ledger against that same typed value,
so a wrong hash typed on both sides also passes. The eleventh trim will copy the pattern for row 10.

**A second trap, found the same way:** the census guard's row mutants anchor on the newest row's full
text and require it to occur exactly once, so a session record that quotes that row word for word turns
four guard tests red at its own commit, and neither the trim's proof nor the trim commit can see it.
Session 266's record avoids the quotation; nothing tells the next author to.

**Small.** Options: derive each resolved hash inside the trim's proof from `git log --diff-filter=A`
(the proof already reads git; the census guard deliberately does not, because CI checks out shallow),
and anchor the composed row pattern to the whole line with a mutant. **Operator call** because ruling F
already names the CI guard as the home for table checks, and a hash check that needs history belongs
in a job that fetches it.

### The read-budget guard cannot model "claim, then a wide close-out" from a close-out state

**Filed Session 266 (the tenth trim's review; a skeptic reproduced it).**

`tests/test_read_budget.py`'s `_successor_wide_closeout_then_claim` (`:995`) returns at once (`:1002`) unless
the newest record is a claim stub, so `test_next_state` never composes a claim and THEN a wide close-out
starting from a finished close-out. In the claim state that follows, the wide model parks the K prefix
within about a line of the page, and mutant M01's padded ledger shifts the page by one line, so
`check_k_lines` co-fires and `check_ceiling` stops being a sole catcher. Measured at 45 B per line: a
close-out of 19,650 B, 19,725 to 19,850 B or 21,975 to 22,050 B is green at its own commit and red at
the next session's claim commit; none at 50, 60, 68 or 73 B per line in about 600 samples. The
close-out's own commit cannot show it.

**Behind it, a recurring cause (learning #287).** `_m08_the_retention_rule_has_no_compliant_cut` exists
to make `check_satisfiable` fire alone. It has been repaired five times in four sessions (256 twice,
258, 262 and 266), and each repair held the quantity the previous red had named. Session 266's was the
bytes of the page's head, which the pad had entered although it sat beyond the K prefix.

**Small.** Add a parametrisation that runs `_successor_claim` and then `_successor_wide_closeout_then_claim`
from a close-out state (the skeptic verified it is red from there on the failing sizes and the other
tests stay green), and assert `page_estimate(mutated) == page_estimate(original)` inside M08, so a promise
it cannot keep is a build error. **Until then:** before committing a close-out, put a claim stub for the
next session above it in a scratch copy and run `uv run pytest tests/test_read_budget.py --no-cov`.

### CI runs the proofs on push, and this repository pushes in bursts

**Filed Session 253. Operator call — it is about cadence, not code.**

Session 253 added a `proofs` job to `.github/workflows/ci.yml` running both modes over every
`docs/architecture-history/*.verify.sh` on push to `master` and on PRs. That is the automation the
operator ruled for, and it works. What it does not fix: measured at the time of filing,
`origin/master` was at `037895b` (Session 249's close-out) while local `master` was **7 commits and
4 sessions ahead**. On that cadence the new job would first have observed the Session 249 breakage
about four sessions after it landed — **the same latency as the outage it repairs.**

The per-session countermeasure landed instead, in `CLAUDE.md`'s trimmed-file bullet: the both-modes
loop, with the reason neither mode alone is sufficient. That is prose, and prose was already
mandating `--self-test` when four sessions did not run it.

**Options:** (a) accept — CI is a backstop, the per-session run is the fast path; (b) a `pre-push`
hook under `.githooks/` (the directory exists and `core.hooksPath` is already the convention here)
running the two-mode loop; (c) push every session. **DONE** = an operator ruling recorded here.


### `PROJECT_LEARNINGS.md` is refused by a default `Read`, and its newest learnings are at the bottom

**Filed Session 255, under the operator's ruling of 2026-09-10 (Option D widened: declare, guard,
file).** `tests/test_read_budget.py` lists this file in `KNOWN_REFUSED`, so the guard tolerates it
over the refusal ceiling — and fails the moment it drops under, until it is removed from that list
and from the sentence in `CLAUDE.md` and `docs/methodology/PROJECT_CONVENTIONS.md` §5 naming it.

Measured Session 255: **298,720 B**, 247 lines, **104,523 tokens** (an explicit `offset`/`limit`
`Read` over the whole file meters it exactly; a default `Read` is refused with zero content). It
crossed 262,144 B at the Session 246 close-out (`ea82065`, 267,155 B) and has grown ~4.6 KB per
session since. **It is oldest-first** — learning #1 at the top, the newest at the bottom — so even
under the ceiling a default `Read` would deliver the oldest learnings and cut the newest.

Constraints any remedy meets: `CLAUDE.md` tells sessions to `grep` it or `Read` it with
`offset`/`limit`, so a default `Read` is not its instructed access path; learnings are cited by
number on ~250 lines across ~19 files outside it; canonical gives on-demand learnings files no token
verdict at all.

- **(a) Archive the oldest rows** into a frozen part beside a `.verify.sh` proving the move lossless
  (PROJECT_CONVENTIONS §3). Row numbers survive; citations of archived rows then point at the wrong file.
- **(b) Reorder newest-first.** One large rewrite; citations by number still resolve by `grep`.
- **(c) Split into an index** (one short line per learning) plus detail.
- **(d) Re-scope**: rule that a grep-only file is outside the read budget, and drop it from D's scope.

**Operator call.** Each is a session of its own.

### `CHANGELOG.md`'s top is not newest-first

**Filed Session 255 as two defects; narrowed Session 257.** A default `Read` of this file is
refused, and its top is out of order. On 2026-09-14 the operator ruled the first with remedy (c) as
filed — *"a write-only file is outside the read budget"* — for this file alone: *"Rule (c) for
CHANGELOG.md — take it off the read budget"* (`PROJECT_CONVENTIONS.md` §5 records why). Its size —
664,625 B when ruled, 2.54× the refusal ceiling — is no longer a defect. The other two remedies
lapse with it, since nothing trims the file: a hand-built archive, and a grammar conversion so the
canonical trimmer stops refusing it with `GRAMMAR_MISMATCH`. **Session 259 (BL-57 P11) changed the
mechanics, not the ruling:** the file now carries tagged entries, so the trimmer parses it and its
trigger fires — and `CLAUDE.md` records, with the measurement, why it must still never be written to.

What remains is order. Under the `## [0.3.0]` heading, four entries (Sessions 191, 193, 203 and
205) sit above the September entries, so the newest entry by position is not the newest by date.
**Where new entries go is no longer part of this item:** since Session 259 they are prepended under
the topmost `## YYYY-MM` heading, which sits above `## [0.3.0]` and everything inside it (operator
decision (b), 2026-09-19). The four are inside the legacy part of the file, which stays as written
unless someone decides otherwise.

**Operator call.** Move the four into date order — a pure reorder of an append-only log, provable
as a permutation of its entries — or accept the order.

### The `SESSION_NOTES.md` shard is past the agent read cap and nothing watches it

**Filed Session 222 by the session that created it**, deliberately not fixed there — the fix lives
upstream in a repository this project does not own.

`docs/architecture-history/SESSION_NOTES-through-S216.md` is **24,564 record lines** (24,590 total). A default
agent `Read` of it is **refused outright** — `File content (3.9MB) exceeds maximum allowed size
(256KB)`, zero content returned, measured Session 249 — so it cannot be read in one pass at all.
The refusal is loud and `offset`/`limit` still reach every line, which is the part the original
filing got wrong: the defect the trim was scoped to remove was relocated, not eliminated, but it was
never the *silent* loss this item claimed until Session 249. **Sessions 224, 228, 231, 235, 239, 242, 245, 256 and 266 widened this:**
there are now **ten** unwatched shards. The second, `SESSION_NOTES-S220-through-S217.md` (804 lines), the
third, `SESSION_NOTES-S224-through-S221.md` (933 lines), the fourth,
`SESSION_NOTES-S227-through-S225.md` (790 lines), the fifth,
`SESSION_NOTES-S231-through-S228.md` (976 lines), the sixth,
`SESSION_NOTES-S235-through-S232.md` (1,057 lines), the seventh,
`SESSION_NOTES-S238-through-S236.md` (644 lines), and the eighth,
`SESSION_NOTES-S241-through-S239.md` (792 lines), were each probed with a default `Read` in
Session 249: the S224, S231 and S235 files **truncate** (26,374 / 27,077 / 30,683 tokens against a
25,000-token cap, announced in full), and the S220, S227, S238 and S241 files return whole. The ninth, `SESSION_NOTES-S248-through-S242.md` (1,732 lines), was probed by Session 256 with an explicit `offset`/`limit` `Read` spanning the whole file: **48,717 tokens**, so a default `Read` of it truncates too. The tenth, `SESSION_NOTES-S257-through-S249.md` (1,498 lines), was probed by Session 266 the same way: **42,378 tokens**, so a default `Read` of it truncates as well. Line
counts do not predict that and never did — the cap is token-denominated — so the claim this item
carried until Session 249, that all seven newer files read whole, was false. Every future trim adds another unwatched path. (The 924 figure this item carried for the
third shard was wrong; 933 is the measured `wc -l`.) Verified: `READ_CAP_WATCHED`
(`methodology_dashboard.py:287-288`, consumed at `:1481`) is an **exact-path membership test** over
`SESSION_NOTES.md`, `CHANGELOG.md`, `HANDOFFS.md` and three `BACKLOG.md` locations. The shard is in
none of them, is not LOC-discounted as a framework doc (`FRAMEWORK_SEED_DOCS` is root-anchored,
`:684-690`), and raises no "large files" row either (that check gates on `ext in SOURCE_EXTS`,
`:2929-2936`). **So no tooling will ever warn about it.**

**The premise is not only prose — it is a CONSTANT in three write-once proofs, and one of them is
green while certifying a falsehood.** `"read_cap": 2000` is declared in the S235, S238 and S241
proofs, and `L12` fails a cut whose shard's LINE count reaches it, with the message
*"truncates in silence"*. Measured Session 249: that shard's line count is nowhere near 2,000
— it is composed above and deliberately not restated here — so the arm passes and the proof
certifies the file as readable in one pass, while a default `Read` of it returns an announced
PARTIAL view at 30,683 tokens against a 25,000-token cap.
**A green, self-tested assertion certifies as readable a file that cannot be read in one pass.** All
three proofs are pinned byte-for-byte by `L10` and can never be corrected. A future proof must
declare the cap in bytes, or not declare it at all. **A byte proxy is derivable here, and the claim
that nothing in this repository can measure the harness — which this item asserted earlier in
Session 249 — is too strong.** Measured at the three cuts probed this session, a default `Read`
stopped after 54,904 / 55,470 / 55,126 bytes; the fleet tool's computed `READ_CAP_BYTES` of 56,750
over-predicts each by under 3.4%. **The ninth trim (Session 256) changed all FIVE things this item
listed** — the `SIZE_PROSE` row keyed to `read_cap`, the `read_cap` key in `SIZES`, the `L12/cap`
arm, the `M63` mutant and the `--self-test` summary line, each re-targeted to the 262,144-byte
refusal ceiling — **and its banner states that ceiling instead of the false premise.** Eight of the
ten banners state the 2,000-line cap and seven of them the silent truncation; the ninth and tenth do neither.

**Three live files are past the real cap too, and two of them return NOTHING.** Measured Session 249
by a default `Read`: `PROJECT_LEARNINGS.md` (272.5 KB) and `CHANGELOG.md` (626.4 KB) are **refused
outright** — `exceeds maximum allowed size (256KB)`, zero content returned — while `SESSION_NOTES.md`
and this file truncate with an announced notice. `CLAUDE.md`'s Learnings pointer directs every session
to read `PROJECT_LEARNINGS.md` when a task resembles earlier work, and that instruction currently
returns nothing at all. This **corrects** Session 248 §12.3, which derived "4.19x the cap" from a
bytes-per-token ratio and therefore predicted truncation: the observed behaviour is refusal, which
delivers none of the file rather than part of it. Not fixed here — Option A was the premise
correction. **Ruled 2026-09-10 (Session 255):** both files are declared over the ceiling and each is
filed as its own remediation item above; at that ruling they measured 291.7 KB and 643.0 KB.
**Narrowed 2026-09-14 (Session 257):** `CHANGELOG.md` is outside the read budget, so only
`PROJECT_LEARNINGS.md` is still declared; the other item now records only that file's order.

**The same false claim is repeated inside the write-once shards and their proofs, where it can
never be repaired.** Those copies join the stale banners this project already documents as
permanently-false-but-frozen. Enumerate them with
`git grep -nE '2,?000|no error and no missing-data marker' -- 'docs/architecture-history/*'` rather
than trusting a count typed here; the classified breakdown (cap-value vs silence, live vs frozen) is
[`docs/planning/ledger-budgets-review.md`](docs/planning/ledger-budgets-review.md) §1.4. **Session 249
corrected every live site and left every frozen one alone.**

**What ships today is prose, and prose only:** the pointer block's second paragraph in
`SESSION_NOTES.md`, the corresponding paragraph of each shard's own banner, and the `CLAUDE.md`
adaptations subsection. Warnings in prose are weaker than one entry in a watched set — and the count
of files carrying them grows by one at every trim, which is the wrong direction.

**Why it was not fixed in Session 222.** The remedy is a `READ_CAP_WATCHED` entry (or a glob) in
`methodology_dashboard.py`, which lives at `~/Development/methodology` and is synced to 13 projects.
Editing it here is forbidden (`CLAUDE.md`; `NOTICE` §1) and editing it upstream is a change to shared
fleet tooling — **an operator call, not an implementer's**, and a different repository's session.

**Options, in ascending cost:** (a) add the shard's path to `READ_CAP_WATCHED` upstream — smallest,
but hardcodes one adopter's filename into fleet tooling; (b) make the watch a **glob** over
`docs/archive/**` and `docs/architecture-history/SESSION_NOTES-through-*.md` — generalises to every
adopter that ever shards a ledger, and is the shape the dashboard's own comment implies it wanted;
(c) accept prose-only and record the acceptance. **Recommended: (b)**, upstream, its own session in
the methodology repo. Note (b) also fixes the same blind spot for the 5 fleet projects that already
have shards under `docs/archive/`.

**⚠ That option was written in Session 222 for a one-shard world and no longer works as stated.**
Measured Session 249: `SESSION_NOTES-.../SESSION_NOTES-through-*.md` matches **one** of the eight files
that existed then — `PROJECT_CONVENTIONS.md` §3 mandates the range form `<STEM>-<NEWEST>-through-<OLDEST>.md`
for every non-first shard and nine trims have obeyed it — and `docs/archive/` does not exist in
this repository at all. Any implementer of (b) must re-derive the pattern first. **And the premise
half of this item is already fixed upstream:** the canonical dashboard was re-denominated onto
bytes on 2026-08-26 (`9e71f83`, `READ_CAP_TOKENS = 25_000`, `READ_CAP_BYTES` computed from it,
the line rate deleted), so what remains here is the WATCH-LIST coverage question, not the cap's
unit. The copy at `~/Development/methodology_dashboard.py` is the stale v2.15.2 and still declares
`READ_CAP_LINES = 2000`; sync it before quoting anything it reports.

### A clean `git merge` or `git pull` carrying a wiki change still publishes nothing

**Filed Session 241, from executing the two items this replaces.** Not a regression — a gap their
diagnosis did not reach, found while proving the fix.

Session 234 filed `.githooks/post-commit` as blind to merge commits, and it was: `git diff-tree
--no-commit-id --name-only -r HEAD` prints nothing for a merge. `72b5718` fixed that with
`--diff-merges=first-parent` (`-m --first-parent` is **not** the fix — `diff-tree` ignores
`--first-parent` when `-m` is given and emits the union over all parents).

**But most merges never reach `post-commit` at all.** Verified in a synthetic repo with both hooks
installed as echo stubs: a clean `git merge --no-ff` fires **`post-merge`** only; `post-commit` fires
for a merge just when the user finishes a *conflicted* merge with `git commit`. This repository
installs no `post-merge` hook, so a clean merge or `git pull` that carries a wiki change publishes
nothing, silently — the same fail-open the two closed items were about, one hook over.

**Fix:** add `.githooks/post-merge`. It must diff **`ORIG_HEAD..HEAD`**, not `HEAD` — a fast-forward
`git pull` advances many commits at once and `diff-tree HEAD` sees only the tip. Guard the squash
case (`$1 = 1`), where no commit was created. **Cost: small.**

**Already pinned:** `tests/scripts/test_wiki_publishing.py::test_a_clean_merge_never_reaches_this_hook`
asserts the publisher does *not* run, so the gap is visible and the test reddens if git ever changes.

### The docs toolchain has no version ceiling — `mkdocs-material>=9.0` admits a major bump

**Filed Session 243, from executing the `uv.lock` / `paths:` ruling.** Not a regression — the other
half of the option the operator did not take, and a deferral that has been outstanding since the
tutorial renderer landed.

`pyproject.toml:41-42` declares `mkdocs>=1.5` and `mkdocs-material>=9.0` — **neither has an upper
bound**, so `uv lock --upgrade` may resolve a major version. This was deliberate:
`docs/architecture-history/tutorial-renderer-migration-plan.md:291` risk #1 says *"A future Material
10 would be a separate review pass. Implementer may choose a tighter ceiling (`<10`) for safety"*,
and `CHANGELOG.md:960` records that the implementer chose not to.

**Why it matters here specifically.** `mkdocs.yml:22-26`'s `exclude_docs` allowlist is a fail-closed
`/*` plus negations, and `!/assets/` is load-bearing because MkDocs applies those patterns to the
**theme's** static files, not just `docs_dir`. That interaction already shipped an unstyled public
site for four weeks (2026-07-27 `b27cc98` → 2026-08-22, Session 237). A theme reorganisation is
exactly the kind of change a major bump makes.

**Session 243 substantially de-risked this, which is why it is small and not urgent.** With `uv.lock`
now in the `paths:` filter and `uv sync --extra docs --locked` asserting the lock governs, a major
bump now *fires a build* and meets `scripts/check_site_assets.py` **before** `gh-deploy` — so it
fails as a red job rather than as a silent unstyled publish. The ceiling is defence in depth: it
stops the resolution instead of catching its result.

**Fix:** `mkdocs>=1.5,<2` and `mkdocs-material>=9.0,<10`, then `uv lock` and commit the lock.
**Non-binding today** — PyPI's latest is `mkdocs-material 9.7.7` / `mkdocs 1.6.1`; 10.x does not
exist (measured 2026-08-24). **Cost: small**, 2 lines + a lock refresh. Note that the lock refresh
itself now fires a deploy, which is correct and is the point.

### Two delivered plans are still filed under `docs/planning/` — `httpx-adapter-migration.md` and `repository-rename.md`

**Filed Session 234 (Phase 5), from `repository-rename.md` §8.1 finding 4.**
`docs/methodology/PROJECT_CONVENTIONS.md` §3: active plans live at `docs/planning/`, and when a
plan's primary scope is delivered it moves to `docs/architecture-history/`. This one's scope is
delivered and it has not moved.

**§8.1's framing is spent — do not carry it forward.** It said the file's *"2 old-name hits would
become historical the moment it is archived — which would shrink this rename's scope by one file.
Worth doing before execution if it is cheap."* Session 233's `1865fc2` rewrote both in place, so the
count is **0** and there is no rename saving left to collect. What remains is filing hygiene, plus
the question the move actually raises: archiving it re-points every citation of its path.
**Cost: small, but do the referrer sweep first** (`git grep -l 'httpx-adapter-migration'`), and it
needs an operator call on whether it moves at all.

**And it is now two files, not one.** `docs/planning/repository-rename.md` went **EXECUTED** in the
same commit that filed this item, so it is the identical case — a delivered plan still sitting in the
active-plans folder. It is the heavier of the two: it is cited from `CLAUDE.md`, `SESSION_NOTES.md`,
`enterprise-migration.md` and its own §7.2 allowlist, and **moving it would change a path that its own
completion criterion matches on**. Rule on both together, or on neither.

### Enterprise migration (`docs/planning/enterprise-migration.md`)

Land the `feat/bedrock-mantle-migration` branch on `origin/master`, converge the three
documentation surfaces, and provision a one-time enterprise clone of the repository + wiki.
**Goals 1 and 2 (land the branch, close the public exposure) are complete** — Phases A1–A4 done
(Sessions 186–189, `41ab834`/`b27cc98`/A3's `35ccbd9`/A4's landing PR #2 → `master@9cabe0e`).
**Correction:** the prior version of this entry (written by Session 188) claimed A4 was still
open and that a later session would mark "Goals 1–2 done" here — that update never actually
landed (Session 189's close-out claimed it did; `git log -- BACKLOG.md` shows no commit between
Session 188's `35ccbd9` and this one touched this file). Fixed by Session 190.

**Plan-revision session done (Session 194, 2026-07-28):** `enterprise-migration.md` §1.3 now
reconciles the operator's 2026-07-27 sequencing decision (D3 + the "platform team" bucket — D4,
D5, D8, D9, D14, D15, D16 — resolved post-fork, inside the clone, not reported back to this
repository; the "security" bucket, D10/D13, is unaffected and stays live) with the plan's phase
gates, §3 Decision Register, dragon #20, §6, and §7. The phase list below reflects the revised
plan; the bullets below are a summary — `enterprise-migration.md` is authoritative.

**Phase C4's gate is now fully satisfied (Session 195, 2026-07-28):** B2 (below) is DONE. C4 can
run as soon as the operator supplies D9 (destination host), D5 (import strategy), D4 (DCO), D8
(wiki destination), and D16 (release disposition) live at that session's start — see
`enterprise-migration.md` Phase C4's "Before step 1" note and dragons #22/#24. This repository does
not pre-answer those five; whoever runs C4 gets them from the operator directly.

**Readiness audit (Session 263, 2026-09-21): not ready yet, but close.** A 13-agent read-only audit
(six dimensions, each adversarially re-verified) measured the tree against the plan; this list is
what the plan's text does not yet say — the plan stays authoritative on the phases. Its one
blocker — local `master` 10 commits ahead of `origin`, which a mirror of `origin` would have dropped
for good, `1e53c20`'s `redact_secrets` fix among them — was cleared the same session by the
operator's push (`f987a6f..0adc8ae`, CI green, 1,481 passed). It reopens whenever a session leaves
commits unpushed. **Do on the original before forking** — the clone cannot receive a fix later:
1. `docs/methodology/README.md:361-369` still carries the superseded no-redistribution licence and
   links a `LICENSE` that does not exist (upstream relicensed to MIT in `49a103a`; `bin/sync` does not
   distribute this file). Fix `NOTICE` with it: `:28` says no listed file has a copyright header,
   `:40` names the canonical upstream as the sync source (it is the operator's fork), and it never
   cites the public relicense.
2. `4795c29` (Session 189's close-out record) exists only on local `feat/bedrock-mantle-migration`:
   push it or drop it deliberately.
3. Tag `v0.3.0` (D12's tag half): both `pyproject.toml` files say 0.3.0; only `v0.1.0`/`v0.2.0` exist.
4. Refresh `audits/2026-07-28-b2-import-readiness.md`: 385 commits scanned where history has 579, a
   pre-rename wiki path, and 39 placeholder database-URL credential lines left unclassified.
5. Give Phase C4 a local-vs-`origin` parity pre-flight (`git ls-remote origin` against local `master`,
   and CI green on that tip); it has none.

**C4-time facts the plan does not carry:** a squash import or signed-history rewrite (D5/D4) turns
all 11 ledger proofs red permanently. `git push --mirror` carries `refs/pull/*`, which GitHub-family
hosts reject, and `gh-pages`, which bundles `wordcut.js` from `mkdocs-material` (upstream LGPL-3.0;
Python runtime deps remain copyleft-free) — push `refs/heads`/`refs/tags` explicitly. On GHES,
disable Actions before the push or `publish-tutorial.yml` fires. `scripts/publish_wiki.sh:48` falls
back to the personal wiki when `WIKI_CLONE` is empty, and the C4/C5 "fails closed" check *runs* the
publisher — step 4 must land before that check or any hook. Stale figures: the wiki has 44 commits /
25 pages (plan: 33 / 23), 188 intra-wiki links (plan: 157), and step 6's `SESSION_RUNNER.md:209`
text is now `CLAUDE.md:75`. Arm 1 of the independence check measures 243 hits against "→ 0"; its
exclusions need a ruling. **C2 was never started** (htmx from unpkg, no intake-UI auth,
`MPC_HOST_URL` ignored, stores created 0644, `--model` defaults wrong for Bedrock, proxy/CA
undocumented) — not a C4 gate, so it becomes the clone's work. Evidence: `SESSION_NOTES.md`,
Session 263.

- **B1 — The legal packet.** **D3-independent core: DONE (Session 190)** — wiki LGPL mislabeling
  fixed, root `SECURITY.md`/`CODEOWNERS`/`THIRD-PARTY-LICENSES`/baseline `CONTRIBUTING.md`/`NOTICE`
  added, D1 attribution in place. **Full B1 (the corporate DCO/CLA mechanism section) is no longer
  a session this repository schedules** — per §1.3, it depends on D3/D4/D9, all deferred post-fork;
  it will be authored inside the enterprise clone, not here. B1's D3-independent core is the actual
  gate on Phase C4, and it's satisfied.
- **B2 — Import readiness.** **DONE (Session 195).** `.gitleaksignore` + classification table +
  secrets attestation + external-asset register at `audits/2026-07-28-b2-import-readiness.md`;
  `releases-export.json`/`prs-export.json` at repo root. The three GitLab pilot projects
  (`subrogation-pilot`, `-v2`, `-v3`) and the two GitHub Releases + tags are registered with a named
  disposition (undecided/D16 for the Releases and pilot projects — recreate-vs-pointer and
  migrate-vs-leave stay live D16/operator calls, not pre-decided). **The three `.env` credential
  rotations, originally flagged here as not done: RESOLVED as not required (Session 198)** — the
  rationale ("so the clone never depends on personal dev credentials") was wrong; Phase C4 step 1's
  `git clone --mirror` already carries zero credential values, so rotation was neither necessary
  nor sufficient. See `docs/planning/enterprise-migration.md` §1.4 and Phase C4 step 9 (corrected):
  the real requirement is provisioning `<enterprise-clone>` with enterprise-owned credentials at
  C4 time, not rotating the personal ones beforehand — no pre-fork action needed. The 162 MB
  `.git`/loose-objects fact from §2.9 is pre-existing repo state, not a B2 action item — `git clone
  --mirror` (C4 step 1) repacks on push regardless.
- **B3 — LGPL removal.** **DONE** (both LGPL SDKs removed via `docs/planning/httpx-adapter-migration.md`,
  Sessions 191–193 — see `CHANGELOG.md`'s 2026-07-27/2026-07-28 entries). D11 is moot; no further action.
- **C1 — Bedrock enterprise correctness.** **Narrowed by §1.3.** **D10 RESOLVED (Session 199):
  Regional. D13 RESOLVED (Session 200):** `require_sigv4` sub-scope only (guard completeness + env
  wiring), not `http_client`. **`bedrock-enterprise.md` §0's three security questions RESOLVED
  (Session 201, 2026-07-29, operator):** Guardrails not mandated, FIPS not mandated (mantle path
  confirmed correct — the plan's scope, which assumed "no" to both, was right), runtime quota
  expected yes (established enterprise account) but not independently verified. **Phase C1's own
  bundled scope is DONE (Session 202, 2026-07-29):** fixed the stale/false `base_url` claims in
  `bedrock-enterprise.md` §4 (it wrongly said the override "does not yet" exist, and wrongly cited
  `ANTHROPIC_BASE_URL` — the SDK's Bedrock-mantle client actually reads a different, mantle-specific
  var, `ANTHROPIC_BEDROCK_MANTLE_BASE_URL`, verified against the installed SDK 0.94.1 source);
  documented that var in `.env.example` and §7; extracted the §3 IAM policy into two standalone
  applyable JSON artifacts — `docs/deployment/bedrock-mantle-execution-role-permissions.json` (the
  real permissions policy) and `docs/deployment/bedrock-mantle-execution-role-trust.json` (the
  trust policy, `Principal` left an explicit D14-blocked placeholder, not guessed). **Phase C1 is
  now fully complete** — no scope remains; D14's trust-relationship fill-in is the enterprise
  clone's own post-fork work, per §1.3.
- **C2 — Runtime, network, and data-at-rest readiness.** **Narrowed by §1.3.** **D13 RESOLVED
  (Session 200) — D13 was this phase's only gate, so C2 is now fully ungated and schedulable.**
  D15's dependency (index-variable documentation) is carved out and deferred post-fork.
- **C2b — Deployment artifact.** **Out of scope for this repository (§1.3)** — its only gate (D14)
  is unanswerable here; this is now the enterprise clone's own future work, not a session this
  repository will schedule.
- **C3 — CI and supply-chain hardening** (targets the enterprise clone's own CI). Gated on **C4
  complete only** — D9/D15 no longer need a written answer here, but the operator must supply both
  live at C3's session start (same pattern C4 uses for D9/D5/D4). Still a session this repository
  schedules, even though its edits land inside `<enterprise-clone>`.
- **C3b — Generated-project CI portability.** **DONE (Session 205, 2026-07-29).** New `CIHostConfig`
  dataclass (base image, index URL, action prefix, pre-commit repo — default to today's public
  values) threaded through `governance_templates.py` → `WebsiteAgent` → the website agent CLI →
  `scripts/run_pipeline.py`'s new `MPC_CI_*` env vars, so pipeline-generated projects can target
  enterprise-internal hosts instead of Docker Hub / the public GitHub Actions marketplace / public
  PyPI / the public `astral-sh/ruff-pre-commit` mirror. Verified: fake-mode run with all four env
  vars set → 0 public-host matches across 39 generated files; unset → public values unchanged.
  See `docs/planning/enterprise-migration.md` Phase C3b for the full breakdown.
- **C4 — Enterprise clone provisioning ("the fork").** Gated on **A1–A4 complete (done), B1's
  D3-independent core complete (done), and B2 complete (done, Session 195) — the gate is fully
  satisfied**. D4/D5/D8/D9/D16 no longer need written answers here; the operator supplies them live
  at C4's session start.
- **C5 — Fork independence verification.** Gated on **C4 complete only** — D16 no longer a written
  pre-req; C5 records whatever the operator decided, live, inside the clone (not back into this
  repository's own tracking).
- **Executive summary / stakeholder readiness dossier — DONE (Session 196).** Requested by the
  operator, 2026-07-28; produced Session 196, 2026-07-28/29. Delivered as
  `executive-summaries/stakeholder-readiness-dossier.qmd` (+ reproducible `.html`/`.pdf` renders,
  gitignored per the `business-value-capture` precedent — the `.qmd` is the committed source of
  truth), covering all three requested sections: (1) business benefit of the pipeline, with an
  honest evidence/limits split (real engineering smoke-test traction vs. no claims-team adoption
  yet); (2) legal safety, re-derived fresh against D1/D2/D3 and the §2.7 licence table (MIT
  consistent, zero LGPL/GPL/AGPL, third-party methodology material under a documented permission
  grant) plus two open items surfaced independently — the generated-project license gap and the
  published wiki's own lack of a license (**both closed, Session 197** — see the dossier's own
  "Open items and owners" table); (3) enterprise-environment readiness across security,
  testing, data readiness, and Bedrock readiness, each split into resolved vs. genuinely open with
  named owners cross-referenced to the plan's §3 decision register and C1-C3 phases. Built via a
  research → draft → 4-lens adversarial verify → fix workflow; verify found 1 blocking gap (the
  wiki-license omission) and 4 minor gaps (an unsubstantiated third disposition option, and three
  "Unassigned"-owner claims that actually duplicate already-scoped C2/C3 phase items) — all fixed
  and spot-checked live before commit (commit counts, license files, LGPL-freedom, wiki license
  absence, and test-collection count independently re-verified, not just trusted from the
  sub-agent). **Phase-structure decision (resolved by this session, as the prior note left open):
  standalone document, not a new lettered A/B/C phase** — it does not gate or get gated by any
  phase; Phase C4's gate (A1–A4, B1-core, B2) remains independently satisfied. Recommendation
  stated in the document: proceed to the fork, carrying the open-items table forward.

**Open decisions this repository still tracks:** none, from either the D-numbered register or
`bedrock-enterprise.md` §0's three (non-D-numbered) security questions — **everything in the
security bucket is now answered.** **D10 (Bedrock endpoint Regional vs Global) is RESOLVED (Session
199, 2026-07-29): Regional** — operator accepted the recommendation; recorded in
`enterprise-migration.md`'s Decision Register and `bedrock-enterprise.md` §5, with the hard-block
residency SCP templated at `docs/deployment/bedrock-residency-scp.json` (specific region allowlist
still an open platform-team placeholder). **D13 (wire `require_sigv4`/`http_client` to app/env) is
RESOLVED (Session 200, 2026-07-29)** — its `require_sigv4` sub-scope only: the guard now checks
both SDK-recognized bearer-token env vars (`AWS_BEARER_TOKEN_BEDROCK` and `ANTHROPIC_AWS_API_KEY`,
was only the first) and defaults from a new `BEDROCK_REQUIRE_SIGV4` env var when not passed
explicitly; recorded in `enterprise-migration.md`'s Decision Register and `bedrock-enterprise.md`
§7. `http_client` wiring remains undone, as the recommendation itself deferred it pending
TLS-inspection confirmation. **`bedrock-enterprise.md` §0's three security questions are RESOLVED
too (Session 201, 2026-07-29, operator):** Guardrails not mandated, FIPS not mandated (mantle path
confirmed correct), runtime quota expected yes (established enterprise account) but **not
independently verified** — that verification needs live access to the actual enterprise account
and is carried forward as a flag, not a blocker, since C1's own remaining scope makes no live AWS
calls. **Phase C1 is now fully complete (Session 202, 2026-07-29)** — its own bundled scope (the
stale `base_url`/`ANTHROPIC_BASE_URL` doc fix, the §3 IAM-permissions-policy extraction into
applyable JSON artifacts) is done; see the C1 bullet above for the full breakdown. No scope remains
in this repository for C1. **Phase C2's gate was already cleared by D13 alone** (D13 was C2's sole
listed gate) — C2's own
scope (htmx vendoring, intake UI auth posture, the `MPC_HOST_URL` gap, plaintext-at-rest,
`run_pipeline.py:450`) is itself untouched but no longer blocked from starting.

**Decisions no longer tracked here (§1.3):** D1, D2, D6, D7, D11, D12 are already answered;
**D3, D4, D5, D8, D9, D14, D15, D16** are resolved by the operator after Phase C4 runs, inside the
enterprise clone, live — not written up in this repository's Decision Register, `BACKLOG.md`, or
`SESSION_NOTES.md`. Whoever runs C3/C4/C5 must get the relevant answers directly from the operator
at that session's start (`enterprise-migration.md` §4's "Before step 1" notes and dragon #22/#24).
See `docs/planning/enterprise-migration.md` §3 for the full Recommendation-column text, preserved
as forward context for whoever eventually answers these inside the clone.

---

Most recently completed: **`httpx-adapter-migration`** (`docs/planning/httpx-adapter-migration.md`)
— all three phases DONE and LANDED (Phase 1 GitLab: Session 191; Phase 2 GitHub: Session 193; Phase
3 optional rename: Session 203). Zero direct dependencies are LGPL as of Session 193's `9aad76b`.
Full per-commit breakdown in `CHANGELOG.md`'s 2026-07-27/2026-07-28/2026-07-29 entries.

Previously completed: **harden the `cycle_time` cadence definitions and corpus**
(gap #2 robustness follow-up) — Session 177 refined `CYCLE_TIME_DEFINITIONS` to
discriminate `tactical`/`operational` on **output purpose** (not run frequency) and
added the role≠frequency corpus case `claim_workqueue_triage` (live cycle_time 60/60 =
100%, gate assert PASS). The operator **deferred** the optional event-driven/episodic
`CycleTime` member (YAGNI — no corpus case needs it; a schema-`Literal` change with a
larger blast radius); reopen only if such a case arises. See `CHANGELOG.md` and
`tests/eval/PHASE_E_AGREEMENT_REPORT.md`.

---

### `README.md`'s test counts are hand-typed and will drift again

**Filed Session 247; the drift it reported was fixed in Session 250.** The three stale rows —
`data_agent_package/` (207 → **257**), `eval/` (94 → **157**) and `test_llm_json_parity.py`
(16 → **34**) — were corrected against a fresh collection pass, not pasted from the filing. At that
pass `pytest --collect-only` reported **1,347** collected, of which 9 skip without live LLM
credentials, and every per-directory row in the block agreed with it, including the three that sum
into `agents/` (155 intake + 199 website + 19 data). The rows sum to the collected total.

**What is still open is the class, not the instance.** Every count in that block is typed by hand
and nothing derives it — this is the fourth surface in this repository to state a count nobody
derives, after the shard census, the size figures and the span sentences.
`tests/test_session_notes_census.py` covers the shard census only; a sibling check that composes
these rows from a collection pass would close the class instead of the instance. That is a design
call, which is why the item stays rather than closes. The alternative is to accept that the block
is re-measured by hand whenever someone notices, with this command:

```bash
uv run pytest --collect-only -q --no-cov 2>/dev/null | command grep '::' \
  | sed 's|^tests/||' | awk -F'/' '{print ($2==""? "ROOT:"$1 : $1"/")}' \
  | sed 's/::.*//' | sort | uniq -c | sort -rn
```

### The wiki's `Contributing.md` carries a second, older test census

**Filed Session 250, found while sweeping for other copies of the counts `README.md` states.**
`docs/wiki/model_project_constructor/Contributing.md` — the "Current snapshot" paragraph and the
`grep` command beneath it annotated *"997 at time of writing"* — counts test **functions** per
directory (`def test_` occurrences), a different measure from `README.md`'s collected tests, and the
page says so itself. Measured with the page's own method at Session 250:

| directory | page says | `def test_` now |
| --- | ---: | ---: |
| `orchestrator/` | 211 | 211 |
| `data_agent_package/` | 199 | **225** |
| `agents/website/` | 191 | 191 |
| `agents/intake/` | 150 | 150 |
| `schemas/` | 81 | 81 |
| `eval/` | 75 | **137** |
| `ui/intake/` | 32 | 32 |
| `scripts/` | 22 | **95** |
| `agents/data/` | 16 | 16 |
| top-level `test_*.py` | 20, across four named files | **29**, across five |
| total | 997 | **1,167** |

The page's *"`pytest -q` currently reports 1110 passed plus 12 credential-gated `live` cases"* is
1,338 and 9 today. **Not fixed here**: a different file in a different denominator, and anything
under `docs/wiki/` publishes to the live GitHub wiki on commit — an outward-facing edit outside what
Session 250 was asked to do. It is the same class as the `README.md` item above and closes under the
same decision: derive it, or accept re-measuring by hand.

```bash
for d in orchestrator data_agent_package agents/website agents/intake agents/data eval schemas scripts ui; do
  printf '%-22s %s\n' "$d" "$(command grep -rhoE '^\s*(async )?def test_' tests/$d --include='*.py' | wc -l | tr -d ' ')"
done
command grep -rhoE '^\s*(async )?def test_' tests --include='*.py' | wc -l   # total
```

