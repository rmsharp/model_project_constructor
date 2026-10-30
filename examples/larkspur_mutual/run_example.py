"""Run the whole Larkspur example, keyless, onto the in-memory fake repository.

From the repository root::

    uv run python examples/larkspur_mutual/run_example.py

1. the interview: the real intake web UI, driven over HTTP (``drive_interview.py``);
2. the claims database: fictitious and generated (``make_synthetic_db.py``);
3. the pipeline: the shipped orchestrator, with the saved ``IntakeReport`` as the intake
   stage, the shipped ``DataAgent`` (a scripted stand-in for its model, real SQL against the
   database) as the data stage, and the shipped ``WebsiteAgent`` writing to an in-memory
   repository as the website stage.

Nothing here calls a language model or a repository host, reads a key, or leaves the
machine. The scaffolded project is written to ``out/project/`` so you can open it.

``scripts/run_pipeline.py`` cannot do step 3 for you: none of its flags accepts an
``IntakeReport`` from a real interview, so this uses the programmatic API, the same
``run_pipeline`` call that script wraps.
"""

from __future__ import annotations

import shutil
import sys

import drive_interview
import make_synthetic_db
from scripted_data_llm import ScriptedDataLLM

from model_project_constructor.agents.data import DataAgent
from model_project_constructor.agents.data.db import ReadOnlyDB
from model_project_constructor.agents.website.agent import WebsiteAgent
from model_project_constructor.agents.website.fake_client import FakeRepoClient
from model_project_constructor.orchestrator import PipelineConfig, run_pipeline
from model_project_constructor.schemas.v1.intake import IntakeReport
from model_project_constructor.schemas.v1.repo import RepoTarget

OUT = make_synthetic_db.OUT
RUN_ID = "larkspur_tl_fnol_keyless"
# Figures the datasheets in scripted_data_llm.py quote, typed by hand. A database that no
# longer matches them (a changed seed, or a platform whose floating point differs) would make
# the generated datasheets state false numbers, so the run stops instead of writing them.
DATASHEET_FIGURES = {
    "claims": 40_000,
    "training_rows": 37_600,
    "closed_total_losses": 3_517,
    "open_claims": 760,
    "planted_acv_zero": 173,
    "planted_drivable_null": 1_226,
    "planted_decision_before_fnol": 9,
}
NOTICE = """\
# This project is an example, not a real project

* **Larkspur Mutual is fictional.** The company, the people, the interview and every
  number in this project were invented. The data is generated, not real.
* **The interview, the SQL, the quality checks and the datasheets were written in advance**
  (drafted with an AI coding assistant working with the operator) and replayed by stand-ins
  for the pipeline's language model. The pipeline's own model wrote none of it. The three
  failed quality checks are the three data problems the author planted and wrote checks for.
* **This project's own tests fail out of the box (8 of 8)** and its CI would fail with them:
  four tests import a module literally named `<project_slug>` (a placeholder the
  scaffold did not fill in), and four put `pass` inside `pytest.raises`. That is a defect in
  the scaffold this tool wrote, recorded in the example's README, not something you did.
* Produced by `examples/larkspur_mutual/run_example.py` in the Model Project Constructor
  repository, with the in-memory repository client. Nothing was created on any host.
"""
TARGET = RepoTarget(
    host_url="https://fake.host.test",
    namespace="larkspur-claims-analytics",
    project_name_hint="total_loss_fnol_pilot",
    visibility="private",
)


def main() -> int:
    print("1. Interview (the intake web UI, keyless, over HTTP):")
    report_path = drive_interview.run(OUT)
    intake = IntakeReport.model_validate_json(report_path.read_text())

    print("\n2. Claims database (fictitious, generated):")
    figures = make_synthetic_db.build(OUT / "larkspur_claims.db")
    stale = {
        name: (expected, figures[name])
        for name, expected in DATASHEET_FIGURES.items()
        if figures[name] != expected
    }
    if stale:
        for name, (expected, actual) in stale.items():
            print(f"  STALE: datasheets say {name} = {expected:,}; the database has {actual:,.0f}")
        print("  Update scripted_data_llm.py and DATASHEET_FIGURES, then re-run.")
        return 1
    print(
        f"  {int(figures['claims']):,} claims, "
        f"{figures['total_loss_rate_of_closed']:.2%} of closed claims are total losses, "
        f"median {figures['median_days_to_decision']} days to the decision"
    )

    print("\n3. Pipeline (shipped orchestrator, DataAgent and WebsiteAgent; fake repository):")
    checkpoints = OUT / "checkpoints"
    shutil.rmtree(checkpoints / RUN_ID, ignore_errors=True)  # a finished run cannot be re-run
    client = FakeRepoClient()
    data_agent = DataAgent(ScriptedDataLLM(), ReadOnlyDB(f"sqlite:///{OUT / 'larkspur_claims.db'}"))
    website_agent = WebsiteAgent(client, ci_platform="gitlab")
    result = run_pipeline(
        PipelineConfig(run_id=RUN_ID, repo_target=TARGET, checkpoint_dir=checkpoints),
        intake_runner=lambda: intake,
        data_runner=data_agent.run,
        website_runner=website_agent.run,
    )
    print(f"  status:  {result.status}")
    print(f"  project: {result.project_url}")
    if result.data_report is not None:
        checks = [qc for pq in result.data_report.primary_queries for qc in pq.quality_checks]
        passed = sum(qc.execution_status == "PASSED" for qc in checks)
        failed = sum(qc.execution_status == "FAILED" for qc in checks)
        print(f"  data:    {len(checks)} quality checks run, {passed} passed, {failed} failed")
    if result.failure_reason:
        print(f"  failure: {result.failure_reason}")
    if result.status != "COMPLETE":
        return 1

    project = next(iter(client.projects.values()))
    target = OUT / "project"
    shutil.rmtree(target, ignore_errors=True)
    for path, content in project.files.items():
        destination = target / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content)
    (target / "EXAMPLE_NOTICE.md").write_text(NOTICE)  # on disk only; not in the repository client
    print(
        f"\nThe scaffolded project ({len(project.files)} files, plus EXAMPLE_NOTICE.md) "
        f"is in {target}"
    )
    print(f"Checkpoints: {checkpoints / RUN_ID}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
