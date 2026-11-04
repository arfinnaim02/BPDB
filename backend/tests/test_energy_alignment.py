"""Source glyph geometry proves the fallback; corrupted tokens remain held."""

import json
from pathlib import Path

import pytest
from ingestion.page1_parser import extract_page_text, parse_page1_text, retry_energy_alignment
from ingestion.validate_page1 import check_record
from pdfplumber.utils import extract_text


class SourcePage:
    def __init__(self):
        fixture = json.loads((Path(__file__).parent /
            "fixtures/page1_geometry/7684_summary_chars.json").read_text(encoding="utf-8"))
        self.chars = [dict(zip(fixture["keys"], row, strict=True)) for row in fixture["rows"]]
        for char in self.chars:
            char.update(doctop=char["top"], upright=True, height=char["bottom"]-char["top"])

    def extract_text(self, **options):
        return extract_text(self.chars, **options)


def initial():
    page = SourcePage()
    text, metadata = extract_page_text(page)
    return page, parse_page1_text(text), metadata


def test_real_source_geometry_recovers_only_labeled_energy():
    page, original, metadata = initial()
    assert original["issues"] == [{"code": "missing_or_ambiguous_metric",
                                    "metric": "energy_generated", "matches": 0}]
    result, method = retry_energy_alignment(page, original, metadata)
    assert result["parser_version"] == "legacy_page1_v5"
    assert result["operational_date"] == "2024-05-25"
    assert result["reporting_date"] == "2024-05-26"
    assert not result["issues"] and not check_record({"extraction": result})
    assert {o["metric"]: o["value"] for o in result["observations"]} == {
        "day_peak_generation": "13726.0", "evening_peak_generation": "14623.0",
        "evening_peak_demand": "14900.0", "maximum_generation": "14707.0",
        "energy_generated": "337.880"}
    assert method["method"] == "legacy_energy_row_alignment_v1"
    assert method["y_tolerance_points"] < 0.5


@pytest.mark.parametrize("old,new", [("337.880", "3 37.880"), ("337.880", "337.880 2"),
    ("13726.0", "13727.0"), ("25-May-24", "24-May-24")])
def test_retry_rejects_ambiguous_tokens_or_disagreement(old, new):
    page, original, metadata = initial()
    extracted = page.extract_text
    page.extract_text = lambda **options: extracted(**options).replace(old, new)
    result, method = retry_energy_alignment(page, original, metadata)
    assert result is original and method == metadata


def test_retry_never_runs_for_multiple_missing_metrics():
    page, original, metadata = initial()
    original["issues"].append({"code": "missing_or_ambiguous_metric",
                               "metric": "maximum_generation", "matches": 0})
    page.extract_text = lambda **options: pytest.fail("Unexpected retry")
    assert retry_energy_alignment(page, original, metadata)[0] is original
