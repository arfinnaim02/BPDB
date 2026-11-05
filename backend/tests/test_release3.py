"""Synthetic final-evaluation safety tests. Never publish these as BPDB scores."""

import copy
import json
import math
from datetime import timedelta
from types import SimpleNamespace

import pytest
from app.api.experiments import load_comparison
from research import release1 as r1
from research import release2 as r2
from research import release3 as r3
from test_release1 import series


def full_series():
    data = series()
    for n in range(365):
        day = r3.FIRST + timedelta(days=n)
        data[day] = {
            "value": 250 + math.sin(n / 40) * 20,
            "original": "250",
            "eligible": True,
            "available_at": None,
        }
    return data


def test_final_input_requires_exact_frozen_archive():
    with pytest.raises(ValueError, match="Exact frozen"):
        r3.run(b"changed", {})


def test_final_settings_are_locked_to_pretest_reference():
    reference = load_comparison()
    expected = r3.locked_configurations(reference)
    assert expected["autoregression"]["id"] == "ols"
    changed = copy.deepcopy(reference)
    changed["selected"]["random_forest"]["parameters"]["max_depth"] = 99
    with pytest.raises(ValueError, match="settings changed"):
        r3.locked_configurations(changed)
    changed = copy.deepcopy(reference)
    changed["training_selected_finalist"] = "random_forest"
    with pytest.raises(ValueError, match="selection reference"):
        r3.locked_configurations(changed)


def test_final_reader_retains_dense_test_calendar_without_changing_release1_reader():
    from app.api.preparation import build_snapshot, bundle
    from test_preparation import day

    originals = []
    for n in range((r1.END - r1.START).days + 1):
        item = day(n + 1, str(200 + n * 0.01))
        item.operational_date = r1.START + timedelta(days=n)
        item.available_at = None
        originals.append(item)
    data = bundle(
        build_snapshot(originals, "energy_generated", r1.START, r1.END, r1.TRAIN_END, r1.VAL_END)
    )
    _, old, _ = r1.read_input(data)
    _, full, coverage = r3.read_final_input(data)
    assert max(old) == r1.VAL_END and max(full) == r3.LAST
    assert len([d for d in full if d >= r3.FIRST]) == 365
    assert coverage["2025"]["eligible"] == 365
    assert all(full[d] == row for d, row in old.items())


@pytest.mark.parametrize(
    "family", ["autoregression", "ridge", "random_forest", "gradient_boosting"]
)
def test_final_fit_never_uses_2025_labels_and_saved_inference_matches(family):
    pytest.importorskip("sklearn")
    data = full_series()
    configs = r3.locked_configurations(load_comparison())
    models, saved, info = r3.fit_models(data, configs)
    assert all(x["last_label"] <= str(r3.FIT_END) for x in info.values())
    day = r3.FIRST + timedelta(days=60)
    f = r1.feature_row(data, day, r2.POLICY)
    prediction = r1.evaluate(models[family], data, r2.POLICY, [day])[day]
    assert abs(r3.saved_predict(saved[family], f["x"]) - prediction) < 1e-8
    for d in data:
        if d >= r3.FIRST:
            data[d]["value"] = -999999
    _, again, _ = r3.fit_models(data, configs)
    assert saved[family] == again[family]


def test_test_features_can_use_past_test_history_but_not_future_or_target():
    data = full_series()
    day = r3.FIRST + timedelta(days=60)
    f = r1.feature_row(data, day, r2.POLICY)
    assert f["latest_donor"] == str(day - timedelta(days=2))
    assert f["latest_donor"] > str(r3.FIRST)
    for d in data:
        if d >= day - timedelta(days=1):
            data[d]["value"] = -999999
    assert r1.feature_row(data, day, r2.POLICY) == f


def test_paired_calendar_bootstrap_is_deterministic_and_preserves_missing_targets():
    rows = []
    for n in range(35):
        row = {
            "date": str(r3.FIRST + timedelta(days=n)),
            "actual": 10 if n % 4 else None,
            **dict.fromkeys(r2.MODELS, 11),
        }
        row["autoregression"] = 13
        rows.append(row)
    result = r3.paired_bootstrap(rows)
    assert result == r3.paired_bootstrap(rows)
    assert [r["block_days"] for r in result] == [7, 14, 28]
    assert all(
        r["point_difference"] == 2 and r["lower_2_5"] == 2 and r["upper_97_5"] == 2 for r in result
    )
    assert all(r["valid_replicates"] == 2000 for r in result)
    assert rows[0]["actual"] is None


def test_retained_final_evaluation_rejects_changed_protocol_key():
    receipt = {"evaluation_key": "different-key"}

    class Request:
        def __init__(self, value):
            self.value = value

        def execute(self, **kwargs):
            return self.value

    class Files:
        def list(self, **kwargs):
            return Request({"files": [{"id": "saved"}]})

        def get_media(self, **kwargs):
            return Request(json.dumps(receipt).encode())

    service = SimpleNamespace(files=lambda: Files())
    with pytest.raises(ValueError, match="already retained"):
        r3.final_registry(service, "test-folder")
    receipt["evaluation_key"] = r3.evaluation_key()
    assert r3.final_registry(service, "test-folder") == receipt


def test_hosted_repeat_restores_result_without_refitting(monkeypatch, tmp_path, capsys):
    import sys

    service = SimpleNamespace(close=lambda: None)
    monkeypatch.setattr("ingestion.online_recovery.drive_service", lambda: (service, "folder"))
    monkeypatch.setattr(r3, "final_registry", lambda *_: {"retained": True})
    monkeypatch.setattr(r3, "restore_result", lambda *_: {"experiment_id": "retained-result"})

    def forbidden(*args):
        raise AssertionError("A retained final evaluation must not be refitted")

    monkeypatch.setitem(
        sys.modules,
        "ingestion.drive_sync",
        SimpleNamespace(digest=forbidden, download=forbidden, find_files=forbidden),
    )
    monkeypatch.setattr(r3, "run", forbidden)
    monkeypatch.setattr(sys, "argv", ["release3", "--online", "--output", str(tmp_path)])
    r3.main()
    assert "restored_existing_final_evaluation" in capsys.readouterr().out
