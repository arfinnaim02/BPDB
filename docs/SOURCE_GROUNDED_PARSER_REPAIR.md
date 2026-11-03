# Source-grounded small-font Page 1 repair

3 November 2026. Parser release: `legacy_page1_v4`, `modern_page1_v5`.
No database migration, canonical promotion or historical re-import is performed here.

## Verified cause

The first online investigation preserved original bytes for 7390page1.pdf and
7396page1.pdf. Their median character heights are about 2.515 and 2.036 PDF points.
Pdfplumber's default 3-point vertical word tolerance interleaved adjacent summary rows.
This produced corrupted labels and numbers in extracted text even though the rendered
PDFs show distinct, readable rows. It was not evidence that those measurements were
absent from the originals.

The originals were downloaded from the hosted artifact, verified against the preserved
SHA-256 values, rendered with Poppler and inspected at an enlarged header crop. Each
of the five supported legacy measurements, operational date and reporting date agreed
with the revised extraction. This targeted inspection is not a random historical
accuracy assessment or a final approval of every field in those reports.

| Original URL suffix | SHA-256 | Operational date | Reporting date |
| --- | --- | --- | --- |
| 7390page1.pdf | d137b0ba773bbb9b9c37d71607f608166cad0d8cff9c9402d232ba9f2953987d | 2024-01-01 | 2024-01-02 |
| 7396page1.pdf | 2c8d54b6ed4d1e490c7b1ec427aaf728acdff117c051ff251478bdfe12da0ed7 | 2024-01-04 | 2024-01-05 |

Official base: `https://misc.bpdb.gov.bd/storage/daily_archive/`.

Verified values (MW except energy, which is million kWh):

| Operational date | Day peak generation | Evening peak generation | Evening peak demand | Maximum generation | Energy generated |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2024-01-01 | 9084.0 | 9944.0 | 9944.0 | 9944.0 | 198.094 |
| 2024-01-04 | 9508.0 | 10107.0 | 10107.0 | 10107.0 | 206.896 |

The right-hand today's estimates and the all-time maximum above the summary are not
used as yesterday's national observations. Fuel-consumed costs remain outside the
supported legacy production-cost definition.

## Deterministic extraction rule

- Compute median finite positive character height over nonblank upright characters.
- If the median is BELOW the library's existing 3-point vertical tolerance, use
  `x_tolerance = 0.4 * median_height` and `y_tolerance = 0.2 * median_height`, retaining
  `layout=True`. These are extraction geometry settings, not statistical imputation rules.
- Otherwise retain the existing default layout extraction. No multiple-extraction search
  chooses whichever numeric result happens to satisfy a validation formula.
- Record method, median height and both tolerances in `source_text_extraction` metadata.
- Do not rewrite, concatenate, estimate or rescale digit strings. Existing strict legacy
  energy-token guards, metric ambiguity checks, dates and units still apply.
- Any unsupported or unresolved source remains held; this rule is not a universal PDF repair.

The online first-page diagnostic uses the same extraction method as the parser. Reports
now record parser-source SHA-256 and pdfplumber runtime version for reproducibility.

## Explicit non-summary rejection

7388page1.pdf (SHA-256 1b6ef38bcb789956ff0a902ad3b9c34b81c824a82ecc366ba172ec4ddf636ddc)
is a single-page station-generation table labelled Page -2 inside the document. Its filename
must not be used to treat it as a national summary. It remains unsupported with safe code
`power_station_table_first_page`; the worker records the code without exposing raw
exception text. No national metrics are fabricated from station-table totals.

## Regression evidence and release checks

- Source-grounded header fixtures cover both repaired PDFs and 7394page1.pdf, a normal-size
  reference for operational 2024-01-03. Dates and all five exact legacy values are asserted.
- An existing modern summary fixture checks all 13 measurements and energy unit handling.
- Geometry tests cover small/normal fonts, missing/nonfinite geometry and unchanged text.
- Existing malformed/split energy-token rejection tests remain active.
- Reparsed eight existing PDF copies (four unique SHA-256s): older legacy and three modern
  operational dates. Extracted values/issues were unchanged, excluding version labels and
  newly added extraction metadata. This is a limited compatibility check, not full-archive validation.
- Local suite: 187 backend tests passed; one optional PostgreSQL integration skipped.
- Hosted workflow runs source-grounded parser/review tests before accessing Drive credentials
  and repeating the bounded source investigation. Cloud acceptance remains a separate gate.

## Hosted evidence artifact change

The diagnostic artifact now includes bounded first-page text and the first FOUR public
original PDF samples in each batch, in addition to JSON findings. All selected originals
remain preserved in Drive; the GitHub artifact is not the complete PDF archive. Credentials
and the collection SQLite journal are excluded. Artifacts retain their existing 14-day lifetime.

## Remaining work

Inspect the new hosted findings; expand supported cases only against preserved real PDFs;
review disagreements and date conflicts; then stage, verify and preview promotion through
versioned ingestion. No current Neon value is changed by deploying this parser, and no
existing frozen research bundle is overwritten. A clean parser result alone does not prove
historical dataset coverage or authorize an imputed/estimated value as source data.
