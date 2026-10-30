"""A keyless stand-in for the data agent's language model (the Larkspur example).

The real data agent asks Claude to write its queries, quality checks, summary and
datasheets. This class answers the same five questions from text written in advance
by the author of this example, so the stage runs with no API key. What is real and
what is not:

* REAL: the agent, its graph, its SQL validation, and the database. The quality checks
  and the baseline query below are executed for real against ``larkspur_claims.db``
  and their pass/fail results are measured, not canned.
* STAND-IN: the SQL text and the datasheets. A model would have written different
  SQL, and might have missed or invented problems; these are the ones this author knew
  the synthetic data holds (``make_synthetic_db.py`` plants them).
* DERIVED: the summary. It is built from the executed checks' statuses and the one-line
  results the agent hands over, and nothing else, which is all a real model would see.

Convention the agent imposes on quality checks (``execute_qc`` in the data agent): a check
PASSES when its SQL returns at least one row and FAILS when it returns none. So each check
below is written to return a row exactly when its expectation holds.
"""

from __future__ import annotations

from textwrap import dedent

from model_project_constructor_data_agent.llm import BaselineQuerySpec

from model_project_constructor.agents.data.llm import (
    PrimaryQuerySpec,
    QualityCheckSpec,
    SummaryResult,
)
from model_project_constructor.schemas.v1.data import (
    DataRequest,
    Datasheet,
    DataSourceInventory,
    QualityCheck,
)


def _sql(text: str) -> str:
    return dedent(text).strip()


AS_OF = "(SELECT as_of_date FROM data_snapshot)"

TRAINING_SET = "fnol_training_set"
DECISION_TIMING = "total_loss_decision_timing"
MONTHLY_VOLUME = "monthly_volume_and_total_loss_rate"

PRIMARY_QUERIES = [
    PrimaryQuerySpec(
        name=TRAINING_SET,
        purpose=(
            "One row per physical-damage claim whose 60-day window has completed, with every "
            "first-notice feature the model may use and the outcome to predict. Features are "
            "those known at first notice only; the repair estimate and settlement fields are "
            "deliberately absent."
        ),
        expected_row_count_order="thousands",
        sql=_sql(f"""
            SELECT c.claim_id,
                   c.fnol_ts,
                   CAST(strftime('%Y', c.fnol_ts) AS INTEGER) - c.vehicle_year AS vehicle_age_years,
                   c.vehicle_acv_usd,
                   c.vehicle_class,
                   c.drivable AS drivable_flag,
                   c.airbags_deployed,
                   c.impact_zone,
                   c.tow_required,
                   c.peril,
                   c.coverage,
                   c.reported_lag_hours,
                   c.photo_count,
                   c.state,
                   CASE WHEN o.settlement_type = 'TOTAL_LOSS' THEN 1 ELSE 0 END AS is_total_loss
            FROM claim c
            JOIN claim_outcome o ON o.claim_id = c.claim_id
            WHERE c.fnol_ts <= date({AS_OF}, '-60 days')
        """),
    ),
    PrimaryQuerySpec(
        name=DECISION_TIMING,
        purpose=(
            "One row per claim that closed as a total loss, with the days from first notice to "
            "the total-loss decision and the carrying costs that accrued while waiting. Feeds the "
            "baseline metric and the value case."
        ),
        expected_row_count_order="thousands",
        sql=_sql("""
            SELECT c.claim_id,
                   c.fnol_ts,
                   o.tl_decision_ts,
                   julianday(o.tl_decision_ts) - julianday(c.fnol_ts) AS days_fnol_to_decision,
                   o.rental_days,
                   o.storage_days,
                   o.repair_started_before_tl,
                   o.paid_indemnity_usd
            FROM claim c
            JOIN claim_outcome o ON o.claim_id = c.claim_id
            WHERE o.settlement_type = 'TOTAL_LOSS'
        """),
    ),
    PrimaryQuerySpec(
        name=MONTHLY_VOLUME,
        purpose=(
            "Claims and total losses by first-notice month and state, for the monitoring plan "
            "and for sizing the holdout."
        ),
        expected_row_count_order="hundreds",
        sql=_sql("""
            SELECT strftime('%Y-%m', c.fnol_ts) AS fnol_month,
                   c.state,
                   COUNT(*) AS claims,
                   SUM(CASE WHEN o.settlement_type = 'TOTAL_LOSS' THEN 1 ELSE 0 END) AS total_losses
            FROM claim c
            JOIN claim_outcome o ON o.claim_id = c.claim_id
            WHERE o.settlement_type IS NOT NULL
            GROUP BY fnol_month, c.state
        """),
    ),
]

_MEDIAN_DAYS = """
    SELECT AVG(days) AS m FROM (
        SELECT julianday(o.tl_decision_ts) - julianday(c.fnol_ts) AS days
        FROM claim c JOIN claim_outcome o ON o.claim_id = c.claim_id
        WHERE o.settlement_type = 'TOTAL_LOSS'{window}
        ORDER BY days
        LIMIT 2 - (SELECT COUNT(*) FROM claim_outcome
                   WHERE settlement_type = 'TOTAL_LOSS'{bare}) % 2
        OFFSET (SELECT (COUNT(*) - 1) / 2 FROM claim_outcome
                WHERE settlement_type = 'TOTAL_LOSS'{bare})
    )
"""


def _median_days_sql(window: str = "", bare: str = "") -> str:
    return _sql(_MEDIAN_DAYS.format(window=window, bare=bare))


CHECKS: dict[str, list[QualityCheckSpec]] = {
    TRAINING_SET: [
        QualityCheckSpec(
            check_name="claim_ids_unique",
            expectation="Every claim_id appears once.",
            check_sql=_sql("""
                SELECT 1 AS ok
                WHERE (SELECT COUNT(*) FROM claim) = (SELECT COUNT(DISTINCT claim_id) FROM claim)
            """),
        ),
        QualityCheckSpec(
            check_name="every_claim_has_an_outcome_row",
            expectation="Every claim has a row in claim_outcome.",
            check_sql=_sql("""
                SELECT 1 AS ok
                WHERE NOT EXISTS (
                    SELECT 1 FROM claim c
                    LEFT JOIN claim_outcome o ON o.claim_id = c.claim_id
                    WHERE o.claim_id IS NULL
                )
            """),
        ),
        QualityCheckSpec(
            check_name="history_starts_in_january_2023",
            expectation="History starts in January 2023, as the stakeholder said.",
            check_sql=_sql("""
                SELECT first_day FROM (SELECT MIN(date(fnol_ts)) AS first_day FROM claim)
                WHERE first_day <= '2023-01-31'
            """),
        ),
        QualityCheckSpec(
            check_name="all_six_states_present",
            expectation="Claims come from all six states the company writes in.",
            check_sql=_sql("""
                SELECT n FROM (SELECT COUNT(DISTINCT state) AS n FROM claim) WHERE n = 6
            """),
        ),
        QualityCheckSpec(
            check_name="total_loss_rate_in_expected_band",
            expectation=(
                "Total losses are 6% to 12% of closed claims (the stakeholder said about 9%)."
            ),
            check_sql=_sql("""
                SELECT ROUND(rate, 4) AS total_loss_rate FROM (
                    SELECT AVG(CASE WHEN settlement_type = 'TOTAL_LOSS' THEN 1.0 ELSE 0.0 END)
                           AS rate
                    FROM claim_outcome WHERE settlement_type IS NOT NULL
                ) WHERE rate BETWEEN 0.06 AND 0.12
            """),
        ),
        QualityCheckSpec(
            check_name="no_claim_open_past_60_days",
            expectation=(
                "No claim older than 60 days is still open, so the outcome is known for "
                "every training row."
            ),
            check_sql=_sql(f"""
                SELECT 1 AS ok
                WHERE NOT EXISTS (
                    SELECT 1 FROM claim c JOIN claim_outcome o ON o.claim_id = c.claim_id
                    WHERE o.closed_ts IS NULL AND c.fnol_ts <= date({AS_OF}, '-60 days')
                )
            """),
        ),
        QualityCheckSpec(
            check_name="vehicle_value_positive_on_every_claim",
            expectation="The estimated vehicle value is present and above zero on every claim.",
            check_sql=_sql("""
                SELECT 1 AS ok
                WHERE NOT EXISTS (
                    SELECT 1 FROM claim WHERE vehicle_acv_usd IS NULL OR vehicle_acv_usd <= 0
                )
            """),
        ),
        QualityCheckSpec(
            check_name="drivable_flag_populated_on_every_claim",
            expectation="The drivable flag is populated on every claim.",
            check_sql=_sql("""
                SELECT 1 AS ok WHERE NOT EXISTS (SELECT 1 FROM claim WHERE drivable IS NULL)
            """),
        ),
        QualityCheckSpec(
            check_name="decision_never_before_first_notice",
            expectation="No total-loss decision is timestamped before the claim's first notice.",
            check_sql=_sql("""
                SELECT 1 AS ok
                WHERE NOT EXISTS (
                    SELECT 1 FROM claim c JOIN claim_outcome o ON o.claim_id = c.claim_id
                    WHERE o.tl_decision_ts < c.fnol_ts
                )
            """),
        ),
    ],
    DECISION_TIMING: [
        QualityCheckSpec(
            check_name="every_closed_total_loss_has_a_decision_time",
            expectation="Every closed total loss has a decision timestamp.",
            check_sql=_sql("""
                SELECT 1 AS ok
                WHERE NOT EXISTS (
                    SELECT 1 FROM claim_outcome
                    WHERE settlement_type = 'TOTAL_LOSS' AND tl_decision_ts IS NULL
                )
            """),
        ),
        QualityCheckSpec(
            check_name="median_days_near_the_stakeholder_figure",
            expectation=(
                "The median days from first notice to decision is between 4 and 6 "
                "(the stakeholder said 5)."
            ),
            check_sql=_sql(
                f"SELECT ROUND(m, 2) AS median_days FROM ({_median_days_sql()}) "
                "WHERE m BETWEEN 4.0 AND 6.0"
            ),
        ),
        QualityCheckSpec(
            check_name="teardown_share_near_one_in_sixteen",
            expectation=(
                "Between 4% and 8% of total losses had teardown started before the decision "
                "(the stakeholder said about one in sixteen)."
            ),
            check_sql=_sql("""
                SELECT ROUND(share, 4) AS teardown_share FROM (
                    SELECT AVG(repair_started_before_tl) AS share FROM claim_outcome
                    WHERE settlement_type = 'TOTAL_LOSS'
                ) WHERE share BETWEEN 0.04 AND 0.08
            """),
        ),
    ],
    MONTHLY_VOLUME: [
        QualityCheckSpec(
            check_name="all_34_months_present",
            expectation="Claims exist in each of the 34 months from January 2023 to October 2025.",
            check_sql=_sql("""
                SELECT months FROM (
                    SELECT COUNT(DISTINCT strftime('%Y-%m', fnol_ts)) AS months FROM claim
                ) WHERE months = 34
            """),
        ),
        QualityCheckSpec(
            check_name="monthly_volume_within_a_factor_of_two",
            expectation=(
                "No month has more than twice the claims of any other, so volume is stable "
                "enough to size a holdout."
            ),
            check_sql=_sql("""
                SELECT ROUND(ratio, 2) AS busiest_to_quietest FROM (
                    SELECT 1.0 * MAX(n) / MIN(n) AS ratio FROM (
                        SELECT COUNT(*) AS n FROM claim GROUP BY strftime('%Y-%m', fnol_ts)
                    )
                ) WHERE ratio < 2.0
            """),
        ),
    ],
}

DATASHEETS: dict[str, Datasheet] = {
    TRAINING_SET: Datasheet(
        motivation=(
            "To train and evaluate a model that scores each physical-damage claim, at first "
            "notice of loss, for the probability that it will end as a total loss."
        ),
        composition=(
            "One row per claim with a completed 60-day window: 37,600 of the 40,000 in the "
            "database at the default seed. Twelve first-notice features and one binary target, "
            "is_total_loss. SYNTHETIC: generated by make_synthetic_db.py for a fictitious company; "
            "no real claim, vehicle or person is represented."
        ),
        collection_process=(
            "Generated, not collected: a hidden repair cost per claim is drawn and a claim is a "
            "total loss when it reaches about 75% of the vehicle's value; the first-notice fields "
            "are drawn from that cost. The same seed reproduces the database."
        ),
        preprocessing=(
            "Vehicle age is derived from the model year and the notice date. No imputation, "
            "filtering of bad rows or encoding has been applied; the blank drivable flag and the "
            "zero vehicle values are left as found."
        ),
        uses=(
            "Exercising this tool and teaching with it. Not suitable for any decision about a real "
            "book of business: the relationships in it were put there by the generator."
        ),
        known_biases=[
            "The blank drivable flag occurs only on web-form claims, so channel and "
            "missingness are confounded and a model may learn the channel rather than the "
            "damage.",
            "A vehicle value of 0 (failed VIN decode, 173 claims at the default seed) distorts any "
            "feature built from value, such as a ratio, and must be handled before modeling.",
            "Vehicle value stands in for income, as the stakeholder warned; differences in who is "
            "flagged by value need review.",
            "760 claims are still open at the snapshot date and are not in this extract; the most "
            "recent 60 days of claims are absent by construction.",
        ],
        maintenance=(
            "Regenerate with make_synthetic_db.py. Nothing refreshes it, because it describes no "
            "real source system."
        ),
    ),
    DECISION_TIMING: Datasheet(
        motivation=(
            "To measure how long the total-loss decision takes today and what the wait costs, for "
            "the baseline metric and the value case."
        ),
        composition=(
            "One row per closed total loss, 3,517 at the default seed: first-notice and decision "
            "timestamps, rental and storage days, whether teardown was started, and the amount "
            "paid. SYNTHETIC."
        ),
        collection_process=(
            "Generated with a median of 5 days to decision and a 75th percentile of 8, as the "
            "stakeholder described, by make_synthetic_db.py."
        ),
        preprocessing=(
            "None. Days to decision is computed in the query from the two timestamps."
        ),
        uses="Computing the baseline median and sizing the saving; not for modeling.",
        known_biases=[
            "A handful of decision times were stamped before the first-notice time after the "
            "March 2024 platform change (a time-zone slip), which gives them a negative duration.",
            "Only claims that closed by the snapshot date are present, so very slow decisions on "
            "recent claims are missing.",
        ],
        maintenance="Regenerate with make_synthetic_db.py.",
    ),
    MONTHLY_VOLUME: Datasheet(
        motivation="To monitor volume and the total-loss rate over time and by state.",
        composition=(
            "One row per first-notice month and state, about 200 rows: claim counts and total-loss "
            "counts for closed claims. SYNTHETIC."
        ),
        collection_process="Aggregated by the query from the claim and claim_outcome tables.",
        preprocessing="Counts only; no smoothing.",
        uses="Monitoring and holdout sizing for the pilot.",
        known_biases=[
            "Recent months are undercounted because open claims are excluded, so the latest "
            "month's total-loss rate is not comparable with earlier months.",
        ],
        maintenance="Re-run the query on the live schedule once a real source exists.",
    ),
}


class ScriptedDataLLM:
    """The data agent's ``LLMClient`` protocol, answered from text written in advance."""

    def generate_primary_queries(
        self,
        request: DataRequest,
        previous_error: str | None = None,
        *,
        data_source_inventory: DataSourceInventory | None = None,
    ) -> list[PrimaryQuerySpec]:
        return list(PRIMARY_QUERIES)

    def generate_quality_checks(
        self, request: DataRequest, primary_queries: list[PrimaryQuerySpec]
    ) -> list[list[QualityCheckSpec]]:
        return [list(CHECKS[query.name]) for query in primary_queries]

    def summarize(
        self,
        request: DataRequest,
        primary_queries: list[PrimaryQuerySpec],
        quality_checks: list[list[QualityCheck]],
        db_executed: bool,
    ) -> SummaryResult:
        """Built only from what the agent hands over: each check's status and one-line result."""
        flat = [check for group in quality_checks for check in group]
        passed = [c for c in flat if c.execution_status == "PASSED"]
        failed = [c for c in flat if c.execution_status == "FAILED"]
        errored = [c for c in flat if c.execution_status == "ERROR"]
        names = ", ".join(q.name for q in primary_queries)
        summary = (
            f"{len(primary_queries)} primary queries ({names}) and {len(flat)} quality checks. "
            + (
                f"The checks were executed against the database: {len(passed)} passed, "
                f"{len(failed)} failed, {len(errored)} errored."
                if db_executed
                else "The checks were not executed (the database was not reachable)."
            )
        )
        if failed:
            summary += " Failed: " + ", ".join(c.check_name for c in failed) + "."
        return SummaryResult(
            summary=summary,
            confirmed_expectations=[c.expectation for c in passed],
            unconfirmed_expectations=[c.expectation for c in failed + errored],
            data_quality_concerns=[
                f"{c.check_name}: the check returned no rows, so the expectation does not hold "
                f'("{c.expectation}")'
                for c in failed
            ]
            + [f"{c.check_name}: {c.result_summary}" for c in errored],
        )

    def generate_datasheet(
        self, request: DataRequest, primary_query: PrimaryQuerySpec
    ) -> Datasheet:
        return DATASHEETS[primary_query.name]

    def generate_baseline_query(
        self,
        request: DataRequest,
        metric_name: str,
        metric_definition: str,
        measurement_window: str,
    ) -> BaselineQuerySpec:
        window = f"\n          AND o.closed_ts > date({AS_OF}, '-12 months')"
        bare = f" AND closed_ts > date({AS_OF}, '-12 months')"
        return BaselineQuerySpec(
            metric_name=metric_name,
            sql=_median_days_sql(window=window, bare=bare),
            measurement_unit="days",
        )
