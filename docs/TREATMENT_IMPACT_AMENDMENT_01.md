# Treatment-impact registration — dataset-goal addendum 01

Date: 8 November 2026, Bangladesh. Status: **before experiment execution; no new fitting or policy adoption**.

Base registration: commit `5a0fc0d0395efaa0a69f1097738a380d284d49a2`.
Base protocol SHA-256: `7ab121397b48acc61261f4276b9ad5c051157c5d5d100dc03483c5977fac7469`.

## Added pre-execution gate

Apply the [working dataset goal](RESEARCH_DATASET_GOAL.md): a trustworthy dataset for each research question, with verified comparable variables and reporting periods.

The registered energy experiment belongs to the **long-history core** profile. Its target remains energy_generated and its nine features remain past energy/calendar features. The absence of modern gas, temperature or cost fields does not justify discarding otherwise accepted historical energy records or inventing those covariates.

Before execution, document source/definition/units acceptance for the selected energy period, retained review exclusions, original-only target labels, issue-time assumptions and common eligible rows. Coverage-plan counts alone cannot satisfy this gate. If repairs are approved, preserve the original frozen primary analysis and identify a repaired-snapshot sensitivity separately.

The **modern reporting** profile has a proposed 1 January 2025 start for richer variables. It is not a certification of completeness, a replacement of the registered energy input, or a new untouched test set. Any richer-variable/cost/demand experiment needs its own selected common window, target-frequency sample-size assessment and registration.

## Unchanged design

The original machine-readable protocol and its hash are preserved. No folds, model family, existing coefficients, scores, support thresholds, 2025 exclusion or reserved future-period rules are changed. No old experimental asset is regenerated. No shadow worker or schedule is started.

If readiness misses the original prospective first issue, a separate dated period amendment is required before a replacement period begins. This addendum does not authorize retrospective forecast reconstruction or silently move the reserved period.

The addendum is published as a separate timestamped Git commit. It adds an explicit dataset acceptance gate; it does not report a new model result.
