# Training-source recovery investigation and experiment registration

Date: **8 November 2026, Bangladesh**. Scope: the frozen treatment study's **67 absent canonical dates and 16 review-held dates**, 2020–2023. This is an evidence investigation, not a completed data repair or a forecasting result.

## Completed investigation

Two hosted batches attempted **all 151 URLs in the same retained candidate plan**: 100 then 51. No candidate overlap was permitted. Candidate-plan SHA-256: `f301acfd404b6a2e8b1ef36eca1e4f9b1c653d0ccde1f926ab31ca1c6ed04e58`.

- [Batch 1 — 42456650793](https://github.com/arfinnaim02/BPDB/actions/runs/42456650793)
- [Batch 2 — 42457409357](https://github.com/arfinnaim02/BPDB/actions/runs/42457409357)

Both jobs completed their investigation and Drive evidence-preservation stages, but correctly ended with **failure status** because retrieval/preservation failures are a strict failure gate. These runs must not be described as fully successful retrieval tests. The 15 recorded failures were **RemoteProtocolError** transport/protocol failures, not proof of absent or empty official reports.

| Evidence/outcome | Count | Meaning |
| --- | ---: | --- |
| Known candidate URLs attempted | 151 / 151 | Complete retained candidate plan; not exhaustive proof of archive coverage |
| Original PDF preservation receipts verified | 136 | PDF hashes/sizes match the retained receipt metadata |
| Text-diagnostic checksums verified | 136 | Artifact text matches archived diagnostic bytes |
| Artifact PDFs independently checksum-checked | 30 | Bounded raw-PDF artifact subset; three source pages visually inspected |
| Matching-date sources passing parser and screen | 8 dates | Unapproved candidates, not imported records |
| Other matching-date sources still held/revision review | 44 dates | Includes 13 of the 16 frozen held dates |
| Wrong-date/unparsed candidate follow-up | 30 dates | Does not establish that the correct original is absent |
| No candidate in retained evidence | 1 date | 2020-02-28; not proof no official report exists |
| Canonical writes / approved repairs / models fit | 0 / 0 / 0 | Existing measurements, model and study remain unchanged |

The 8 + 44 matching-date groups represent 52 affected dates: 39 of the 67 absent dates and 13 of the 16 held dates. Counts by date differ from URL-level statuses: 118 held-for-review, 10 parse/unsupported failures, 15 transport failures and 8 parsed review candidates. A valid neighbouring-day report can be held because its operational date does not match the candidate gap.

## Confirmed extraction defects in three visual examples

Rendered original PDF pages show these energy cells. Each source's bytes match the frozen source SHA-256. One visual reading per source was performed in this work session; this is not a claim of an independent second-reader approval or completion of full-record promotion review.

| Operational date | Frozen captured value | Original PDF cell | Source |
| --- | ---: | ---: | --- |
| 2020-01-04 | 1.000000 | 157.6 | [Official PDF](https://misc.bpdb.gov.bd/storage/daily_archive/4472page1.pdf) |
| 2020-02-04 | 17.000000 | 174.1 | [Official PDF](https://misc.bpdb.gov.bd/storage/daily_archive/4534page1.pdf) |
| 2020-06-18 | 2.000000 | 214.6 | [Official PDF](https://misc.bpdb.gov.bd/storage/daily_archive/4800page1.pdf) |

Unit: **million kWh** (source label MKWH). The text extractor interleaves letters from **System Load Factor** with energy digits. For example, the first source's text diagnostic contains `1S5y7s.t6em`, while the visual energy cell reads **157.6**. Earlier extraction captured only the numeric prefix; the current guarded parser refuses the corrupted token instead of silently keeping the prefix.

These are **original-source recovery leads**, not values inferred from a neighbouring day, a peak-to-energy formula or a model. The peak screen only prioritizes review; it is not used to calculate a replacement. No current parser rule or official value was changed in this delivery. Do not clear all held records based on these three examples.

The exact byte identities, visual readings and non-approval status are retained in [TRAINING_SOURCE_VISUAL_CHECKS.json](TRAINING_SOURCE_VISUAL_CHECKS.json).

## Eight absent-date candidates passing existing parser and screen

Operational dates come from the PDF's parsed summary, not archive hints. These candidates pass existing extraction/validation and the generation/energy screen; independent original-page review and a safe staging preview are still required.

| Operational date | Parsed energy (million kWh) | Official source |
| --- | ---: | --- |
| 2023-07-16 | 303.5 | [PDF](https://misc.bpdb.gov.bd/storage/daily_archive/7052page1.pdf) |
| 2023-11-12 | 232.880 | [PDF](https://misc.bpdb.gov.bd/storage/daily_archive/7290page1.pdf) |
| 2023-12-02 | 202.247 | [PDF](https://misc.bpdb.gov.bd/storage/daily_archive/7330page1.pdf) |
| 2023-12-06 | 215.007 | [PDF](https://misc.bpdb.gov.bd/storage/daily_archive/7338page1.pdf) |
| 2023-12-07 | 208.070 | [PDF](https://misc.bpdb.gov.bd/storage/daily_archive/7340page1.pdf) |
| 2023-12-16 | 168.897 | [PDF](https://misc.bpdb.gov.bd/storage/daily_archive/7358page1.pdf) |
| 2023-12-18 | 202.409 | [PDF](https://misc.bpdb.gov.bd/storage/daily_archive/7362page1.pdf) |
| 2023-12-27 | 208.632 | [PDF](https://misc.bpdb.gov.bd/storage/daily_archive/7380page1.pdf) |

All eight are still absent in the investigated canonical date window. They were not automatically promoted. Their evidence includes parsed dates, retained PDF hashes, source URLs and validation flags in [the per-date assessment](TRAINING_SOURCE_RECOVERY_ASSESSMENT.json).

## What remains unresolved

- Three held dates have no matching parsed source in these attempts: **2020-07-02, 2020-07-31, 2020-09-02**. Do not infer their values from the three examples above.
- Retry the **15 transport failures** using a bounded official-source request strategy; preserve new attempt outcomes. Failure does not imply PDF absence.
- Investigate the one unlocated retained-evidence date separately. The original historical archive on the home machine may hold additional evidence not backed up to Drive.
- Handle unsupported first-page layouts and corrupted energy tokens using source-specific fixtures and strict date/unit/number guards, not broad character deletion or unchecked digit concatenation.
- Retain all failed, conflicting and negative findings. No candidate is an approved modelling label until the source correction is independently reviewed and versioned.

## Registered chronological experiment

The design is fixed in [TREATMENT_IMPACT_PROTOCOL.md](TREATMENT_IMPACT_PROTOCOL.md) and [its machine-readable specification](TREATMENT_IMPACT_PROTOCOL.json).

- Registration commit: [5a0fc0d0](https://github.com/arfinnaim02/BPDB/commit/5a0fc0d0395efaa0a69f1097738a380d284d49a2).
- Protocol SHA-256: `7ab121397b48acc61261f4276b9ad5c051157c5d5d100dc03483c5977fac7469`.
- Historical folds: target years 2021, 2022 and 2023; each fit uses only earlier complete-original rows through two days before the first target. One fixed OLS coefficient set per fold is shared across all inference policies.
- Compare observed-only, previous-week-original and recent-original inputs. Primary contrast uses affected shared target dates, with original-only scoring labels, coverage and abstention reporting.
- These historical years are retrospective diagnostics; policy selection already saw 2020–2023 masks. 2024 is previously exposed secondary evidence. **2025 remains excluded.**
- Reserve a separate 30-day prospective shadow window, **10 November–9 December 2026**, using unchanged saved model coefficients and before-issue evidence. This is a planned reservation, not a running worker. If first issue readiness is missed, dates must be amended before a replacement period starts.
- No experiment, production retraining, shadow schedule or target imputation was started. Results remain null.

## Tests and reproducibility

Local full backend suite: **330 passed, 1 skipped**. Frontend: **46 passed**; TypeScript and production build passed. Authenticated production-build HTTP checks confirmed the registered-design section and links; no-session access did not expose the study identity. Existing Starlette/httpx deprecation warning remains.

New checks cover frozen-date scoping, refusing unrelated sources, present-date versus verified-value distinctions, changed source hashes, zero approvals, corrupt report/PDF receipts, stable-plan/disjoint batch merging, chronological embargo, excluded 2025, forbidden target filling/execution, reserved future dates and null results. Synthetic tests are not substitutes for the real source findings.

Verify/merge downloaded artifact folders:

```text
python -m research.summarize_training_sources --folder first_batch --additional-folder second_batch --output recovery_assessment.json
python -m research.treatment_impact_protocol
```

The assessor refuses changed worklists/plans, mismatched retained-file receipts, overlapping batches and unexpected import/approval activity. Original PDFs and reports remain preserved by content-addressed Drive blobs. GitHub diagnostic artifacts have 14-day retention; the report hashes are retained in the assessment for later retrieval from the operator's Drive archive.

## Next concrete execution

1. Build and test a narrowly guarded source-recovery parser preview using the visually checked originals; independently inspect the eight full-record candidates and retry the transport failures.
2. Review staging/promotion previews, then create a new versioned snapshot for approved originals. Keep the published frozen study and primary diagnostic input unchanged; record any repaired-snapshot sensitivity separately.
3. Implement the registered diagnostic/shadow experiment with date-level provenance and original-only targets. Do not retrain or switch the live model on the strength of reconstruction error alone.

Current conclusion: recoverable original information exists. The next data action is source recovery with explicit provenance, not blanket imputation.
