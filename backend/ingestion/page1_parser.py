"""Page 1 national-metric parser. Extraction is not final validation."""

import re
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


def parse_page1(path):
    # Text-only parser tests and API checks do not require the PDF runtime.
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        if not pdf.pages:
            raise ValueError("PDF has no pages")
        text = pdf.pages[0].extract_text(layout=True) or ""

    return parse_page1_text(text)


def parse_page1_text(text):
    observations = []
    issues = []
    metric_text = text

    def add(metric, pattern, unit):
        matches = list(re.finditer(pattern, metric_text, re.I))

        if len(matches) != 1:
            issues.append({
                "code": "missing_or_ambiguous_metric",
                "metric": metric,
                "matches": len(matches),
            })
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
                observation["transformation"] = (
                    "MWh / 1000 = million_kWh"
                )
            elif normalized == "mkwhr":
                observation["transformation"] = (
                    "MKWHr = million_kWh; unchanged"
                )
            else:
                raise ValueError(
                    f"Unsupported energy unit: {source_unit}"
                )

        observations.append(observation)

    if "System Summary Report" in text:
        parser_version = "modern_page1_v4"

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

        operational_date = datetime.strptime(
            dates[0], "%d-%m-%Y"
        ).date().isoformat()
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
            matches = list(re.finditer(
                r"Total:\s*" + NUMBER + r"\s*Tk\.",
                cost_section.group(1),
                re.I,
            ))

            if len(matches) == 1:
                match = matches[0]
                observations.append({
                    "metric": "total_production_cost",
                    "value": str(Decimal(
                        match.group(1).replace(",", "")
                    )),
                    "unit": "BDT",
                    "source_page": 1,
                    "raw_text": match.group(0),
                })
            else:
                issues.append({
                    "code": "missing_or_ambiguous_total_cost"
                })
        else:
            issues.append({"code": "missing_cost_section"})

        values = {
            item["metric"]: Decimal(item["value"])
            for item in observations
        }
        energy_fields = (
            "energy_generated",
            "energy_unserved",
            "energy_demand",
        )

        if all(field in values for field in energy_fields):
            residual = (
                values["energy_demand"]
                - values["energy_generated"]
                - values["energy_unserved"]
            )

            if abs(residual) > Decimal("0.0001"):
                issues.append({
                    "code": "energy_balance_mismatch",
                    "residual_million_kWh": str(residual),
                })

    elif "The Summary of Yesterday" in text:
        parser_version = "legacy_page1_v3"
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
        reporting_date = (
            legacy_date(reporting_match.group(1))
            if reporting_match
            else None
        )

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
            r"Total Gen\.\s*\(MKWH\)\s*:\s*" + NUMBER
            + r"(?![0-9.,A-Za-z])(?!(?:[ \t]+)[0-9.,])"
            + r"(?!(?:[ \t]*\n[ \t]*)[0-9.,])",
            "million_kWh",
        )

    else:
        raise ValueError("Unsupported Page 1 layout")

    return {
        "parser_version": parser_version,
        "operational_date": operational_date,
        "reporting_date": reporting_date,
        "quality_status": (
            "quarantined" if issues else "pilot_extracted"
        ),
        "observations": observations,
        "issues": issues,
    }
