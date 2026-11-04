# Reviewed April and May 2024 recovery

The source review from investigation 41786772769 supports these exact revisions:

| PDF | Operational date | Reporting date | SHA-256 |
| --- | --- | --- | --- |
| 7614page1.pdf | 2024-04-20 | 2024-04-21 | a42f66f0b99d97046c2597ca4057451d1fd292579a0362f335e395205e27b8d1 |
| 7684page1.pdf | 2024-05-25 | 2024-05-26 | ed683801649616264678baf8d92c185f207a5c12b1b7cf5beb58bf75fb2f4235 |

Both original PDFs were rendered and their printed dates, labels and five values
checked visually. Exact expected values and parser versions are pinned in
SPRING_REVIEW in backend/ingestion/reviewed_recovery.py. The five metrics are day
peak generation, evening peak generation, evening peak demand, maximum generation,
and daily energy generated. No new metrics or estimates are introduced.

## Source-supported parser repair

In the May PDF, the energy value and the load-factor percentage share top position
77.4224947 points. The intervening System Load Factor label starts 0.3599963 points
lower. The tiny-font tolerance was 0.3593175 points, which separated the label from
the value row and made the energy's following percentage look like a malformed
numeric token. The source's energy is 337.880 MKWH; load factor is a separate field.

The normal extraction remains the first attempt. Only a tiny-font legacy source
whose sole issue is missing energy receives a retry at one-quarter font height
(0.4491469 points here). The retry is accepted only if it produces all five metrics
without issues and agrees with both dates and every already extracted metric/unit/
value. All existing split-token guards still apply. No digits are rewritten.

Accepted retry cases use legacy_page1_v5 with legacy_energy_row_alignment_v1
metadata and both tolerance values recorded. Other legacy sources retain v4;
modern sources retain their existing parser. The real PDF glyph geometry fixture
contains a bounded summary/header subset, with coordinates rounded to seven decimal
places. It reproduces the original failure and the accepted retry. Regression
tests reject changed dates, changed peaks, split energy digits and extra numeric
tokens, and prohibit this retry when multiple metrics are missing.

The clipped 7 April PDF remains quarantined. Its missing labels are not restored
from numeric row positions. Mismatched-date and station-table sources remain held.

## Hosted recovery

BPDB reviewed gap recovery now runs the explicit --batch spring sequence:
preview, atomic registration/staging, independent readback, gap-only promotion,
and final verification. The default CLI batch remains january for compatibility.
Each batch has its own hash/version key; existing canonical records cannot be
replaced. Reports are preserved in Drive and GitHub artifacts, and Neon keeps the
reviewed extraction in ingestion-run lineage. No historical availability time is
invented and no collection checkpoint is replaced.

Expected first successful spring run: ten inserted measurements, then two promoted
dates. Successful repeats insert and promote zero. A new research snapshot is
required to include recovered records in any previously frozen analysis.

## Predeployment verification

Ruff passed. Backend tests: 210 passed, one opt-in database integration skipped.
Both exact original PDF review gates passed locally. The source-comparison check
compares original PDF extractions against the previous parser: only the reviewed
May source may gain its missing energy observation. Hosted acceptance is recorded
after the online job completes.
