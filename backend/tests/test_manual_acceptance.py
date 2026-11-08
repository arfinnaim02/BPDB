import io
import zipfile

import pytest
from app.api.preparation import bundle
from research.check_manual_acceptance import inspect_zip
from test_preparation import build, day


def test_export_acceptance_checks_real_blank_cells_without_fabricating_estimates():
    result = inspect_zip(bundle(build([day(1), day(11), day(15)])), 15)
    assert result["csv_rows"] == 15
    assert result["missing_original_cells"] == 12
    assert result["estimated_rows"] == 0
    assert result["blank_preservation"] == "passed"


def test_export_acceptance_refuses_modified_csv_bytes():
    data = bundle(build([day(1)]))
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as source, zipfile.ZipFile(out, "w") as target:
        for name in source.namelist():
            value = source.read(name)
            target.writestr(name, value + b"changed" if name == "daily_values.csv" else value)
    with pytest.raises(AssertionError):
        inspect_zip(out.getvalue(), 15)
