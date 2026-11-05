from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from app.api.forecasts import read_history
from app.db.models import ResearchForecast, ResearchForecastOutcome
from app.services import forecasting as f
from research import release1 as r1
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from test_preparation import day

NOW = datetime(2026, 1, 5, 12, tzinfo=timezone.utc)  # 18:00 Bangladesh, not planned noon.


def prepared():
    target = NOW.astimezone(f.DHAKA).date() + timedelta(days=1)
    start, end = target - timedelta(days=35), target - timedelta(days=2)
    days, sources, versions = [], {}, {}
    for n in range(34):
        d = day(n + 1, "200", available=False)
        d.operational_date = start + timedelta(days=n)
        days.append(d)
        sources[d.sources[0].id] = {
            "created_at": NOW - timedelta(days=1),
            "retrieved_at": NOW - timedelta(days=1),
            "published_at": None,
        }
        versions[d.report_version_id] = NOW - timedelta(days=1)
    return days, sources, versions, start, end


def snapshot():
    args = prepared()
    return f.freeze_days(*args, NOW - timedelta(seconds=1))


def issue(rows=None, now=NOW):
    model, card = f.loaded_model()
    return f.build_issue(
        snapshot() if rows is None else rows, model, card, now - timedelta(seconds=1), now
    )


def test_prospective_features_match_evaluated_math_and_keep_actual_late_issue_time():
    candidate = issue()
    assert candidate["target_date"] == date(2026, 1, 6)
    assert candidate["issued_at"] == NOW and candidate["status"] == "forecast"
    assert len(candidate["payload"]["used_inputs"]) == 9
    series = {
        date.fromisoformat(r["date"]): {"value": float(r["value"]), "available_at": None}
        for r in snapshot()
    }
    expected = r1.feature_row(series, candidate["target_date"], "seasonal_original_7")
    assert candidate["payload"]["features"] == expected["x"]
    assert candidate["payload"]["unknown_official_time_slots"] == 9
    assert candidate["payload"]["latest_donor"] == "2026-01-04"


def test_future_capture_and_nonmatching_calendar_are_refused():
    model, card = f.loaded_model()
    with pytest.raises(ValueError, match="Capture cannot"):
        f.build_issue(snapshot(), model, card, NOW + timedelta(seconds=1), NOW)
    with pytest.raises(ValueError, match="Input window"):
        f.build_issue(snapshot()[1:], model, card, NOW, NOW)


def test_future_platform_timestamp_is_excluded_and_original_week_donor_used():
    days, sources, versions, start, end = prepared()
    sources[days[-1].sources[0].id]["retrieved_at"] = NOW + timedelta(days=1)
    rows = f.freeze_days(days, sources, versions, start, end, NOW)
    assert not rows[-1]["eligible"] and "known_timestamp_after_capture" in rows[-1]["reasons"]
    candidate = issue(rows)
    donor = next(r for r in candidate["payload"]["used_inputs"] if r["requested_date"] == str(end))
    assert donor["date"] == str(end - timedelta(days=7)) and donor["substituted"]


def test_missing_inputs_withhold_without_fabricated_target_or_recursive_fill():
    rows = snapshot()
    for r in rows:
        if r["date"] in ("2026-01-04", "2025-12-28"):
            r["eligible"] = False
    candidate = issue(rows)
    assert candidate["status"] == "withheld" and candidate["prediction"] is None
    assert candidate["payload"]["missing_requested_dates"] == ["2026-01-04"]
    assert candidate["payload"]["reason"] == "missing_usable_original_inputs"


def test_invalid_units_or_numerical_values_are_held_without_changing_originals():
    days, sources, versions, start, end = prepared()
    days[-1].measurements[0].unit = "MWh"
    rows = f.freeze_days(days, sources, versions, start, end, NOW)
    assert not rows[-1]["eligible"]
    assert days[-1].measurements[0].value == "200"


@pytest.mark.parametrize("raw", [-1, float("nan"), 1e-12, 1e16])
def test_unsafe_or_rounded_nonpositive_output_is_withheld(monkeypatch, raw):
    monkeypatch.setattr(f, "predict_saved", lambda *_: raw)
    candidate = issue()
    assert candidate["status"] == "withheld" and candidate["prediction"] is None
    assert candidate["payload"]["reason"] == "unsafe_model_output"


def test_issue_deduplicates_same_snapshot_without_changing_first_issue_time(session):
    first, inserted = f.retain_issue(session, issue())
    again, repeated = f.retain_issue(session, issue(now=NOW + timedelta(hours=1)))
    assert inserted and not repeated and first.id == again.id
    assert f.utc(again.issued_at) == NOW
    assert session.scalar(select(func.count()).select_from(ResearchForecast)) == 1
    changed = snapshot()
    changed[-1]["value"] = "201"
    revision, is_new = f.retain_issue(session, issue(changed, NOW + timedelta(hours=1)))
    assert is_new and revision.id != first.id
    assert first.payload["snapshot"][-1]["value"] == "200"


def test_database_rejects_prediction_attached_to_withheld_record(session):
    values = issue()
    values.update(status="withheld", prediction=Decimal("1"))
    with pytest.raises(IntegrityError):
        session.add(ResearchForecast(**values))
        session.flush()
    session.rollback()


def test_outcomes_keep_revisions_and_summary_scores_first_successful_issue_only(session):
    from app.db.models import ReportVersion, VersionSource
    from test_missingness import energy

    first, _ = f.retain_issue(session, issue())
    changed = snapshot()
    changed[-1]["value"] = "400"
    later, _ = f.retain_issue(session, issue(changed, NOW + timedelta(hours=1)))
    report, version, source = energy(session, date(2026, 1, 6), "210")
    actual = {
        "date": "2026-01-06",
        "eligible": True,
        "value": "210",
        "version_id": version.id,
        "source_id": source.id,
        "source_url": source.original_url,
        "source_sha256": source.sha256,
    }
    assert not f.retain_outcome(session, first, actual, NOW)
    compared = NOW + timedelta(days=2)
    assert f.retain_outcome(session, first, actual, compared)
    assert not f.retain_outcome(session, first, actual, compared)
    assert f.retain_outcome(session, later, actual, compared)
    history = read_history(session, 20, compared)
    assert history["summary"]["scored_dates"] == 1
    assert history["summary"]["mae"] == pytest.approx(float(abs(first.prediction - Decimal("210"))))
    revision = ReportVersion(
        report_id=report.id, version_number=2, quality_status="validated", parser_version="revised"
    )
    session.add(revision)
    session.flush()
    session.add(VersionSource(version_id=revision.id, source_id=source.id))
    session.flush()
    revised = {**actual, "version_id": revision.id, "value": "211"}
    assert f.retain_outcome(session, first, revised, compared + timedelta(days=1))
    assert session.scalar(select(func.count()).select_from(ResearchForecastOutcome)) == 3
    updated = read_history(session, 20, compared + timedelta(days=1))
    assert updated["summary"]["mae"] == pytest.approx(float(abs(first.prediction - Decimal("211"))))


def test_capture_reads_only_canonical_records_and_retains_platform_lineage(session):
    from test_missingness import energy

    _, version, source = energy(session, date(2026, 1, 4), "200")
    captured = datetime.now(timezone.utc) + timedelta(seconds=1)
    rows = f.capture_days(session, date(2026, 1, 3), date(2026, 1, 4), captured)
    assert not rows[0]["eligible"] and rows[1]["eligible"]
    assert rows[1]["version_id"] == version.id and rows[1]["source_id"] == source.id
    assert not session.dirty and not session.new
