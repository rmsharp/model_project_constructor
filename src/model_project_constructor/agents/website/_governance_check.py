"""Check that this project's governance record is complete and readable.

Run by CI and by pre-commit as ``python governance/check_governance.py``. It uses only
the standard library, so it needs no install. Exit 0 means every check passed and 1
means at least one problem, each of which is printed. Nothing is rewritten.

It checks that ``governance/model_registry.json`` parses and carries every key with
the right type and a known value, and that each file the registry calls for exists and
is not empty: the documents its risk tier requires, the EU AI Act file when
``affects_consumers`` is true, and one datasheet for each ``queries/primary/*.sql``. It
does not check what a person has written in those files.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

RISK_TIERS = ("tier_1_critical", "tier_2_high", "tier_3_moderate", "tier_4_low")
CYCLE_TIMES = ("strategic", "tactical", "operational", "continuous")
MODEL_TYPES = (
    "supervised_classification",
    "supervised_regression",
    "unsupervised_clustering",
    "unsupervised_anomaly",
    "time_series",
    "reinforcement",
    "other",
)

# key -> (the types its value may have, the values it may take or None for any).
# ``target_variable`` is null for an unsupervised model: the key must exist,
# the value need not.
REGISTRY: dict[str, tuple[tuple[type, ...], tuple[str, ...] | None]] = {
    "schema_version": ((str,), None),
    "model_id": ((str,), None),
    "project_name": ((str,), None),
    "owner_stakeholder_id": ((str,), None),
    "intake_session_id": ((str,), None),
    "created_at": ((str,), None),
    "target_variable": ((str, type(None)), None),
    "model_type": ((str,), MODEL_TYPES),
    "risk_tier": ((str,), RISK_TIERS),
    "cycle_time": ((str,), CYCLE_TIMES),
    "regulatory_frameworks": ((list,), None),
    "affects_consumers": ((bool,), None),
    "uses_protected_attributes": ((bool,), None),
}

ALWAYS = (
    "governance/model_registry.json",
    "governance/model_card.md",
    "governance/change_log.md",
)
# The least severe tier number that needs the file: 3 means tiers 3, 2 and 1.
FROM_TIER = {
    "governance/three_pillar_validation.md": 3,
    "governance/ongoing_monitoring.md": 3,
    "governance/deployment_gates.md": 3,
    "governance/impact_assessment.md": 2,
    "governance/regulatory_mapping.md": 2,
    "governance/lcp_integration.md": 1,
    "governance/audit_log/README.md": 1,
}
CONSUMER_FACING = ("governance/eu_ai_act_compliance.md",)

REGISTRY_PATH = "governance/model_registry.json"


def load_registry(root: Path, problems: list[str]) -> dict[str, Any] | None:
    try:
        entry = json.loads((root / REGISTRY_PATH).read_text(encoding="utf-8"))
    except FileNotFoundError:
        problems.append(f"{REGISTRY_PATH}: missing")
        return None
    except (OSError, ValueError) as error:
        problems.append(f"{REGISTRY_PATH}: cannot be read as JSON ({error})")
        return None
    if not isinstance(entry, dict):
        problems.append(f"{REGISTRY_PATH}: the top level must be an object")
        return None
    return entry


def check_registry(entry: dict[str, Any], problems: list[str]) -> None:
    for key, (types, allowed) in REGISTRY.items():
        if key not in entry:
            problems.append(f"{REGISTRY_PATH}: missing key {key!r}")
            continue
        value = entry[key]
        if not isinstance(value, types):
            problems.append(f"{REGISTRY_PATH}: {key!r} has the wrong type")
        elif allowed is not None and value not in allowed:
            problems.append(
                f"{REGISTRY_PATH}: {key!r} is {value!r}, not one of {allowed}"
            )
    frameworks = entry.get("regulatory_frameworks")
    if isinstance(frameworks, list) and not all(isinstance(f, str) for f in frameworks):
        problems.append(f"{REGISTRY_PATH}: 'regulatory_frameworks' must hold strings")


def required_files(entry: dict[str, Any], root: Path) -> list[tuple[str, str]]:
    """Return ``(path, why it is required)`` for every file the registry calls for."""
    tier = entry.get("risk_tier")
    number = RISK_TIERS.index(tier) + 1 if tier in RISK_TIERS else 4
    required = [(path, "every project") for path in ALWAYS]
    required += [
        (path, f"risk_tier is {tier}")
        for path, floor in FROM_TIER.items()
        if number <= floor
    ]
    if entry.get("affects_consumers") is True:
        required += [(path, "affects_consumers is true") for path in CONSUMER_FACING]
    primary = root / "queries" / "primary"
    for query in sorted(primary.glob("*.sql")) if primary.is_dir() else []:
        # ``removesuffix``, not ``Path.stem``: a query named "" is written as ``.sql``,
        # whose stem is ".sql", while its datasheet is ``datasheet_.md``.
        name = query.name.removesuffix(".sql")
        required.append(
            (f"data/datasheet_{name}.md", f"queries/primary/{query.name} exists")
        )
    return required


def check_files(entry: dict[str, Any], root: Path, problems: list[str]) -> None:
    for relative, why in required_files(entry, root):
        path = root / relative
        if not path.is_file():
            problems.append(f"{relative}: missing (required: {why})")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, ValueError) as error:
            problems.append(f"{relative}: cannot be read ({error})")
            continue
        if not text.strip():
            problems.append(f"{relative}: is empty")


def check(root: Path) -> list[str]:
    """Return every problem found under ``root`` (none means the record is sound)."""
    problems: list[str] = []
    entry = load_registry(root, problems)
    if entry is not None:
        check_registry(entry, problems)
        check_files(entry, root, problems)
    return problems


def main() -> int:
    problems = check(ROOT)
    for problem in problems:
        print(problem)
    print(f"governance check: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
