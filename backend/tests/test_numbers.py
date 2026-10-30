from decimal import Decimal

import pytest
from ingestion.numbers import decimal_token


@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, None),
        ("", None),
        ("-", None),
        ("0", Decimal("0")),
        ("1,234.50", Decimal("1234.50")),
        (" -12.30 ", Decimal("-12.30")),
    ],
)
def test_exact_decimal_and_missing(raw, expected):
    actual = decimal_token(raw)
    assert actual == expected
    if actual is not None:
        assert actual.as_tuple() == expected.as_tuple()


@pytest.mark.parametrize("raw", ["abc", "1,2", "NaN", "12 MW"])
def test_ambiguous_token_rejected(raw):
    with pytest.raises(ValueError):
        decimal_token(raw)
