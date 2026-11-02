from datetime import date
from decimal import Decimal

import pytest
from app.api.measurement_review import read_review, screen
from app.api.monitoring import read_session
from app.core.config import Settings
from app.db.models import GenerationObservation, VersionSource
from app.main import app
from fastapi import HTTPException
from fastapi.testclient import TestClient
from ingestion.page1_parser import parse_page1_text
from sqlalchemy import select
from test_quality import seed


def pair(session, day, energy="160", peak="8000", **kwargs):
    report, version, source = seed(session, day, value=6000, **kwargs)
    for metric, value, unit, period in (
        ("energy_generated", energy, "million_kWh", "daily"),
        ("maximum_generation", peak, "MW", "daily_maximum"),
    ):
        session.add(
            GenerationObservation(
                version_id=version.id,
                source_id=source.id,
                metric=metric,
                value=Decimal(value),
                unit=unit,
                period=period,
                raw_text=f"Synthetic {metric}: {value}",
                source_page=1,
            )
        )
    session.flush()
    return report, version, source


def codes(flags):
    return {f.code for f in flags}


def test_screen_physical_bounds_and_low_ratio_are_distinct():
    flags, ratio = screen({"energy_generated": Decimal(1), "maximum_generation": Decimal(8397)})
    assert codes(flags) == {"low_energy_to_peak_ratio"}
    assert flags[0].kind == "heuristic" and ratio == "0.004962"
    flags, _ = screen({"energy_generated": Decimal(250), "maximum_generation": Decimal(8000)})
    assert "energy_above_peak_daily_ceiling" in codes(flags)
    flags, _ = screen({"energy_generated": Decimal(100), "minimum_generation": Decimal(5000)})
    assert "energy_below_minimum_daily_floor" in codes(flags)


def test_tolerance_and_heuristic_boundary():
    flags, _ = screen({"energy_generated": Decimal("192.192"), "maximum_generation": Decimal(8000)})
    assert not flags
    flags, _ = screen({"energy_generated": Decimal("19.2"), "maximum_generation": Decimal(8000)})
    assert not flags  # Exactly 0.10 is not below the threshold.
    flags, _ = screen({"energy_generated": Decimal(0), "maximum_generation": Decimal(0)})
    assert "non_positive_core_value" in codes(flags)


def test_generation_consistency_flags_do_not_change_values():
    values = {
        "day_peak_generation": Decimal(9000),
        "maximum_generation": Decimal(8000),
        "minimum_generation": Decimal(-1),
    }
    before = values.copy()
    flags, ratio = screen(values)
    assert codes(flags) == {"generation_above_daily_maximum", "non_positive_core_value"}
    assert values == before and ratio is None


def test_value_change_invalidates_fingerprint_and_caps_evidence(session):
    _, version, _ = pair(session, date(2020, 1, 1), energy="1")
    energy = session.scalar(
        select(GenerationObservation).where(
            GenerationObservation.version_id == version.id,
            GenerationObservation.metric == "energy_generated",
        )
    )
    energy.raw_text = "x" * 2000
    session.flush()
    before = read_review(session)
    assert (
        len(
            next(m.raw_text for m in before.items[0].measurements if m.metric == "energy_generated")
        )
        == 1000
    )
    energy.value = Decimal(160)
    session.flush()
    after = read_review(session)
    assert before.data_fingerprint != after.data_fingerprint and not after.items


def test_empty_and_nulls_do_not_invent_evidence(session):
    assert read_review(session).items == []
    seed(session, date(2020, 1, 1), value=None)
    result = read_review(session)
    assert result.canonical_dates == 1 and result.energy_peak_pairs == 0
    assert result.flagged_dates == 0


def test_provenance_pagination_filters_and_read_only(session):
    for day in (1, 2, 3):
        pair(session, date(2020, 1, day), energy="1")
    before = session.scalars(select(GenerationObservation.value)).all()
    result = read_review(session, page=2, page_size=1)
    assert result.flagged_dates == 3 and result.total_pages == 3
    assert result.items[0].operational_date == date(2020, 1, 2)
    assert result.items[0].measurements[0].source_sha256 == "a" * 64
    assert result.flag_counts == {"low_energy_to_peak_ratio": 3}
    assert result.data_fingerprint == read_review(session, page_size=50).data_fingerprint
    selected = read_review(session, start_date=date(2020, 1, 2), end_date=date(2020, 1, 2))
    assert selected.flagged_dates == 1 and selected.canonical_dates == 1
    assert before == session.scalars(select(GenerationObservation.value)).all()
    assert not session.dirty and not session.new and not session.deleted


def test_wrong_dimensions_are_reviewed_without_computing_ratio(session):
    _, version, _ = pair(session, date(2020, 1, 1), energy="1")
    energy = session.scalar(
        select(GenerationObservation).where(
            GenerationObservation.version_id == version.id,
            GenerationObservation.metric == "energy_generated",
        )
    )
    energy.unit = "MWh"
    session.flush()
    result = read_review(session)
    assert result.energy_peak_pairs == 0
    assert codes(result.items[0].flags) == {"measurement_dimension_or_provenance"}
    assert result.items[0].energy_to_peak_ratio is None


def test_missing_link_is_reviewed(session):
    _, version, _ = pair(session, date(2020, 1, 1))
    link = session.scalar(select(VersionSource).where(VersionSource.version_id == version.id))
    session.delete(link)
    session.flush()
    assert read_review(session).flagged_dates == 1


def test_regional_and_noncanonical_versions_excluded(session):
    pair(session, date(2020, 1, 1))
    pair(session, date(2020, 1, 2), energy="1", quality="quarantined")
    pair(session, date(2020, 1, 3), energy="1", grain="regional_daily")
    report, _, _ = pair(session, date(2020, 1, 4), energy="1")
    report.current_version_id = None
    session.flush()
    result = read_review(session)
    assert result.canonical_dates == 1 and result.flagged_dates == 0


def test_review_auth_validation_no_store(monkeypatch, session):
    settings = Settings(_env_file=None, admin_api_key="review-test-only")
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    snapshot = read_review(session)
    monkeypatch.setattr("app.api.measurement_review.read_review", lambda *_: snapshot)
    app.dependency_overrides[read_session] = lambda: None
    try:
        with TestClient(app) as client:
            assert client.get("/api/v1/dataset/measurement-review").status_code == 401
            headers = {"X-API-Key": "review-test-only"}
            assert (
                client.get(
                    "/api/v1/dataset/measurement-review?page_size=51", headers=headers
                ).status_code
                == 422
            )
            response = client.get("/api/v1/dataset/measurement-review", headers=headers)
            assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    finally:
        app.dependency_overrides.clear()
    with pytest.raises(HTTPException):
        read_review(session, start_date=date(2020, 2, 1), end_date=date(2020, 1, 1))


LEGACY = """The Summary of Yesterday's 04-Jan-2020
Day Peak Generation : 6108.5MW
Evening Peak Generation : 8397.0MW
E.P. Demand (at gen end) : 8397.0MW
Maximum Generation : 8397.0MW
Total Gen. (MKWH) : """


@pytest.mark.parametrize("token", ["1 57.6", "1\t57.6", "1\n57.6", "1.2.3", "1,57.6", "1e3"])
def test_legacy_energy_never_silently_accepts_numeric_prefix(token):
    result = parse_page1_text(LEGACY + token)
    assert result["quality_status"] == "quarantined"
    assert not any(m["metric"] == "energy_generated" for m in result["observations"])


@pytest.mark.parametrize(
    "token,expected", [("157.6", "157.6"), ("1,234.50", "1234.50"), ("0", "0")]
)
def test_legacy_valid_energy_preserves_exact_value(token, expected):
    result = parse_page1_text(LEGACY + token + "\nEXPORT / IMPORT")
    assert result["parser_version"] == "legacy_page1_v3"
    assert result["quality_status"] == "pilot_extracted"
    assert (
        next(m["value"] for m in result["observations"] if m["metric"] == "energy_generated")
        == expected
    )
