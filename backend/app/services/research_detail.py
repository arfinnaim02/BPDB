"""Descriptive detail from frozen predictions; never fit or select a new model."""

import math
import statistics
from html import escape

KEYS = ("latest_report", "weekly", "ridge", "autoregression", "random_forest", "gradient_boosting")
SHORT = ("Lag 2", "Lag 7", "Ridge", "OLS", "Forest", "Boosting")


def quantile(values, probability):
    ordered = sorted(values)
    if not ordered:
        return None
    position = (len(ordered) - 1) * probability
    low, high = math.floor(position), math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def details(report):
    common = [
        r
        for r in report["test_predictions"]
        if r["actual"] is not None and all(r[k] is not None for k in KEYS)
    ]
    rows = []
    baseline = [abs(r["latest_report"] - r["actual"]) for r in common]
    for key in KEYS:
        errors = [r[key] - r["actual"] for r in common]
        absolute = [abs(e) for e in errors]
        mae = statistics.mean(absolute) if absolute else None
        mean_actual = statistics.mean(r["actual"] for r in common) if common else None
        rows.append(
            {
                "model": key,
                "n": len(common),
                "median_absolute_error": quantile(absolute, 0.5),
                "p90_absolute_error": quantile(absolute, 0.9),
                "p95_absolute_error": quantile(absolute, 0.95),
                "maximum_absolute_error": max(absolute, default=None),
                "mean_actual": mean_actual,
                "mae_percent_of_mean_actual": 100 * mae / mean_actual if mean_actual else None,
                "underprediction_days": sum(e < 0 for e in errors),
                "overprediction_days": sum(e > 0 for e in errors),
                "exact_days": sum(e == 0 for e in errors),
                "beats_lag2_days": sum(a < b for a, b in zip(absolute, baseline)),
                "ties_lag2_days": sum(a == b for a, b in zip(absolute, baseline)),
                "loses_lag2_days": sum(a > b for a, b in zip(absolute, baseline)),
            }
        )
    largest = sorted(common, key=lambda r: (-abs(r["autoregression"] - r["actual"]), r["date"]))[
        :15
    ]
    monthly = []
    for month in report["test_monthly"]:
        observed = [
            r["actual"]
            for r in report["test_predictions"]
            if r["date"].startswith(month["month"]) and r["actual"] is not None
        ]
        ols = next(s for s in month["scores"] if s["model"] == "autoregression")
        monthly.append(
            {
                "month": month["month"],
                "calendar_days": month["calendar_days"],
                "observed_days": len(observed),
                "observed_mean": statistics.mean(observed) if observed else None,
                "observed_minimum": min(observed, default=None),
                "observed_maximum": max(observed, default=None),
                "ols_forecasts": ols["calendar_forecasts"],
                "ols_own_scored": ols["own_dates"]["n"],
                "common_scored": ols["common_dates"]["n"],
            }
        )
    return {
        "scope": (
            "Post-evaluation descriptive diagnostics on retained frozen "
            "predictions; no model reselection"
        ),
        "quantile_rule": "Linear interpolation at (n-1)*p (type 7)",
        "common_diagnostics": rows,
        "monthly_coverage": monthly,
        "largest_ols_errors": [
            {
                "date": r["date"],
                "actual": r["actual"],
                "prediction": r["autoregression"],
                "signed_error": r["autoregression"] - r["actual"],
                "absolute_error": abs(r["autoregression"] - r["actual"]),
                "lag2_absolute_error": abs(r["latest_report"] - r["actual"]),
            }
            for r in largest
        ],
    }


def appendix_pages(r):
    """Eleven explicitly paginated appendices, shared with the Markdown export."""
    from app.services.research_report import NAMES

    def f(v):
        return "-" if v is None else f"{v:.4f}"

    d = r["details"]
    pages = []
    pages.append(
        (
            "7. How to read the results",
            [
                (
                    "All energy values and forecast errors are million kWh. One million "
                    "kWh equals 1 GWh. MW peak measurements are power, not daily energy, "
                    "and cannot be substituted for this target."
                ),
                (
                    "Signed error = prediction minus observed energy. Negative bias "
                    "indicates average underprediction; positive bias indicates "
                    "overprediction. Bias can cancel across dates, so a near-zero bias "
                    "does not imply small errors."
                ),
                (
                    "MAE = mean absolute error on the stated paired dates. RMSE = square "
                    "root of mean squared error and gives greater weight to large misses."
                    " Median absolute error describes the middle miss; the 90th and 95th "
                    "percentiles describe the observed upper error tail."
                ),
                (
                    "Primary comparisons use dates with an observed target and all six "
                    "forecasts. Own-date results use each method's available observations"
                    " and are not directly ranked against different samples. Forecast "
                    "coverage uses all calendar days, including dates whose actual is "
                    "unavailable."
                ),
                (
                    "The MAE reduction is 100*(benchmark MAE - OLS MAE)/benchmark MAE. "
                    "The reported 13.41% is historical matched-sample improvement, not a "
                    "percentage increase in generation, a guaranteed cost saving or live "
                    "accuracy."
                ),
                (
                    "Quantiles use linear interpolation at (n-1)*p. MAE divided by mean "
                    "actual, reported below as a contextual percentage, is NOT MAPE. No "
                    "percentage-error statistic is calculated by dividing individual "
                    "errors by small or zero daily targets."
                ),
                (
                    "These detailed appendices expand the retained results without "
                    "retraining, changing the OLS primary choice, filling missing targets"
                    " or creating new inferential tests. Dashes mean unavailable, never "
                    "zero."
                ),
            ],
            [],
        )
    )
    year = [
        [
            y,
            str(x["calendar"]),
            str(x["observed"]),
            str(x["held"]),
            str(x["eligible"]),
            f"{100 * x['eligible'] / x['calendar']:.2f}%",
        ]
        for y, x in r["coverage"].items()
    ]
    month = [
        [
            x["month"],
            str(x["calendar_days"]),
            str(x["observed_days"]),
            str(x["ols_forecasts"]),
            str(x["ols_own_scored"]),
            str(x["common_scored"]),
        ]
        for x in d["monthly_coverage"]
    ]
    pages.append(
        (
            "8. Missingness and scoring coverage",
            [
                (
                    "Frozen research eligibility is separate from today's database "
                    "inventory. Observed minus held equals eligible in this retained "
                    "study. An absent or held measurement is not evidence of zero "
                    "generation."
                ),
                (
                    "January 2025 has no all-six-method matched dates; its common-date "
                    "errors remain unavailable. Early-year feature availability limits "
                    "model forecasts even where some original targets exist. Do not "
                    "attribute this automatically to an official outage or missing "
                    "publication."
                ),
            ],
            [
                (["Year", "Calendar", "Observed", "Held", "Eligible", "Eligible %"], year),
                (
                    [
                        "2025 month",
                        "Calendar",
                        "Observed",
                        "OLS forecasts",
                        "OLS paired",
                        "All-six paired",
                    ],
                    month,
                ),
            ],
        )
    )
    training = [
        [NAMES[x["family"]], str(x["n"]), f(x["mae"]), f(x["rmse"]), f(x["bias"])]
        for x in r["training_selection"]
    ]
    pages.append(
        (
            "9. Training selection and fixed features",
            [
                (
                    "Training-only expanding origins produced the ranking below on 755 "
                    "common scored dates. The OLS primary family was chosen before the "
                    "final year was evaluated. This training result is not a substitute "
                    "for the separate 2024 validation or 2025 final test."
                ),
                "Fixed features: "
                + ", ".join(r["study"]["feature_names"])
                + (
                    ". Lag 2/7/14/28 encode original earlier energy; mean_2_to_8 "
                    "summarizes past energy; sine/cosine calendar pairs encode cyclical "
                    "weekday and annual position."
                ),
                (
                    "Missing past feature inputs use the fixed exact original previous-"
                    "week donor rule. Donors are not newly imputed labels. Targets, "
                    "current measurements and future observations are never replaced by "
                    "these feature substitutions."
                ),
                (
                    "The final fitted sample contains 1,557 eligible labels. Its last "
                    "usable label is 2024-10-18 although the nominal cutoff is "
                    "2024-12-30. A nominal calendar window must not be described as "
                    "complete usable training coverage."
                ),
                "Retained tree settings: "
                + str(
                    {
                        x["family"]: x.get("parameters", {})
                        for x in r["training_selection"]
                        if x["family"] in ("random_forest", "gradient_boosting")
                    }
                ),
                (
                    "Hyperparameters are documented for reproducibility, not evidence "
                    "that every possible tree configuration was explored. Subsequent "
                    "model development requires a newly declared evaluation design."
                ),
            ],
            [(["Training family", "Common n", "MAE", "RMSE", "Bias"], training)],
        )
    )
    for title, key, days in [
        ("10. Validation 2024 - complete score table", "validation_scores", 366),
        ("11. Final test 2025 - complete score table", "test_scores", 365),
    ]:
        scores = r[key]
        common = [
            [
                NAMES[x["model"]],
                str(x["common_dates"]["n"]),
                f(x["common_dates"]["mae"]),
                f(x["common_dates"]["rmse"]),
                f(x["common_dates"]["bias"]),
            ]
            for x in scores
        ]
        own = [
            [
                NAMES[x["model"]],
                str(x["own_dates"]["n"]),
                f(x["own_dates"]["mae"]),
                f(x["own_dates"]["rmse"]),
                f(x["own_dates"]["bias"]),
            ]
            for x in scores
        ]
        cov = [
            [
                NAMES[x["model"]],
                str(x["calendar_forecasts"]),
                str(days),
                f"{100 * x['calendar_forecasts'] / days:.2f}%",
                str(x.get("negative_forecasts", 0)),
            ]
            for x in scores
        ]
        pages.append(
            (
                title,
                [
                    (
                        "Table 1 uses identical observed dates across all six methods. Table "
                        "2 uses each method's own available observed dates; samples differ. "
                        "Table 3 reports forecast availability across the calendar, not "
                        "observed-target coverage."
                    ),
                    (
                        "Errors are shown to four decimals; machine-readable exports retain "
                        "stored precision. Year-to-year changes mix different samples, "
                        "conditions and refitted models and cannot be interpreted as a "
                        "controlled treatment effect."
                    ),
                ],
                [
                    (["Matched sample", "n", "MAE", "RMSE", "Bias"], common),
                    (["Own sample", "n", "MAE", "RMSE", "Bias"], own),
                    (["Coverage", "Forecasts", "Calendar", "Forecast %", "Negative"], cov),
                ],
            )
        )
    for number, metric, label in [
        (12, "mae", "MAE"),
        (13, "rmse", "RMSE"),
        (14, "bias", "signed bias"),
    ]:
        rows = []
        for month in r["test_monthly"]:
            scores = {s["model"]: s["common_dates"] for s in month["scores"]}
            rows.append(
                [month["month"], str(scores["autoregression"]["n"])]
                + [f(scores[k][metric]) for k in KEYS]
            )
        pages.append(
            (
                f"{number}. Monthly matched-date {label}",
                [
                    (
                        "All six methods use the same observed dates within each row; month-"
                        "specific sample sizes differ. January has no common sample. No month"
                        " is filled or extrapolated to create a complete annual result."
                    ),
                    (
                        "Negative bias means underprediction. Monthly patterns describe this "
                        "evaluated year and do not prove seasonality or its causes. Local "
                        "monthly winners do not change the preselected primary model."
                    ),
                    (
                        "Annual metrics are calculated from individual matched-day errors, "
                        "not the unweighted average of monthly metrics. Months with more "
                        "paired dates contribute more to annual MAE and bias; annual RMSE "
                        "requires aggregation of squared errors."
                    ),
                ],
                [(["Month", "n"] + list(SHORT), rows)],
            )
        )
    diag = d["common_diagnostics"]
    distribution = [
        [
            NAMES[x["model"]],
            f(x["median_absolute_error"]),
            f(x["p90_absolute_error"]),
            f(x["p95_absolute_error"]),
            f(x["maximum_absolute_error"]),
        ]
        for x in diag
    ]
    counts = [
        [
            NAMES[x["model"]],
            str(x["underprediction_days"]),
            str(x["overprediction_days"]),
            str(x["exact_days"]),
            str(x["beats_lag2_days"]),
        ]
        for x in diag
    ]
    percentages = [
        [NAMES[x["model"]], f(x["mean_actual"]), f(x["mae_percent_of_mean_actual"])] for x in diag
    ]
    pages.append(
        (
            "15. Error distribution and direction",
            [
                (
                    "All diagnostics below use the same 287 final-test matched dates. "
                    "Under/over counts use the exact signed stored arithmetic. Beating "
                    "lag 2 on an individual date is a descriptive count, not a "
                    "significance test or independent trial."
                ),
                (
                    "Upper error quantiles describe realized 2025 misses, not forecast "
                    "intervals. They are not calibrated probabilities for tomorrow. The "
                    "contextual MAE/mean-actual percentage is distinct from MAPE."
                ),
            ],
            [
                (["Method", "Median AE", "90th AE", "95th AE", "Max AE"], distribution),
                (["Method", "Under", "Over", "Exact", "Beats lag 2"], counts),
                (["Method", "Mean actual", "MAE / mean actual %"], percentages),
            ],
        )
    )
    worst = [
        [
            x["date"],
            f(x["actual"]),
            f(x["prediction"]),
            f(x["signed_error"]),
            f(x["absolute_error"]),
            f(x["lag2_absolute_error"]),
        ]
        for x in d["largest_ols_errors"]
    ]
    pages.append(
        (
            "16. Largest primary-model misses",
            [
                (
                    "Fifteen largest OLS absolute errors on the all-six-method common "
                    "sample, descending by absolute error, with date as the tie-breaker. "
                    "This is a diagnostic subset, not a new evaluation sample or an "
                    "instruction to remove inconvenient observations."
                ),
                (
                    "The original daily source/version lineage remains in the frozen "
                    "experiment and master platform. Investigate these dates against "
                    "official PDFs and system context before proposing an explanation. "
                    "Demand, weather, fuel constraints or outages are possible research "
                    "questions, not established causes from this table."
                ),
                (
                    "Actual and prediction are daily energy; signed error is prediction "
                    "minus actual. A large realized miss cannot be corrected "
                    "retrospectively and counted as the original model's performance."
                ),
            ],
            [(["Date", "Actual", "OLS", "Signed error", "Absolute error", "Lag-2 AE"], worst)],
        )
    )
    monthly = [
        [
            x["month"],
            str(x["observed_days"]),
            str(x["calendar_days"]),
            f(x["observed_mean"]),
            f(x["observed_minimum"]),
            f(x["observed_maximum"]),
        ]
        for x in d["monthly_coverage"]
    ]
    pages.append(
        (
            "17. Observed energy and interpretation",
            [
                (
                    "These summaries use only eligible observed targets in the frozen "
                    "2025 study. Means/minima/maxima refer to the available subset, not "
                    "necessarily the complete month. No missing day contributes zero and "
                    "no monthly total is invented."
                ),
                (
                    "Compare observed counts with calendar days before comparing monthly "
                    "means. Incomplete coverage, particularly January, can change "
                    "apparent differences. One evaluated year is insufficient to "
                    "establish stable long-run seasonality."
                ),
                (
                    "The chart's annual shape may motivate seasonal analysis, but the "
                    "table alone cannot identify why energy changed. Additional evidence "
                    "would be needed to separate demand, supply limitations, weather, "
                    "holidays, reporting revisions and other mechanisms."
                ),
            ],
            [(["Month", "Observed", "Calendar", "Mean", "Minimum", "Maximum"], monthly)],
        )
    )
    return pages


def detailed_markdown(report):
    lines = ["", "# Detailed results appendices", ""]
    for title, paragraphs, tables in appendix_pages(report):
        lines += ["## " + title, ""]
        for paragraph in paragraphs:
            lines += [paragraph, ""]
        for header, rows in tables:
            lines += [
                "| " + " | ".join(header) + " |",
                "| " + " | ".join(["---"] * len(header)) + " |",
            ]
            lines += ["| " + " | ".join(str(x) for x in row) + " |" for row in rows]
            lines += [""]
    return "\n".join(lines)


def append_pdf(report, next_page, heading, add, table):
    for title, paragraphs, tables in appendix_pages(report):
        next_page()
        heading(title)
        for paragraph in paragraphs:
            add(escape(paragraph))
        for header, rows in tables:
            table([header] + rows)
