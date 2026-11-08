import copy
import json

import pytest
from research.treatment_impact_protocol import PATH, validate


def protocol():
    return json.loads(PATH.read_text())


def test_registration_has_no_results_or_executable_model_updates():
    data = protocol()
    assert validate(data) == validate(copy.deepcopy(data))
    assert len(validate(data)) == 64
    assert data["results"] is None
    assert all(value == 0 for value in data["safety"].values())
    assert data["prospective_confirmation"]["fit"].startswith("None.")
    assert data["historical_design"]["parameter_search"] is False


@pytest.mark.parametrize(
    "key",
    [
        "production_retraining",
        "target_imputation",
        "run_experiment_now",
        "auto_promote_recovered_sources",
    ],
)
def test_registration_refuses_execution_or_invented_targets(key):
    data = protocol()
    data["safety"][key] = True
    with pytest.raises(ValueError, match="authorize execution"):
        validate(data)


def test_training_embargo_and_previously_evaluated_year_are_guarded():
    data = protocol()
    data["historical_design"]["folds"][0]["fit_stop"] = "2021-01-01"
    with pytest.raises(ValueError, match="embargo"):
        validate(data)
    data = protocol()
    data["scope"]["excluded_years"] = []
    with pytest.raises(ValueError, match="excluded"):
        validate(data)


def test_changed_source_or_inserted_results_require_new_registration():
    data = protocol()
    data["source"]["bundle_sha256"] = "changed"
    with pytest.raises(ValueError, match="source"):
        validate(data)
    data = protocol()
    data["results"] = {"mae": 1}
    with pytest.raises(ValueError, match="results"):
        validate(data)


def test_future_period_is_reserved_and_inconclusive_outcome_is_explicit():
    data = protocol()
    assert "inconclusive" in data["prospective_confirmation"]["decision"]
    assert "Never reconstruct" in data["prospective_confirmation"]["missed_issues"]
    data["prospective_confirmation"]["target_start"] = "2025-01-01"
    with pytest.raises(ValueError, match="Prospective"):
        validate(data)
