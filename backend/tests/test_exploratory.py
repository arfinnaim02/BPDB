from datetime import date, timedelta
from decimal import Decimal

import pytest
from app.api.exploratory import build_eda, correlation, describe, ranks, read_eda
from app.api.monitoring import read_session
from app.core.config import Settings
from app.db.models import CostObservation, EnvironmentObservation, GenerationObservation
from app.main import app
from fastapi import HTTPException
from fastapi.testclient import TestClient
from test_quality import seed


def ds(values):
    return [None if v is None else Decimal(str(v)) for v in values]


def test_descriptive_quantiles_moments_and_missingness():
    s = describe(ds([1, 2, None, None, 3, 4]))
    assert s["observations"] == 4 and s["missing_days"] == 2
    assert s["q1"] == "1.75" and s["q3"] == "3.25" and s["median"] == "2.5"
    assert s["sample_stddev"] == "1.290994"
    assert s["adjusted_skewness"] == "0"
    assert s["adjusted_excess_kurtosis"] == "-1.2"
    assert s["longest_missing_run"] == 2


def test_empty_constant_zero_and_tukey_candidates_are_not_errors():
    s = describe(ds([0, 0, None]))
    assert s["zero_days"] == 2 and s["mean"] == "0" and s["cv_percent"] is None
    assert s["adjusted_skewness"] is None
    assert describe(ds([None]))["mean"] is None
    assert describe(ds([1, 1, 1, 1, 100]))["iqr_outside_days"] == 1
    assert correlation(ds([1, 1, 1]), ds([2, 3, 4])) == (None, "constant_variable")
    assert correlation(ds([1, 2]), ds([2, 3])) == (None, "insufficient_pairs")


def test_tied_ranks_and_correlations():
    assert ranks(ds([10, 10, 30])) == ds([1.5, 1.5, 3])
    assert correlation(ds([1, 2, 3, 4]), ds([8, 6, 4, 2]))[0] == -1


def test_pairwise_calendar_differences_and_lags_do_not_compress_gaps():
    dates = [date(2025, 1, 1) + timedelta(days=i) for i in range(6)]
    meta = {k: {"label": k, "unit": "MW"} for k in ("x", "y")}
    r = build_eda(dates, {"x": ds([1, None, 3, 4, 8, 16]), "y": ds([2, 4, 6, 8, 16, 32])}, meta, [])
    pair = next(p for p in r["relationships"] if p["x"] == "x" and p["y"] == "y")
    assert pair["n"] == 5 and pair["pearson"] == pair["spearman"] == 1
    assert pair["change_n"] == 3 and pair["change_pearson"] == 1
    assert r["variables"][0]["lags"][0]["n"] == 3
    assert r["complete_case_days"] == 5 and r["rows"][1]["x"] is None
    assert len(r["analysis_id"]) == 64


def test_eda_reads_original_values_provenance_and_modern_covariates(session):
    for i in range(4):
        _, v, src = seed(session, date(2025, 1, 1) + timedelta(days=i), value=i)
        session.add_all(
            [
                GenerationObservation(
                    version_id=v.id,
                    source_id=src.id,
                    metric="energy_generated",
                    unit="million_kWh",
                    period="daily",
                    value=Decimal(i) * 2,
                ),
                EnvironmentObservation(
                    version_id=v.id,
                    source_id=src.id,
                    metric="maximum_temperature",
                    unit="degC",
                    period="daily_maximum",
                    value=Decimal(i) + 25,
                ),
                CostObservation(
                    version_id=v.id,
                    source_id=src.id,
                    metric="total_production_cost",
                    unit="BDT",
                    period="daily",
                    fuel="all",
                    value=Decimal(i) * 100,
                ),
                CostObservation(
                    version_id=v.id,
                    source_id=src.id,
                    metric="total_production_cost",
                    unit="BDT",
                    period="daily",
                    fuel="gas",
                    value=999,
                ),
            ]
        )
    session.flush()
    r = read_eda(session, ["energy_generated", "maximum_temperature", "total_production_cost"])
    assert r["calendar_days"] == 4 and r["complete_case_days"] == 4
    assert Decimal(r["rows"][0]["total_production_cost"]) == 0
    assert r["variables"][1]["statistics"]["cv_percent"] is None
    assert len(r["lineage"]) == 4
    assert not session.new and not session.dirty


def test_selection_bounds_and_outside_range(session):
    for metrics in ([], ["not_a_variable"], ["energy_generated"] * 2, list("123456789")):
        with pytest.raises(HTTPException) as e:
            read_eda(session, metrics)
        assert e.value.status_code == 422
    seed(session, date(2025, 1, 1))
    r = read_eda(session, ["energy_generated"], date(2026, 1, 1))
    assert r["rows"] == [] and r["calendar_days"] == 0


def test_duplicate_measurements_fail_closed(session):
    _, v, src = seed(session, date(2025, 1, 1))
    session.add(
        GenerationObservation(
            version_id=v.id,
            source_id=src.id,
            metric="day_peak_generation",
            unit="MW",
            period="day_peak",
            value=99,
        )
    )
    # Existing uniqueness constraints prevent exact duplicates; wrong periods are also refused.
    session.rollback()
    _, v, src = seed(session, date(2025, 1, 1), row=False)
    session.add(
        GenerationObservation(
            version_id=v.id,
            source_id=src.id,
            metric="day_peak_generation",
            unit="MW",
            period="wrong",
            value=99,
        )
    )
    session.flush()
    with pytest.raises(HTTPException) as e:
        read_eda(session, ["day_peak_generation"])
    assert e.value.status_code == 503


def test_eda_auth_and_input_validation(monkeypatch):
    settings = Settings(_env_file=None, admin_api_key="eda-test-key")
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    app.dependency_overrides[read_session] = lambda: None
    try:
        with TestClient(app) as client:
            assert client.get("/api/v1/analytics/exploratory").status_code == 401
            assert (
                client.get(
                    "/api/v1/analytics/exploratory?metric=invalid",
                    headers={"X-API-Key": "eda-test-key"},
                ).status_code
                == 422
            )
            assert (
                client.get(
                    "/api/v1/analytics/exploratory?start_date=2025-02-30",
                    headers={"X-API-Key": "eda-test-key"},
                ).status_code
                == 422
            )
    finally:
        app.dependency_overrides.clear()
