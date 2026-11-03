import json
from pathlib import Path

import pytest
from ingestion.page1_parser import (
    NonSummaryFirstPage,
    extract_page_text,
    parse_page1_text,
)
from ingestion.validate_page1 import check_record

FIXTURES = Path(__file__).parent / "fixtures/page1_geometry"
SOURCES = json.loads((FIXTURES / "sources.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("source", SOURCES, ids=lambda s: s["fixture"])
def test_verified_legacy_rows_preserve_dates_units_and_five_exact_values(source):
    text = (FIXTURES / source["fixture"]).read_text(encoding="utf-8")
    result = parse_page1_text(text)
    assert result["parser_version"] == "legacy_page1_v4"
    assert result["operational_date"] == source["operational_date"]
    assert result["reporting_date"] == source["reporting_date"]
    assert result["issues"] == [] and check_record({"extraction": result}) == []
    assert {m["metric"]: m["value"] for m in result["observations"]} == source["values"]
    assert all(
        m["unit"] == "MW" for m in result["observations"] if m["metric"] != "energy_generated"
    )
    assert next(m for m in result["observations"] if m["metric"] == "energy_generated")["unit"] == (
        "million_kWh"
    )
    # The right-hand today's estimates are not yesterday's measurements.
    assert len(result["observations"]) == 5
    assert not any(
        m["metric"] in ("day_peak_demand", "minimum_generation") for m in result["observations"]
    )


class Page:
    def __init__(self, heights):
        self.chars = [{"height": h, "text": "A", "upright": True} for h in heights]
        self.options = None

    def extract_text(self, **options):
        self.options = options
        return "original unchanged text 1 57.6"


def test_physically_small_font_uses_bounded_tolerances_without_rewriting_text():
    page = Page([2.0, 2.0, 2.0, 20.0])
    text, metadata = extract_page_text(page)
    assert text == "original unchanged text 1 57.6"
    assert metadata["method"] == "font_scaled_layout_v1"
    assert page.options["layout"] is True
    assert page.options["y_tolerance"] < 1
    assert page.options["x_tolerance"] < 1
    assert metadata["median_character_height_points"] == 2.0


def test_normal_text_keeps_existing_extraction_and_ignores_nonfinite_geometry():
    page = Page([8.0, 8.0, float("nan"), 0.0, float("inf")])
    _, metadata = extract_page_text(page)
    assert page.options == {"layout": True}
    assert metadata["method"] == "default_layout_v1"
    assert metadata["median_character_height_points"] == 8.0


def test_missing_character_geometry_does_not_guess_a_layout():
    page = Page([])
    _, metadata = extract_page_text(page)
    assert metadata["median_character_height_points"] is None
    assert page.options == {"layout": True}


def test_page2_station_table_remains_an_explicit_unsupported_source_kind():
    text = """EVENING PEAK GENERATION AND DAY LONG ENERGY DATA OF POWER STATIONS
Date : 31-Dec-23 Page -2
Name of the Power Stations Installed Capacity MW Energy Generated KWH"""
    with pytest.raises(NonSummaryFirstPage) as error:
        parse_page1_text(text)
    assert error.value.code == "power_station_table_first_page"


def test_existing_modern_sample_preserves_all_thirteen_measurements_and_units():
    evidence = json.loads((FIXTURES / "modern_recent.json").read_text(encoding="utf-8"))
    result = parse_page1_text((FIXTURES / "modern_recent.txt").read_text(encoding="utf-8"))
    assert result["parser_version"] == "modern_page1_v5"
    assert result["operational_date"] == evidence["operational_date"]
    assert result["issues"] == [] and len(result["observations"]) == 13
    assert {m["metric"]: m["value"] for m in result["observations"]} == evidence["values"]
    for m in result["observations"]:
        if m["metric"] in ("energy_generated", "energy_demand", "energy_unserved"):
            assert m["unit"] == "million_kWh" and m["source_unit"].lower().startswith("mkwhr")
