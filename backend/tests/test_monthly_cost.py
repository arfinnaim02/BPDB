from datetime import datetime, timezone

import pytest

pytest.importorskip("sklearn")

from research.monthly_cost import (  # noqa: E402
    available,
    days_in,
    feature,
    fit_predict,
    metrics,
    monthly_audit,
    shift,
)


def month(key, value=100, published=None):
    n = days_in(key)
    return {
        "month": key,
        "calendar_days": n,
        "eligible": True,
        "total_bdt": str(value * n),
        "daily": [{"source": {"published_at": published}} for _ in range(n)],
    }


def test_calendar_shift_and_leap_year():
    assert shift("2025-01", -2) == "2024-11"
    assert shift("2025-12", 1) == "2026-01"
    assert days_in("2024-02") == 29


def test_missing_original_does_not_become_month_total():
    daily = {
        f"2025-02-{d:02}": {
            "date": f"2025-02-{d:02}",
            "eligible": True,
            "value_bdt": "10",
            "reasons": [],
        }
        for d in range(1, 28)
    }
    r = monthly_audit(daily, "2025-02", "2025-02")[0]
    assert r["eligible_days"] == 27 and r["total_bdt"] is None
    assert r["missing_or_held_dates"] == ["2025-02-28"]
    daily["2025-02-28"] = {"date": "2025-02-28", "eligible": True, "value_bdt": "10", "reasons": []}
    assert monthly_audit(daily, "2025-02", "2025-02")[0]["total_bdt"] == "280"


def test_two_month_information_lag_and_stale_refusal():
    data = {m: month(m) for m in ("2025-01", "2025-03")}
    assert feature("2025-03", data)[1]["month"] == "2025-01"
    assert feature("2025-05", {"2025-01": month("2025-01")})[0] is None
    assert feature("2025-04", data)[1]["month"] == "2025-01"


def test_known_late_publication_refused():
    row = month("2025-01", published="2025-04-01T00:00:00+00:00")
    assert not available(row, datetime(2025, 2, 8, tzinfo=timezone.utc))
    assert feature("2025-03", {"2025-01": row})[0] is None


def test_no_fit_below_eight_and_no_future_labels():
    data = {shift("2025-01", i): month(shift("2025-01", i), 100 + i) for i in range(22)}
    early = fit_predict("2025-06", data)
    assert early["forecasts_bdt"]["ridge"] is None
    target = "2026-03"
    a = fit_predict(target, data)
    assert a["fit_rows"] >= 8
    assert max(a["fit_months"]) <= "2026-01"
    data["2026-02"] = month("2026-02", 99999999)
    data["2026-03"] = month("2026-03", 99999999)
    b = fit_predict(target, data)
    assert a["forecasts_bdt"] == b["forecasts_bdt"]
    assert a["models"]["ridge"] == b["models"]["ridge"]


def test_metrics_and_empty_are_exact():
    assert metrics([])["mae_bdt"] is None
    m = metrics([(100, 90), (200, 220)])
    assert m["mae_bdt"] == 15 and m["bias_bdt"] == 5
    assert m["rmse_bdt"] == pytest.approx(250**0.5)


def raw_day(value="100", unit="BDT", linked=True):
    return {
        "operational_date": "2025-01-01",
        "report_version_id": "v1",
        "parser_version": "modern",
        "sources": [{"id": "s1", "sha256": "a" * 64}] if linked else [],
        "measurements": [
            {
                "metric": "total_production_cost",
                "value": value,
                "unit": unit,
                "period": "daily",
                "fuel": "all",
                "zone": "national",
                "source_id": "s1",
                "source_page": 1,
                "raw_text": "Total: 100 Tk.",
            }
        ],
    }


@pytest.mark.parametrize(
    "value,unit,linked",
    [
        ("0", "BDT", True),
        ("-1", "BDT", True),
        ("100", "MW", True),
        ("100", "BDT", False),
        (None, "BDT", True),
    ],
)
def test_daily_target_exclusions(value, unit, linked):
    from research.monthly_cost import daily_audit

    assert not daily_audit([raw_day(value, unit, linked)])["2025-01-01"]["eligible"]


def test_duplicate_date_and_original_positive():
    from research.monthly_cost import daily_audit

    r = raw_day()
    assert daily_audit([r])["2025-01-01"]["eligible"]
    with pytest.raises(ValueError, match="Duplicate"):
        daily_audit([r, r])
