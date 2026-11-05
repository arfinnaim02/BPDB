"""Prospective saved-model research inference with immutable captured inputs."""

import hashlib
import json
import math
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from research.release1 import FEATURES, predict_saved
from sqlalchemy import func, select

from app.api.final_evaluation import load_final, model_bytes
from app.api.measurement_review import FIELDS, screen
from app.api.monitoring import DAILY_COLUMNS, canonical_query, materialize_days
from app.api.preparation import encode
from app.db.models import ReportVersion, ResearchForecast, ResearchForecastOutcome, SourceDocument

RULE = "prospective_ols_v1"
DHAKA = timezone(timedelta(hours=6))
QUANTUM = Decimal("0.000000001")


def utc(value):
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


def iso(value):
    return utc(value).isoformat() if value else None


def loaded_model():
    report = load_final()
    model = json.loads(model_bytes(report))["autoregression"]
    if (
        model["family"] != "autoregression"
        or tuple(model["feature_names"]) != FEATURES
        or any(len(model[k]) != len(FEATURES) for k in ("mean", "scale", "coefficients"))
        or any(
            not math.isfinite(float(v)) for k in ("mean", "scale", "coefficients") for v in model[k]
        )
        or any(v <= 0 for v in model["scale"])
        or not math.isfinite(model["intercept"])
    ):
        raise ValueError("Unsupported saved OLS model")
    return model, {
        "model_id": hashlib.sha256(encode(model)).hexdigest(),
        "experiment_id": report["experiment_id"],
        "family": "Autoregressive OLS",
        "unit": "million_kWh",
        "last_fit_label": model["last_label"],
        "fit_rows": model["rows"],
        "historical_test_mae": next(
            r["common_dates"]["mae"] for r in report["scores"] if r["model"] == "autoregression"
        ),
        "policy": RULE,
        "features": list(FEATURES),
    }


def capture_days(session, start, end, captured_at):
    rows = session.execute(
        canonical_query()
        .where(
            canonical_query().selected_columns.operational_date >= start,
            canonical_query().selected_columns.operational_date <= end,
        )
        .order_by(canonical_query().selected_columns.operational_date)
    ).all()
    days = materialize_days(session, rows)
    source_ids = {s.id for d in days for s in d.sources}
    source_meta = {
        s.id: {
            "created_at": s.created_at,
            "retrieved_at": s.retrieved_at,
            "published_at": s.published_at,
        }
        for s in session.scalars(select(SourceDocument).where(SourceDocument.id.in_(source_ids)))
    }
    versions = {
        v.id: v.created_at
        for v in session.scalars(
            select(ReportVersion).where(ReportVersion.id.in_([d.report_version_id for d in days]))
        )
    }
    return freeze_days(days, source_meta, versions, start, end, captured_at)


def freeze_days(days, sources, versions, start, end, captured_at):
    by_date = {d.operational_date: d for d in days}
    if len(by_date) != len(days):
        raise ValueError("Duplicate canonical input dates")
    definitions = {c[1]: (c[2], c[3], c[4]) for c in DAILY_COLUMNS}
    result = []
    for n in range((end - start).days + 1):
        day = start + timedelta(days=n)
        d = by_date.get(day)
        row = {
            "date": str(day),
            "value": None,
            "eligible": False,
            "reasons": ["no_canonical_record"],
        }
        if d:
            flags, core = [], {}
            for key in FIELDS:
                matches = [m for m in d.measurements if m.metric == key]
                if len(matches) > 1 or any(
                    (m.unit, m.period, m.fuel) != definitions[key] or m.zone != "national"
                    for m in matches
                ):
                    flags.append("ambiguous_or_invalid_dimensions")
                    continue
                if matches and matches[0].value is not None:
                    try:
                        value = Decimal(matches[0].value)
                        if not value.is_finite():
                            raise InvalidOperation
                        core[key] = value
                    except InvalidOperation:
                        flags.append("invalid_numeric_input")
            quality, _ = screen(core)
            flags.extend(f.code for f in quality)
            matched = [m for m in d.measurements if m.metric == "energy_generated"]
            m = matched[0] if len(matched) == 1 else None
            source = next((s for s in d.sources if m and s.id == m.source_id), None)
            meta = sources.get(source.id, {}) if source else {}
            times = {
                "version_created_at": versions.get(d.report_version_id),
                "source_created_at": meta.get("created_at"),
                "retrieved_at": meta.get("retrieved_at"),
                "published_at": meta.get("published_at"),
                "available_at": d.available_at,
            }
            if not source or not all(
                times.get(k) for k in ("version_created_at", "source_created_at", "retrieved_at")
            ):
                flags.append("missing_platform_lineage")
            if any(v and utc(v) > utc(captured_at) for v in times.values()):
                flags.append("known_timestamp_after_capture")
            value = core.get("energy_generated")
            if value is None:
                flags.append("missing_energy_input")
            row = {
                "date": str(day),
                "value": str(value) if value is not None else None,
                "eligible": value is not None and value > 0 and not flags,
                "reasons": sorted(set(flags)),
                "version_id": d.report_version_id,
                "source_id": source.id if source else None,
                "source_url": source.url if source else None,
                "source_sha256": source.sha256 if source else None,
                "source_page": m.source_page if m else None,
                "screen_values": {k: str(v) for k, v in core.items()},
                **{k: iso(v) for k, v in times.items()},
            }
        result.append(row)
    return result


def build_issue(snapshot, model, card, captured_at, issued_at):
    captured_at, issued_at = utc(captured_at), utc(issued_at)
    if captured_at > issued_at:
        raise ValueError("Capture cannot follow issue time")
    target = issued_at.astimezone(DHAKA).date() + timedelta(days=1)
    expected = [str(target - timedelta(days=i)) for i in range(35, 1, -1)]
    if [r["date"] for r in snapshot] != expected:
        raise ValueError("Input window must end at T-2 and include T-35")
    lookup = {r["date"]: r for r in snapshot}
    values, trace, missing, visited = {}, [], [], set()
    for lag in (2, 7, 14, 28, *range(2, 9)):
        if lag in visited:
            continue
        visited.add(lag)
        requested = target - timedelta(days=lag)
        chosen = None
        for offset in (0, 7):
            row = lookup.get(str(requested - timedelta(days=offset)))
            if row and row["eligible"]:
                chosen = {**row, "requested_date": str(requested), "substituted": offset == 7}
                break
        if chosen is None:
            missing.append(str(requested))
            continue
        values[lag] = float(chosen["value"])
        trace.append(chosen)
    features, calculation, value = None, None, None
    reason = "missing_usable_original_inputs" if missing else None
    if not missing:
        angle = 2 * math.pi * ((target - date(target.year, 1, 1)).days) / 365.25
        weekday = 2 * math.pi * target.weekday() / 7
        features = [values[i] for i in (2, 7, 14, 28)] + [
            sum(values[i] for i in range(2, 9)) / 7,
            math.sin(weekday),
            math.cos(weekday),
            math.sin(angle),
            math.cos(angle),
        ]
        raw = predict_saved(model, features)
        if not math.isfinite(raw) or raw <= 0 or raw >= 1e15:
            reason = "unsafe_model_output"
        else:
            value = Decimal(str(raw)).quantize(QUANTUM)
            if value <= 0 or value >= Decimal("1e15"):
                value, reason = None, "unsafe_model_output"
            calculation = {
                "intercept": model["intercept"],
                "terms": [
                    {
                        "feature": name,
                        "input": x,
                        "mean": mean,
                        "scale": scale,
                        "coefficient": coefficient,
                        "contribution": (x - mean) / scale * coefficient,
                    }
                    for name, x, mean, scale, coefficient in zip(
                        FEATURES,
                        features,
                        model["mean"],
                        model["scale"],
                        model["coefficients"],
                        strict=True,
                    )
                ],
            }
    status = "forecast" if value is not None else "withheld"
    fingerprint = hashlib.sha256(
        encode(
            {
                "model_id": card["model_id"],
                "target": str(target),
                "policy": RULE,
                "snapshot": snapshot,
                "features": features,
                "status": status,
                "reason": reason,
            }
        )
    ).hexdigest()
    identity = hashlib.sha256(
        encode(
            {"model_id": card["model_id"], "target": str(target), "input_fingerprint": fingerprint}
        )
    ).hexdigest()
    payload = {
        "policy": RULE,
        "model_card": card,
        "captured_at": iso(captured_at),
        "reason": reason,
        "missing_requested_dates": missing,
        "features": features,
        "feature_names": list(FEATURES),
        "used_inputs": trace,
        "snapshot": snapshot,
        "calculation": calculation,
        "substituted_slots": sum(r["substituted"] for r in trace),
        "unknown_official_time_slots": sum(r.get("published_at") is None for r in trace),
        "latest_donor": max((r["date"] for r in trace), default=None),
        "availability_basis": (
            "Canonical versions captured in Neon before actual issuance; "
            "unknown official publication times remain disclosed"
        ),
    }
    return {
        "id": identity,
        "model_id": card["model_id"],
        "model_experiment_id": card["experiment_id"],
        "target_date": target,
        "issued_at": issued_at,
        "status": status,
        "prediction": value,
        "input_fingerprint": fingerprint,
        "payload": payload,
    }


def insert_statement(session, table):
    if session.get_bind().dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    return insert(table)


def retain_issue(session, issue):
    inserted = session.scalar(
        insert_statement(session, ResearchForecast)
        .values(**issue)
        .on_conflict_do_nothing(index_elements=["model_id", "target_date", "input_fingerprint"])
        .returning(ResearchForecast.id)
    )
    return session.get(ResearchForecast, issue["id"]), inserted is not None


def retain_outcome(session, forecast, actual, captured_at):
    if (
        forecast.status != "forecast"
        or not actual["eligible"]
        or date.fromisoformat(actual["date"]) != forecast.target_date
        or forecast.target_date >= utc(captured_at).astimezone(DHAKA).date()
        or utc(forecast.issued_at).astimezone(DHAKA).date() >= forecast.target_date
    ):
        return False
    observed = Decimal(actual["value"])
    error = Decimal(forecast.prediction) - observed
    values = {
        "forecast_id": forecast.id,
        "actual_version_id": actual["version_id"],
        "source_id": actual["source_id"],
        "observed": observed,
        "signed_error": error,
        "absolute_error": abs(error),
        "created_at": utc(captured_at),
        "lineage": {
            "source_sha256": actual["source_sha256"],
            "source_url": actual["source_url"],
            "captured_at": iso(captured_at),
            "unit": "million_kWh",
            "period": "daily",
        },
    }
    result = session.scalar(
        insert_statement(session, ResearchForecastOutcome)
        .values(**values)
        .on_conflict_do_nothing(index_elements=["forecast_id", "actual_version_id", "source_id"])
        .returning(ResearchForecastOutcome.id)
    )
    return result is not None


def capture_clock(session):
    if session.get_bind().dialect.name == "postgresql":
        return utc(session.scalar(select(func.clock_timestamp())))
    return datetime.now(timezone.utc)
