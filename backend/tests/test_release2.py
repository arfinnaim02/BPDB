"""Synthetic checks are separate from published real-data experiment results."""

import copy
from datetime import date, timedelta

import pytest
from research import release1 as r1
from research import release2 as r2
from test_release1 import series


def test_frozen_identity_rejects_changed_input_before_fitting():
    with pytest.raises(ValueError, match="exact frozen"):
        r2.run(b"different input", {})


def test_tree_inference_matches_float32_split_semantics():
    tree = {
        "left": [1, -1, -1],
        "right": [2, -1, -1],
        "feature": [0, -2, -2],
        "threshold": [1.0, -2, -2],
        "value": [0, 5, 10],
    }
    assert r2.tree_predict(tree, [1.000000001]) == 5
    assert r2.tree_predict(tree, [1.001]) == 10


@pytest.mark.parametrize("family", ["autoregression", "random_forest", "gradient_boosting"])
def test_fit_is_train_only_and_saved_models_reproduce_predictions(family):
    pytest.importorskip("sklearn")
    data = series()
    config = next(c for c in r2.CANDIDATES if c["family"] == family)
    stop = date(2021, 12, 30)
    model, info = r2.fit_candidate(data, config, stop)
    expected = r1.evaluate(model, data, r2.POLICY, [date(2022, 1, 1), date(2022, 6, 1)])
    saved = r2.export_model(model, config, info)
    assert info["last_label"] == str(stop)
    for day, value in expected.items():
        features = r1.feature_row(data, day, r2.POLICY)["x"]
        assert abs(r2.predict_saved(saved, features) - value) < 1e-8
    for day in data:
        if day > stop:
            data[day]["value"] = 100000
    second, again = r2.fit_candidate(data, config, stop)
    assert r2.export_model(second, config, again) == saved


def test_training_selection_ignores_validation_targets_and_uses_common_dates():
    pytest.importorskip("sklearn")
    data = series()
    first = r2.select_training(data)
    for day in data:
        if day > r1.TRAIN_END:
            data[day]["value"] = -999999
    assert r2.select_training(data) == first
    selected, scores, folds = first
    assert len(scores) == 5 and len(selected) == 3 and len(folds) == 3
    assert len({c["n"] for c in scores}) == 1
    for f in folds:
        stop = date.fromisoformat(f["start"]) - timedelta(days=2)
        assert all(date.fromisoformat(x["last_label"]) <= stop for x in f["fits"])


def test_common_validation_scores_exclude_missing_and_own_dates_differ():
    rows = [
        {"date": "2024-01-01", "actual": 100, **dict.fromkeys(r2.MODELS, 110)},
        {"date": "2024-01-02", "actual": None, **dict.fromkeys(r2.MODELS, 80)},
        {"date": "2024-01-03", "actual": 100, **dict.fromkeys(r2.MODELS, 120)},
    ]
    rows[2]["gradient_boosting"] = None
    scores = r2.summarize(rows)
    assert all(s["common_dates"]["n"] == 1 for s in scores)
    assert all(s["common_dates"]["mae"] == 10 for s in scores)
    assert scores[0]["own_dates"]["n"] == 2 and scores[-1]["own_dates"]["n"] == 1
    assert scores[0]["calendar_forecasts"] == 3
    assert rows[1]["actual"] is None


def test_model_grid_is_fixed_and_does_not_request_test_evaluation():
    grid = copy.deepcopy(r2.CANDIDATES)
    assert len(grid) == 5 and r2.POLICY == "seasonal_original_7"
    assert all(c["parameters"].get("random_state", r2.SEED) == r2.SEED for c in grid)
    assert "reserved" in r2.PROTOCOL["test"]
