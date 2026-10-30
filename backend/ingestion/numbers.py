"""Adapted from the supplied legacy parser's _f helper, with strict token validation.

No unit rescaling, estimation or float round-trip. Caller retains the source raw text.
"""

import re
from decimal import Decimal

TOKEN = re.compile(r"[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?")


def decimal_token(raw: str | None) -> Decimal | None:
    if raw is None or raw.strip() in {"", "-"}:
        return None
    token = raw.strip()
    if not TOKEN.fullmatch(token):
        raise ValueError("Ambiguous or malformed numeric token")
    return Decimal(token.replace(",", ""))
