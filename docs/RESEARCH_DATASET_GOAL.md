# Working research dataset goal

Adopted 8 November 2026: **a trustworthy dataset for each research question, using verified comparable variables and reporting periods.**

One rectangular table with estimated values in every year is not the objective. Authoritative observations remain in Neon. Research datasets are versioned, source-linked products for specific targets, definitions, forecast issue times and evaluation designs.

## Two planning profiles

| Profile | Variables and period | Appropriate uses | Required evidence |
| --- | --- | --- | --- |
| Long-history core | Day peak generation, evening peak generation, evening peak demand, maximum generation, energy generated; actual observed bounds | Core generation, energy and supported evening-demand research | Comparable units/definitions, source lineage, original recovery, review eligibility and issue-time checks |
| Modern reporting | Richer supported national Page 1 variables; proposed conservative start 1 January 2025 | Multivariable analysis and supported cost/day-demand research | Actual variable coverage, common eligible dates, target-frequency sample size and source-definition acceptance |

The 2025 boundary is a user-proposed study restriction, **not proof that all later observations are complete or that every earlier field was unpublished**. The live matrix retains each variable's full observed bounds, including modern-variable values before 2025. These earlier originals are not deleted or reclassified as fabricated.

The five core variables match the capabilities shared by the supported legacy and modern parser families. Capability is not a certificate for every original report. The other eight fields require a supported reporting period; absence from an older parser/report layout must not be filled as though it were a short random interruption.

## Missingness decisions

- Absent canonical date: investigate registered sources/journal/archive; it does not prove that no official PDF exists.
- Field outside a supported reporting layout: retain as unreported/unsupported when source evidence establishes that cause; never manufacture a multi-year history.
- Extraction failure: recover a source-derived value using validated parsing and original evidence.
- Numerical/source review hold: exclude the suspect value from donors and model labels until review is resolved.
- Short temporary feature gap: treatment is allowed only under an explicit metric-specific experiment and chronological availability rules.
- Unknown cause: keep it unknown until investigated; do not infer publication status from database absence.

Never impute observed training/scoring target labels. Experimental prepared values are input candidates; original-target eligibility remains separately recorded. Monthly energy/total-cost targets require complete original, eligible daily observations for the full month. Cost per kWh is a different target from total cost and must not be summed as money.

## Modelling and evaluation

Select variables, definitions, reporting window, issue cutoff and target frequency before fitting. Count **joint eligible rows**, not only per-column observations. Retain dense calendar rows, original values and held/missing flags; lags must not skip missing dates.

Fit scalers, selection and any experimental input treatment within each chronological training fold. Record unavailable predictions and coverage. Restrict labels to accepted originals and disclose publication-time assumptions.

Longer verified core history and richer recent data answer different questions; neither is automatically superior. A short recent period may offer too few complete monthly cost targets or seasonal cycles for a complex model. Zonal load-shedding research requires separate validated zonal data; national energy-unserved measurements are not a substitute.

Previously exposed 2025 observations cannot become a newly untouched final test. Preserve the registered energy-treatment design and past results. New datasets, repairs or design changes require versioned manifests and prospective amendments where applicable.

## Implemented changes

- Protected **/quality/strategy** page and **/api/v1/dataset/research-profiles** endpoint.
- Live full-history/modern calendar coverage for all 13 supported national variables.
- Explicit proposed-boundary labels; joint eligible-row count stays null until actually assessed.
- Question-to-profile mapping and source/definition/sample-size gates; no automatic training readiness.
- Modern-layout-only fields cannot use the experimental previous-week preparation policy. Both frontend controls and backend validation enforce this. Observed-only previews remain available, including earlier real observations.
- Existing eligible core snapshot identity calculations, frozen files, official values, model coefficients and schedules remain unchanged.
- A read-only hosted acceptance workflow records actual live coverage and confirms PostgreSQL read-only mode. It does not create a training dataset or fit a model.

See [TREATMENT_IMPACT_AMENDMENT_01.md](TREATMENT_IMPACT_AMENDMENT_01.md) for the additional pre-execution dataset gate.

## Next execution

Finish source-derived recovery previews, review candidates and version any approved repairs. Then build question-specific source-linked research snapshots with explicit joint eligibility, target-frequency counts and chronological splits. Execute the registered energy diagnostic only after its source/definition gates pass; register other targets and richer-variable experiments separately.
