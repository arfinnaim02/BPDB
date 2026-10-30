# Existing project audit — 2026-10-25

## Material actually inspected

The two locally attached files were instructions only. The previously shared Drive folder
was then read successfully. Originals were not changed. This is a targeted source audit,
not a claim that every notebook or saved model has been reproduced.

| Source | Inspected content | Decision |
|---|---|---|
| [bpdp.zip](https://drive.google.com/file/d/1R4xtXFPSO7ofmrVthjem-ES9cEsXnTyv/view) | parser.py, run.py, archive contents | Retain parsing patterns as candidates; replace collector persistence/deduplication |
| [Existing thesis project ZIP](https://drive.google.com/file/d/1JUNuiGvd0zufyyChkp7Ni34ftusz7vRx/view) | Core aggregation, features, walk-forward code, parser tests, methodology, validation report, archive inventory | Adapt after chronological/calendar/availability tests; retain original project |
| [bpdb_daily.csv](https://drive.google.com/file/d/1EaVOoNJq_DO7gGtvPzVcrYOeMeQEGHcJ/view) | All rows and headers for structural audit | Preserve as legacy evidence; do not ingest as validated canonical data yet |
| [06 monthly notebook](https://drive.google.com/file/d/1fuU2SeLVe6R4osNMVA97tZNUnJu48m12/view) | Downloaded, code extracted for later audit | Experiment not rerun; no performance claims adopted |
| [05 prediction validation notebook](https://drive.google.com/file/d/1PD7f_3eEDwp8hsvwn1xUXIHzLHRiTaG8/view) | Source including missing-value reconstruction branch | Reconstruction policy needs source-specific evidence |
| Other EDA / feature / baseline / cost notebooks | Folder inventory only | Full review still pending |

## CSV observations (local structural checks, not original-PDF verification)

- 556 rows, 142 columns; dates parse with `%m/%d/%Y` in this CSV.
- Dates: 2025-01-01 through 2026-07-10, no duplicate dates or internal calendar gaps.
- Extraction labels: 525 `ok`, 31 `partial`; review labels: 548 `no`, 8 `yes`.
- 22 blank `production_cost_per_kwh_tk` cells.
- 22 rows have `energy_generated_mkwh` > 10,000; observed range 171.70542–232175.79.
  `total_generation_mkwh` also has 22 values > 10,000. This is a scale-review flag,
  not permission to divide those rows by 1,000. Verify printed units in originals.
- Source URL and filename columns are present, but original PDF checksums/bytes are absent.
- CSV SHA-256: `006b21b743e52b9fc4a940a49c0d0daaa3c407b5e4e55d3396f5dd6771aad5db`.
- Neither ZIP contains original PDF files.

## Reusable components and required changes

1. **Numeric preservation:** legacy `_f` strips commas without a float round-trip.
   Adapted now as `backend/ingestion/numbers.py` with Decimal, strict grouping validation,
   explicit missing tokens and tests. It does not apply source unit conversions.
2. **Parser patterns:** modern/legacy headings, zone aliases and fuel labels are useful
   starting points. PDF glyph de-doubling and positional column matching need actual
   PDF fixtures. Original cost values must be retained even when a validator flags them.
3. **Date semantics:** legacy parsing falls back from yesterday's operational date to
   a reporting/issue date; the collector can further fall back to filename date.
   Those fallbacks must become explicit ambiguity flags rather than confirmed report dates.
4. **Mixed temporal grains:** the legacy zone table comments distinguish yesterday's
   shedding, today's demand and today's shedding. They cannot automatically share the
   national operational date or be treated as all-realized next-day targets.
5. **Collector:** existing run.py intentionally fetches PDFs into memory and discards bytes;
   overwrites one CSV; resolves competing dates by dropping losing rows; scans with 8 workers.
   Replace those operations with persistent original storage, version history, transactional
   canonical promotion, bounded rate-aware collection and a database-derived master export.
6. **Validation:** legacy sums use `value or 0`. Incomplete fuel/zone components must produce
   an unknown reconciliation outcome, not a successful comparison based on missing-as-zero.
7. **Monthly aggregation:** the existing `_sum_complete` requires every daily value and its
   count to match the month. Preserve that principle after source and uniqueness validation.
8. **Calendar targeting:** existing feature engineering filters incomplete months *before*
   `shift(-1)` and lag generation. If an interior month is missing/ineligible, the next row
   can belong to a different calendar month while still being labeled t+1. Reindex the full
   monthly calendar and join exact next-month targets before filtering supervised rows.
9. **Evaluation:** expanding windows and training-fold feature filtering are useful patterns.
   Add explicit source availability cutoffs, calendar continuity tests, comparable test periods,
   and independent reproduction before adopting any saved metric or chosen model.
10. **Unit reconstruction:** the prediction notebook divides energy >10,000 by 1,000 when
    reconstructing cost per kWh. That heuristic must not alter original observations or
    become a verified conversion without original-document unit evidence.

No legacy ML code or model artifact was executed or loaded. Existing saved forecasts,
validation reports and model comparisons are historical claims requiring reproduction,
not verified results of the new platform.
