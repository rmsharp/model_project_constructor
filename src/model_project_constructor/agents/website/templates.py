"""File content templates for the Website Agent's base scaffolding.

Each ``render_*`` function returns a ``(path, contents)`` pair or a list of
them. ``build_base_files(intake, data, project_name, project_slug)`` composes
all of them into the dict that ``SCAFFOLD_BASE`` writes into
``WebsiteState.files_pending``.

Phase 4A scope (architecture-plan §14 Phase 4A + §8.2):

- Everything listed in §11 *except* governance artifacts
- That excludes ``governance/``, ``data/datasheet_*.md``,
  ``.gitlab-ci.yml`` and ``.pre-commit-config.yaml`` (§8.2 classifies
  those as governance artifacts — they land in Phase 4B's
  SCAFFOLD_GOVERNANCE node)

Templates are pure Python f-strings; there is no template engine. The
content is deterministic for a given input so tests can byte-equal the
output.
"""

from __future__ import annotations

import json
import re
from typing import Any

from model_project_constructor.agents.website._file_stems import (
    primary_query_stems,
    quality_check_stems,
)
from model_project_constructor.agents.website._quarto_markup import (
    neutralise_quarto_markup,
    neutralise_report,
)
from model_project_constructor.agents.website._reserved_names import RESERVED_SLUGS, SUFFIX

# The one ruff version a generated project names: ``pyproject.toml`` asks for ``ruff>=`` this
# and the pre-commit hook pins ``rev: v`` this, so both start from the same release
# (``uv sync`` resolves the newest at or above it, the hook runs exactly it; the formatters
# agree on the generated files across 0.15 to 0.17). It was two unrelated hand-typed literals
# (``>=0.5`` and ``v0.5.0``), both June 2024. Raise it only together with
# ``uv lock --upgrade-package ruff``: the scaffold tests format generated files with this
# repository's locked ruff, and ``TestTheRuffVersionIsDeclaredOnce`` fails when the pin is
# ahead of it.
RUFF_VERSION = "0.15.10"

_SLUG_INVALID = re.compile(r"[^a-z0-9_]+")
_NAME_INVALID = re.compile(r"[^a-z0-9\-]+")


def derive_project_name(hint: str) -> str:
    """Turn a free-form ``project_name_hint`` into a GitLab-safe project name.

    Lowercased, hyphen-separated, no trailing/leading hyphens. Collapses
    runs of non-alphanumeric characters to a single hyphen.
    """

    lowered = hint.strip().lower()
    replaced = _NAME_INVALID.sub("-", lowered)
    collapsed = re.sub(r"-+", "-", replaced).strip("-")
    return collapsed or "model-project"


def derive_project_slug(project_name: str) -> str:
    """Turn a project name into a python-package-safe slug.

    Lowercase, underscore-separated, must start with a letter. A slug that
    is the name of a standard-library module, ``test``, ``tests`` or a Python
    keyword gets ``_model`` appended (``types`` -> ``types_model``), because
    the generated tests and notebooks import the package by this name and the
    wrong module would answer (see ``_reserved_names``). Every other slug is
    unchanged, so a repository created before that rule keeps its name.
    """

    base = project_name.replace("-", "_").lower()
    cleaned = _SLUG_INVALID.sub("_", base)
    collapsed = re.sub(r"_+", "_", cleaned).strip("_")
    if not collapsed or not collapsed[0].isalpha():
        collapsed = f"m_{collapsed}" if collapsed else "model_project"
    if collapsed in RESERVED_SLUGS:
        collapsed = f"{collapsed}{SUFFIX}"
    return collapsed


# --- individual file renderers ------------------------------------------------


def render_gitignore() -> str:
    return (
        "# Python\n"
        "__pycache__/\n"
        "*.py[cod]\n"
        "*.egg-info/\n"
        ".venv/\n"
        "venv/\n"
        "build/\n"
        "dist/\n"
        "\n"
        "# Testing / coverage\n"
        ".pytest_cache/\n"
        ".coverage\n"
        "htmlcov/\n"
        "\n"
        "# Editors\n"
        ".vscode/\n"
        ".idea/\n"
        ".DS_Store\n"
        "\n"
        "# Quarto\n"
        "_site/\n"
        "*_files/\n"
        "*.html\n"
        "\n"
        "# Data — never commit raw extracts\n"
        "data/raw/\n"
        "data/processed/\n"
        "*.csv\n"
        "*.parquet\n"
        "*.feather\n"
    )


def _uses_protected_attributes(intake: dict[str, Any]) -> bool:
    """Whether the fairness scaffold (``src/<slug>/fairness/`` and friends) is emitted.

    The same test ``governance_templates.build_analysis_files`` and ``build_test_files`` apply.
    ``test_the_extensions_notebook_points_at_the_fairness_package_only_if_it_exists`` fails if
    the two ever disagree.
    """

    return bool((intake.get("governance") or {}).get("uses_protected_attributes"))


def render_readme(
    *, intake: dict[str, Any], project_name: str, data: dict[str, Any] | None = None
) -> str:
    """Render ``README.md``.

    ``data`` is the data report. The layout lists ``queries/`` and the datasheets only when the
    report has primary queries, because only then do they exist.

    Quarto renders a ``.md`` it is asked to render as it does a ``.qmd`` (``_quarto_markup.py``),
    so the report text is neutralised here as it is in the notebooks.
    """

    intake = neutralise_report(intake)
    business_problem = str(intake.get("business_problem", "")).strip()
    proposed_solution = str(intake.get("proposed_solution", "")).strip()
    model_solution = intake.get("model_solution") or {}
    target_variable = model_solution.get("target_variable") or "unsupervised"
    model_type = model_solution.get("model_type") or "other"
    stakeholder_id = intake.get("stakeholder_id", "unknown")
    has_queries = bool((data or {}).get("primary_queries"))
    queries_line = (
        "- `queries/` — SQL pulled directly from the Data Agent report.\n" if has_queries else ""
    )
    data_line = (
        "- `data/` — data dictionary and a datasheet for each primary query.\n"
        if has_queries
        else "- `data/` — data dictionary.\n"
    )

    return (
        f"# {project_name}\n"
        "\n"
        "> **Draft model project.** This repository was scaffolded by the\n"
        "> Model Project Constructor pipeline. The Data Science team should\n"
        "> treat every section below as a starting point, not a deliverable.\n"
        "\n"
        "## Business Problem\n"
        "\n"
        f"{business_problem}\n"
        "\n"
        "## Proposed Solution\n"
        "\n"
        f"{proposed_solution}\n"
        "\n"
        "## Model at a Glance\n"
        "\n"
        f"- **Target:** `{target_variable}`\n"
        f"- **Model type:** `{model_type}`\n"
        f"- **Requesting stakeholder:** `{stakeholder_id}`\n"
        "\n"
        "## Repository Layout\n"
        "\n"
        "- `src/` — unit-testable Python modules (data loading, features,\n"
        "  models, evaluation). All analysis code lives here.\n"
        "- `analysis/` — Quarto narratives that import from `src/`.\n"
        f"{queries_line}"
        "- `tests/` — scaffolded unit tests for the `src/` modules.\n"
        "- `reports/` — the intake and data reports in both JSON and Markdown.\n"
        f"{data_line}"
        "- `governance/` — governance artifacts proportional to the model's risk\n"
        "  tier and cycle time (the model registry, model card and change log at\n"
        "  every tier).\n"
        "\n"
        "## Getting Started\n"
        "\n"
        "```bash\n"
        "uv sync --extra dev\n"
        "uv run pytest\n"
        "```\n"
        "\n"
        "## Rendering the analysis notebooks\n"
        "\n"
        "The files in `analysis/` are [Quarto](https://quarto.org/docs/get-started/)\n"
        "documents. Quarto is a separate install, not a Python package, and it runs\n"
        "their Python cells through Jupyter, which the `notebooks` extra provides.\n"
        "Render one file at a time (`quarto render analysis` needs a `_quarto.yml`):\n"
        "\n"
        "```bash\n"
        "uv run --extra notebooks quarto render analysis/03_eda.qmd\n"
        "```\n"
        "\n"
        "## License\n"
        "\n"
        "See [LICENSE](LICENSE) — not yet confirmed by Legal.\n"
    )


def render_license(*, intake: dict[str, Any], project_name: str) -> str:
    stakeholder_id = intake.get("stakeholder_id", "unknown")
    created = str(intake.get("created_at", "")) or "unknown"
    return (
        f"{project_name} — PROPRIETARY AND CONFIDENTIAL (SCAFFOLD PLACEHOLDER)\n"
        "\n"
        "This repository was generated by the Model Project Constructor pipeline\n"
        "for an internal Data Science project. No license or distribution terms\n"
        "have been confirmed by Legal for this project's code or model\n"
        f"artifacts. Requesting stakeholder: {stakeholder_id}. Scaffolded: {created}.\n"
        "\n"
        "Until Legal reviews this project and replaces this file with the\n"
        "organization's actual terms, treat all contents as proprietary and\n"
        "confidential. Do not publish, redistribute, or open-source this\n"
        "repository or any derived model artifacts.\n"
    )


def render_pyproject(*, project_name: str, project_slug: str) -> str:
    return (
        "[project]\n"
        f'name = "{project_name}"\n'
        'version = "0.1.0"\n'
        f'description = "Draft model project scaffolded by Model Project Constructor"\n'
        'requires-python = ">=3.11"\n'
        "dependencies = [\n"
        '    "pandas>=2",\n'
        '    "scikit-learn>=1.4",\n'
        '    "sqlalchemy>=2",\n'
        "]\n"
        "\n"
        "[project.optional-dependencies]\n"
        "dev = [\n"
        '    "pytest>=8",\n'
        '    "pytest-cov>=5",\n'
        f'    "ruff>={RUFF_VERSION}",\n'
        "]\n"
        # What Quarto needs to run a Python cell through Jupyter, and no more: not the
        # ``jupyter`` metapackage (an 80-package closure) and not ``quarto-cli`` (an sdist
        # that downloads Quarto from GitHub at build time, which fails behind an internal
        # package index). A separate extra because every CI job installs ``dev`` and none
        # opens a notebook.
        "notebooks = [\n"
        '    "ipykernel>=6",\n'
        '    "nbclient>=0.8",\n'
        '    "nbformat>=5.7",\n'
        '    "pyyaml>=6",\n'
        "]\n"
        "\n"
        "[build-system]\n"
        'requires = ["hatchling"]\n'
        'build-backend = "hatchling.build"\n'
        "\n"
        "[tool.hatch.build.targets.wheel]\n"
        f'packages = ["src/{project_slug}"]\n'
        "\n"
        "[tool.pytest.ini_options]\n"
        'testpaths = ["tests"]\n'
        'pythonpath = ["src"]\n'
    )


def render_src_init(*, project_name: str, project_slug: str) -> str:
    return (
        f'"""{project_name} — model package.\n'
        "\n"
        "Scaffolded by Model Project Constructor. Keep all unit-testable\n"
        "code inside this package; the ``analysis/*.qmd`` narratives import\n"
        "from here.\n"
        '"""\n'
        "\n"
        '__all__: list[str] = []\n'
    )


def _py_str_literal(value: str) -> str:
    """A Python string literal for ``value``, spelled the way ``ruff format`` keeps it.

    A metric or query name is any string (the schemas constrain neither), and it is written
    into generated source, so what comes back from ``ast.literal_eval`` must be ``value`` and
    nothing in it may end the literal or run. ``json.dumps`` is not the answer: it always
    uses double quotes, and ``ruff format`` rewrites ``"a\\"b"`` to ``'a"b'``, so the
    generated project's own formatter hook would change the file on its first commit.

    The quote is the one ruff chooses: double, unless the value holds more double quotes than
    single ones. Only that quote is escaped. Every other character is spelled as ``repr``
    spells it: a backslash, a newline, a tab and every character that is not printable (a NUL,
    an escape, ``U+2028``, a lone surrogate) as an escape, and printable text, accents and
    emoji included, as it stands. So the file never holds a control character or a character
    no UTF-8 file can hold, and a terminal that shows it is not driven by it.
    """

    quote = "'" if value.count('"') > value.count("'") else '"'
    # ``repr(char)[1:-1]`` is how one character is spelled inside a literal. It leaves both
    # quote characters bare, so the chosen quote is the only one that needs a backslash.
    spelled = [repr(char)[1:-1] for char in value]
    body = "".join(
        "\\" + spelling if char == quote else spelling
        for char, spelling in zip(value, spelled, strict=True)
    )
    return quote + body + quote


def _str_list_literal(items: list[str]) -> str:
    """A ``list[str]`` literal written the way ``ruff format`` writes it.

    One item per line with a trailing comma, which ruff keeps; ``[]`` when there are none,
    because ruff rewrites ``[`` newline ``]`` to that and the generated pre-commit config
    runs ``ruff-format``. Both lists this renders can be empty in a valid report. Each item is
    a string literal that evaluates back to the item (:func:`_py_str_literal`).
    """

    if not items:
        return "[]"
    return "[\n" + "".join(f"    {_py_str_literal(item)},\n" for item in items) + "]"


def render_data_loading(*, project_slug: str, primary_query_names: list[str]) -> str:
    names_literal = _str_list_literal(primary_query_names)
    return (
        '"""Data loading functions.\n'
        "\n"
        "These are called from ``analysis/02_data.qmd`` and from the unit\n"
        "tests in ``tests/test_data_loading.py``. Each primary query listed\n"
        "in the Data Agent report has a loader stub below; fill in the\n"
        "actual SQLAlchemy connection when the Data Science team is ready.\n"
        '"""\n'
        "\n"
        "from __future__ import annotations\n"
        "\n"
        "from pathlib import Path\n"
        "\n"
        "QUERIES_DIR = Path(__file__).resolve().parents[2] / \"queries\" / \"primary\"\n"
        "\n"
        f"PRIMARY_QUERY_NAMES: list[str] = {names_literal}\n"
        "\n"
        "\n"
        "def read_sql(query_name: str) -> str:\n"
        '    """Return the SQL text for a primary query by name."""\n'
        '    path = QUERIES_DIR / f"{query_name}.sql"\n'
        "    return path.read_text()\n"
        "\n"
        "\n"
        "def load_primary(query_name: str) -> object:\n"
        '    """Load the result of a primary query into a DataFrame.\n'
        "\n"
        "    Stub — wire up your SQLAlchemy engine here.\n"
        '    """\n'
        '    raise NotImplementedError("Wire up SQLAlchemy engine before calling")\n'
    )


def render_features() -> str:
    return (
        '"""Feature engineering functions — all unit-testable.\n'
        "\n"
        "Add one function per feature. Each should take a DataFrame and\n"
        "return a DataFrame with the new feature attached. Keep them pure\n"
        "(no I/O, no global state) so the tests in ``tests/test_features.py``\n"
        "can exercise them with small synthetic inputs.\n"
        '"""\n'
        "\n"
        "from __future__ import annotations\n"
        "\n"
        "\n"
        "def build_feature_matrix(df: object) -> object:\n"
        '    """Assemble the full feature matrix from a raw DataFrame."""\n'
        '    raise NotImplementedError("Fill in feature engineering")\n'
    )


def render_models(*, intake: dict[str, Any]) -> str:
    model_solution = intake.get("model_solution") or {}
    model_type = model_solution.get("model_type") or "other"
    return (
        '"""Model training and inference.\n'
        "\n"
        f"The intake report classifies this project as a ``{model_type}``\n"
        "model. The stub below is deliberately minimal — the Data Science\n"
        "team will replace ``train`` / ``predict`` with a real implementation.\n"
        '"""\n'
        "\n"
        "from __future__ import annotations\n"
        "\n"
        "\n"
        "def train(features: object, target: object) -> object:\n"
        '    """Fit a model on the supplied feature matrix and target."""\n'
        '    raise NotImplementedError("Wire up training pipeline")\n'
        "\n"
        "\n"
        "def predict(model: object, features: object) -> object:\n"
        '    """Score a fitted model over a feature matrix."""\n'
        '    raise NotImplementedError("Wire up inference path")\n'
    )


def render_evaluation(*, intake: dict[str, Any]) -> str:
    model_solution = intake.get("model_solution") or {}
    metrics = list(model_solution.get("evaluation_metrics") or [])
    metrics_literal = _str_list_literal(metrics)
    return (
        '"""Evaluation functions — thin wrappers around sklearn metrics.\n'
        "\n"
        "The intake report requested the metrics below. Add one function\n"
        "per metric; each should accept ``y_true`` and ``y_pred`` and return\n"
        "a float.\n"
        '"""\n'
        "\n"
        "from __future__ import annotations\n"
        "\n"
        f"REQUESTED_METRICS: list[str] = {metrics_literal}\n"
        "\n"
        "\n"
        "def evaluate(y_true: object, y_pred: object) -> dict[str, float]:\n"
        '    """Return a dict of metric name → score for the requested metrics."""\n'
        '    raise NotImplementedError("Wire up metric computation")\n'
    )


# --- Quarto narratives --------------------------------------------------------


def _qmd_header(title: str) -> str:
    return f"---\ntitle: \"{title}\"\nformat: html\n---\n\n"


def _format_usd_band(low: Any, high: Any, *, suffix: str = "") -> str:
    """Format a low/high USD pair as ``$L – $H<suffix>``.

    Returns ``(not estimated)`` when either bound is absent — the Phase-1
    ``EstimatedValue`` business-case fields are all optional, so a sparse
    intake must still render a structurally complete business case.
    """
    if low is None or high is None:
        return "(not estimated)"
    return f"${low:,.0f} – ${high:,.0f}{suffix}"


def _render_business_case_block(*, intake: dict[str, Any]) -> str:
    """Render the shared business-case sections for the generated website's
    ``analysis/01_business_understanding.qmd`` and ``reports/intake_report.md``.

    Both surfaces present the same case — Annual Impact Band, Cost of
    Inaction, Implementation Cost, Payback, Value Drivers, Assumptions,
    Decision Rights — so the block lives in one helper (Phase 4 of
    ``docs/planning/business-value-capture-plan.md``). Every section is
    always emitted; a missing optional field renders a ``(not estimated)``
    / ``(none declared)`` placeholder so the business case stays
    structurally complete no matter how sparse the intake is.

    Both callers pass their already-neutralised intake (Quarto reads a ``.qmd`` and a ``.md``
    for more than prose, ``_quarto_markup.py``), so the block is the same text in both.
    """
    ev = intake.get("estimated_value") or {}
    vmp = intake.get("value_measurement_plan") or {}

    impact_band = _format_usd_band(
        ev.get("annual_impact_usd_low"),
        ev.get("annual_impact_usd_high"),
        suffix=" per year",
    )
    cost_of_inaction = str(ev.get("cost_of_inaction_narrative") or "").strip()
    cost_of_inaction_band = _format_usd_band(
        ev.get("annual_cost_of_inaction_usd_low"),
        ev.get("annual_cost_of_inaction_usd_high"),
        suffix=" per year",
    )
    implementation_band = _format_usd_band(
        ev.get("implementation_cost_band_usd_low"),
        ev.get("implementation_cost_band_usd_high"),
    )
    payback = ev.get("payback_months")
    payback_md = f"{payback} months" if payback is not None else "(not estimated)"
    value_drivers = ev.get("value_drivers") or []
    value_drivers_md = (
        "\n".join(f"- {d}" for d in value_drivers)
        if value_drivers
        else "- (none declared)"
    )
    assumptions = ev.get("assumptions") or []
    assumptions_md = (
        "\n".join(f"- {a}" for a in assumptions)
        if assumptions
        else "- (none declared)"
    )
    decision_rights = str(vmp.get("decision_rights") or "").strip()

    return (
        "## Annual Impact Band\n\n"
        f"{impact_band}\n\n"
        "## Cost of Inaction\n\n"
        f"{cost_of_inaction or '(not estimated)'}\n\n"
        f"**Estimated annual cost of inaction:** {cost_of_inaction_band}\n\n"
        "## Implementation Cost\n\n"
        f"**Estimated one-time implementation cost:** {implementation_band}\n\n"
        "## Payback\n\n"
        f"**Estimated payback period:** {payback_md}\n\n"
        "## Value Drivers\n\n"
        f"{value_drivers_md}\n\n"
        "## Assumptions\n\n"
        f"{assumptions_md}\n\n"
        "## Decision Rights\n\n"
        f"{decision_rights or '(not specified)'}\n"
    )


def render_qmd_business_understanding(*, intake: dict[str, Any]) -> str:
    intake = neutralise_report(intake)
    estimated_value = intake.get("estimated_value") or {}
    narrative = str(estimated_value.get("narrative", "")).strip()
    return (
        _qmd_header("01 — Business Understanding")
        + "## Business Problem\n\n"
        + str(intake.get("business_problem", "")).strip()
        + "\n\n"
        + "## Proposed Solution\n\n"
        + str(intake.get("proposed_solution", "")).strip()
        + "\n\n"
        + "## Estimated Value\n\n"
        + narrative
        + "\n\n"
        + _render_business_case_block(intake=intake)
    )


def render_qmd_data(*, data: dict[str, Any], project_slug: str) -> str:
    # The file a query is written to comes from the report as given, as it does in every other
    # renderer; the neutraliser below changes the text a reader sees, not the path.
    stems = primary_query_stems(data)
    data = neutralise_report(data)
    summary = str(data.get("summary", "")).strip()
    primary_queries = data.get("primary_queries") or []
    lines = [
        _qmd_header("02 — Data"),
        "## Data Agent Summary\n",
        summary,
        "\n\n## Primary Queries\n",
    ]
    for q, stem in zip(primary_queries, stems, strict=True):
        name = q.get("name", "unknown")
        purpose = q.get("purpose", "")
        lines.append(f"\n### {name}\n\n{purpose}\n")
        lines.append(f"\nSQL: `queries/primary/{stem}.sql`\n")
    lines.append(
        "\n```{python}\n"
        f"# from {project_slug}.data_loading import load_primary\n"
        "# df = load_primary(\"<query_name>\")\n"
        "```\n"
    )
    return "".join(lines)


def render_qmd_eda() -> str:
    return (
        _qmd_header("03 — Exploratory Data Analysis")
        + "This notebook is a scaffold. The Data Science team should:\n\n"
        + "1. Load each primary query via ``data_loading.load_primary``.\n"
        + "2. Document row counts, missing-value rates, and value distributions.\n"
        + "3. Surface any anomalies that weren't caught by the Data Agent's\n"
        + "   quality checks.\n\n"
        + "```{python}\n"
        + "# EDA code goes here\n"
        + "```\n"
    )


def render_qmd_feature_engineering(*, project_slug: str) -> str:
    return (
        _qmd_header("04 — Feature Engineering")
        + f"Features are implemented in ``src/{project_slug}/features.py`` so they\n"
        + "can be unit-tested. This narrative demonstrates their use.\n\n"
        + "```{python}\n"
        + f"# from {project_slug}.features import build_feature_matrix\n"
        + "# X = build_feature_matrix(raw_df)\n"
        + "```\n"
    )


def render_qmd_initial_models(*, intake: dict[str, Any], project_slug: str) -> str:
    intake = neutralise_report(intake)
    ms = intake.get("model_solution") or {}
    metrics = ", ".join(ms.get("evaluation_metrics") or []) or "(none declared)"
    return (
        _qmd_header("05 — Initial Models")
        + f"**Model type:** `{ms.get('model_type', 'other')}`\n\n"
        + f"**Requested evaluation metrics:** {metrics}\n\n"
        + "```{python}\n"
        + f"# from {project_slug}.models import train, predict\n"
        + f"# from {project_slug}.evaluation import evaluate\n"
        + "# model = train(X_train, y_train)\n"
        + "# preds = predict(model, X_test)\n"
        + "# scores = evaluate(y_test, preds)\n"
        + "```\n"
    )


def _render_production_measurement_plan(
    *, intake: dict[str, Any], data: dict[str, Any]
) -> str:
    """Render the post-deployment measurement methodology for the generated
    website's ``analysis/06_implementation_plan.qmd``.

    The intake estimate is a forecast; this block records *how the realised
    value gets measured* once the model ships (Phase 5 of
    ``docs/planning/business-value-capture-plan.md``). The baseline figure is
    interpolated from the Data Agent's ``DataReport.baseline_snapshot`` with a
    citation footnote preserving provenance; the counterfactual / attribution /
    horizon / logging / cadence / criteria / decision-rights sections come from
    the intake's ``ValueMeasurementPlan``. Every section is always emitted — a
    missing field renders a placeholder so the plan stays structurally complete
    no matter how sparse the inputs are.
    """
    vmp = intake.get("value_measurement_plan") or {}
    snapshot = data.get("baseline_snapshot") or {}

    # --- Baseline: current-state metric from DataReport.baseline_snapshot ---
    if snapshot:
        metric_name = snapshot.get("metric_name") or vmp.get("baseline_metric_name")
        definition = str(vmp.get("baseline_metric_definition") or "").strip()
        value = snapshot.get("value")
        unit = str(snapshot.get("measurement_unit") or "").strip()
        if value is not None:
            value_md = f"{value:,} {unit}".strip() + " [^baseline-src]"
        else:
            value_md = "(not measured) [^baseline-src]"
        window_start = snapshot.get("measurement_window_start")
        window_end = snapshot.get("measurement_window_end")
        # The report was neutralised on the way in, and the dates are datetimes in a validated
        # report, so only a hand-built dict puts text here. Cutting the end can leave a ``---``
        # alone on its line (the template's newline follows it), so the end is neutralised again
        # after the cut; the start has the arrow after it on its line, which a cut cannot undo.
        window_md = (
            f"{str(window_start)[:10]} → {neutralise_quarto_markup(str(window_end)[:10])}"
            if window_start and window_end
            else "(not recorded)"
        )
        status = snapshot.get("query_execution_status") or "UNKNOWN"
        baseline_lines = [
            f"- **Metric:** `{metric_name or '(not specified)'}`",
            f"- **Definition:** {definition or '(not specified)'}",
            f"- **Current value:** {value_md}",
            f"- **Measurement window:** {window_md}",
            f"- **Query execution status:** `{status}`",
        ]
        caveats = snapshot.get("caveats") or []
        if caveats:
            baseline_lines.append(
                "- **Caveats:** " + "; ".join(str(c) for c in caveats)
            )
        baseline_md = "\n".join(baseline_lines) + (
            "\n\n[^baseline-src]: Baseline figures are sourced from "
            "`reports/data_report.json` (`baseline_snapshot`), collected by "
            "the Data Agent."
        )
    else:
        baseline_md = (
            "No baseline snapshot was collected by the Data Agent. Establish "
            "the current-state metric before deployment — see "
            "`reports/data_report.json` and the intake report's value "
            "measurement plan."
        )

    # --- Methodology: from the intake's ValueMeasurementPlan ---
    counterfactual_rationale = str(vmp.get("counterfactual_rationale") or "").strip()
    attribution = str(vmp.get("attribution_method_narrative") or "").strip()
    horizon = vmp.get("evaluation_horizon_months")
    horizon_md = f"{horizon} months" if horizon is not None else "(not specified)"
    logging_reqs = vmp.get("logging_requirements") or []
    logging_md = (
        "\n".join(f"- {r}" for r in logging_reqs)
        if logging_reqs
        else "- (none declared)"
    )
    success_criteria = vmp.get("success_criteria") or []
    success_md = (
        "\n".join(f"- {c}" for c in success_criteria)
        if success_criteria
        else "- (none declared)"
    )
    decision_rights = str(vmp.get("decision_rights") or "").strip()

    return (
        "## Production Measurement Plan\n\n"
        "The figures above are estimates captured at intake. This section\n"
        "records the *methodology* for measuring the model's realised value\n"
        "after deployment — actual outcomes flow into the sections below\n"
        "post-launch. The Data Science team owns wiring the production\n"
        "logging.\n\n"
        "## Baseline\n\n"
        f"{baseline_md}\n\n"
        "## Counterfactual Design\n\n"
        f"**Design:** `{vmp.get('counterfactual_design') or 'none_declared'}`\n\n"
        f"{counterfactual_rationale or '(rationale not specified)'}\n\n"
        "## Attribution Method\n\n"
        f"{attribution or '(not specified)'}\n\n"
        "## Evaluation Horizon\n\n"
        f"{horizon_md}\n\n"
        "## Logging Requirements\n\n"
        "The Data Science team must instrument production logging for:\n\n"
        f"{logging_md}\n\n"
        "## Review Cadence\n\n"
        f"`{vmp.get('review_cadence') or 'ad_hoc'}`\n\n"
        "## Success Criteria\n\n"
        f"{success_md}\n\n"
        "## Decision Rights\n\n"
        f"{decision_rights or '(not specified)'}\n"
    )


def render_qmd_implementation_plan(
    *, intake: dict[str, Any], data: dict[str, Any]
) -> str:
    intake = neutralise_report(intake)
    data = neutralise_report(data)
    estimated_value = intake.get("estimated_value") or {}
    impact = _format_usd_band(
        estimated_value.get("annual_impact_usd_low"),
        estimated_value.get("annual_impact_usd_high"),
        suffix=" per year",
    )
    confidence = estimated_value.get("confidence", "unknown")
    assumptions = estimated_value.get("assumptions") or []
    assumptions_md = (
        "\n".join(f"- {a}" for a in assumptions) if assumptions else "- (none declared)"
    )
    return (
        _qmd_header("06 — Implementation Plan & Measuring Value")
        + f"**Estimated annual impact:** {impact}\n\n"
        + f"**Confidence:** {confidence}\n\n"
        + "## Assumptions\n\n"
        + assumptions_md
        + "\n\n"
        + _render_production_measurement_plan(intake=intake, data=data)
    )


def render_qmd_extensions(*, intake: dict[str, Any], project_slug: str) -> str:
    """Render ``analysis/99_extensions.qmd``.

    The fairness bullet names the fairness scaffold only when the project has one: it is emitted
    when the intake report declares protected attributes, at every risk tier, and not otherwise.
    """

    if _uses_protected_attributes(intake):
        fairness = (
            "- Fairness / subgroup analyses (start from `analysis/fairness_audit.qmd`\n"
            f"  and the package in `src/{project_slug}/fairness/`)\n"
        )
    else:
        fairness = (
            "- Fairness / subgroup analyses (no fairness scaffold was generated: the\n"
            "  intake report does not say the model uses protected attributes)\n"
        )
    return (
        _qmd_header("99 — Extensions & Next Experiments")
        + "Candidate extensions for future iterations:\n\n"
        + "- Additional feature sources surfaced by EDA\n"
        + "- Alternative model families beyond the initial choice\n"
        + fairness
    )


# --- Queries and tests --------------------------------------------------------


def render_primary_query_files(*, data: dict[str, Any]) -> dict[str, str]:
    """One ``queries/primary/<stem>.sql`` per primary query.

    The stem is not the report's name: a name is any string, and it used to be written here as
    given (``_file_stems``, BACKLOG (7)(a)).
    """

    out: dict[str, str] = {}
    queries = data.get("primary_queries") or []
    for q, stem in zip(queries, primary_query_stems(data), strict=True):
        out[f"queries/primary/{stem}.sql"] = str(q.get("sql", "")).rstrip() + "\n"
    return out


def render_quality_check_files(*, data: dict[str, Any]) -> dict[str, str]:
    """One ``queries/quality/<query stem>/<check stem>.sql`` per quality check."""

    out: dict[str, str] = {}
    queries = data.get("primary_queries") or []
    for q, primary_stem in zip(queries, primary_query_stems(data), strict=True):
        checks = q.get("quality_checks") or []
        for check, check_stem in zip(checks, quality_check_stems(q), strict=True):
            path = f"queries/quality/{primary_stem}/{check_stem}.sql"
            out[path] = str(check.get("check_sql", "")).rstrip() + "\n"
    return out


def render_tests_init() -> str:
    return ""


# The stubs ``build_base_files`` scaffolds, and how to call each one. Every stub body is
# ``raise NotImplementedError``, so the generated ``tests/test_<module>.py`` calls each of
# them once and expects exactly that. ``render_data_loading`` and its siblings write the stubs,
# so a stub added there has to be listed here;
# ``test_every_scaffolded_stub_is_called_by_its_test`` fails when the two disagree.
_STUB_CALLS: dict[str, tuple[tuple[str, str], ...]] = {
    "data_loading": (("load_primary", '"example"'),),
    "features": (("build_feature_matrix", "None"),),
    "models": (("train", "None, None"), ("predict", "None, None")),
    "evaluation": (("evaluate", "None, None"),),
}


def render_test_stub(module: str, project_slug: str) -> str:
    """Render ``tests/test_<module>.py`` for one scaffolded ``src/<slug>/<module>.py``.

    The output is already ``ruff format``-clean, because the generated pre-commit config runs
    that hook and a file it rewrites fails the first commit. The package name appears only in
    ``import <slug>.<module> as module`` statements, which ``ruff format`` cannot wrap, so
    that holds whatever length the slug has (a string constant could be wrapped, and was, for
    slugs of 77 to 82 characters).
    """

    calls = "".join(
        f"    with pytest.raises(NotImplementedError):\n        module.{name}({args})\n"
        for name, args in _STUB_CALLS[module]
    )
    return (
        f'"""Unit tests for ``{module}``. Scaffolded — fill in real cases."""\n'
        "\n"
        "from __future__ import annotations\n"
        "\n"
        "import pytest\n"
        "\n"
        "\n"
        f"def test_{module}_importable() -> None:\n"
        f"    import {project_slug}.{module} as module\n"
        "\n"
        "    assert module is not None\n"
        "\n"
        "\n"
        f"def test_{module}_stub_raises() -> None:\n"
        "    # Replace with real assertions once the implementation lands: a stub that no\n"
        "    # longer raises makes this test fail, which is the prompt to do so.\n"
        f"    import {project_slug}.{module} as module\n"
        "\n"
        f"{calls}"
    )


# --- Data dictionary and reports ---------------------------------------------


def render_data_readme(*, data: dict[str, Any]) -> str:
    # The datasheet a query is named for comes from the report as given; the neutraliser changes
    # the text a reader sees, not the path (the same order as ``render_qmd_data``).
    stems = primary_query_stems(data)
    data = neutralise_report(data)
    queries = data.get("primary_queries") or []
    lines = [
        "# Data Dictionary\n",
        "\n",
        "This directory holds the data contract for the project.\n",
    ]
    if queries:
        lines.append("Each primary query has a datasheet here, `datasheet_<query>.md`.\n")
    lines += [
        "\n",
        "## Primary Queries\n",
        "\n",
    ]
    for q, stem in zip(queries, stems, strict=True):
        name = q.get("name", "unnamed")
        # "unknown" is a defensive sentinel: expected_row_count_order is a
        # REQUIRED PrimaryQuery field (schemas.RowCountOrder), so a validly
        # serialized DataReport always carries a real member — this fallback
        # renders only on malformed/partial input (O4 plan §1.6, Q5).
        row_order = q.get("expected_row_count_order", "unknown")
        purpose = q.get("purpose", "")
        lines.append(f"### `{name}`\n\n")
        lines.append(f"- **Expected row order:** {row_order}\n")
        lines.append(f"- **Purpose:** {purpose}\n")
        lines.append(f"- **Datasheet:** `datasheet_{stem}.md`\n\n")
    return "".join(lines)


def render_reports_intake_json(*, intake: dict[str, Any]) -> str:
    return json.dumps(intake, indent=2, default=str) + "\n"


def render_reports_intake_md(*, intake: dict[str, Any]) -> str:
    intake = neutralise_report(intake)
    ms = intake.get("model_solution") or {}
    ev = intake.get("estimated_value") or {}
    gov = intake.get("governance") or {}
    return (
        "# Intake Report\n"
        "\n"
        f"- **Stakeholder:** `{intake.get('stakeholder_id', 'unknown')}`\n"
        f"- **Session:** `{intake.get('session_id', 'unknown')}`\n"
        f"- **Status:** `{intake.get('status', 'unknown')}`\n"
        f"- **Questions asked:** {intake.get('questions_asked', 0)}\n"
        f"- **Revision cycles:** {intake.get('revision_cycles', 0)}\n"
        "\n"
        "## Business Problem\n\n"
        f"{intake.get('business_problem', '')}\n\n"
        "## Proposed Solution\n\n"
        f"{intake.get('proposed_solution', '')}\n\n"
        "## Model Solution\n\n"
        f"- Target: `{ms.get('target_variable', 'n/a')}`\n"
        f"- Type: `{ms.get('model_type', 'other')}`\n"
        f"- Metrics: {', '.join(ms.get('evaluation_metrics') or []) or '(none)'}\n"
        "\n"
        "## Estimated Value\n\n"
        f"{ev.get('narrative', '')}\n\n"
        + _render_business_case_block(intake=intake)
        + "\n## Governance\n\n"
        f"- Cycle time: `{gov.get('cycle_time', 'unknown')}`\n"
        f"- Risk tier: `{gov.get('risk_tier', 'unknown')}`\n"
        "- Regulatory frameworks: "
        f"{', '.join(gov.get('regulatory_frameworks') or []) or '(none)'}\n"
    )


def render_reports_data_json(*, data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, default=str) + "\n"


def render_reports_data_md(*, data: dict[str, Any]) -> str:
    data = neutralise_report(data)
    queries = data.get("primary_queries") or []
    lines = [
        "# Data Report\n",
        "\n",
        f"- **Status:** `{data.get('status', 'unknown')}`\n",
        f"- **Primary queries:** {len(queries)}\n",
        "\n",
        "## Summary\n\n",
        str(data.get("summary", "")).strip() + "\n\n",
        "## Confirmed Expectations\n\n",
    ]
    for item in data.get("confirmed_expectations") or []:
        lines.append(f"- {item}\n")
    lines.append("\n## Unconfirmed Expectations\n\n")
    for item in data.get("unconfirmed_expectations") or []:
        lines.append(f"- {item}\n")
    lines.append("\n## Data Quality Concerns\n\n")
    for item in data.get("data_quality_concerns") or []:
        lines.append(f"- {item}\n")
    return "".join(lines)


# --- composition --------------------------------------------------------------


def build_base_files(
    *,
    intake: dict[str, Any],
    data: dict[str, Any],
    project_name: str,
    project_slug: str,
) -> dict[str, str]:
    """Return every non-governance file the website agent scaffolds in 4A.

    The resulting dict maps repo-relative path → file contents. The
    ``SCAFFOLD_BASE`` node writes this verbatim into
    ``WebsiteState.files_pending`` and ``INITIAL_COMMITS`` flushes it to
    the client in a single commit.
    """

    src_prefix = f"src/{project_slug}"
    # The loader reads ``queries/primary/<name>.sql``, so the list holds the stems the files are
    # written under, not the report's names.
    primary_query_names = primary_query_stems(data)

    files: dict[str, str] = {
        ".gitignore": render_gitignore(),
        "README.md": render_readme(intake=intake, project_name=project_name, data=data),
        "LICENSE": render_license(intake=intake, project_name=project_name),
        "pyproject.toml": render_pyproject(
            project_name=project_name, project_slug=project_slug
        ),
        f"{src_prefix}/__init__.py": render_src_init(
            project_name=project_name, project_slug=project_slug
        ),
        f"{src_prefix}/data_loading.py": render_data_loading(
            project_slug=project_slug, primary_query_names=primary_query_names
        ),
        f"{src_prefix}/features.py": render_features(),
        f"{src_prefix}/models.py": render_models(intake=intake),
        f"{src_prefix}/evaluation.py": render_evaluation(intake=intake),
        "analysis/01_business_understanding.qmd": render_qmd_business_understanding(
            intake=intake
        ),
        "analysis/02_data.qmd": render_qmd_data(data=data, project_slug=project_slug),
        "analysis/03_eda.qmd": render_qmd_eda(),
        "analysis/04_feature_engineering.qmd": render_qmd_feature_engineering(
            project_slug=project_slug
        ),
        "analysis/05_initial_models.qmd": render_qmd_initial_models(
            intake=intake, project_slug=project_slug
        ),
        "analysis/06_implementation_plan.qmd": render_qmd_implementation_plan(
            intake=intake, data=data
        ),
        "analysis/99_extensions.qmd": render_qmd_extensions(
            intake=intake, project_slug=project_slug
        ),
        "tests/__init__.py": render_tests_init(),
        "tests/test_data_loading.py": render_test_stub("data_loading", project_slug),
        "tests/test_features.py": render_test_stub("features", project_slug),
        "tests/test_models.py": render_test_stub("models", project_slug),
        "tests/test_evaluation.py": render_test_stub("evaluation", project_slug),
        "data/README.md": render_data_readme(data=data),
        "reports/intake_report.json": render_reports_intake_json(intake=intake),
        "reports/intake_report.md": render_reports_intake_md(intake=intake),
        "reports/data_report.json": render_reports_data_json(data=data),
        "reports/data_report.md": render_reports_data_md(data=data),
    }
    files.update(render_primary_query_files(data=data))
    files.update(render_quality_check_files(data=data))
    return files
