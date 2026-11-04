"""Page 1 national-metric parser. Extraction is not final validation."""

import math
import re
import statistics
from datetime import datetime
from decimal import Decimal

from ingestion.numbers import decimal_token

NUMBER = r"([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)"

COST_SECTION = (
    r"(?:Production\s+Cost\s*\(Tk\.\)"
    r"|PPrroodduuccttiioonn\s+CCoosstt\s*\(\(TTkk\.\.\)\))"
    r"(.*?)"
    r"(?:E-W Interconnector|Zone-wise Load"
    r"|Status of unavailable Power Plant|\Z)"
)


def legacy_date(value):
    year = value.split("-")[-1]
    pattern = "%d-%b-%Y" if len(year) == 4 else "%d-%b-%y"
    return datetime.strptime(value, pattern).date().isoformat()


class UnsupportedPage1Layout(ValueError):
    code = "unsupported_page1_layout"


class NonSummaryFirstPage(UnsupportedPage1Layout):
    code = "power_station_table_first_page"


def extract_page_text(page):
    """Scale tolerances for physically tiny text; never alter extracted digits."""
    heights = [
        float(c["height"])
        for c in page.chars
        if c.get("text", "").strip()
        and c.get("upright", True)
        and isinstance(c.get("height"), (int, float))
        and math.isfinite(c["height"])
        and c["height"] > 0
    ]
    height = statistics.median(heights) if heights else None
    options = {"layout": True}
    method = "default_layout_v1"
    # The library's default y_tolerance is 3 PDF points. In the verified tiny-font
    # sources entire adjacent rows are closer than that and become interleaved.
    if height is not None and height < 3:
        options.update(x_tolerance=height * 0.4, y_tolerance=height * 0.2)
        method = "font_scaled_layout_v1"
    return page.extract_text(**options) or "", {
        "method": method,
        "median_character_height_points": height,
        "x_tolerance_points": options.get("x_tolerance", 3),
        "y_tolerance_points": options.get("y_tolerance", 3),
    }


def parse_page1(path):
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        if not pdf.pages:
            raise ValueError("PDF has no pages")
        text, extraction_method = extract_page_text(pdf.pages[0])
        result = parse_page1_text(text)
        result, extraction_method = retry_energy_alignment(
            pdf.pages[0], result, extraction_method
        )
    result["source_text_extraction"] = extraction_method
    return result


def retry_energy_alignment(page, original, metadata):
    """Recover a slightly displaced adjacent label without relaxing numeric guards.

    The verified May source offsets System Load Factor by 0.36 points while
    its tiny font's initial row tolerance is 0.3593. A quarter-font tolerance
    reunites that label with its percentage, keeping distinct data rows apart.
    """
    if (original["parser_version"] != "legacy_page1_v4"
            or metadata["method"] != "font_scaled_layout_v1"
            or original["issues"] != [{"code": "missing_or_ambiguous_metric",
                                      "metric": "energy_generated", "matches": 0}]):
        return original, metadata
    height = metadata["median_character_height_points"]
    text = page.extract_text(layout=True, x_tolerance=height * 0.4, y_tolerance=height * 0.25)
    candidate = parse_page1_text(text or "")
    before = {(o["metric"], o["unit"], o["value"]) for o in original["observations"]}
    after = {(o["metric"], o["unit"], o["value"]) for o in candidate["observations"]
             if o["metric"] != "energy_generated"}
    if (candidate["issues"] or len(candidate["observations"]) != 5
            or len(before) != 4 or before != after
            or candidate["operational_date"] != original["operational_date"]
            or candidate["reporting_date"] != original["reporting_date"]):
        return original, metadata
    candidate["parser_version"] = "legacy_page1_v5"
    return candidate, {**metadata, "method": "legacy_energy_row_alignment_v1",
                        "y_tolerance_points": height * 0.25,
                        "initial_y_tolerance_points": metadata["y_tolerance_points"]}


def parse_page1_text(text):
    observations = []
    issues = []
    metric_text = text

    def add(metric, pattern, unit):
        matches = list(re.finditer(pattern, metric_text, re.I))

        if len(matches) != 1:
            issues.append(
                {
                    "code": "missing_or_ambiguous_metric",
                    "metric": metric,
                    "matches": len(matches),
                }
            )
            return

        match = matches[0]
        source_value = match.group(1)
        value = Decimal(source_value.replace(",", ""))
        if parser_version.startswith("legacy") and metric == "energy_generated":
            try:
                value = decimal_token(source_value)
            except ValueError:
                issues.append({"code": "invalid_numeric_token", "metric": metric})
                return

        observation = {
            "metric": metric,
            "value": str(value),
            "unit": unit,
            "source_page": 1,
            "raw_text": match.group(0),
        }

        if unit == "million_kWh" and match.lastindex == 2:
            source_unit = match.group(2)
            observation["source_value"] = source_value
            observation["source_unit"] = source_unit
            normalized = source_unit.lower().rstrip(".")

            if normalized == "mwhr":
                observation["value"] = str(value / Decimal("1000"))
                observation["transformation"] = "MWh / 1000 = million_kWh"
            elif normalized == "mkwhr":
                observation["transformation"] = "MKWHr = million_kWh; unchanged"
            else:
                raise ValueError(f"Unsupported energy unit: {source_unit}")

        observations.append(observation)

    if "System Summary Report" in text:
        parser_version = "modern_page1_v5"

        metric_text = re.split(
            r"Zone-wise Generation Summary",
            text,
            maxsplit=1,
            flags=re.I,
        )[0]

        dates = re.findall(
            r"Date\s*:\s*(\d{2}-\d{2}-\d{4})",
            metric_text,
        )
        if len(set(dates)) != 1:
            raise ValueError("Missing or ambiguous operational date")

        operational_date = datetime.strptime(dates[0], "%d-%m-%Y").date().isoformat()
        reporting_date = None

        specifications = [
            ("day_peak_generation", "Day Peak Generation", "MW"),
            ("day_peak_demand", "Day Peak Demand", "MW"),
            (
                "evening_peak_generation",
                "Evening Peak Generation",
                "MW",
            ),
            ("evening_peak_demand", "Evening Peak Demand", "MW"),
            (
                "minimum_generation",
                "Minimum Generation of the Day",
                "MW",
            ),
            (
                "maximum_generation",
                "Maximum Generation of the Day",
                "MW",
            ),
            ("energy_generated", "Energy Generated", "million_kWh"),
            (
                "energy_unserved",
                r"Energy Unserv(?:er|e)d",
                "million_kWh",
            ),
            ("energy_demand", "Energy Demand", "million_kWh"),
            ("maximum_temperature", "Maximum Temperature", "degC"),
            ("gas_supplied", "Total Gas Supplied", "MMCFD"),
            (
                "production_cost_per_kwh",
                "Production Cost per KWHr",
                "BDT/kWh",
            ),
        ]

        source_units = {
            "million_kWh": r"(MKWHr\.?|MWHr\.?)",
            "degC": r"°C",
            "BDT/kWh": r"Tk\.?",
        }

        for metric, label, unit in specifications:
            source_unit = source_units.get(unit, re.escape(unit))
            add(
                metric,
                label + r"\s*" + NUMBER + r"\s*" + source_unit,
                unit,
            )

        cost_section = re.search(
            COST_SECTION,
            text,
            re.S | re.I,
        )

        if cost_section:
            matches = list(
                re.finditer(
                    r"Total:\s*" + NUMBER + r"\s*Tk\.",
                    cost_section.group(1),
                    re.I,
                )
            )

            if len(matches) == 1:
                match = matches[0]
                observations.append(
                    {
                        "metric": "total_production_cost",
                        "value": str(Decimal(match.group(1).replace(",", ""))),
                        "unit": "BDT",
                        "source_page": 1,
                        "raw_text": match.group(0),
                    }
                )
            else:
                issues.append({"code": "missing_or_ambiguous_total_cost"})
        else:
            issues.append({"code": "missing_cost_section"})

        values = {item["metric"]: Decimal(item["value"]) for item in observations}
        energy_fields = (
            "energy_generated",
            "energy_unserved",
            "energy_demand",
        )

        if all(field in values for field in energy_fields):
            residual = (
                values["energy_demand"] - values["energy_generated"] - values["energy_unserved"]
            )

            if abs(residual) > Decimal("0.0001"):
                issues.append(
                    {
                        "code": "energy_balance_mismatch",
                        "residual_million_kWh": str(residual),
                    }
                )

    elif "The Summary of Yesterday" in text:
        parser_version = "legacy_page1_v4"
        metric_text = text.split("EXPORT / IMPORT", 1)[0]

        date_match = re.search(
            r"The Summary of Yesterday['’]s\s+"
            r"(\d{1,2}-[A-Za-z]{3}-\d{2,4})",
            metric_text,
        )
        if not date_match:
            raise ValueError("Missing legacy operational date")

        operational_date = legacy_date(date_match.group(1))

        reporting_match = re.search(
            r"Reporting Date\s*:\s*"
            r"(\d{1,2}-[A-Za-z]{3}-\d{2,4})",
            metric_text,
        )
        reporting_date = legacy_date(reporting_match.group(1)) if reporting_match else None

        specifications = [
            ("day_peak_generation", "Day Peak Generation"),
            ("evening_peak_generation", "Evening Peak Generation"),
            (
                "evening_peak_demand",
                r"E\.P\. Demand \(at gen end\)",
            ),
            ("maximum_generation", "Maximum Generation"),
        ]

        for metric, label in specifications:
            add(
                metric,
                label + r"\s*:\s*" + NUMBER + r"\s*MW",
                "MW",
            )

        add(
            "energy_generated",
            # Do not accept a numeric prefix from a split/malformed token.
            # Never join digits speculatively: ambiguous extraction is quarantined.
            r"Total Gen\.\s*\(MKWH\)\s*:\s*"
            + NUMBER
            + r"(?![0-9.,A-Za-z])(?!(?:[ \t]+)[0-9.,])"
            + r"(?!(?:[ \t]*\n[ \t]*)[0-9.,])",
            "million_kWh",
        )

    else:
        if re.search(
            r"EVENING PEAK GENERATION AND DAY LONG ENERGY DATA OF POWER STATIONS",
            text,
            re.I,
        ):
            raise NonSummaryFirstPage("First page is a station table, not a national summary")
        raise UnsupportedPage1Layout("Unsupported Page 1 layout")

    return {
        "parser_version": parser_version,
        "operational_date": operational_date,
        "reporting_date": reporting_date,
        "quality_status": ("quarantined" if issues else "pilot_extracted"),
        "observations": observations,
        "issues": issues,
    }
