# Troubleshooting

Diagnostic walkthroughs for each `FAILED_AT_*` halt path in the
orchestrator pipeline. Each section tells you what to inspect, where the
files are, and what to do next. For the operational runbook see
`OPERATIONS.md`; for the system design see `docs/architecture-history/
architecture-plan.md` §12 (orchestration) and §14 (phases).

---

## Common diagnostics

Regardless of which stage failed, start here:

1. **Find the run's checkpoint directory:**
   ```
   $MPC_CHECKPOINT_DIR/<run_id>/
   ```
   Default: `.orchestrator/checkpoints/<run_id>/`.

2. **List what's on disk:**
   ```bash
   ls -la "$MPC_CHECKPOINT_DIR/<run_id>/"
   ```
   Which files exist tells you how far the run got (see `OPERATIONS.md`
   §2 for the full matrix).

3. **Check the structured logs.** If you wrapped runners with
   `make_logged_runner`, look for `agent.error` events at level
   `ERROR` in the `model_project_constructor.orchestrator` logger. The
   `context` dict includes `error_type`, `error_message`, and
   `duration_ms`.

4. **Check metrics.** If you used `MetricsRegistry`, call
   `registry.snapshot()` to see the status distribution and per-agent
   latency at a glance.

---

## FAILED_AT_INTAKE

**What happened:** The Intake Agent returned an `IntakeReport` with
`status != "COMPLETE"` (usually `DRAFT_INCOMPLETE`).

**Checkpoint state:** Only `IntakeReport.json` is present.

**What to inspect:**

```python
from pathlib import Path
from model_project_constructor.orchestrator import CheckpointStore

store = CheckpointStore(Path("<checkpoint_dir>"))
intake = store.load_payload("<run_id>", "IntakeReport")
print(intake.status)          # e.g. "DRAFT_INCOMPLETE"
print(intake.missing_fields)  # list of fields the stakeholder didn't provide
```

**Root causes:**
- The stakeholder didn't answer enough questions (the agent hit its
  20-question cap before converging on all 4 required sections).
- The fixture used in a scripted run was incomplete or missing fields.

**Resolution:**
- If live: run a new intake interview with the stakeholder, focusing on
  the `missing_fields`. Feed the completed report back into the pipeline
  as a new run.
- If fixture: fix the fixture file and re-run.

---

## FAILED_AT_DATA

**What happened:** The Data Agent returned a `DataReport` with
`status != "COMPLETE"` (e.g. `EXECUTION_FAILED`, `INCOMPLETE_REQUEST`).

**Checkpoint state:** `IntakeReport.json`, `DataRequest.json`, and
`DataReport.json` are present. `RepoTarget.json` is NOT written
(the pipeline halts before the website stage).

**What to inspect:**

```python
store = CheckpointStore(Path("<checkpoint_dir>"))
request = store.load_payload("<run_id>", "DataRequest")
report  = store.load_payload("<run_id>", "DataReport")
print(report.status)
print(report.data_quality_concerns)
print(report.summary)
for q in report.primary_queries:
    print(q.name, q.status, q.sql)
```

**Root causes:**
- `EXECUTION_FAILED`: a SQL query failed against the database. Check
  `report.primary_queries` for individual query statuses and error
  messages. Common causes: table doesn't exist, column renamed, read-
  only credential lacks permission on a specific schema.
- `INCOMPLETE_REQUEST`: the `DataRequest` built by the adapter was
  too ambiguous for the Data Agent. Check
  `request.target_description` and `request.required_features`.
- Database connectivity: the `db_url` or read-only credential was
  wrong or expired.

**Resolution:**
- Fix the upstream problem (database access, query logic, or the
  intake report's `target_definition`).
- Re-run with a fresh `run_id`. The intake stage is deterministic
  for fixtures, so you can stub it with the checkpoint:
  ```python
  intake = store.load_payload("<old_run_id>", "IntakeReport")
  result = run_pipeline(
      new_config,
      intake_runner=lambda: intake,
      data_runner=real_data_runner,
      website_runner=real_website_runner,
  )
  ```

---

## FAILED_AT_WEBSITE

**What happened:** The Website Agent returned a `RepoProjectResult`
with `status != "COMPLETE"` (usually `FAILED` or `PARTIAL`).

**Checkpoint state:** All envelope files AND
`RepoProjectResult.result.json` are present. The terminal result is
persisted even on failure so you can inspect the partial project.

**What to inspect:**

```python
import json
from pathlib import Path

result_path = Path("<checkpoint_dir>/<run_id>/RepoProjectResult.result.json")
result = json.loads(result_path.read_text())
print(result["status"])
print(result["failure_reason"])
print(result["files_created"])     # partial list if PARTIAL
print(result["project_url"])       # may be set even on FAILED if the project was created
```

**Root causes:**
- `FAILED`: the repo host rejected the commit or project creation.
  Common causes: expired token, namespace doesn't exist, name
  collision (project already exists), permission error.
- `PARTIAL`: the project was created but some files failed to commit
  (e.g. the governance tier required an artifact that hit a template
  error). Check `files_created` against the expected set.
- Timeout: the repo host was too slow. Check `duration_ms` in the
  `agent.end` or `agent.error` log event.

**A token leaked by a run before Session 273.** If the token had a trailing carriage
return, line feed, tab or space (or a NUL, vertical tab or form feed inside it), the HTTP
library refused the request and quoted the whole token in its message, and the agent
copied that into `failure_reason` as `repo_error: ... Illegal header value b'<the
token>'`. The website CLI printed that on stdout and wrote it to its `-o` file;
`scripts/run_pipeline.py` printed it in its `Failure:` line and saved it in
`<checkpoint_dir>/<run_id>/RepoProjectResult.result.json`. Since Session 273 such a token
is refused before any request and nothing is printed. To find an old leak:

```bash
grep -rl 'Illegal header value' "$MPC_CHECKPOINT_DIR" <your -o files> <saved CI logs>
```

Rotate any token that turns up, then delete or redact those files and logs. (A token with a
non-ASCII character was not quoted whole: the error named the character and its position.)

**A token the repository host echoed back, in a run before Session 274.** A host, gateway
or proxy that sends the request headers back in an error reply (a debug gateway, an echoing
reverse proxy, a misconfigured firewall page; GitLab's and GitHub's own error pages do not)
put the valid token into `failure_reason`, in the same three places: the website CLI's JSON
on stdout or in its `-o` file, the pipeline script's `Failure:` line, and
`<checkpoint_dir>/<run_id>/RepoProjectResult.result.json`. The same happened when the host's
reply was malformed and the HTTP library quoted it (`illegal header line:
bytearray(b'PRIVATE-TOKEN glpat-...')`). Since Session 274 every failure message that leaves
a repository adapter has the token replaced by `***`, control characters turned into spaces,
and a cut at 1,000 characters (`... [N more characters not shown]`). Nothing is written to
the old files again, and nothing rewrites the ones already on disk. To find an old leak,
search for the first characters of your token, which a checkpoint directory has no other
reason to hold:

```bash
grep -rlF 'glpat-' "$MPC_CHECKPOINT_DIR" <your -o files> <saved CI logs>   # or ghp_ / github_pat_
```

The party that echoed the headers already held the token, so the exposure is wherever the
output went: the terminal, CI logs, the checkpoint directory. Rotate a token that turns up,
then delete or redact those files and logs.

**Resolution:**
- Fix the host-side issue (token, permissions, namespace).
- If the project was partially created, delete the partial project on
  the host before re-running. The Website Agent creates idempotent
  commits but does NOT delete existing projects.
- Re-run with a fresh `run_id`, stubbing the intake and data stages
  with the previous checkpoints if they were fine:
  ```python
  intake = store.load_payload("<old_run_id>", "IntakeReport")
  data   = store.load_payload("<old_run_id>", "DataReport")
  result = run_pipeline(
      new_config,
      intake_runner=lambda: intake,
      data_runner=lambda _req: data,
      website_runner=real_website_runner,
  )
  ```

---

## Unhandled exceptions (pipeline crash)

If the pipeline raises an unhandled exception (as opposed to returning
a `FAILED_AT_*` status), the `PipelineResult` was never constructed.
The checkpoint files written before the crash are still on disk.

**What to inspect:**
- The exception traceback from the caller's error handler.
- The `agent.error` structured log event (if runners were instrumented
  with `make_logged_runner`).
- The checkpoint directory — files stop at whichever stage was running
  when the crash happened.

**Resolution:**
- Treat as a bug. The pipeline is designed to capture all agent-level
  failures as status codes and only crash on true infrastructure
  failures (disk full, network timeout, serialization error in the
  checkpoint store, etc.).
- File a bug report with the traceback and the checkpoint directory
  contents.

---

## Quick reference

| Symptom | First action |
|---|---|
| `ConfigError: GITLAB_TOKEN is required` | Set `GITLAB_TOKEN` in the environment or `.env` file. |
| `ConfigError: MPC_HOST must be 'gitlab' or 'github'` | Check the `MPC_HOST` env var for typos. |
| `ERROR: --private-token: a repository host token may contain only printable ASCII characters ...` (or the same sentence, as `InvalidRepoTokenError`, at the end of a traceback from `scripts/run_pipeline.py`) | The token has a trailing carriage return, line feed, tab or space, or a non-ASCII character. A CRLF file keeps its carriage return, and so do the `.env` loading recipes in `docs/tutorial.md` (Options B and C). Clean the value (`printf %s "$GITLAB_TOKEN" \| tr -d '\r\n '`) or convert the file to LF. This is a configuration error, not a bug. If a run **before Session 273** had such a token, see "A token leaked by a run before Session 273" under `FAILED_AT_WEBSITE`. |
| Run completes but no project on host | Check `result.status` — it may be `FAILED_AT_WEBSITE` with a descriptive `failure_reason`. |
| All checkpoints present but `status=FAILED` | Read `RepoProjectResult.result.json → failure_reason`. Usually a host-side permission issue. |
| `failure_reason` (or the `Failure:` line) holds `***`, or ends `... [N more characters not shown]` | `***` is where your access token was: the repository host, or a proxy in front of it, sent the request headers back in its reply, and the agent removed the token before it reached the screen, the `-o` file or the checkpoint. The rest of the line is the host's own message, on one line and cut at 1,000 characters. Look at what sits between you and the host (a debug gateway, an echoing proxy), and rotate the token if that party is not yours. |
| No checkpoint directory at all | The pipeline crashed before the first agent returned. Check the traceback and `agent.error` log events. |
| Tests pass locally, CI fails | Check that CI has `uv` available and runs `uv sync --extra agents --extra dev` before `pytest`. See `.github/workflows/ci.yml`. |
