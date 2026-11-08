"""Fixed exploratory monthly-cost study; read-only acquisition, no production writes."""

import argparse
import calendar
import csv
import hashlib
import io
import json
import math
from contextlib import contextmanager
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
from app.api.measurement_review import FIELDS, screen
from app.api.monitoring import canonical_query, materialize_days, read_session
from app.db.models import DailyReport, SourceDocument
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import StandardScaler
from sqlalchemy import select, text

ROOT = Path(__file__).resolve().parents[2]
ZONE = ZoneInfo("Asia/Dhaka")
METHODS = ("latest_total", "daily_mean", "ols", "ridge")
MIN_FIT = 8


def encode(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def shift(month, count):
    y, m = map(int, month.split("-"))
    n = y * 12 + m - 1 + count
    return f"{n // 12:04}-{n % 12 + 1:02}"


def days_in(month):
    y, m = map(int, month.split("-"))
    return calendar.monthrange(y, m)[1]


def issue_for(month):
    y, m = map(int, shift(month, -1).split("-"))
    return datetime(y, m, 8, 12, tzinfo=ZONE)


def parsed_time(value):
    if not value:
        return None
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp


def daily_audit(raw):
    result = {}
    for row in raw:
        dt = row["operational_date"]
        if dt in result:
            raise ValueError("Duplicate canonical operational date")
        flags, _ = screen(
            {
                m["metric"]: Decimal(m["value"])
                for m in row["measurements"]
                if m["metric"] in FIELDS and m["value"] is not None
            }
        )
        reasons = [f.code for f in flags]
        matches = [m for m in row["measurements"] if m["metric"] == "total_production_cost"]
        sources = {s["id"]: s for s in row["sources"]}
        value, source = None, None
        if len(matches) != 1:
            reasons.append("missing_or_ambiguous_cost")
        else:
            m = matches[0]
            source = sources.get(m["source_id"])
            if (m["unit"], m["period"], m["fuel"], m["zone"]) != (
                "BDT",
                "daily",
                "all",
                "national",
            ):
                reasons.append("invalid_dimensions")
            if not source or not source.get("sha256") or m.get("source_page") != 1:
                reasons.append("incomplete_provenance")
            if m["value"] is None:
                reasons.append("null_cost")
            else:
                number = Decimal(m["value"])
                if not number.is_finite() or number <= 0:
                    reasons.append("nonpositive_or_nonfinite_cost")
                else:
                    value = str(number)
        result[dt] = {
            "date": dt,
            "value_bdt": value,
            "eligible": not reasons,
            "reasons": reasons,
            "version_id": row["report_version_id"],
            "parser_version": row["parser_version"],
            "source": source,
            "raw_text": matches[0].get("raw_text") if len(matches) == 1 else None,
        }
    return result


def monthly_audit(daily, start, end):
    out = []
    current = start
    while current <= end:
        records = []
        for day in range(1, days_in(current) + 1):
            key = f"{current}-{day:02}"
            records.append(
                daily.get(
                    key,
                    {
                        "date": key,
                        "value_bdt": None,
                        "eligible": False,
                        "reasons": ["no_canonical_record"],
                    },
                )
            )
        accepted = all(r["eligible"] for r in records)
        out.append(
            {
                "month": current,
                "calendar_days": len(records),
                "eligible_days": sum(r["eligible"] for r in records),
                "missing_or_held_dates": [r["date"] for r in records if not r["eligible"]],
                "eligible": accepted,
                "total_bdt": str(sum((Decimal(r["value_bdt"]) for r in records), Decimal(0)))
                if accepted
                else None,
                "daily": records,
            }
        )
        current = shift(current, 1)
    return out


def available(month, issue):
    if not month["eligible"]:
        return False
    for r in month["daily"]:
        source = r.get("source") or {}
        stamp = parsed_time(source.get("published_at"))
        if stamp and stamp > issue:
            return False
    return True


def feature(month, months, issue=None):
    issue = issue or issue_for(month)
    for age in (2, 3):
        donor = months.get(shift(month, -age))
        if donor and available(donor, issue):
            mean = float(Decimal(donor["total_bdt"]) / donor["calendar_days"])
            angle = 2 * math.pi * (int(month[5:]) - 1) / 12
            return [mean, math.sin(angle), math.cos(angle)], donor, age
    return None, None, None


def fit_predict(target, months, issue=None):
    issue = issue or issue_for(target)
    x, donor, age = feature(target, months, issue)
    result = {
        "target_month": target,
        "issue_at": issue.isoformat(),
        "donor_month": None,
        "donor_age_months": None,
        "fit_months": [],
        "fit_rows": 0,
        "forecasts_bdt": dict.fromkeys(METHODS),
        "models": {},
        "reason": None,
    }
    if x is None:
        result["reason"] = "no_complete_available_donor_within_2_or_3_months"
        return result
    result["donor_month"], result["donor_age_months"] = donor["month"], age
    result["forecasts_bdt"]["latest_total"] = float(donor["total_bdt"])
    result["forecasts_bdt"]["daily_mean"] = x[0] * days_in(target)
    xs, ys, fit_months = [], [], []
    for m, row in sorted(months.items()):
        if m > shift(target, -2) or not available(row, issue):
            continue
        xx, _, _ = feature(m, months)
        if xx is None:
            continue
        xs.append(xx)
        ys.append(float(Decimal(row["total_bdt"]) / row["calendar_days"]))
        fit_months.append(m)
    result["fit_months"], result["fit_rows"] = fit_months, len(ys)
    if len(ys) < MIN_FIT:
        result["reason"] = "fewer_than_8_chronological_fit_rows"
        return result
    scaler = StandardScaler().fit(xs)
    xx = scaler.transform([x])
    for name, estimator in (("ols", LinearRegression()), ("ridge", Ridge(alpha=1.0))):
        estimator.fit(scaler.transform(xs), ys)
        prediction = float(estimator.predict(xx)[0] * days_in(target))
        result["forecasts_bdt"][name] = (
            prediction if math.isfinite(prediction) and prediction >= 0 else None
        )
        result["models"][name] = {
            "coefficients": estimator.coef_.tolist(),
            "intercept": float(estimator.intercept_),
            "feature_mean": scaler.mean_.tolist(),
            "feature_scale": scaler.scale_.tolist(),
            "fit_months": fit_months,
            "features": x,
        }
    return result


def metrics(pairs):
    if not pairs:
        return {"n": 0, "mae_bdt": None, "rmse_bdt": None, "bias_bdt": None, "mape_percent": None}
    errors = np.array([p - a for a, p in pairs])
    return {
        "n": len(pairs),
        "mae_bdt": float(np.mean(abs(errors))),
        "rmse_bdt": float(np.sqrt(np.mean(errors**2))),
        "bias_bdt": float(np.mean(errors)),
        "mape_percent": float(np.mean([abs(p - a) / a for a, p in pairs]) * 100),
    }


def experiment(raw, captured):
    current = captured.astimezone(ZONE).strftime("%Y-%m")
    last = shift(current, -1)
    months = monthly_audit(daily_audit(raw), "2025-01", last)
    by_month = {m["month"]: m for m in months}
    predictions = []
    for m in months:
        r = fit_predict(m["month"], by_month)
        r["actual_bdt"] = m["total_bdt"]
        r["errors_bdt"] = {
            k: (v - float(m["total_bdt"])) if v is not None and m["eligible"] else None
            for k, v in r["forecasts_bdt"].items()
        }
        predictions.append(r)
    shared = [
        r
        for r in predictions
        if r["actual_bdt"] is not None and all(v is not None for v in r["forecasts_bdt"].values())
    ]
    scores = []
    for name in METHODS:
        own = [
            r
            for r in predictions
            if r["actual_bdt"] is not None and r["forecasts_bdt"][name] is not None
        ]
        scores.append(
            {
                "method": name,
                "forecasts": sum(r["forecasts_bdt"][name] is not None for r in predictions),
                "own": metrics([(float(r["actual_bdt"]), r["forecasts_bdt"][name]) for r in own]),
                "shared": metrics(
                    [(float(r["actual_bdt"]), r["forecasts_bdt"][name]) for r in shared]
                ),
            }
        )
    future_target = shift(current, 1)
    future = fit_predict(future_target, by_month, captured)
    future["issued_at"] = datetime.now(timezone.utc).isoformat()
    future["actual_bdt"] = None
    assert date.fromisoformat(future_target + "-01") > captured.astimezone(ZONE).date()
    unknown = sum(
        not (r.get("source") or {}).get("published_at")
        for m in months
        if m["eligible"]
        for r in m["daily"]
    )
    return {
        "protocol": "monthly_cost_v1",
        "capture_at": captured.isoformat(),
        "snapshot_sha256": hashlib.sha256(encode(raw)).hexdigest(),
        "primary_model": "ridge",
        "start_month": "2025-01",
        "end_month": last,
        "calendar_months": len(months),
        "complete_months": sum(m["eligible"] for m in months),
        "shared_scored_months": len(shared),
        "scores": scores,
        "predictions": predictions,
        "future": future,
        "months": months,
        "unknown_publication_days_in_complete_months": unknown,
        "conclusion_status": "small_sample_exploratory_only"
        if len(shared) >= 6
        else "insufficient_shared_months",
        "limitations": [
            "No independently audited accounting-scope certification.",
            "Current canonical revisions; unknown historical publication times are assumed.",
            "Historical day-eight issue differs from actual current issue time.",
            "No untouched historical final test; no production policy or energy model changed.",
            "Missing target months are never estimated; no calibrated prediction intervals.",
        ],
    }


def csv_bytes(rows):
    out = io.StringIO(newline="")
    if rows:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return out.getvalue().encode("utf-8-sig")


def save(raw, report, out):
    out.mkdir(parents=True, exist_ok=True)
    (out / "canonical_snapshot.json").write_bytes(encode(raw))
    (out / "experiment.json").write_bytes(encode(report))
    (out / "monthly_audit.csv").write_bytes(
        csv_bytes(
            [
                {
                    k: ("|".join(v) if isinstance(v, list) else v)
                    for k, v in m.items()
                    if k != "daily"
                }
                for m in report["months"]
            ]
        )
    )
    (out / "predictions.csv").write_bytes(
        csv_bytes(
            [
                {
                    "target_month": r["target_month"],
                    "issue_at": r["issue_at"],
                    "actual_bdt": r["actual_bdt"],
                    "donor_month": r["donor_month"],
                    "fit_rows": r["fit_rows"],
                    "reason": r["reason"],
                    **{k + "_prediction_bdt": v for k, v in r["forecasts_bdt"].items()},
                    **{k + "_error_bdt": v for k, v in r["errors_bdt"].items()},
                }
                for r in report["predictions"]
            ]
        )
    )
    (out / "future_forecast.json").write_bytes(encode(report["future"]))
    manifest = {
        p.name: {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
        for p in sorted(out.iterdir())
        if p.is_file() and p.name != "manifest.json"
    }
    (out / "manifest.json").write_bytes(encode(manifest))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "data/monthly_cost")
    args = parser.parse_args()
    if args.snapshot:
        raw = json.loads(args.snapshot.read_bytes())
        captured = datetime.now(timezone.utc)
    else:
        print("Reading canonical cost evidence from Neon in read-only mode...", flush=True)
        with contextmanager(read_session)() as session:
            assert session.get_bind().dialect.name == "postgresql"
            assert session.scalar(text("SHOW transaction_read_only")) == "on"
            records = session.execute(
                canonical_query()
                .where(DailyReport.report_date >= date(2025, 1, 1))
                .order_by(DailyReport.report_date)
            ).all()
            raw = [d.model_dump(mode="json") for d in materialize_days(session, records)]
            source_ids = {s["id"] for d in raw for s in d["sources"]}
            source_rows = session.scalars(
                select(SourceDocument).where(SourceDocument.id.in_(source_ids))
            ).all()
            metadata = {s.id: s for s in source_rows}
            for d in raw:
                for source in d["sources"]:
                    original = metadata[source["id"]]
                    source["published_at"] = (
                        original.published_at.isoformat() if original.published_at else None
                    )
                    source["retrieved_at"] = original.retrieved_at.isoformat()

        captured = datetime.now(timezone.utc)
    report = experiment(raw, captured)
    report["code_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report["protocol_sha256"] = hashlib.sha256(
        (ROOT / "docs/MONTHLY_COST_PROTOCOL.md").read_bytes()
    ).hexdigest()
    save(raw, report, args.output)
    print(
        json.dumps(
            {k: v for k, v in report.items() if k not in ("months", "predictions")}, indent=2
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
