"""Reproducible research exports, separate from authoritative measurements."""

import csv
import hashlib
import io
import json
import zipfile
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.measurement_review import FIELDS, screen
from app.api.measurement_review import RULE_VERSION as REVIEW_RULE
from app.api.missingness import MissingMetric, read_missingness
from app.api.monitoring import DAILY_COLUMNS, Database, canonical_query, materialize_days
from app.db.models import DailyReport

router = APIRouter(prefix="/api/v1/dataset", tags=["Research preparation"])
RULE_VERSION = "preparation_v1"
Policy = Literal["observed_only", "past_week_train_only"]
LIMITATIONS = [
    "Research candidate, not a model-ready or source-verified dataset.",
    "Current canonical revisions are frozen; this is not a historical point-in-time database.",
    "Availability timestamps can be unknown or later than operational dates.",
    "Review flags are conservative holds, not confirmed errors. Other errors may be unscreened.",
    "No validation/test targets are estimated. "
    "Monthly totals require every day observed and unheld.",
    "A previous-week training estimate is experimental, not an approved missing-data treatment.",
    "No Neon records, PDFs, canonical pointers or review decisions are changed.",
    "Download the bundle to retain it; the server does not persist this research snapshot.",
]


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def csv_data(rows, fields):
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode("utf-8-sig")


def build_snapshot(
    days, metric: str, start: date, end: date, train_end: date, validation_end: date,
    policy: str = "observed_only", max_gap: int = 1,
):
    definitions = {c[1]: c for c in DAILY_COLUMNS}
    if metric not in definitions or policy not in ("observed_only", "past_week_train_only"):
        raise HTTPException(422, "Unknown measurement or treatment policy")
    if not start <= train_end < validation_end < end:
        raise HTTPException(422, "Use start <= training end < validation end < end")
    if not 1 <= max_gap <= 3 or (end - start).days >= 3660:
        raise HTTPException(422, "Use 1-3 gap days and at most 3660 calendar days")
    label, _, unit, period, fuel = definitions[metric]
    originals = sorted(
        (d for d in days if start <= d.operational_date <= end),
        key=lambda d: d.operational_date,
    )
    by_date = {d.operational_date: d for d in originals}
    if len(by_date) != len(originals):
        raise HTTPException(503, "Duplicate canonical dates")
    rows = []
    flags_by_date = {}
    for d in originals:
        core = {m.metric: Decimal(m.value) for m in d.measurements
                if m.metric in FIELDS and m.value is not None}
        flags, _ = screen(core)
        flags_by_date[d.operational_date] = [f.code for f in flags]
    current = start
    while current <= end:
        d = by_date.get(current)
        matched = [m for m in d.measurements if m.metric == metric] if d else []
        if len(matched) > 1 or any(
            (m.unit, m.period, m.fuel, m.zone) != (unit, period, fuel, "national")
            or m.source_id not in {s.id for s in d.sources}
            or (m.value is not None and not Decimal(m.value).is_finite())
            for m in matched
        ):
            raise HTTPException(503, "Measurement dimensions or provenance need review")
        m = matched[0] if matched else None
        value = m.value if m else None
        flags = list(flags_by_date.get(current, []))
        if value is not None and Decimal(value) < 0 and metric != "maximum_temperature":
            flags.append("negative_selected_measurement")
        state = ("no_canonical_record" if d is None else "absent_field" if m is None
                 else "explicit_null" if value is None else "observed")
        split = "train" if current <= train_end else (
            "validation" if current <= validation_end else "test"
        )
        row = {
            "operational_date": current.isoformat(), "split": split, "state": state,
            "original_value": value, "prepared_train_value": None,
            "observed_target_candidate": value is not None and not flags,
            "review_hold": bool(flags), "review_flags": "|".join(sorted(set(flags))),
            "method": "unfilled", "reason": "missing_value_preserved",
            "version_id": d.report_version_id if d else None,
            "source_id": m.source_id if m else None,
            "source_page": m.source_page if m else None,
            "available_at": d.available_at.isoformat() if d and d.available_at else None,
            "donor_date": None, "donor_version_id": None, "donor_source_id": None,
        }
        if value is not None:
            row["reason"] = "numerical_review_hold" if flags else "original_observation"
            row["method"] = "observed_held" if flags else "observed"
            if split == "train" and not flags:
                row["prepared_train_value"] = value
        elif split != "train":
            row["reason"] = "held_out_target_never_filled"
        rows.append(row)
        current += timedelta(days=1)
    # Only internal short gaps bounded by usable ORIGINAL training observations qualify.
    if policy == "past_week_train_only":
        i = 0
        while i < len(rows) and rows[i]["split"] == "train":
            if rows[i]["state"] == "observed":
                i += 1
                continue
            j = i
            while j < len(rows) and rows[j]["split"] == "train" and rows[j]["state"] != "observed":
                j += 1
            internal = (i > 0 and j < len(rows) and rows[j]["split"] == "train"
                        and rows[i - 1]["observed_target_candidate"]
                        and rows[j]["observed_target_candidate"])
            for k in range(i, j):
                row = rows[k]
                row["reason"] = "boundary_gap_not_filled" if not internal else "gap_above_limit"
                if not internal or j - i > max_gap:
                    continue
                if row["review_hold"]:
                    row["reason"] = "numerical_review_hold"
                    continue
                donor_index = k - 7
                donor = rows[donor_index] if donor_index >= 0 else None
                row["reason"] = "no_usable_original_week_donor"
                if not donor or donor["split"] != "train" or not donor["observed_target_candidate"]:
                    continue
                row["reason"] = "donor_availability_unknown"
                available = by_date[date.fromisoformat(donor["operational_date"])].available_at
                if available is None:
                    continue
                # End of missing operational day in Bangladesh, an explicit preparation cutoff.
                origin = datetime.combine(
                    date.fromisoformat(row["operational_date"]) + timedelta(days=1),
                    time.min, ZoneInfo("Asia/Dhaka"),
                )
                if available.tzinfo is None:
                    available = available.replace(tzinfo=timezone.utc)
                row["reason"] = "donor_not_available_at_preparation_cutoff"
                if available > origin:
                    continue
                row.update(prepared_train_value=donor["original_value"],
                           method="past_week_original_v1", reason="experimental_training_estimate",
                           donor_date=donor["operational_date"],
                           donor_version_id=donor["version_id"], donor_source_id=donor["source_id"])
            i = j
    config = {
        "rule_version": RULE_VERSION, "review_rule": REVIEW_RULE, "metric": metric,
        "label": label, "unit": unit, "period": period, "fuel": fuel,
        "start_date": str(start), "end_date": str(end), "train_end": str(train_end),
        "validation_end": str(validation_end), "policy": policy, "max_gap": max_gap,
        "donor_cutoff": "start of next calendar day Asia/Dhaka",
    }
    original = [d.model_dump(mode="json") for d in originals]
    # Canonical JSON ordering: table query order is not part of dataset identity.
    for d in original:
        d["sources"].sort(key=lambda s: s["id"])
        d["measurements"].sort(key=lambda m: (
            m["metric"], m["unit"], m["period"], m["fuel"] or "", m["source_id"]
        ))
    identity = hashlib.sha256(encode({"config": config, "original": original})).hexdigest()
    splits = {}
    for split in ("train", "validation", "test"):
        selected = [r for r in rows if r["split"] == split]
        splits[split] = {
            "calendar_days": len(selected),
            "observed_days": sum(r["state"] == "observed" for r in selected),
            "missing_days": sum(r["state"] != "observed" for r in selected),
            "review_held_days": sum(r["review_hold"] for r in selected),
            "observed_target_candidates": sum(r["observed_target_candidate"] for r in selected),
            "estimated_training_days": sum(
                r["method"] == "past_week_original_v1" for r in selected
            ),
            "prepared_training_days": sum(r["prepared_train_value"] is not None for r in selected),
        }
    months = []
    for month in sorted({r["operational_date"][:7] for r in rows}):
        group = [r for r in rows if r["operational_date"].startswith(month)]
        first = date.fromisoformat(month + "-01")
        next_month = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
        full = len(group) == (next_month - first).days
        complete = full and all(r["observed_target_candidate"] for r in group)
        # Only additive energy and TOTAL cost have meaningful daily-to-month totals.
        additive = metric in ("energy_generated", "energy_demand", "energy_unserved",
                              "total_production_cost")
        total = (str(sum((Decimal(r["original_value"]) for r in group), Decimal(0)))
                 if complete and additive else None)
        months.append({"month": month, "calendar_days_selected": len(group),
                       "whole_month_selected": full, "all_days_observed_unheld": complete,
                       "split": group[0]["split"] if len({r["split"] for r in group}) == 1
                       else "crosses_split_boundary", "observed_month_total": total})
    return {"snapshot_id": identity, "config": config, "splits": splits,
            "reasons": dict(Counter(r["reason"] for r in rows)), "rows": rows,
            "months": months, "original": original, "limitations": LIMITATIONS}


def read_snapshot(session: Session, metric, start_date, end_date, train_end, validation_end,
                  policy="observed_only", max_gap=1):
    # Reuse strict expected-table/dimension/source-link checks before materializing lineage.
    assessment = read_missingness(session, metric, start_date, end_date)
    if assessment.start_date != start_date or assessment.end_date != end_date:
        raise HTTPException(422, "Select a window entirely within known canonical history")
    if (not start_date <= train_end < validation_end < end_date
            or (end_date-start_date).days >= 3660):
        raise HTTPException(422, "Use ordered split dates and at most 3660 calendar days")
    rows = session.execute(canonical_query().where(
        DailyReport.report_date.between(start_date, end_date)
    ).order_by(DailyReport.report_date)).all()
    return build_snapshot(materialize_days(session, rows), metric, start_date, end_date,
                          train_end, validation_end, policy, max_gap)


def bundle(snapshot):
    files = {
        "original_snapshot.json": encode(snapshot["original"]),
        "daily_audit.csv": csv_data(snapshot["rows"], list(snapshot["rows"][0])),
        "daily_values.csv": csv_data([
            {"Operational Date": r["operational_date"],
             "Original " + snapshot["config"]["label"]: r["original_value"],
             "Prepared Training " + snapshot["config"]["label"]: r["prepared_train_value"]}
            for r in snapshot["rows"]
        ], ["Operational Date", "Original " + snapshot["config"]["label"],
            "Prepared Training " + snapshot["config"]["label"]]),
        "monthly_observed.csv": csv_data(snapshot["months"], list(snapshot["months"][0])),
    }
    metadata = {k: v for k, v in snapshot.items() if k not in ("original", "rows", "months")}
    metadata["created_at"] = datetime.now(timezone.utc).isoformat()
    metadata["files"] = {name: {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                         for name, data in files.items()}
    files["manifest.json"] = encode(metadata)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return out.getvalue()


@router.get("/preparation")
def preparation(
    response: Response, session: Database, metric: MissingMetric,
    start_date: date, end_date: date, train_end: date, validation_end: date,
    policy: Policy = "observed_only", max_gap: int = 1,
    download: bool = False, expected_id: str | None = None,
):
    response.headers["Cache-Control"] = "no-store"
    snapshot = read_snapshot(session, metric, start_date, end_date, train_end, validation_end,
                             policy, max_gap)
    if expected_id and snapshot["snapshot_id"] != expected_id:
        raise HTTPException(
            409, "Canonical inputs changed. Refresh the preview before downloading."
        )
    if download:
        return Response(bundle(snapshot), media_type="application/zip", headers={
            "Cache-Control": "no-store",
            "Content-Disposition": 'attachment; filename="bpdb-research-'
            + snapshot["snapshot_id"][:12] + '.zip"',
        })
    return {k: v for k, v in snapshot.items() if k not in ("original", "rows", "months")} | {
        "preview_rows": snapshot["rows"][:30], "preview_limit": 30,
        "months": snapshot["months"],
    }
