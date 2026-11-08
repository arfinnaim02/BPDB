# Dataset-goal adoption — acceptance report

Completed 8 November 2026, Bangladesh. Goal: **a trustworthy dataset for each research question, using verified comparable variables and reporting periods**.

Implementation commit: [5eb43f11](https://github.com/arfinnaim02/BPDB/commit/5eb43f110b672cedfab58a52acbb8e6ecf5324a3).
Live read-only acceptance: [GitHub Actions 42469281560](https://github.com/arfinnaim02/BPDB/actions/runs/42469281560), successful. Capture time: 2026-11-08T15:57:20.133291+06:00.

## User-visible result

The protected **/quality/strategy** page shows two planning profiles, observed metric bounds, full-history versus modern-window calendar coverage, and research-question mappings. The sidebar and preparation page link to it.

- Long-history core: five metrics supported by both parser families, within actual canonical bounds.
- Modern reporting: all 13 supported national variables, with a **proposed** 1 January 2025 boundary.
- Both profiles require definition/source/issue-time and joint-eligibility checks. No automatic training-readiness certificate is issued.
- Modern-only variables cannot use experimental previous-week filling. The form switches those selections to observed-only, and the backend returns 422 for attempts to bypass the guard.
- Earlier observed values remain available; observed-only previews before 2025 are permitted.

The current registered energy experiment and all frozen artifacts remain unchanged. A separate [pre-execution addendum](TREATMENT_IMPACT_AMENDMENT_01.md) documents the dataset acceptance gate without rewriting the original protocol or its hash.

## Actual live coverage finding

Known canonical bounds in this acceptance snapshot: **2019-10-19–2026-11-04** (2,574 calendar days). Each core variable has **2,390 non-null dates** over that full history. Richer fields first occur in the current database on **2025-01-23**.

For the proposed modern window **2025-01-01–2026-11-04**, every listed field has **629 non-null dates out of 673 calendar days: 93.46% availability**. These counts are not 629 approved training rows. The page does not infer joint eligible dates, review clearance or publication-time validity from marginal counts.

| Field | First recorded value | Full-history non-null dates | Modern-window non-null / calendar | Modern coverage |
| --- | --- | ---: | ---: | ---: |
| Day Peak Generation (MW) | 2019-10-19 | 2390 | 629 / 673 | 93.46% |
| Evening Peak Generation (MW) | 2019-10-19 | 2390 | 629 / 673 | 93.46% |
| Day Peak Demand (MW) | 2025-01-23 | 629 | 629 / 673 | 93.46% |
| Evening Peak Demand (MW) | 2019-10-19 | 2390 | 629 / 673 | 93.46% |
| Minimum Generation (MW) | 2025-01-23 | 629 | 629 / 673 | 93.46% |
| Maximum Generation (MW) | 2019-10-19 | 2390 | 629 / 673 | 93.46% |
| Energy Generated (million kWh) | 2019-10-19 | 2390 | 629 / 673 | 93.46% |
| Energy Demand (million kWh) | 2025-01-23 | 629 | 629 / 673 | 93.46% |
| Energy Unserved (million kWh) | 2025-01-23 | 629 | 629 / 673 | 93.46% |
| Maximum Temperature (deg C) | 2025-01-23 | 629 | 629 / 673 | 93.46% |
| Gas Supplied (MMCFD) | 2025-01-23 | 629 | 629 / 673 | 93.46% |
| Production Cost per kWh (BDT/kWh) | 2025-01-23 | 629 | 629 / 673 | 93.46% |
| Total Production Cost (BDT) | 2025-01-23 | 629 | 629 / 673 | 93.46% |

Important: the first recorded date in Neon is **not proof of the official reporting-format transition or first publication date**. Missing canonical data and parser limitations remain separate questions. The 2025 proposal is therefore explicitly labelled, not promoted to a universal completeness claim.

Coverage assessment ID: `20328a87e042dc9fc6fd8b232f3e54d5d187c3c6b648ce7640027ec273975b7c`. This hashes coverage/plan content, not measurement values, and is not a frozen training-snapshot ID.

## Verification

| Check | Result |
| --- | --- |
| Full local backend suite | 343 passed, 1 skipped |
| Full frontend suite | 48 passed |
| Ruff | Passed |
| Frontend TypeScript | Passed |
| Next production build | Passed |
| Hosted PostgreSQL session | Confirmed transaction_read_only = on |
| Live catalog | 13 supported variables; 5 long-history-core candidates |
| Source-layout filling guard | All 8 modern-only fields rejected for experimental filling |
| Earlier originals and numerical zero | Preserved by observed-only planning/preparation |
| Empty history | No fabricated observed bounds or model readiness |
| Model eligibility from marginal counts | Explicitly not approved; joint eligible count null |
| Auth/API cache | No-key request 401; authenticated response no-store |
| Frontend HTTP contract | Strategy, captured real coverage, login protection and disabled modern-field treatment passed |
| Frozen input bundle | Original SHA-256 unchanged |
| Registered impact protocol | Original SHA-256 unchanged; addendum separate |
| Database writes / models fitted | 0 / 0 |

The HTTP frontend check used the verified hosted coverage payload as a local backend fixture. Backend logic and PostgreSQL read-only behaviour were independently exercised by unit tests and the real hosted check. This is not a claim of a signed-in production browser test or a completed modelling dataset.

The existing Starlette/httpx deprecation warning and existing skipped integration test remain. Host CI may skip additional optional-learner tests when research dependencies are not installed; the stated full local suite includes those available dependencies.

## Reproduce and next execution

```text
python -m research.check_dataset_profiles
```

The command requires existing DATABASE_URL configuration and refuses a live check outside a PostgreSQL read-only transaction. It saves planning/verification JSON under data/research_dataset_profiles and never prepares a training dataset, fits a model or changes the collection schedule.

Next: complete source-derived recovery previews and explicit repair review, then create question-specific research snapshots with joint eligible-row counts and target-frequency sample sizes. Execute the registered energy diagnostic after its gates pass; register richer-variable/cost/demand studies separately.
