"""Tests for the website agent's base-scaffolding templates."""

from __future__ import annotations

import ast
import itertools
from typing import Any

import pytest

from model_project_constructor.agents.website.templates import (
    _STUB_CALLS,
    _str_list_literal,
    build_base_files,
    derive_project_name,
    derive_project_slug,
    render_data_loading,
    render_data_readme,
    render_evaluation,
    render_features,
    render_gitignore,
    render_license,
    render_models,
    render_pyproject,
    render_qmd_business_understanding,
    render_qmd_data,
    render_qmd_extensions,
    render_qmd_feature_engineering,
    render_qmd_implementation_plan,
    render_qmd_initial_models,
    render_readme,
    render_reports_data_md,
    render_reports_intake_md,
    render_test_stub,
)
from model_project_constructor.schemas.v1.data import DataReport
from model_project_constructor.schemas.v1.intake import IntakeReport
from tests.agents.website.hostile_names import HOSTILE_IDS, HOSTILE_VALUES


class TestProjectNameDerivation:
    def test_basic_lowercasing(self) -> None:
        assert derive_project_name("Subrogation Model") == "subrogation-model"

    def test_strips_punctuation(self) -> None:
        assert derive_project_name("  Claims -- Triage!  ") == "claims-triage"

    def test_collapses_runs(self) -> None:
        assert derive_project_name("foo___bar...baz") == "foo-bar-baz"

    def test_empty_input_fallback(self) -> None:
        assert derive_project_name("") == "model-project"
        assert derive_project_name("---") == "model-project"


class TestProjectSlugDerivation:
    def test_dashes_to_underscores(self) -> None:
        assert derive_project_slug("subrogation-model") == "subrogation_model"

    def test_strips_invalid_chars(self) -> None:
        assert derive_project_slug("foo-bar!@baz") == "foo_bar_baz"

    def test_leading_digit_prefixed(self) -> None:
        # A project name starting with a digit isn't a valid python identifier
        assert derive_project_slug("123-model").startswith("m_")

    def test_empty_fallback(self) -> None:
        assert derive_project_slug("") == "model_project"


class TestIndividualRenderers:
    def test_gitignore_has_python_and_quarto(self) -> None:
        out = render_gitignore()
        assert "__pycache__/" in out
        assert "_site/" in out
        assert "*.parquet" in out

    def test_readme_surfaces_business_problem(
        self, intake_report: IntakeReport
    ) -> None:
        intake = intake_report.model_dump(mode="json")
        readme = render_readme(intake=intake, project_name="foo-bar")
        assert "# foo-bar" in readme
        assert "Subrogation recovery dropped" in readme
        assert "stakeholder_claims_001" in readme
        assert "## License" in readme
        assert "LICENSE" in readme

    def test_readme_lists_queries_and_datasheets_only_when_the_report_has_queries(
        self, intake_report: IntakeReport
    ) -> None:
        intake = intake_report.model_dump(mode="json")
        queries = {"primary_queries": [{"name": "q1"}]}
        with_queries = render_readme(intake=intake, project_name="p", data=queries)
        assert "- `queries/` —" in with_queries
        assert "datasheet" in with_queries
        for data in (None, {}, {"primary_queries": []}):
            readme = render_readme(intake=intake, project_name="p", data=data)
            assert "`queries/`" not in readme
            assert "datasheet" not in readme
            assert "- `data/` — data dictionary.\n" in readme

    def test_readme_does_not_defer_governance_to_a_later_phase(
        self, intake_report: IntakeReport
    ) -> None:
        readme = render_readme(intake=intake_report.model_dump(mode="json"), project_name="p")
        assert "Phase" not in readme
        assert "- `governance/` — governance artifacts proportional" in readme

    def test_extensions_notebook_names_the_fairness_package_with_the_slug(self) -> None:
        intake = {"governance": {"uses_protected_attributes": True}}
        text = render_qmd_extensions(intake=intake, project_slug="renewal_pricing")
        assert "`src/renewal_pricing/fairness/`" in text
        assert "`analysis/fairness_audit.qmd`" in text
        assert "src/fairness/" not in text
        assert "Phase" not in text

    def test_extensions_notebook_names_no_fairness_path_without_protected_attributes(
        self,
    ) -> None:
        unflagged: list[dict[str, Any]] = [
            {},
            {"governance": {}},
            {"governance": {"uses_protected_attributes": False}},
        ]
        for intake in unflagged:
            text = render_qmd_extensions(intake=intake, project_slug="renewal_pricing")
            assert "fairness/" not in text
            assert "fairness_audit" not in text
            assert "no fairness scaffold was generated" in text
            assert "Phase" not in text

    def test_data_readme_promises_a_datasheet_per_query_and_none_without_queries(self) -> None:
        data = {"primary_queries": [{"name": "alpha"}, {"purpose": "no name given"}]}
        text = render_data_readme(data=data)
        assert "`datasheet_alpha.md`" in text
        assert "`datasheet_unnamed.md`" in text
        assert "Phase" not in text
        for empty in ({}, {"primary_queries": []}):
            assert "datasheet" not in render_data_readme(data=empty)

    def test_license_is_proprietary_placeholder_not_a_known_license(
        self, intake_report: IntakeReport
    ) -> None:
        intake = intake_report.model_dump(mode="json")
        out = render_license(intake=intake, project_name="foo-bar")
        assert "PROPRIETARY AND CONFIDENTIAL" in out
        assert "stakeholder_claims_001" in out
        assert "Legal" in out
        # Must not resemble a real open-source grant (MIT, Apache, etc.) that
        # SPDX/license-detection tooling could mistake for a real license.
        assert "Permission is hereby granted" not in out
        assert "MIT" not in out

    def test_pyproject_uses_slug_for_wheel(self) -> None:
        out = render_pyproject(project_name="foo-bar", project_slug="foo_bar")
        assert 'name = "foo-bar"' in out
        assert 'packages = ["src/foo_bar"]' in out

    def test_data_loading_lists_primary_queries(self) -> None:
        out = render_data_loading(
            project_slug="foo_bar",
            primary_query_names=["alpha", "beta"],
        )
        assert '"alpha"' in out
        assert '"beta"' in out
        assert "NotImplementedError" in out
        assert "Wire up SQLAlchemy" in out

    def test_models_embeds_declared_model_type(
        self, intake_report: IntakeReport
    ) -> None:
        intake = intake_report.model_dump(mode="json")
        out = render_models(intake=intake)
        assert "supervised_classification" in out
        assert "NotImplementedError" in out

    def test_evaluation_lists_requested_metrics(
        self, intake_report: IntakeReport
    ) -> None:
        intake = intake_report.model_dump(mode="json")
        out = render_evaluation(intake=intake)
        assert '"AUC"' in out
        assert '"precision_at_top_decile"' in out

    def test_evaluation_handles_missing_metrics(self) -> None:
        out = render_evaluation(intake={"model_solution": {}})
        assert "REQUESTED_METRICS" in out

    def test_qmd_business_uses_narrative(
        self, intake_report: IntakeReport
    ) -> None:
        intake = intake_report.model_dump(mode="json")
        out = render_qmd_business_understanding(intake=intake)
        assert "## Business Problem" in out
        assert "## Proposed Solution" in out
        assert "Subrogation recovery dropped" in out

    def test_qmd_business_renders_business_case(
        self, intake_report: IntakeReport
    ) -> None:
        intake = intake_report.model_dump(mode="json")
        out = render_qmd_business_understanding(intake=intake)
        # All seven business-case sections are present...
        for heading in (
            "## Annual Impact Band",
            "## Cost of Inaction",
            "## Implementation Cost",
            "## Payback",
            "## Value Drivers",
            "## Assumptions",
            "## Decision Rights",
        ):
            assert heading in out
        # ...populated with the intake's figures.
        assert "$2,000,000 – $4,000,000 per year" in out
        assert "$250,000 – $500,000" in out
        assert "4 months" in out
        assert "improved_subrogation_recovery_rate" in out
        assert "Claims VP + Data Science lead" in out

    def test_qmd_business_missing_fields_render_placeholders(self) -> None:
        # A sparse intake (no estimated_value, no value_measurement_plan)
        # still yields a structurally complete business case.
        out = render_qmd_business_understanding(intake={})
        assert "## Cost of Inaction" in out
        assert "## Decision Rights" in out
        assert "(not estimated)" in out
        assert "- (none declared)" in out
        assert "(not specified)" in out

    def test_qmd_data_lists_queries(self, data_report: DataReport) -> None:
        data = data_report.model_dump(mode="json")
        out = render_qmd_data(data=data, project_slug="foo_bar")
        assert "subrogation_training_set" in out
        assert "queries/primary/subrogation_training_set.sql" in out
        assert "# from foo_bar.data_loading import load_primary" in out

    def test_qmd_initial_models_includes_metrics(
        self, intake_report: IntakeReport
    ) -> None:
        intake = intake_report.model_dump(mode="json")
        out = render_qmd_initial_models(intake=intake, project_slug="foo_bar")
        assert "AUC" in out
        assert "supervised_classification" in out
        assert "# from foo_bar.models import train, predict" in out

    def test_qmd_feature_engineering_names_the_package(self) -> None:
        out = render_qmd_feature_engineering(project_slug="foo_bar")
        assert "``src/foo_bar/features.py``" in out
        assert "# from foo_bar.features import build_feature_matrix" in out

    def test_qmd_implementation_plan_formats_dollar_range(
        self, intake_report: IntakeReport, data_report: DataReport
    ) -> None:
        intake = intake_report.model_dump(mode="json")
        data = data_report.model_dump(mode="json")
        out = render_qmd_implementation_plan(intake=intake, data=data)
        assert "$2,000,000" in out
        assert "$4,000,000" in out

    def test_qmd_implementation_plan_handles_missing_estimate(self) -> None:
        out = render_qmd_implementation_plan(
            intake={"estimated_value": {}}, data={}
        )
        assert "not estimated" in out
        assert "(none declared)" in out

    def test_qmd_implementation_plan_renders_production_measurement_plan(
        self, intake_report: IntakeReport, data_report: DataReport
    ) -> None:
        intake = intake_report.model_dump(mode="json")
        data = data_report.model_dump(mode="json")
        out = render_qmd_implementation_plan(intake=intake, data=data)

        # Every Production Measurement Plan section is present.
        for heading in (
            "## Production Measurement Plan",
            "## Baseline",
            "## Counterfactual Design",
            "## Attribution Method",
            "## Evaluation Horizon",
            "## Logging Requirements",
            "## Review Cadence",
            "## Success Criteria",
            "## Decision Rights",
        ):
            assert heading in out

        # Baseline value is interpolated from DataReport.baseline_snapshot
        # with a citation footnote (operator-selected rendering).
        assert "subrogation_recovery_rate" in out
        assert "0.41 ratio" in out
        assert "[^baseline-src]: Baseline figures are sourced from" in out
        assert "`EXECUTED`" in out
        assert "2024-01-01 → 2024-12-31" in out
        # Methodology fields from the intake's ValueMeasurementPlan.
        assert "champion_challenger" in out
        assert "6 months" in out
        assert "claim_id" in out
        # The Phase-5 structured plan replaces the old TODO scaffold.
        assert "intentionally sparse" not in out

    def test_qmd_implementation_plan_missing_plan_renders_placeholders(
        self,
    ) -> None:
        out = render_qmd_implementation_plan(intake={}, data={})

        # Sections still render even with no value_measurement_plan / snapshot.
        assert "## Production Measurement Plan" in out
        assert "## Baseline" in out
        assert "## Decision Rights" in out
        assert "No baseline snapshot was collected by the Data Agent" in out
        assert "none_declared" in out
        assert "(not specified)" in out
        # No baseline value → no interpolated figure and no footnote.
        assert "[^baseline-src]" not in out
        assert "intentionally sparse" not in out

    def test_qmd_implementation_plan_baseline_collected_but_not_measured(
        self,
    ) -> None:
        # A baseline snapshot exists but the SQL did not yield a value
        # (Phase-3 FAILED / NOT_EXECUTED path) — the section still renders.
        data = {
            "baseline_snapshot": {
                "metric_name": "subrogation_recovery_rate",
                "value": None,
                "measurement_unit": "ratio",
                "query_execution_status": "FAILED",
                "caveats": [],
            }
        }
        out = render_qmd_implementation_plan(intake={}, data=data)
        assert "## Baseline" in out
        assert "(not measured) [^baseline-src]" in out
        assert "`FAILED`" in out
        # No measurement window recorded → placeholder, not a date range.
        assert "(not recorded)" in out
        # The provenance footnote is still emitted for a present snapshot.
        assert "[^baseline-src]: Baseline figures are sourced from" in out

    def test_intake_report_md_renders_governance(
        self, intake_report: IntakeReport
    ) -> None:
        intake = intake_report.model_dump(mode="json")
        out = render_reports_intake_md(intake=intake)
        assert "tier_3_moderate" in out
        assert "tactical" in out
        assert "SR_26_2" in out

    def test_intake_report_md_renders_business_case(
        self, intake_report: IntakeReport
    ) -> None:
        intake = intake_report.model_dump(mode="json")
        out = render_reports_intake_md(intake=intake)
        assert "## Cost of Inaction" in out
        assert "## Payback" in out
        assert "## Decision Rights" in out
        assert "$250,000 – $500,000" in out
        # The business case sits between Estimated Value and Governance.
        assert out.index("## Cost of Inaction") < out.index("## Governance")

    def test_intake_report_md_missing_fields_render_placeholders(self) -> None:
        out = render_reports_intake_md(intake={})
        assert "## Value Drivers" in out
        assert "- (none declared)" in out
        assert "(not specified)" in out
        # The Governance section still renders after the business case.
        assert "## Governance" in out

    def test_data_report_md_lists_expectations(
        self, data_report: DataReport
    ) -> None:
        data = data_report.model_dump(mode="json")
        out = render_reports_data_md(data=data)
        assert "Row count in the millions" in out
        assert "Information_completeness_score" in out


class TestBuildBaseFiles:
    def test_returns_expected_file_set(
        self,
        intake_report: IntakeReport,
        data_report: DataReport,
    ) -> None:
        files = build_base_files(
            intake=intake_report.model_dump(mode="json"),
            data=data_report.model_dump(mode="json"),
            project_name="subrogation-model",
            project_slug="subrogation_model",
        )

        expected = {
            ".gitignore",
            "README.md",
            "LICENSE",
            "pyproject.toml",
            "src/subrogation_model/__init__.py",
            "src/subrogation_model/data_loading.py",
            "src/subrogation_model/features.py",
            "src/subrogation_model/models.py",
            "src/subrogation_model/evaluation.py",
            "analysis/01_business_understanding.qmd",
            "analysis/02_data.qmd",
            "analysis/03_eda.qmd",
            "analysis/04_feature_engineering.qmd",
            "analysis/05_initial_models.qmd",
            "analysis/06_implementation_plan.qmd",
            "analysis/99_extensions.qmd",
            "tests/__init__.py",
            "tests/test_data_loading.py",
            "tests/test_features.py",
            "tests/test_models.py",
            "tests/test_evaluation.py",
            "data/README.md",
            "reports/intake_report.json",
            "reports/intake_report.md",
            "reports/data_report.json",
            "reports/data_report.md",
            "queries/primary/subrogation_training_set.sql",
            "queries/quality/subrogation_training_set/row_count_sanity.sql",
            "queries/quality/subrogation_training_set/target_nullability.sql",
        }
        assert expected <= set(files.keys())
        # Phase 4A MUST NOT emit governance artifacts yet
        for path in files:
            assert not path.startswith("governance/")
        assert "data/datasheet_subrogation_training_set.md" not in files
        assert ".gitlab-ci.yml" not in files
        assert ".pre-commit-config.yaml" not in files

    def test_primary_query_contents_match_sql(
        self,
        intake_report: IntakeReport,
        data_report: DataReport,
    ) -> None:
        files = build_base_files(
            intake=intake_report.model_dump(mode="json"),
            data=data_report.model_dump(mode="json"),
            project_name="subrogation-model",
            project_slug="subrogation_model",
        )
        sql = files["queries/primary/subrogation_training_set.sql"]
        assert "FROM claims_dw.public.claims" in sql
        assert sql.endswith("\n")

    def test_quality_check_contents_match(
        self,
        intake_report: IntakeReport,
        data_report: DataReport,
    ) -> None:
        files = build_base_files(
            intake=intake_report.model_dump(mode="json"),
            data=data_report.model_dump(mode="json"),
            project_name="subrogation-model",
            project_slug="subrogation_model",
        )
        row_count = files[
            "queries/quality/subrogation_training_set/row_count_sanity.sql"
        ]
        assert "SELECT COUNT(*)" in row_count

    def test_reports_json_round_trips_through_pydantic(
        self,
        intake_report: IntakeReport,
        data_report: DataReport,
    ) -> None:
        import json

        files = build_base_files(
            intake=intake_report.model_dump(mode="json"),
            data=data_report.model_dump(mode="json"),
            project_name="subrogation-model",
            project_slug="subrogation_model",
        )
        intake_json: Any = json.loads(files["reports/intake_report.json"])
        assert intake_json["status"] == "COMPLETE"
        data_json: Any = json.loads(files["reports/data_report.json"])
        assert data_json["status"] == "COMPLETE"

    def test_empty_data_report_yields_no_query_files(
        self, intake_report: IntakeReport
    ) -> None:
        empty_data = {
            "status": "COMPLETE",
            "summary": "",
            "primary_queries": [],
            "confirmed_expectations": [],
            "unconfirmed_expectations": [],
            "data_quality_concerns": [],
        }
        files = build_base_files(
            intake=intake_report.model_dump(mode="json"),
            data=empty_data,
            project_name="p",
            project_slug="p",
        )
        assert not any(path.startswith("queries/") for path in files)


class TestScaffoldedStubTests:
    """``tests/test_<module>.py`` calls every stub the scaffold writes, so none can drift."""

    @staticmethod
    def _module_sources() -> dict[str, str]:
        return {
            "data_loading": render_data_loading(project_slug="foo_bar", primary_query_names=[]),
            "features": render_features(),
            "models": render_models(intake={}),
            "evaluation": render_evaluation(intake={}),
        }

    def test_every_scaffolded_stub_is_called_by_its_test(self) -> None:
        sources = self._module_sources()
        assert set(_STUB_CALLS) == set(sources)
        for module, source in sources.items():
            called = [name for name, _ in _STUB_CALLS[module]]
            for name in called:
                assert f"def {name}(" in source, (module, name)
            # One ``raise NotImplementedError`` per stub, and no stub that is not called.
            assert source.count("raise NotImplementedError") == len(called), module

    def test_base_files_write_one_test_per_scaffolded_module(self) -> None:
        files = build_base_files(
            intake={}, data={}, project_name="foo-bar", project_slug="foo_bar"
        )
        written = {p for p in files if p.startswith("tests/test_")}
        assert written == {f"tests/test_{module}.py" for module in _STUB_CALLS}

    def test_the_test_imports_the_real_package_and_calls_each_stub(self) -> None:
        out = render_test_stub("models", "foo_bar")
        assert out.count("    import foo_bar.models as module\n") == 2
        assert "<" not in out
        assert "pass" not in out
        assert out.count("pytest.raises(NotImplementedError)") == 2
        assert "module.train(None, None)" in out
        assert "module.predict(None, None)" in out

    def test_the_package_name_appears_only_in_import_statements(self) -> None:
        # An import statement cannot be wrapped by ``ruff format``, so the output stays
        # format-stable whatever the slug's length; a string constant was not (slugs of 77 to
        # 82 characters), which ``test_scaffold_runs`` measures over every length.
        short = render_test_stub("features", "a").splitlines()
        long = render_test_stub("features", "a_much_longer_slug").splitlines()
        assert len(short) == len(long)
        differing = [i for i, (x, y) in enumerate(zip(short, long, strict=True)) if x != y]
        assert [short[i] for i in differing] == ["    import a.features as module"] * 2


class TestEmptyListsAreWrittenAsRuffFormatsThem:
    """``[`` newline ``]`` is rewritten to ``[]`` by the ``ruff-format`` hook the scaffold ships."""

    def test_no_primary_queries(self) -> None:
        out = render_data_loading(project_slug="foo_bar", primary_query_names=[])
        assert "PRIMARY_QUERY_NAMES: list[str] = []\n" in out

    def test_no_evaluation_metrics(self) -> None:
        out = render_evaluation(intake={"model_solution": {}})
        assert "REQUESTED_METRICS: list[str] = []\n" in out

    def test_a_non_empty_list_stays_one_item_per_line_with_a_trailing_comma(self) -> None:
        out = render_data_loading(project_slug="foo_bar", primary_query_names=["a", "b"])
        assert 'PRIMARY_QUERY_NAMES: list[str] = [\n    "a",\n    "b",\n]\n' in out


def _assigned(source: str, name: str) -> Any:
    """The value of the module-level ``name: ... = <literal>`` in ``source``, evaluated safely."""

    for node in ast.parse(source).body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
        ):
            assert node.value is not None
            return ast.literal_eval(node.value)
    raise AssertionError(f"{name} is not assigned in:\n{source}")


class TestNamesAreWrittenAsPythonStrings:
    """A metric or query name is any string; the list it lands in must say exactly that string.

    Session 293's review: ``f'"{item}"'`` made a double quote, a newline or a NUL a syntax
    error, changed a backslash, split ``a", "b`` into two items and ran ``a"+str(1+1)+"b`` when
    the generated module was imported, and the run still ended ``COMPLETE``.
    """

    @pytest.mark.parametrize("value", HOSTILE_VALUES, ids=HOSTILE_IDS)
    def test_a_metric_comes_back_as_the_same_string(self, value: str) -> None:
        metrics = ["first", value, "last"]
        out = render_evaluation(intake={"model_solution": {"evaluation_metrics": metrics}})
        assert _assigned(out, "REQUESTED_METRICS") == metrics

    @pytest.mark.parametrize("value", HOSTILE_VALUES, ids=HOSTILE_IDS)
    def test_a_query_name_comes_back_as_the_same_string(self, value: str) -> None:
        names = ["first", value, "last"]
        out = render_data_loading(project_slug="foo_bar", primary_query_names=names)
        assert _assigned(out, "PRIMARY_QUERY_NAMES") == names

    @pytest.mark.parametrize("value", HOSTILE_VALUES, ids=HOSTILE_IDS)
    def test_nothing_unprintable_reaches_the_file(self, value: str) -> None:
        """A NUL, an escape, a separator or a lone surrogate is written as its escape."""

        outs = [
            render_evaluation(intake={"model_solution": {"evaluation_metrics": [value]}}),
            render_data_loading(project_slug="foo_bar", primary_query_names=[value]),
        ]
        for out in outs:
            assert all(char.isprintable() or char == "\n" for char in out)
            out.encode("utf-8")  # a lone surrogate would raise here

    @pytest.mark.parametrize("value", HOSTILE_VALUES, ids=HOSTILE_IDS)
    def test_every_python_file_of_the_scaffold_parses(
        self, intake_report: IntakeReport, data_report: DataReport, value: str
    ) -> None:
        intake = intake_report.model_dump(mode="json")
        intake["model_solution"]["evaluation_metrics"] = [value]
        data = data_report.model_dump(mode="json")
        data["primary_queries"][0]["name"] = value
        files = build_base_files(
            intake=intake,
            data=data,
            project_name="subrogation-model",
            project_slug="subrogation_model",
        )
        for path, text in files.items():
            if path.endswith(".py"):
                ast.parse(text)
        evaluation = files["src/subrogation_model/evaluation.py"]
        loading = files["src/subrogation_model/data_loading.py"]
        assert _assigned(evaluation, "REQUESTED_METRICS") == [value]
        assert _assigned(loading, "PRIMARY_QUERY_NAMES")[0] == value

    @pytest.mark.parametrize(
        ("value", "literal"),
        [
            # ruff-format prefers double quotes and changes a string only to avoid
            # escapes: single quotes when the string holds more double quotes than single.
            ("plain", '"plain"'),
            ("", '""'),
            ('a"b', r"""'a"b'"""),
            ("a'b", r'''"a'b"'''),
            ("a'b\"c", r'''"a'b\"c"'''),
            ('a""b\'c', r"""'a""b\'c'"""),
            ("a'b'c\"d", r'''"a'b'c\"d"'''),
            ('"', r"""'"'"""),
            ("'", r'''"'"'''),
            # Every other character is spelled the way ``repr`` spells it.
            ("a\nb", r'"a\nb"'),
            ("a\\b", r'"a\\b"'),
            ("a\x00b", r'"a\x00b"'),
            ("a\u2028b", r'"a\u2028b"'),
            ("a\ud800b", r'"a\ud800b"'),
            # Printable text is left readable.
            ("Précision@k", '"Précision@k"'),
        ],
    )
    def test_the_quote_is_the_one_ruff_format_keeps(self, value: str, literal: str) -> None:
        assert _str_list_literal([value]) == f"[\n    {literal},\n]"

    def test_every_short_string_over_the_awkward_characters_round_trips(self) -> None:
        """All 781 strings of up to four of: a double quote, a single quote, a backslash,
        a newline and a letter, so every order and every tie and near-tie in the quote counts."""

        alphabet = ['"', "'", "\\", "\n", "a"]
        every = [
            "".join(chars)
            for length in range(5)
            for chars in itertools.product(alphabet, repeat=length)
        ]
        assert len(every) == 781
        out = render_evaluation(intake={"model_solution": {"evaluation_metrics": every}})
        assert _assigned(out, "REQUESTED_METRICS") == every
