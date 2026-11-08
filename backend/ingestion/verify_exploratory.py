"""Read-only hosted acceptance for multivariable EDA; never modifies Neon."""

import hashlib
import json
import statistics
from contextlib import contextmanager
from decimal import Decimal, localcontext
from pathlib import Path
from time import monotonic

from app.api.exploratory import read_eda
from app.api.monitoring import read_session
from app.api.preparation import encode


def main():
    started = monotonic()
    metrics = [
        "energy_generated",
        "evening_peak_generation",
        "evening_peak_demand",
        "maximum_temperature",
        "gas_supplied",
        "production_cost_per_kwh",
        "total_production_cost",
        "energy_unserved",
    ]
    with localcontext() as context:
        context.prec = 50
        with contextmanager(read_session)() as session:
            report = read_eda(session, metrics)
            if session.new or session.dirty or session.deleted:
                raise RuntimeError("EDA must not stage database changes")
    assert report["calendar_days"] == len(report["rows"])
    assert len({r["date"] for r in report["rows"]}) == len(report["rows"])
    assert len(report["relationships"]) == 36
    for variable in report["variables"]:
        values = [
            Decimal(r[variable["key"]]) for r in report["rows"] if r[variable["key"]] is not None
        ]
        assert values, f"No retained observations for {variable['key']}"
        assert len(values) == variable["statistics"]["observations"]
        assert abs(sum(values) / len(values) - Decimal(variable["statistics"]["mean"])) <= Decimal(
            ".000001"
        )
    for pair in report["relationships"]:
        rows = [r for r in report["rows"] if r[pair["x"]] is not None and r[pair["y"]] is not None]
        assert len(rows) == pair["n"]
        if pair["pearson"] is not None:
            value = statistics.correlation(
                [float(r[pair["x"]]) for r in rows], [float(r[pair["y"]]) for r in rows]
            )
            assert abs(value - pair["pearson"]) < 1e-7
    data = encode(report)
    assert len(data) <= 3_500_000
    folder = Path("data/eda_acceptance")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "analysis.json").write_bytes(data)
    result = {
        "status": "passed",
        "analysis_id": report["analysis_id"],
        "start_date": report["start_date"],
        "end_date": report["end_date"],
        "calendar_days": report["calendar_days"],
        "complete_case_days": report["complete_case_days"],
        "observations": {v["key"]: v["statistics"]["observations"] for v in report["variables"]},
        "pairs_including_diagonal": len(report["relationships"]),
        "json_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "elapsed_seconds": round(monotonic() - started, 2),
        "database_writes": 0,
        "scope": "Consistency and numerical acceptance, not independent original-PDF validation",
    }
    (folder / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
