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
    print(f"\nThe scaffolded project ({len(project.files)} files) is in {target}")
    print(f"Checkpoints: {checkpoints / RUN_ID}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
