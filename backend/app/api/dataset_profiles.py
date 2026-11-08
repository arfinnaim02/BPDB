"""Research dataset planning over observed coverage; never certify or fit a model."""

import hashlib
from datetime import date

from fastapi import APIRouter, Response

from app.api.monitoring import DAILY_COLUMNS, Database
from app.api.preparation import encode
from app.api.quality import read_quality
from app.core.dataset_policy import CORE_METRICS, GOAL, PROPOSED_MODERN_START, RULE_VERSION

router = APIRouter(prefix="/api/v1/dataset", tags=["Research dataset strategy"])


def build_profiles(quality):
    start, end = quality.earliest_operational_date, quality.latest_operational_date
    modern = date.fromisoformat(PROPOSED_MODERN_START)
    by_grain = {(m.metric, m.unit, m.period, m.fuel): m for m in quality.metrics}
    variables = []
    for label, metric, unit, period, fuel in DAILY_COLUMNS:
        m = by_grain[(metric, unit, period, fuel)]
        years = {row.year: row.non_null_dates for row in m.by_year}
        modern_days = (end - modern).days + 1 if end and end >= modern else 0
        modern_observed = sum(n for y, n in years.items() if y >= modern.year)
        variables.append(
            {
                "metric": metric,
                "label": label,
                "unit": unit,
                "period": period,
                "fuel": fuel,
                "parser_support": (
                    "legacy_and_modern" if metric in CORE_METRICS else "modern_layout_only"
                ),
                "long_history_candidate": metric in CORE_METRICS,
                "earliest_observed_date": str(m.earliest_value_date)
                if m.earliest_value_date
                else None,
                "latest_observed_date": str(m.latest_value_date) if m.latest_value_date else None,
                "full_history_observed_days": m.non_null_dates,
                "full_history_calendar_days": quality.calendar_days,
                "full_history_calendar_coverage_percent": (
                    round(100 * m.non_null_dates / quality.calendar_days, 2)
                    if quality.calendar_days
                    else None
                ),
                "modern_observed_days": modern_observed,
                "modern_calendar_days": modern_days,
                "modern_missing_calendar_days": modern_days - modern_observed,
                "modern_calendar_coverage_percent": (
                    round(100 * modern_observed / modern_days, 2) if modern_days else None
                ),
                "experimental_weekly_preparation_allowed": metric in CORE_METRICS,
                "model_eligibility": "not_approved_by_availability_counts",
            }
        )
    profiles = [
        {
            "id": "long_history_core",
            "label": "Long-history core",
            "purpose": "Energy and supported core generation/evening-demand research.",
            "start_date": str(start) if start else None,
            "end_date": str(end) if end else None,
            ("boundary_status"): (
                "Current canonical bounds, not proof of comparable historical definitions."
            ),
            "metrics": [v["metric"] for v in variables if v["long_history_candidate"]],
            "joint_complete_eligible_dates": None,
            "eligibility_status": "requires_source_definition_and_joint_row_checks",
        },
        {
            "id": "modern_reporting",
            "label": "Modern reporting",
            "purpose": "Richer multivariable analysis and supported cost/demand research.",
            "start_date": PROPOSED_MODERN_START,
            "end_date": str(end) if end and end >= modern else None,
            ("boundary_status"): (
                "User-proposed conservative boundary; not a verified universal "
                "publication transition."
            ),
            "metrics": [v["metric"] for v in variables],
            "joint_complete_eligible_dates": None,
            "eligibility_status": "requires_variable_specific_and_joint_row_checks",
        },
    ]
    payload = {
        "rule_version": RULE_VERSION,
        "goal": GOAL,
        "generated_at": quality.generated_at.isoformat(),
        "scope": "Current national Page 1 coverage and research planning; no training approval.",
        "profiles": profiles,
        "variables": variables,
        "research_questions": [
            {
                "question": "Daily national energy forecasting",
                "profile": "long_history_core",
                "status": "candidate_after_original_recovery_and_eligibility_checks",
            },
            {
                "question": "Evening peak demand forecasting",
                "profile": "long_history_core",
                "status": "candidate_after_definition_and_issue_time_checks",
            },
            {
                "question": "Day peak demand / richer multivariable models",
                "profile": "modern_reporting",
                "status": "candidate_after_common_window_and_sample_size_checks",
            },
            {
                "question": "Next-month total production cost",
                "profile": "modern_reporting",
                "status": "requires_complete_original_months_and_enough_monthly_targets",
            },
            {
                "question": "Zonal load-shedding forecasting",
                "profile": None,
                "status": "requires_separate_validated_zonal_data_not_national_Page_1_proxies",
            },
        ],
        "rules": [
            "Recover original data before considering estimates.",
            (
                "Separate absent dates, unsupported fields, extraction failures, "
                "holds and unknown causes."
            ),
            (
                "Do not manufacture historical values for fields outside the "
                "supported reporting layout."
            ),
            (
                "Preserve unknown causes; missing canonical data is not proof that "
                "BPDB never published a report."
            ),
            (
                "Use eligible original targets only and fit treatments/scalers within "
                "chronological training folds."
            ),
            (
                "Check joint eligible dates and sample size at the target frequency, "
                "not marginal availability alone."
            ),
            "2025 has prior research exposure and cannot be declared a newly untouched final test.",
            (
                "Existing studies keep their frozen inputs; a changed dataset/design "
                "needs a dated version or amendment."
            ),
        ],
        "limitations": [
            (
                "Availability counts do not verify individual sources, definitions, "
                "review holds or publication-time eligibility."
            ),
            (
                "Legacy parser support is implementation capability, not a claim "
                "about every historical publication."
            ),
            (
                "The modern boundary is proposed; earlier supported observations are "
                "retained in the master dataset."
            ),
            "Joint eligible-row counts are not computed here; no training dataset is certified.",
            (
                "Incomplete energy/total-cost months cannot become observed monthly "
                "totals through filling."
            ),
            "No measurements, model coefficients, past results or schedules are changed.",
        ],
        ("identity_scope"): (
            "Coverage-plan identity only, not a frozen measurement-value fingerprint."
        ),
        "database_writes": 0,
        "models_fit": 0,
    }
    payload["coverage_assessment_id"] = hashlib.sha256(
        encode({k: v for k, v in payload.items() if k != "generated_at"})
    ).hexdigest()
    return payload


@router.get("/research-profiles")
def research_profiles(response: Response, session: Database):
    response.headers["Cache-Control"] = "no-store"
    return build_profiles(read_quality(session, gap_page=1, gap_page_size=1))
