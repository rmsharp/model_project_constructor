"""The check the generated project's ``governance`` CI job runs.

The job used to run ``json.load(open('governance/model_registry.json'))``: it passed on ``{}``,
on ``[]``, on a risk tier that does not exist, and with every other governance file deleted.
``_governance_check.py`` is the source of the ``governance/check_governance.py`` the scaffold
now writes; these tests run it on real scaffolds, damage them one way at a time, and hold its
tables against the generator that writes the files it expects.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, get_args

import pytest
import yaml

from model_project_constructor.agents.website import _governance_check as gc
from model_project_constructor.agents.website.agent import WebsiteAgent
from model_project_constructor.agents.website.fake_client import FakeRepoClient
from model_project_constructor.agents.website.governance_templates import (
    build_governance_files,
    build_model_registry_entry,
    render_github_actions_ci,
    render_gitlab_ci,
    render_pre_commit_config,
)
from model_project_constructor.schemas.v1.common import CycleTime, ModelType, RiskTier
from model_project_constructor.schemas.v1.data import DataReport
from model_project_constructor.schemas.v1.intake import IntakeReport
from model_project_constructor.schemas.v1.repo import RepoTarget

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
SCRIPT = "governance/check_governance.py"


def _load(name: str) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads((FIXTURES / name).read_text())
    return loaded


def _tier4() -> dict[str, Any]:
    intake = _load("subrogation_intake.json")
    intake["governance"]["risk_tier"] = "tier_4_low"
    intake["governance"]["affects_consumers"] = False
    return intake


INTAKES = {
    "tier1": lambda: _load("tier1_intake.json"),
    "tier2": lambda: _load("tier2_intake.json"),
    "tier3": lambda: _load("subrogation_intake.json"),
    "tier4": _tier4,
}


def _generate(intake: dict[str, Any]) -> dict[str, str]:
    client = FakeRepoClient()
    result = WebsiteAgent(client, ci_platform="gitlab").run(
        IntakeReport.model_validate(intake),
        DataReport.model_validate(_load("sample_datareport.json")),
        RepoTarget(
            host_url="https://gitlab.example.com",
            namespace="data-science/model-drafts",
            project_name_hint="Governance Check",
            visibility="private",
        ),
    )
    assert result.status == "COMPLETE", result.failure_reason
    return client.get_files(result.project_id)


@pytest.fixture(scope="module", params=list(INTAKES))
def pristine(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp(request.param) / "project"
    for relative, text in _generate(INTAKES[request.param]()).items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


@pytest.fixture
def project(pristine: Path, tmp_path: Path) -> Path:
    copy = tmp_path / "project"
    shutil.copytree(pristine, copy)
    return copy


def _registry(root: Path) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads((root / gc.REGISTRY_PATH).read_text())
    return loaded


def _set_registry(root: Path, **changes: Any) -> None:
    entry = _registry(root)
    entry.update(changes)
    (root / gc.REGISTRY_PATH).write_text(json.dumps(entry), encoding="utf-8")


class TestAScaffoldPasses:
    def test_a_fresh_scaffold_has_no_problem(self, project: Path) -> None:
        assert gc.check(project) == []

    def test_an_unsupervised_model_with_no_target_passes(self, project: Path) -> None:
        _set_registry(project, target_variable=None)
        assert gc.check(project) == []

    def test_a_project_edited_down_to_a_lower_tier_passes(self, project: Path) -> None:
        # Files the old tier required stay; nothing demands they be deleted.
        _set_registry(project, risk_tier="tier_4_low", affects_consumers=False)
        assert gc.check(project) == []


class TestTheRegistry:
    def test_an_empty_object_is_missing_every_key(self, project: Path) -> None:
        # ``{}`` is falsy, and a first draft that tested ``if entry:`` passed it.
        (project / gc.REGISTRY_PATH).write_text("{}", encoding="utf-8")
        problems = gc.check(project)
        assert sum("missing key" in p for p in problems) == len(gc.REGISTRY) == 13

    @pytest.mark.parametrize("text", ["[]", '"x"', "null", "3"])
    def test_a_registry_that_is_not_an_object_is_refused(self, project: Path, text: str) -> None:
        (project / gc.REGISTRY_PATH).write_text(text, encoding="utf-8")
        assert [p for p in gc.check(project) if "top level" in p]

    def test_text_that_is_not_json_is_refused(self, project: Path) -> None:
        (project / gc.REGISTRY_PATH).write_text("{not json", encoding="utf-8")
        assert any("cannot be read as JSON" in p for p in gc.check(project))

    def test_bytes_that_are_not_text_are_refused(self, project: Path) -> None:
        (project / gc.REGISTRY_PATH).write_bytes(b"\xff\xfe\x00")
        assert any("cannot be read as JSON" in p for p in gc.check(project))

    def test_a_deleted_registry_is_missing(self, project: Path) -> None:
        (project / gc.REGISTRY_PATH).unlink()
        assert gc.check(project) == [f"{gc.REGISTRY_PATH}: missing"]

    @pytest.mark.parametrize(
        ("key", "value"),
        [
            ("risk_tier", "tier_9_unknown"),
            ("cycle_time", "weekly"),
            ("model_type", "gradient_boosting"),
        ],
    )
    def test_a_value_outside_its_vocabulary_is_refused(
        self, project: Path, key: str, value: str
    ) -> None:
        _set_registry(project, **{key: value})
        assert [p for p in gc.check(project) if key in p and "not one of" in p]

    def test_an_unknown_tier_is_one_problem_and_not_a_cascade(self, project: Path) -> None:
        # With no tier to read, nothing beyond the files every project has can be demanded.
        _set_registry(project, risk_tier="tier_9_unknown", affects_consumers=False)
        problems = gc.check(project)
        assert len(problems) == 1 and "risk_tier" in problems[0], problems

    @pytest.mark.parametrize(
        ("key", "value"),
        [
            ("affects_consumers", "yes"),
            ("uses_protected_attributes", 1),
            ("model_id", None),
            ("regulatory_frameworks", "SR_26_2"),
            ("created_at", 20260101),
        ],
    )
    def test_a_value_of_the_wrong_type_is_refused(
        self, project: Path, key: str, value: Any
    ) -> None:
        _set_registry(project, **{key: value})
        assert [p for p in gc.check(project) if key in p and "wrong type" in p]

    def test_frameworks_must_be_strings(self, project: Path) -> None:
        _set_registry(project, regulatory_frameworks=["SR_26_2", 7])
        assert [p for p in gc.check(project) if "must hold strings" in p]


class TestTheRequiredFiles:
    def test_a_registry_problem_and_a_missing_file_are_both_printed(self, project: Path) -> None:
        # "Every problem is printed": a bad registry must not hide a deleted document.
        _set_registry(project, cycle_time="weekly")
        (project / "governance" / "model_card.md").unlink()
        problems = gc.check(project)
        assert any("cycle_time" in p for p in problems)
        assert any("model_card.md: missing" in p for p in problems)

    def test_a_deleted_model_card_is_missing_at_every_tier(self, project: Path) -> None:
        (project / "governance" / "model_card.md").unlink()
        assert gc.check(project) == [
            "governance/model_card.md: missing (required: every project)"
        ]

    def test_an_empty_change_log_is_refused(self, project: Path) -> None:
        (project / "governance" / "change_log.md").write_text(" \n\n", encoding="utf-8")
        assert gc.check(project) == ["governance/change_log.md: is empty"]

    def test_a_file_that_is_not_text_is_refused_not_a_traceback(self, project: Path) -> None:
        (project / "governance" / "change_log.md").write_bytes(b"\xff\xfe\xfa")
        assert [p for p in gc.check(project) if p.startswith("governance/change_log.md: cannot")]

    def test_a_directory_in_place_of_a_file_is_missing(self, project: Path) -> None:
        card = project / "governance" / "model_card.md"
        card.unlink()
        card.mkdir()
        assert [p for p in gc.check(project) if "model_card.md: missing" in p]

    def test_a_deleted_datasheet_is_missing(self, project: Path) -> None:
        sheets = sorted((project / "data").glob("datasheet_*.md"))
        assert sheets
        sheets[0].unlink()
        problems = gc.check(project)
        assert len(problems) == 1
        assert problems[0].startswith(f"data/{sheets[0].name}: missing (required: queries/primary/")

    def test_raising_the_tier_in_the_registry_demands_the_files_it_calls_for(
        self, project: Path
    ) -> None:
        # A tier-1 project needs the LCP integration and the audit log; edit any lower-tier
        # project up to tier 1 and the check asks for them.
        already_tier_1 = _registry(project)["risk_tier"] == "tier_1_critical"
        _set_registry(project, risk_tier="tier_1_critical")
        problems = gc.check(project)
        if already_tier_1:
            assert problems == []
            return
        assert (
            "governance/lcp_integration.md: missing (required: risk_tier is tier_1_critical)"
            in problems
        )
        assert any("audit_log/README.md: missing" in p for p in problems)

    def test_consumer_facing_models_need_the_eu_ai_act_file(self, project: Path) -> None:
        _set_registry(project, affects_consumers=True)
        eu_ai_act = project / "governance" / "eu_ai_act_compliance.md"
        eu_ai_act.unlink(missing_ok=True)
        assert [p for p in gc.check(project) if "eu_ai_act_compliance.md: missing" in p]

    def test_a_consumer_flag_that_is_not_a_boolean_requires_nothing_extra(
        self, project: Path
    ) -> None:
        # ``"yes"`` is refused by the registry check; it must not also be read as true.
        _set_registry(project, affects_consumers="yes")
        (project / "governance" / "eu_ai_act_compliance.md").unlink(missing_ok=True)
        assert [p for p in gc.check(project) if "eu_ai_act" in p] == []


class TestAQueryWithAnEmptyName:
    """The generator writes ``unnamed.sql`` and ``datasheet_unnamed.md`` for it.

    It wrote ``queries/primary/.sql`` and ``data/datasheet_.md`` until Session 296
    (``_file_stems``). A hand-made project can still hold the first, and the check must agree
    with it, so the unit test below keeps building that tree itself.
    """

    def test_the_check_asks_for_the_datasheet_the_generator_wrote(self, tmp_path: Path) -> None:
        primary = tmp_path / "queries" / "primary"
        primary.mkdir(parents=True)
        (primary / ".sql").write_text("select 1\n", encoding="utf-8")
        assert gc.required_files({}, tmp_path)[-1] == (
            "data/datasheet_.md",
            "queries/primary/.sql exists",
        )

    def test_a_scaffold_with_such_a_query_passes_its_own_check(self, tmp_path: Path) -> None:
        data = _load("sample_datareport.json")
        data["primary_queries"][0]["name"] = ""
        intake = _load("subrogation_intake.json")
        client = FakeRepoClient()
        result = WebsiteAgent(client, ci_platform="gitlab").run(
            IntakeReport.model_validate(intake),
            DataReport.model_validate(data),
            RepoTarget(
                host_url="https://gitlab.example.com",
                namespace="ns",
                project_name_hint="Empty Name",
                visibility="private",
            ),
        )
        assert result.status == "COMPLETE", result.failure_reason
        files = client.get_files(result.project_id)
        assert "data/datasheet_unnamed.md" in files and "queries/primary/unnamed.sql" in files
        assert "data/datasheet_.md" not in files and "queries/primary/.sql" not in files
        for relative, text in files.items():
            (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / relative).write_text(text, encoding="utf-8")
        assert gc.check(tmp_path) == []


class TestTheTablesFollowTheGenerator:
    """A tier table copied into the generated script is a second copy; these check it."""

    def test_the_vocabularies_are_the_schemas(self) -> None:
        assert get_args(RiskTier) == gc.RISK_TIERS
        assert get_args(CycleTime) == gc.CYCLE_TIMES
        assert get_args(ModelType) == gc.MODEL_TYPES

    def test_the_registry_keys_are_the_ones_the_generator_writes(self) -> None:
        entry = build_model_registry_entry(
            intake=_load("tier1_intake.json"), project_name="p", project_slug="p"
        )
        assert set(gc.REGISTRY) == set(entry)

    @pytest.mark.parametrize("tier", get_args(RiskTier))
    @pytest.mark.parametrize("consumers", [True, False])
    def test_the_files_it_requires_are_exactly_the_governance_files_emitted(
        self, tier: str, consumers: bool, tmp_path: Path
    ) -> None:
        intake = _load("subrogation_intake.json")
        intake["governance"]["risk_tier"] = tier
        intake["governance"]["affects_consumers"] = consumers
        files = build_governance_files(
            intake=intake,
            data=_load("sample_datareport.json"),
            project_name="p",
            project_slug="p",
        )
        # The script is emitted into ``governance/`` and does not require itself.
        emitted = {path for path in files if path.startswith("governance/")} - {SCRIPT}
        assert SCRIPT in files
        entry = json.loads(files[gc.REGISTRY_PATH])
        # ``tmp_path`` holds no ``queries/``, so only the governance files are asked for.
        required = {path for path, _ in gc.required_files(entry, tmp_path)}
        assert required == emitted


def _run_script(root: Path, *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run the scaffold's own copy the way a CI job does: ``python <path>``, isolated."""
    target = SCRIPT if cwd is None else str(root / SCRIPT)
    return subprocess.run(
        [sys.executable, "-I", target],
        cwd=cwd or root,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


class TestTheScaffoldWritesAndRunsIt:
    def test_the_scaffold_writes_the_module_source_unchanged(self, pristine: Path) -> None:
        assert (pristine / SCRIPT).read_text() == Path(gc.__file__).read_text()

    def test_run_as_the_job_runs_it_a_fresh_scaffold_passes(self, pristine: Path) -> None:
        done = _run_script(pristine)
        assert done.returncode == 0, done.stdout + done.stderr
        assert done.stdout.strip().endswith("governance check: 0 problem(s)")

    def test_run_as_the_job_runs_it_a_damaged_scaffold_fails(self, project: Path) -> None:
        (project / "governance" / "model_card.md").unlink()
        done = _run_script(project)
        assert done.returncode == 1, done.stdout + done.stderr
        assert "governance/model_card.md: missing" in done.stdout
        assert done.stdout.strip().endswith("governance check: 1 problem(s)")

    def test_a_registry_that_is_an_empty_object_fails_the_job(self, project: Path) -> None:
        # What the old one-line check passed.
        (project / gc.REGISTRY_PATH).write_text("{}", encoding="utf-8")
        assert _run_script(project).returncode == 1

    def test_it_reads_the_project_it_sits_in_not_the_working_directory(
        self, project: Path, tmp_path: Path
    ) -> None:
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        done = _run_script(project, cwd=elsewhere)
        assert done.returncode == 0, done.stdout + done.stderr


class TestEveryCallerRunsIt:
    COMMAND = "uv run python governance/check_governance.py"

    def test_the_gitlab_job_runs_it(self) -> None:
        job = yaml.safe_load(render_gitlab_ci())["model-registry-schema"]
        assert job["script"] == [self.COMMAND]

    def test_the_github_job_runs_it(self) -> None:
        steps = yaml.safe_load(render_github_actions_ci())["jobs"]["governance"]["steps"]
        assert self.COMMAND in [step.get("run") for step in steps]

    def test_the_pre_commit_hook_runs_it_in_an_environment_that_has_python(self) -> None:
        config = yaml.safe_load(render_pre_commit_config())
        (hook,) = [h for repo in config["repos"] if repo["repo"] == "local" for h in repo["hooks"]]
        # ``language: system`` ran a bare ``python``, which does not exist on a machine that
        # has only ``python3``; ``language: python`` gives the hook its own environment.
        assert hook["language"] == "python"
        assert hook["entry"] == "python governance/check_governance.py"
        # The script reads the whole record, not the files staged.
        assert hook["pass_filenames"] is False

    def test_the_hook_runs_on_every_commit_so_a_deletion_is_seen(self) -> None:
        # pre-commit never hands a deleted path to a hook, so a ``files`` filter skips a commit
        # that only deletes a governance document, which is the case the check exists for. The
        # script costs milliseconds and reads the whole record, so it runs every time.
        config = yaml.safe_load(render_pre_commit_config())
        (hook,) = [h for repo in config["repos"] if repo["repo"] == "local" for h in repo["hooks"]]
        assert hook["always_run"] is True
        assert "files" not in hook

    def test_neither_job_can_pass_when_the_check_fails(self) -> None:
        # An advisory or manual or conditional job would restore the old behaviour: green
        # whatever the record holds.
        gitlab = yaml.safe_load(render_gitlab_ci())["model-registry-schema"]
        for key in ("allow_failure", "when", "rules", "only", "except", "needs"):
            assert key not in gitlab, key
        github = yaml.safe_load(render_github_actions_ci())["jobs"]["governance"]
        for key in ("continue-on-error", "if", "needs"):
            assert key not in github, key
        for step in github["steps"]:
            assert "continue-on-error" not in step and "if" not in step, step
