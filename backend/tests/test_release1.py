"""Leakage and reproducibility checks; synthetic series are never published as results."""

import math
from datetime import date, timedelta

import pytest
from research import release1 as r


def series():
    output = {}
    day = r.START
    while day <= r.VAL_END:
        n = (day - r.START).days
        output[day] = {
            "value": 200 + math.sin(n / 50) * 20 + n * 0.02,
            "original": str(200 + n * 0.02),
            "eligible": True,
            "available_at": None,
        }
        day += timedelta(days=1)
    return output


def test_origin_uses_calendar_lags_and_rejects_unknown_strict_availability():
    data = series()
    target = date(2024, 4, 20)
    f = r.feature_row(data, target, "complete")
    assert f["latest_donor"] == "2024-04-18" and f["unknown_availability_inputs"] == 9
    assert r.feature_row(data, target, "complete", strict=True) is None
    assert r.donor(data, target - timedelta(days=1), target) is None
    data[target - timedelta(days=2)]["available_at"] = "2024-04-20T06:00:00Z"
    assert r.donor(data, target - timedelta(days=2), target) is None


def test_input_fill_uses_original_past_only_and_has_bounded_refusals():
    data = series()
    target, requested = date(2024, 4, 20), date(2024, 4, 18)
    for i in range(5):
        data[requested - timedelta(days=i)]["value"] = None
    assert r.input_value(data, requested, target, "past_original_3")[0] is None
    value, filled = r.input_value(data, requested, target, "seasonal_original_7")
    assert filled and value[1] == requested - timedelta(days=7)
    data[requested - timedelta(days=7)]["value"] = None
    assert r.input_value(data, requested, target, "seasonal_original_7")[0] is None


def test_future_and_target_changes_do_not_change_origin_features():
    data = series()
    target = date(2024, 4, 20)
    expected = r.feature_row(data, target, "complete")
    for day in data:
        if day >= target - timedelta(days=1):
            data[day]["value"] = 999999
    assert r.feature_row(data, target, "complete") == expected


def test_masking_is_training_only_deterministic_and_keeps_abstention():
    data = series()
    first = r.masking_experiment(data)
    for day in data:
        if day > r.TRAIN_END:
            data[day]["value"] = -100000
    assert r.masking_experiment(data) == first
    assert all(x["filled_days"] == 0 for x in first if x["policy"] == "complete")
    assert all(x["masked_days"] == 20 * x["block_days"] for x in first)


def test_error_metrics_and_empty_coverage():
    assert r.metrics([1, 2], [2, 1]) == {"n": 2, "mae": 1, "rmse": 1, "bias": 0}
    assert r.metrics([], [])["mae"] is None


def test_real_ridge_scaling_fit_cutoff_and_saved_inference():
    pytest.importorskip("sklearn")
    data = series()
    stop = date(2022, 12, 30)
    model, info = r.fit(data, "complete", 10, stop)
    assert info["last_label"] == str(stop)
    before = r.evaluate(model, data, "complete", [date(2023, 1, 1)])
    for day in data:
        if day > stop:
            data[day]["value"] = 100000
    again, _ = r.fit(data, "complete", 10, stop)
    assert model.steps[0][1].mean_.tolist() == again.steps[0][1].mean_.tolist()
    assert before and model.steps[1][1].coef_.tolist() == again.steps[1][1].coef_.tolist()


def test_end_to_end_synthetic_pipeline_reserves_test_and_exports_saved_model():
    pytest.importorskip("sklearn")
    from app.api.preparation import build_snapshot, bundle
    from test_preparation import day

    days = []
    for n in range((r.END - r.START).days + 1):
        d = day(n + 1, str(200 + 10 * math.sin(n / 40) + n * 0.01))
        d.operational_date = r.START + timedelta(days=n)
        d.available_at = None
        days.append(d)
    snapshot = build_snapshot(days, "energy_generated", r.START, r.END, r.TRAIN_END, r.VAL_END)
    report, input_series = r.run(bundle(snapshot))
    assert max(input_series) == r.VAL_END
    assert report["reserved_test"]["metrics"] is None
    assert report["reserved_test"]["predictions"] is None
    assert report["test_report"]["no_test_predictions"]
    assert report["strict_availability_feature_days"] == 0
    assert report["test_report"]["saved_model_max_difference"] < 1e-8
    assert len(report["predictions"]) == 366
    assert all(
        date.fromisoformat(row["latest_donor"])
        <= date.fromisoformat(row["date"]) - timedelta(days=2)
        for row in report["predictions"]
    )
    assert all(row["common_dates"]["n"] == 366 for row in report["validation"])
