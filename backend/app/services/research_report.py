"""Snapshot-consistent reporting over retained experiments and prospective issues."""

import csv
import hashlib
import io
import math
from datetime import datetime, timezone
from pathlib import Path

from app.api.experiments import load_comparison, load_experiment
from app.api.final_evaluation import load_final
from app.api.forecasts import read_history
from app.api.monitoring import read_summary
from app.api.preparation import encode
from app.services.research_detail import detailed_markdown, details

SCHEMA = "bpdb_research_report_v1"
METHODS = (
    "latest_report",
    "weekly",
    "ridge",
    "autoregression",
    "random_forest",
    "gradient_boosting",
)
NAMES = {
    "latest_report": "Latest report (lag 2)",
    "weekly": "Same weekday (lag 7)",
    "ridge": "Ridge",
    "autoregression": "OLS (primary)",
    "random_forest": "Random Forest",
    "gradient_boosting": "Gradient Boosting",
}
FIGURES = ("models", "daily", "monthly", "scatter")


def build_report(inventory, history, generated_at=None):
    development, final, first = load_comparison(), load_final(), load_experiment()
    if development["experiment_id"] != final["reference_experiment_id"]:
        raise ValueError("Model comparison and final evaluation do not match")
    history = {k: v for k, v in history.items() if k != "generated_at"}
    inventory = {k: v for k, v in inventory.items() if k != "generated_at"}
    # Bind the summary to retained first-issue/actual pairs, not just an untraceable aggregate.
    evidence = history.get("summary_evidence", [])
    scored = [r for r in evidence if r["outcome"]]
    if len(scored) != history["summary"]["scored_dates"]:
        raise ValueError("Prospective summary evidence is incomplete")
    if len(evidence) != history["summary"]["completed_targets_with_forecast"]:
        raise ValueError("Prospective forecast coverage evidence is incomplete")
    if (
        len(history.get("attempted_target_dates", []))
        != history["summary"]["completed_targets_attempted"]
    ):
        raise ValueError("Prospective attempt coverage evidence is incomplete")
    if scored:
        errors = [float(row["outcome"]["signed_error"]) for row in scored]
        expected = {
            "mae": sum(abs(e) for e in errors) / len(errors),
            "rmse": math.sqrt(sum(e * e for e in errors) / len(errors)),
            "bias": sum(errors) / len(errors),
        }
        if any(abs(value - history["summary"][key]) > 1e-8 for key, value in expected.items()):
            raise ValueError("Prospective summary does not match retained evidence")
    elif any(history["summary"][key] is not None for key in ("mae", "rmse", "bias")):
        raise ValueError("Empty prospective scores must remain unavailable")
    scores = {r["model"]: r for r in final["scores"]}
    base, primary = (
        scores["latest_report"]["common_dates"],
        scores["autoregression"]["common_dates"],
    )
    report = {
        "schema": SCHEMA,
        "title": "BPDB energy forecasting research report",
        "scope": "Research evidence and methods/results support, not a complete submitted thesis",
        "generated_at": (generated_at or datetime.now(timezone.utc)).isoformat(),
        "source_ids": {
            "snapshot": final["snapshot_id"],
            "release1": first["experiment_id"],
            "release2": development["experiment_id"],
            "release3": final["experiment_id"],
            "final_evaluation_key": final["evaluation_key"],
            "prospective_model": history["model"]["model_id"],
        },
        "code_sha256": {
            p.name: hashlib.sha256(p.read_text(encoding="utf-8").encode()).hexdigest()
            for p in (
                Path(__file__),
                Path(__file__).with_name("report_pdf.py"),
                Path(__file__).with_name("research_detail.py"),
            )
        },
        "study": {
            "target": "National daily energy generated",
            "unit": "million kWh",
            "training": "2020-2023",
            "validation": "2024",
            "final_test": "2025",
            "primary_model": "autoregression",
            "test_fit_cutoff": "2024-12-30",
            "last_usable_fit_label": final["models"]["autoregression"]["last_label"],
            "fit_rows": final["models"]["autoregression"]["rows"],
            "input_policy": "Exact original previous-week donor for missing past inputs",
            "issue_scenario": "Noon Asia/Dhaka on T-1; latest original input T-2",
            "strict_historical_feature_days": final["strict_availability_feature_days"],
            "feature_names": final["feature_names"],
        },
        "coverage": final["coverage"],
        "training_selection": development["training_ranking"],
        "validation_scores": development["validation"],
        "test_scores": final["scores"],
        "test_monthly": final["monthly"],
        "test_predictions": final["predictions"],
        "paired_sensitivity": final["paired_mae_sensitivity"],
        "effect": {
            "primary_mae": primary["mae"],
            "baseline_mae": base["mae"],
            "common_dates": primary["n"],
            "mae_reduction_percent": 100 * (base["mae"] - primary["mae"]) / base["mae"],
        },
        "current_inventory": inventory,
        "prospective": history,
        "limitations": [
            (
                "Historical publication times are unknown; the 2025 results assume"
                " the stated reporting-delay scenario and current canonical "
                "revisions, not verified point-in-time availability."
            ),
            (
                "OLS was selected before final-test scoring. Ridge is practically "
                "tied; no post-test switching, universal superiority, causal "
                "conclusion or significance claim is supported."
            ),
            (
                "Missing or held targets remain unscored. Common-date results and "
                "forecast coverage must be read together; own-date scores use "
                "different samples."
            ),
            (
                "Circular-block ranges are descriptive dependence sensitivity, not"
                " future prediction intervals or calibrated significance tests."
            ),
            (
                "Prospective issues use actual capture/issue times and a saved "
                "older model. Unknown official timestamps, model age, changing "
                "conditions and input substitution can affect performance."
            ),
            (
                "The prospective summary is a separate 90-day log using earliest "
                "successful issues and latest retained actual revisions. A small "
                "or empty scored sample does not establish current reliability."
            ),
            (
                "Current database inventory and prospective rows can change; "
                "frozen model-study results do not. Capture the report JSON and "
                "identifiers to preserve this report snapshot."
            ),
            (
                "This evidence report supports thesis writing but is not a "
                "complete literature review, institution-specific thesis or "
                "independent verification of every original PDF measurement."
            ),
        ],
    }
    report["details"] = details(report)
    report["report_id"] = hashlib.sha256(
        encode({k: v for k, v in report.items() if k != "generated_at"})
    ).hexdigest()
    return report


def read_report(session):
    return build_report(
        read_summary(session).model_dump(mode="json"),
        read_history(session, 100, include_evidence=True),
    )


def tables_csv(report):
    out = io.StringIO(newline="")
    w = csv.writer(out)
    w.writerow(
        [
            "Stage",
            "Method",
            "Common Dates",
            "MAE (million kWh)",
            "RMSE (million kWh)",
            "Bias (million kWh)",
            "Own Scored Dates",
            "Calendar Forecasts",
            "Calendar Days",
        ]
    )
    for stage, key, days in (
        ("Validation 2024", "validation_scores", 366),
        ("Final test 2025", "test_scores", 365),
    ):
        for r in report[key]:
            c = r["common_dates"]
            w.writerow(
                [
                    stage,
                    NAMES[r["model"]],
                    c["n"],
                    c["mae"],
                    c["rmse"],
                    c["bias"],
                    r["own_dates"]["n"],
                    r["calendar_forecasts"],
                    days,
                ]
            )
    return out.getvalue().encode("utf-8-sig")


def methods_markdown(r):
    e, s, p = r["effect"], r["study"], r["prospective"]["summary"]
    lines = [
        "# BPDB energy forecasting - methods and results evidence",
        "",
        "This is generated research evidence, not a complete submitted thesis.",
        "",
        f"Report snapshot: `{r['report_id']}`",
        f"Generated at: {r['generated_at']}",
        "",
        "## Data and chronological design",
        "",
        (
            "The target is national daily energy generated in million kWh. "
            "Original source values, calendar gaps and source/version lineage "
            "are retained. Training used 2020-2023; 2024 was the validation "
            "year; 2025 was evaluated only after model settings and the OLS "
            "primary choice were fixed."
        ),
        "",
        (
            "Three expanding full-year training origins selected settings "
            "using identical common dates. Nine lag/calendar features and "
            "original previous-week input substitution were fixed. Labels and "
            "evaluation targets were not imputed. Scaling was fitted on "
            "training data."
        ),
        "",
        (
            f"Final models were refitted once with nominal cutoff "
            f"{s['test_fit_cutoff']}, using {s['fit_rows']} usable rows. The "
            f"actual last usable fitting label was "
            f"{s['last_usable_fit_label']}. Earlier 2025 originals could enter "
            f"later origin features, but test-year labels never updated model "
            f"parameters."
        ),
        "",
        (
            "Historical issue time was assumed to be noon Bangladesh on T-1, "
            "with latest original input T-2. Strict verified historical "
            "feature coverage is 0/365 final-test days, so this is not a "
            "verified point-in-time backtest."
        ),
        "",
        "## Retained historical results",
        "",
        "| Stage | Method | Common dates | MAE | RMSE | Bias |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for stage, key in (
        ("Validation 2024", "validation_scores"),
        ("Final test 2025", "test_scores"),
    ):
        for row in r[key]:
            c = row["common_dates"]
            lines.append(
                (
                    f"| {stage} | {NAMES[row['model']]} | {c['n']} | {c['mae']:.4f} | "
                    f"{c['rmse']:.4f} | {c['bias']:.4f} |"
                )
            )
    lines += [
        "",
        (
            f"On {e['common_dates']} identical final-test dates, primary OLS "
            f"MAE was {e['primary_mae']:.4f} million kWh versus "
            f"{e['baseline_mae']:.4f} for exact lag 2, a descriptive reduction "
            f"of {e['mae_reduction_percent']:.2f}%. Ridge was practically "
            f"equivalent; OLS remained the predefined primary model. The tested "
            f"tree configurations did not improve this MAE comparison."
        ),
        "",
        (
            "Calendar forecast coverage and own scored dates differ across "
            "methods. Validation and final test use different years/samples "
            "and final models were refitted; year-to-year errors are not a "
            "paired comparison."
        ),
        "",
        "## Prospective log - separate from the historical test",
        "",
        (
            f"Window: {p['window_start']} through {p['window_end']}. Completed "
            f"target dates attempted: {p['completed_targets_attempted']}; dates "
            f"with a forecast: {p['completed_targets_with_forecast']}; paired "
            f"scored dates: {p['scored_dates']}. Prospective MAE: "
            f"{p['mae'] if p['mae'] is not None else 'not available'}."
        ),
        "",
        (
            "Each prospective record freezes actual issue/capture times and "
            "source versions. The earliest successful issue per target is "
            "compared with its latest retained actual revision. Missing "
            "actuals remain blank. These prospective counts are not copied "
            "from the historical evaluation."
        ),
        "",
        "## Limitations",
        "",
    ]
    lines += ["- " + text for text in r["limitations"]]
    lines += ["", "## Reproducibility identifiers", ""]
    lines += [f"- {k}: `{v}`" for k, v in r["source_ids"].items()]
    lines += [
        "",
        "## Implementation and methodology references",
        "",
        "- Official BPDB archive: https://misc.bpdb.gov.bd/daily-generation-archive",
        (
            "- Forecasting: Principles and Practice, forecast evaluation: "
            "https://otexts.com/fpp3/toolbox.html"
        ),
        (
            "- scikit-learn, train-only preprocessing: https://scikit-"
            "learn.org/stable/common_pitfalls.html"
        ),
        (
            "- arch, time-series bootstrap forms: "
            "https://bashtage.github.io/arch/bootstrap/timeseries-"
            "bootstraps.html"
        ),
        "",
    ]
    return "\n".join(lines) + detailed_markdown(r)
