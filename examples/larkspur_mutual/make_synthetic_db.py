"""Build the fictitious Larkspur Mutual claims database (SQLite, standard library only).

Larkspur Mutual is FICTIONAL and so is every row here: the data is generated, not
sampled from or about any real insurer, policyholder or vehicle. Run from the
repository root::

    uv run python examples/larkspur_mutual/make_synthetic_db.py

writes ``out/larkspur_claims.db``. The same seed gives the same database on the same
machine, and only ``random.random()`` is used (the other ``random`` methods may change
between Python versions; ``random()`` is guaranteed not to). ``math.exp``, ``log`` and
``cos`` can differ in the last bit between platforms, so a different platform may
produce a slightly different database; ``run_example.py`` checks the counts the
datasheets quote and says so if they move.

How the data is made, so a reader can judge what it can and cannot show:

* Each claim draws a hidden repair cost, and the car is a total loss when that cost
  reaches about 75% of its value (the rule of thumb carriers use, with noise for local
  labour rates and salvage). One multiplier on every cost is searched so that 9% of
  claims end as total losses, matching the interview.
* What the claims system would record at first notice (airbags, drivable, tow, ...) is
  drawn from that hidden cost, so a model can learn real structure from it.
* Days from first notice to a total-loss decision have a median of 5 and a 75th
  percentile of 8, as the stakeholder said.
* Three problems from the interview are planted on purpose, so that quality checks have
  something true to find: a blank ``drivable`` flag on some web-form claims, an estimated
  value of 0 where the VIN decode failed, and a few decision times stamped before the
  first-notice time after the March 2024 platform change.

None of this makes the data realistic enough to train a model whose results mean
anything for a real book of business; it makes it structured enough to exercise the
pipeline honestly.
"""

from __future__ import annotations

import math
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"

SEED = 20251031
N_CLAIMS = 40_000
START = datetime(2023, 1, 1)
AS_OF = datetime(2025, 10, 31)
PLATFORM_CHANGE = datetime(2024, 3, 1)
TARGET_TOTAL_LOSS_RATE = 0.09
N_DRAWS = 16  # one uniform per decision below, so unrelated fields are not correlated

# (value, weight, ...) tuples, picked by weight
STATES = (("IA", 0.10), ("IL", 0.28), ("IN", 0.14), ("MN", 0.14), ("OH", 0.22), ("WI", 0.12))
CLASSES = (  # (class, share, value in USD of the vehicle new)
    ("SEDAN", 0.26, 27_000),
    ("SUV", 0.30, 38_000),
    ("PICKUP", 0.16, 42_000),
    ("COMPACT", 0.15, 22_000),
    ("VAN", 0.05, 36_000),
    ("LUXURY", 0.08, 62_000),
)
CHANNELS = (("PHONE", 0.45), ("APP", 0.30), ("WEB", 0.25))
COLLISION_ZONES = (
    ("FRONT", 0.40),
    ("REAR", 0.28),
    ("SIDE", 0.24),
    ("MULTIPLE", 0.05),
    ("ROLLOVER", 0.03),
)
ZONE_COST_FACTOR = {"FRONT": 1.15, "REAR": 0.85, "SIDE": 1.0, "MULTIPLE": 1.5, "ROLLOVER": 2.2}
COMPREHENSIVE_SHARE = 0.22
# comprehensive peril -> (share of comprehensive claims, median repair cost USD, log-sigma)
PERILS = {
    "HAIL": (0.35, 2_800, 0.6),
    "ANIMAL": (0.25, 3_000, 0.6),
    "THEFT": (0.15, 4_500, 0.9),
    "VANDALISM": (0.10, 1_800, 0.7),
    "FIRE": (0.05, 14_000, 0.9),
    "FLOOD": (0.10, 11_000, 0.8),
}
PERIL_NOT_DRIVABLE = {"FIRE": 0.90, "FLOOD": 0.90, "THEFT": 0.40}
COLLISION_MEDIAN_COST, COLLISION_SIGMA = 3_200, 0.85
LUXURY_REPAIR_FACTOR = 1.35
MEDIAN_DAYS_TO_DECISION, DAYS_LOG_SIGMA = 5.0, 0.697  # sigma puts the 75th percentile at 8 days

SCHEMA = """
CREATE TABLE data_snapshot (
    as_of_date TEXT NOT NULL
);
CREATE TABLE claim (
    claim_id           TEXT PRIMARY KEY,
    fnol_ts            TEXT NOT NULL,   -- first notice of loss, 'YYYY-MM-DD HH:MM:SS'
    fnol_channel       TEXT NOT NULL,   -- PHONE | APP | WEB
    state              TEXT NOT NULL,
    coverage           TEXT NOT NULL,   -- COLLISION | COMPREHENSIVE
    peril              TEXT NOT NULL,
    vehicle_class      TEXT NOT NULL,
    vehicle_year       INTEGER NOT NULL,
    vehicle_acv_usd    REAL,            -- vendor VIN-decode estimate; 0 where the decode failed
    drivable           INTEGER,         -- 1 | 0 | NULL (blank on some web-form claims)
    airbags_deployed   INTEGER NOT NULL,
    impact_zone        TEXT NOT NULL,
    tow_required       INTEGER NOT NULL,
    police_report      INTEGER NOT NULL,
    photo_count        INTEGER NOT NULL,
    reported_lag_hours REAL NOT NULL
);
CREATE TABLE claim_outcome (
    claim_id                  TEXT PRIMARY KEY REFERENCES claim (claim_id),
    closed_ts                 TEXT,     -- NULL while the claim is open
    settlement_type           TEXT,     -- TOTAL_LOSS | REPAIR | CLOSED_NO_PAY; NULL while open
    tl_decision_ts            TEXT,     -- when the total-loss decision was made
    repair_started_before_tl  INTEGER,  -- 1 where a shop began teardown that was then reversed
    paid_indemnity_usd        REAL,
    rental_days               INTEGER,
    storage_days              INTEGER
);
CREATE INDEX idx_claim_fnol ON claim (fnol_ts);
"""


def _gauss(rng: random.Random) -> float:
    """Standard normal from two ``random()`` draws (Box-Muller)."""
    u1 = 1.0 - rng.random()  # in (0, 1], so the log is finite
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * rng.random())


def _pick(rng: random.Random, options: tuple[tuple[Any, ...], ...]) -> tuple[Any, ...]:
    x = rng.random() * sum(option[1] for option in options)
    for option in options:
        x -= option[1]
        if x <= 0:
            return option
    return options[-1]


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _ts(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%d %H:%M:%S")


def _draw_claims(rng: random.Random) -> list[dict[str, Any]]:
    """Every random draw a claim needs, except the ones that depend on the cost multiplier."""
    span = (AS_OF - START).total_seconds()
    claims = []
    for _ in range(N_CLAIMS):
        fnol = START + timedelta(seconds=int(rng.random() * span))
        vclass, _, new_value = _pick(rng, CLASSES)
        age = min(18, int(-7.0 * math.log(1.0 - rng.random())))
        value = max(1_500.0, new_value * 0.88**age * math.exp(0.12 * _gauss(rng)))
        comprehensive = rng.random() < COMPREHENSIVE_SHARE
        if comprehensive:
            peril = _pick(rng, tuple((p, v[0]) for p, v in PERILS.items()))[0]
            _, median_cost, sigma = PERILS[peril]
            zone = "FRONT" if peril == "ANIMAL" and rng.random() < 0.8 else "NOT_APPLICABLE"
        else:
            peril = "COLLISION"
            median_cost, sigma = COLLISION_MEDIAN_COST, COLLISION_SIGMA
            zone = _pick(rng, COLLISION_ZONES)[0]
        cost = median_cost * math.exp(sigma * _gauss(rng)) * ZONE_COST_FACTOR.get(zone, 1.0)
        if vclass == "LUXURY":
            cost *= LUXURY_REPAIR_FACTOR
        claims.append(
            {
                "fnol": fnol,
                "state": _pick(rng, STATES)[0],
                "channel": _pick(rng, CHANNELS)[0],
                "class": vclass,
                "age": age,
                "value": value,
                "comprehensive": comprehensive,
                "peril": peril,
                "zone": zone,
                "cost": cost,
                "threshold": 0.75 * value * math.exp(0.10 * _gauss(rng)),
                "u": [rng.random() for _ in range(N_DRAWS)],
                "z": [_gauss(rng) for _ in range(2)],
            }
        )
    return claims


def _calibrate_multiplier(claims: list[dict[str, Any]]) -> float:
    """The cost multiplier at which 9% of claims are total losses (bisection)."""
    lo, hi = 0.05, 20.0
    for _ in range(60):
        mid = (lo + hi) / 2
        rate = sum(c["cost"] * mid >= c["threshold"] for c in claims) / len(claims)
        if rate < TARGET_TOTAL_LOSS_RATE:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _claim_row(claim_id: str, c: dict[str, Any], cost: float) -> tuple[Any, ...]:
    """What the claims system records at first notice, drawn from the hidden cost."""
    u, z = c["u"], c["z"]
    log_cost = math.log(cost / 1000.0)
    not_drivable_p = PERIL_NOT_DRIVABLE.get(c["peril"], _sigmoid(2.2 * (log_cost - math.log(4.5))))
    not_drivable = u[0] < not_drivable_p
    c["not_drivable"] = not_drivable  # the truth; the recorded flag below may be blanked
    tow = u[1] < (0.88 if not_drivable else 0.03)
    airbags = (not c["comprehensive"]) and u[2] < _sigmoid(3.0 * (log_cost - math.log(6.0)))
    if c["peril"] == "THEFT":
        police_p = 0.90
    elif c["comprehensive"]:
        police_p = 0.10
    else:
        police_p = 0.35 + 0.40 * not_drivable
    photos = max(0, min(15, round((2.0 if c["channel"] == "PHONE" else 5.0) + 1.6 * z[0])))
    lag_mean = 16.0 if not c["comprehensive"] else (60.0 if c["peril"] == "HAIL" else 30.0)
    lag = round(-lag_mean * math.log(1.0 - u[4]), 1)
    value_recorded = 0.0 if u[5] < 0.004 else round(c["value"], 0)  # 0: the VIN decode failed
    drivable: int | None = 0 if not_drivable else 1
    if c["channel"] == "WEB" and u[6] < 0.12:
        drivable = None  # blank on the web form
    return (
        claim_id,
        _ts(c["fnol"]),
        c["channel"],
        c["state"],
        "COMPREHENSIVE" if c["comprehensive"] else "COLLISION",
        c["peril"],
        c["class"],
        c["fnol"].year - c["age"],
        value_recorded,
        drivable,
        int(airbags),
        c["zone"],
        int(tow),
        int(police_p > u[3]),
        photos,
        lag,
    )


def _outcome_row(
    claim_id: str, c: dict[str, Any], cost: float, claim_row: tuple[Any, ...]
) -> tuple[Any, ...]:
    """How the claim ends, and when, as the snapshot date sees it."""
    u, z = c["u"], c["z"]
    fnol: datetime = c["fnol"]
    deductible = 500 if u[7] < 0.6 else 1000
    not_drivable_and_towed = c["not_drivable"] and claim_row[12] == 1
    decision: datetime | None = None
    teardown: int | None = None
    if cost >= c["threshold"]:
        settlement = "TOTAL_LOSS"
        log_days = math.log(MEDIAN_DAYS_TO_DECISION) + DAYS_LOG_SIGMA * z[1]
        days = min(40.0, max(0.3, math.exp(log_days)))
        decision = fnol + timedelta(days=days)
        if fnol >= PLATFORM_CHANGE and u[8] < 0.006:
            decision = fnol - timedelta(hours=5 if u[13] < 0.5 else 6)  # the time-zone slip
        closed = min(decision + timedelta(days=8 + 12 * u[10]), fnol + timedelta(days=55))
        teardown = int(u[11] < 0.06)
        rental = 0 if u[12] > 0.9 else math.ceil(days) + 2 + int(u[13] * 3)
        storage = math.ceil(days) if not_drivable_and_towed else 0
        paid = max(0.0, round(c["value"] * (0.97 + 0.03 * u[9]) - deductible, 2))
    elif u[14] < 0.04:
        settlement, closed = "CLOSED_NO_PAY", fnol + timedelta(days=5 + 20 * u[10])
        paid, rental, storage = 0.0, 0, 0
    else:
        settlement, closed = "REPAIR", fnol + timedelta(days=8 + 22 * u[10])
        paid = max(0.0, round(cost - deductible, 2))
        if u[12] < 0.45:
            rental = 0  # no rental coverage
        elif c["not_drivable"]:
            rental = 3 + int(9 * u[15])  # not drivable: a longer rental
        else:
            rental = 2 + int(5 * u[15])
        storage = 0
    if closed > AS_OF:  # still open at the snapshot date: nothing is known yet
        return (claim_id, None, None, None, None, None, None, None)
    decided = decision if (decision is not None and decision <= AS_OF) else None
    return (
        claim_id,
        _ts(closed),
        settlement,
        _ts(decided) if decided else None,
        teardown,
        paid,
        rental,
        storage,
    )


def build(path: Path = OUT / "larkspur_claims.db") -> dict[str, float]:
    """Create the database at ``path`` (replacing any there) and return its headline figures."""
    path.parent.mkdir(exist_ok=True)
    for suffix in ("", "-shm", "-wal", "-journal"):
        Path(f"{path}{suffix}").unlink(missing_ok=True)

    claims = _draw_claims(random.Random(SEED))
    multiplier = _calibrate_multiplier(claims)
    claims.sort(key=lambda c: c["fnol"])

    claim_rows: list[tuple[Any, ...]] = []
    outcome_rows: list[tuple[Any, ...]] = []
    per_year: dict[int, int] = {}
    for c in claims:
        year = c["fnol"].year
        per_year[year] = per_year.get(year, 0) + 1
        claim_id = f"LM-{year}-{per_year[year]:06d}"
        cost = c["cost"] * multiplier
        row = _claim_row(claim_id, c, cost)
        claim_rows.append(row)
        outcome_rows.append(_outcome_row(claim_id, c, cost, row))

    connection = sqlite3.connect(path)
    try:
        connection.executescript(SCHEMA)
        connection.execute("INSERT INTO data_snapshot VALUES (?)", (AS_OF.strftime("%Y-%m-%d"),))
        marks = ",".join
        connection.executemany(f"INSERT INTO claim VALUES ({marks('?' * 16)})", claim_rows)
        connection.executemany(f"INSERT INTO claim_outcome VALUES ({marks('?' * 8)})", outcome_rows)
        connection.commit()
        figures = _headline_figures(connection)
    finally:
        connection.close()
    figures["cost_multiplier"] = round(multiplier, 4)
    return figures


def _headline_figures(connection: sqlite3.Connection) -> dict[str, float]:
    """Ground truth read back from the finished database, for checking reports against."""

    def one(sql: str) -> float:
        value = connection.execute(sql).fetchone()[0]
        return float(value) if value is not None else float("nan")

    ordered = [
        row[0]
        for row in connection.execute(
            "SELECT julianday(o.tl_decision_ts) - julianday(c.fnol_ts) FROM claim c "
            "JOIN claim_outcome o ON o.claim_id = c.claim_id "
            "WHERE o.settlement_type = 'TOTAL_LOSS' AND o.tl_decision_ts >= c.fnol_ts ORDER BY 1"
        )
    ]
    return {
        "claims": one("SELECT COUNT(*) FROM claim"),
        "training_rows": one(
            "SELECT COUNT(*) FROM claim "
            "WHERE fnol_ts <= date((SELECT as_of_date FROM data_snapshot), '-60 days')"
        ),
        "closed_total_losses": one(
            "SELECT COUNT(*) FROM claim_outcome WHERE settlement_type = 'TOTAL_LOSS'"
        ),
        "open_claims": one("SELECT COUNT(*) FROM claim_outcome WHERE settlement_type IS NULL"),
        "total_loss_rate_of_closed": round(
            one(
                "SELECT AVG(settlement_type = 'TOTAL_LOSS') FROM claim_outcome "
                "WHERE settlement_type IS NOT NULL"
            ),
            4,
        ),
        "median_days_to_decision": round(ordered[len(ordered) // 2], 2),
        "p75_days_to_decision": round(ordered[(3 * len(ordered)) // 4], 2),
        "planted_acv_zero": one("SELECT COUNT(*) FROM claim WHERE vehicle_acv_usd = 0"),
        "planted_drivable_null": one("SELECT COUNT(*) FROM claim WHERE drivable IS NULL"),
        "planted_decision_before_fnol": one(
            "SELECT COUNT(*) FROM claim c JOIN claim_outcome o ON o.claim_id = c.claim_id "
            "WHERE o.tl_decision_ts < c.fnol_ts"
        ),
        "teardown_share_of_total_losses": round(
            one(
                "SELECT AVG(repair_started_before_tl) FROM claim_outcome "
                "WHERE settlement_type = 'TOTAL_LOSS'"
            ),
            4,
        ),
    }


if __name__ == "__main__":
    for name, value in build().items():
        print(f"  {name:34s} {value:,}")
