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
from pathlib import Path
from typing import Any, get_args

import pytest

from model_project_constructor.agents.website import _governance_check as gc
from model_project_constructor.agents.website.agent import WebsiteAgent
from model_project_constructor.agents.website.fake_client import FakeRepoClient
from model_project_constructor.agents.website.governance_templates import (
    build_governance_files,
    build_model_registry_entry,
)
from model_project_constructor.schemas.v1.common import CycleTime, ModelType, RiskTier
from model_project_constructor.schemas.v1.data import DataReport
from model_project_constructor.schemas.v1.intake import IntakeReport
from model_project_constructor.schemas.v1.repo import RepoTarget

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


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
        emitted = {path for path in files if path.startswith("governance/")}
        entry = json.loads(files[gc.REGISTRY_PATH])
        # ``tmp_path`` holds no ``queries/``, so only the governance files are asked for.
        required = {path for path, _ in gc.required_files(entry, tmp_path)}
        assert required == emitted
