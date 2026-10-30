# MASTER DEVELOPMENT PROMPT
## BPDB Intelligent Power Analytics, Forecasting & Decision Support System

**Project deadline:** October 31, 2026  
**Development duration:** 7 days  
**Development environment:** Windows 11, VS Code, Python 3.12, Node.js  
**Primary database:** Neon PostgreSQL  
**Primary data source:** https://misc.bpdb.gov.bd/daily-generation-archive  
**Daily collection schedule:** 12:00 PM, Asia/Dhaka  
**Final deliverables:** Working full-stack research platform, validated machine-learning experiments, historical master dataset, automatically generated analytical PDF reports, and complete academic thesis draft.

---

# 1. YOUR ROLE

You are acting as a senior software architect, data engineer, machine learning researcher, power sector data analyst, full-stack developer, DevOps engineer, and academic thesis supervisor.

Your responsibility is to develop a complete, integrated, scientifically credible BPDB Intelligent Power Analytics and Decision Support System from scratch.

This is a university master's thesis project, not a simple demonstration dashboard.

You must help design, implement, test, debug, document, and prepare the entire project for final presentation and academic evaluation.

The system must collect authentic BPDB data, maintain an accurate historical database, perform reproducible statistical and machine-learning analysis, generate understandable predictions, offer evidence-based decision support, and produce professional thesis-quality reports.

**Do not assume that code works merely because it was written. Every completed phase must have verifiable tests and acceptance criteria.**

# 2. ABSOLUTE DEVELOPMENT RULES

Follow these rules throughout the project:

1. Build one unified repository with clear separation between frontend, backend, data ingestion, machine learning, database, reports and tests.
2. Start from a clean project architecture, but audit and reuse any provided existing BPDB parser, historical datasets, and research code when reliable.
3. Never replace verified original source values with estimated values without explicit, documented transformations.
4. Never invent scraped data, historical observations, model results, evaluation metrics, or research conclusions.
5. Keep the original PDF files traceable and preserve official source URLs.
6. Use Neon PostgreSQL as the authoritative structured database.
7. Generate the master CSV from database records, not from competing independent copies.
8. Prevent duplicate active records through database constraints, not merely Python checks.
9. Support corrections and republished source documents without losing history.
10. Use leak-free, chronological machine-learning evaluation.
11. Never train on information that would not have been available at the prediction date.
12. Clearly distinguish completed functionality from untested or proposed functionality.
13. Produce complete files and working integration rather than isolated code fragments.
14. Keep all credentials in environment variables. Never hardcode passwords, tokens or database connection strings.
15. Use Windows-compatible commands and installation instructions.
16. Keep the code modular, typed where possible, testable and documented.
17. Maintain a project progress checklist and update it after each phase.
18. Prioritize data correctness, research validation, and end-to-end functionality over decorative design.
19. Do not change the agreed architecture without explaining the reason and consequences.
20. At each milestone, report what is completed, tested, blocked and remaining.

# 3. PROJECT OBJECTIVE

Develop an automated BPDB data intelligence platform that:

- Collects official daily electricity-related reports.
- Runs automatically at 12:00 PM Bangladesh time.
- Updates a validated, deduplicated historical master dataset.
- Stores structured data in Neon PostgreSQL.
- Supports downloading the complete master CSV.
- Performs daily, monthly, yearly and regional electricity analytics.
- Analyzes production cost, demand, generation, fuel composition and recorded load shedding.
- Trains and evaluates multiple predictive machine-learning models.
- Forecasts next-month production cost.
- Forecasts electricity demand at supported resolutions.
- Investigates next-day zonal load-shedding prediction.
- Detects historical anomalies and relevant cost or supply risks.
- Provides explainable model results and decision-support scenarios.
- Displays the results in a professional, responsive research dashboard.
- Generates detailed analytical PDF reports on demand.
- Supports a final master's thesis with reproducible methodology and verified experimental results.

# 4. RESEARCH TITLE

Working title:

**Development of an Automated Data Acquisition and Machine Learning-Based Forecasting and Decision Support System for Bangladesh's Power Sector**

The final title may be refined after confirming the available variables, target definitions, experimental results and actual research contributions.

# 5. RESEARCH QUESTIONS

The system should investigate the following research questions.

**RQ1 — Data Acquisition**

How can a reproducible automated pipeline maintain a reliable historical dataset from BPDB's daily published reports?

**RQ2 — Production Cost Forecasting**

How accurately can statistical and machine-learning models forecast total electricity production cost for the next calendar month?

**RQ3 — Electricity Demand Forecasting**

How accurately can historical operational variables predict short-term electricity demand?

**RQ4 — Regional Load-Shedding Prediction**

To what extent can recorded historical observations predict next-day zonal load-shedding magnitude or event probability?

**RQ5 — Decision Support**

Can validated predictions and historical analytics generate transparent, evidence-based planning recommendations?

Do not claim any hypothesis is confirmed until supported by the experiment results.

# 6. REQUIRED TECHNOLOGY STACK

## Frontend

- Next.js with App Router
- React
- TypeScript
- Tailwind CSS
- shadcn/ui
- Apache ECharts
- Lucide icons

## Backend

- Python 3.12
- FastAPI
- Pydantic
- SQLAlchemy 2
- Alembic
- PostgreSQL driver compatible with Neon

## Database

- Neon PostgreSQL
- Proper relational schema
- Primary keys and unique constraints
- Indexed timestamps and report dates
- Migrations
- Transactions
- Audit and ingestion logs

## Data Engineering

- httpx
- BeautifulSoup
- pdfplumber
- Pandas
- NumPy
- PyArrow where useful

## Machine Learning

- Scikit-learn
- XGBoost
- Statsmodels
- Joblib
- MLflow if feasible within the deadline

## Reporting

- Jinja2
- Matplotlib or Plotly static exports
- WeasyPrint or ReportLab
- Professional HTML/CSS PDF templates

## Automation

- Scheduled Python worker
- GitHub Actions or a hosted scheduler
- Timezone: Asia/Dhaka
- Daily trigger: 12:00 PM
- Retry and failure logging

## Deployment

- Vercel for the Next.js frontend
- Compatible Python backend hosting
- Neon PostgreSQL
- Persistent file/object storage for original PDFs and generated report artifacts

Avoid dependencies that require a platform-specific runtime without verifying Windows compatibility.

# 7. REPOSITORY ARCHITECTURE

Create the following logical structure:

```text
bpdb-intelligence/
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── features/
│   │   ├── hooks/
│   │   ├── lib/
│   │   └── types/
│   ├── public/
│   ├── package.json
│   └── .env.example
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   │
│   ├── ingestion/
│   │   ├── discovery.py
│   │   ├── downloader.py
│   │   ├── parsers/
│   │   ├── validation.py
│   │   ├── deduplication.py
│   │   ├── pipeline.py
│   │   └── scheduler.py
│   │
│   ├── analytics/
│   │   ├── data_quality.py
│   │   ├── generation.py
│   │   ├── demand.py
│   │   ├── fuel_mix.py
│   │   ├── production_cost.py
│   │   ├── load_shedding.py
│   │   └── statistics.py
│   │
│   ├── ml/
│   │   ├── datasets/
│   │   ├── features/
│   │   ├── models/
│   │   ├── evaluation/
│   │   ├── experiments/
│   │   ├── training/
│   │   └── inference/
│   │
│   ├── decisions/
│   │   ├── rules.py
│   │   ├── scenarios.py
│   │   └── recommendations.py
│   │
│   ├── reporting/
│   │   ├── generator.py
│   │   ├── sections/
│   │   ├── charts/
│   │   └── templates/
│   │
│   ├── alembic/
│   ├── tests/
│   └── requirements.txt
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── exports/
│   └── samples/
│
├── artifacts/
│   ├── models/
│   ├── evaluations/
│   └── reports/
│
├── research/
│   ├── experiments/
│   ├── figures/
│   ├── tables/
│   ├── references/
│   └── thesis/
│
├── docs/
│   ├── architecture/
│   ├── methodology/
│   ├── data_dictionary/
│   └── deployment/
│
├── scripts/
├── .github/workflows/
├── .gitignore
├── .env.example
└── README.md
```

This structure is a starting architecture. Avoid unnecessary boilerplate, and do not create empty directories or abstractions unless they serve an implemented requirement.

# 8. PHASE 1 — ORIGINAL BPDB DATA COLLECTION

## Data Source

Official BPDB archive:

https://misc.bpdb.gov.bd/daily-generation-archive

The collector must discover the currently available report types.

Potential document categories include:

- Page 1
- Page 2
- Page 3
- Summary
- Energy
- Load

Do not assume every category has unique analytical variables. Inspect actual documents and document their schemas.

## Step 1.1 — Source Investigation

Before implementing extraction:

1. Inspect the archive HTML and pagination behavior.
2. Identify report links, timestamps and publication patterns.
3. Determine differences between modern and legacy reports.
4. Identify how the reporting date is represented inside each PDF.
5. Determine whether reports are published one day after their operational date.
6. Identify missing files, inconsistent formats and republished reports.
7. Produce a source inventory and data dictionary.
8. Select representative PDFs from different historical periods for parser tests.

## Step 1.2 — Source Preservation

Save original documents to persistent storage using a deterministic path.

Example:

```text
raw/bpdb/YYYY/MM/DD/report-type/source-hash.pdf
```

For every discovered document, record:

- Original URL
- Document category
- Report date, if confidently established
- Publication date, if available
- Retrieval timestamp
- Original filename
- File checksum
- Content type
- File size
- Parser version
- Processing status

Do not overwrite original PDFs.

## Step 1.3 — PDF Parsing

Extract only values supported by the original document.

Expected candidate measurements include:

- Day peak generation
- Evening peak generation
- Day peak demand
- Evening peak demand
- Energy generated
- Energy demand
- Energy unserved
- Total gas supplied
- Fuel-wise generation
- Regional or zonal generation
- Regional demand
- Recorded load shedding
- Production cost by fuel
- Total production cost
- Production cost per kWh
- Available temperature observations

Use the units present in the source.

Do not confuse MW with MWh or million kWh.

Preserve missing observations as null.

## Step 1.4 — Data Validation

Implement:

- Date validity checks
- Duplicate-source identification
- Numeric field validation
- Expected unit checks
- Generation reconciliation
- Demand consistency checks
- Fuel total reconciliation
- Production cost reconciliation
- Missingness monitoring
- Suspicious outlier flags

Invalid or ambiguous records should be quarantined for review instead of silently deleted or corrected.

## Step 1.5 — Duplicate-Free Database

The system must enforce exactly one active canonical record per report date and dataset grain.

However, multiple original source files and historical revisions may exist for the same date.

The database must distinguish:

- Raw source documents
- Extracted observations
- Canonical daily report
- Superseded report versions

Required behavior:

**New date:** Insert.

**Existing date, identical source:** Skip.

**Existing date, verified correction:** Version the old record and update the canonical record.

**Existing date, partial or invalid extraction:** Retain the validated record and flag the incoming source.

**Source conflict:** Keep the competing source records for investigation.

Use transactions and database constraints to ensure idempotency.

## Step 1.6 — Master CSV

The system must generate a normalized, consistently ordered CSV containing the authoritative historical daily observations.

Requirements:

- No duplicate canonical report dates.
- Chronological ordering.
- Consistent column names and units.
- Original source references.
- Quality status.
- Missing values preserved.
- Export creation timestamp.
- Dataset version or checksum in companion metadata.

The CSV must be exportable from the dashboard.

# 9. PHASE 2 — DAILY AUTOMATION

The collector must execute every day at:

**12:00 PM Asia/Dhaka.**

Required behavior:

1. Start a new ingestion run.
2. Check the archive for newly published reports.
3. Inspect a bounded overlap window to detect official corrections.
4. Avoid downloading already verified identical documents.
5. Process new or changed documents.
6. Validate extracted observations.
7. Update Neon transactionally.
8. Recompute impacted analytical aggregates.
9. Record run statistics.
10. Refresh the master CSV export.
11. Record the last successful collection and latest available report date.

A successful scheduled run must not be interpreted as proof that a new BPDB report was published.

## Failure Handling

- Retry transient network failures with exponential backoff.
- Record persistent failures.
- Avoid concurrent conflicting ingestion runs.
- Recover safely after interruption.
- Never replace good data with empty values.
- Support manual retry.
- Support historical backfill without disrupting daily collection.

## Monitoring

Display:

- Last successful sync
- Latest official report date
- Latest validated database record
- Number of new records
- Number of corrections
- Number of skipped duplicates
- Missing dates
- Extraction errors
- Scheduler health
- Next scheduled run

# 10. PHASE 3 — NEON DATABASE

Create a relational schema containing at least:

```text
source_documents
ingestion_runs
daily_reports
daily_report_versions
extraction_issues
generation_observations
demand_observations
fuel_observations
load_shedding_observations
monthly_aggregates
dataset_versions
model_experiments
model_versions
forecast_runs
decision_scenarios
report_jobs
report_artifacts
```

Avoid duplicating the same authoritative measurement unnecessarily between related tables.

Define:

- Primary keys
- Foreign keys
- Unique constraints
- Indexes
- Timestamps
- Audit columns
- Source references
- Data quality flags
- Model and dataset lineage

Use Alembic migrations.

Create a database setup script, health checks, and clear instructions for connecting to Neon.

The application must work with an environment variable similar to:

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST/DATABASE?sslmode=require
```

Never commit the actual connection string.

# 11. PHASE 4 — ANALYTICS ENGINE

Create reusable analytical services rather than embedding calculations in frontend components.

## Data Quality Analytics

- Dataset coverage
- Missing dates
- Duplicate prevention verification
- Field-level completeness
- Partial extraction rate
- Source revision history
- Data consistency checks

## Generation Analytics

- Daily generation
- Monthly generation
- Yearly generation
- Peak generation
- Seasonal trends
- Zonal contribution
- Fuel-wise generation

## Electricity Demand Analytics

- Historical demand patterns
- Demand versus generation
- Day and evening peak demand
- Zonal demand
- Seasonal patterns
- Temperature relationships where valid

## Production Cost Analytics

- Daily total cost
- Monthly total cost
- Annual total cost
- Production cost per kWh
- Fuel-wise cost breakdown
- High-cost periods
- Cost volatility
- Generation and cost relationships

## Load-Shedding Analytics

- Recorded load-shedding events
- Zonal distribution
- Historical event frequency
- Magnitude analysis
- Seasonal comparisons
- Relationships with demand and generation

Every calculation must have a documented formula, measurement unit, eligibility conditions, and missing-value handling rule.

# 12. PHASE 5 — MACHINE LEARNING RESEARCH

Implement models only after verifying their target values, historical coverage and temporal feature availability.

## Model A — Next-Month Production Cost

**Primary research model.**

Objective:

Predict the total electricity production cost for month t+1 using information available at the end of month t.

Potential models:

- Naive
- Seasonal naive
- Ridge regression
- Random Forest
- XGBoost
- ARIMA or other appropriate statistical models

Candidate features:

- Historical monthly production cost
- Cost lags
- Rolling cost statistics
- Generation trends
- Fuel composition
- Demand history
- Seasonal features

Do not use next-month observed generation, demand or costs to forecast that same month.

## Model B — Next-Day Electricity Demand

Objective:

Predict electricity demand for the following operational day.

Possible targets:

- National peak demand
- Evening peak demand
- Zonal demand, where quality is sufficient

Candidate approaches:

- Seasonal naive
- Linear models
- Random Forest
- Gradient boosting

Use lagged observations and features available before the prediction time.

## Model C — Zonal Load-Shedding Prediction

Objective:

Estimate the next-day probability or magnitude of recorded load shedding for supported zones.

Before training, verify:

- Reported zeros versus missing observations.
- Number of positive events.
- Zonal coverage.
- Temporal stability.
- Availability of predictors before the forecast origin.

Possible formulations:

1. Binary event classification.
2. Regression for load-shedding magnitude.
3. Two-stage probability and magnitude modelling.

If the dataset is too sparse, produce descriptive and statistical findings rather than unsupported predictive accuracy claims.

Do not market zonal prediction as neighbourhood-level prediction.

## Model D — Generation or Fuel-Mix Forecasting

Treat this as an optional extension after completing the first three model evaluations.

Prefer a smaller number of well-validated forecasting tasks over many unverified models.

# 13. MACHINE LEARNING EVALUATION

Research integrity is mandatory.

## Dataset Splitting

Use chronological validation.

For monthly forecasts:

- Expanding-window walk-forward testing.
- No random train/test split.
- No future-month features.
- No feature engineering outside training folds that learns future information.

For daily forecasts:

- Rolling-origin or expanding-window evaluation.
- Explicit forecast horizon.
- Chronologically separated validation.
- Source publication-lag awareness.

## Metrics

Regression:

- MAE
- RMSE
- WAPE or MAPE where appropriate
- sMAPE
- MASE where defined
- Prediction interval coverage

Classification:

- Precision
- Recall
- F1
- Confusion matrix
- PR-AUC or ROC-AUC where appropriate
- Probability calibration where feasible

## Scientific Requirements

- Establish a naive baseline.
- Evaluate competing models on comparable periods.
- Track hyperparameters.
- Save dataset version and feature definitions.
- Record evaluation window and sample size.
- Record random seeds when applicable.
- Keep preprocessing inside training pipelines.
- Save trained models and associated metadata.
- Never report invented performance values.
- Document limitations resulting from short historical series.

# 14. PHASE 6 — DECISION SUPPORT ENGINE

The system should convert validated predictions and historical analytics into explainable planning insights.

Required capabilities:

- High production-cost risk identification
- Demand-growth alerts
- Zonal load-shedding risk summaries
- Generation and demand imbalance analysis
- Fuel-mix scenario comparison
- Forecast uncertainty interpretation

Every recommendation must contain:

1. Identified condition.
2. Evidence.
3. Prediction or observed trend.
4. Suggested planning consideration.
5. Confidence or uncertainty.
6. Relevant limitations.

Do not claim optimization of real electricity dispatch without actual operational constraints, cost functions and safety limits.

Avoid presenting model feature importance as causal proof.

# 15. PHASE 7 — PREMIUM WEB DASHBOARD

The UI must be a professional, research-grade, responsive application.

Visual direction:

- Modern analytical command center.
- Premium navy and neutral palette.
- Clear typographic hierarchy.
- Clean cards, tables and charts.
- Excellent spacing and alignment.
- Light and dark mode where practical.
- Fully responsive desktop, tablet and mobile layouts.
- Loading, empty, failure and no-data states.
- Accessible navigation and chart labels.
- No decorative fake data.

## Required Pages

### Overview

- Latest report date
- Total historical records
- Dataset coverage
- Generation summary
- Production cost summary
- Recorded load-shedding overview
- Latest forecast
- Data collection health

### Data Collection

- Last run and next scheduled run
- Ingestion history
- Newly added records
- Corrections
- Download and parser failures
- Manual collection trigger
- Historical backfill controls

### Master Dataset

- Searchable records
- Date filtering
- Column selection
- Quality filtering
- CSV download
- Source-document links

### Data Quality

- Missing values
- Calendar gaps
- Validation failures
- Partial extraction distribution
- Source coverage and revisions

### Generation & Demand

- Historical trends
- Demand comparison
- Fuel contribution
- Regional analysis
- Interactive charts

### Production Cost

- Daily and monthly cost
- Cost per unit
- Fuel-wise cost
- Historical comparisons
- Cost drivers

### Machine Learning

- Forecast configuration
- Model comparison
- Actual versus predicted
- Prediction intervals
- Evaluation periods
- Feature importance
- Model metadata

### Load-Shedding Intelligence

- Historical zonal data
- Event frequency
- Predicted risk, when validated
- Uncertainty and limitations

### Decision Support

- Scenario controls
- Evidence-backed risk indicators
- Explainable recommendations

### Thesis Studio

- Select all available history or a date range.
- Select research modules.
- Generate analytical sections.
- Export a professional PDF.
- View previous reports and data versions.

### Settings

- Non-secret source configuration
- Collection schedule
- System health
- Model refresh configuration
- Administrative controls

# 16. PHASE 8 — AUTOMATIC REPORT GENERATOR

Create a complete PDF reporting system.

The default report should use all available historical data.

## Report Sections

1. Cover Page
2. Executive Summary
3. Research Objectives
4. Dataset Description
5. Data Acquisition Methodology
6. Data Quality Assessment
7. Generation and Demand Analysis
8. Fuel-Mix Analysis
9. Production Cost Analysis
10. Load-Shedding Analysis
11. Forecasting Methodology
12. Experimental Evaluation
13. Forecast Results
14. Decision Support Findings
15. Discussion
16. Limitations
17. Conclusions
18. References
19. Appendices

## PDF Requirements

- A4 academic layout.
- Automatic page numbering.
- Numbered figures and tables.
- High-resolution vector or print-quality charts.
- Professional statistical tables.
- Clear source citations.
- Report generation timestamp.
- Source dataset cutoff date.
- Dataset version.
- Model version and evaluation details.
- Clear explanation of missing data.
- No fabricated findings or references.

Reports must be generated from a consistent, frozen analytical snapshot.

If a new daily record arrives while a report is generating, the report must continue using its original snapshot.

# 17. PHASE 9 — FINAL THESIS BOOK

Prepare a comprehensive master's thesis draft with the following structure:

## Chapter 1 — Introduction

- Bangladesh power sector context
- Research motivation
- Problem statement
- Research objectives
- Research questions
- Study scope
- Expected contributions

## Chapter 2 — Literature Review

- Electricity production cost forecasting
- Demand forecasting
- Load-shedding analysis
- Time-series machine learning
- Existing power analytics and decision-support research
- Identified research gap

All literature citations must be verified.

## Chapter 3 — System Architecture

- BPDB data sources
- Collection pipeline
- Data storage
- Application architecture
- Technology selection
- Database design
- Data flow diagrams

## Chapter 4 — Data Preparation and Methodology

- Historical data coverage
- Extraction methodology
- Data validation
- Preprocessing
- Feature engineering
- Missing-data policy
- Forecast target definitions
- Evaluation design

## Chapter 5 — Proposed Models

- Baselines
- Statistical models
- Machine learning algorithms
- Model configurations
- Training procedures
- Evaluation metrics

## Chapter 6 — Results and Analysis

- Dataset statistics
- Historical analytics
- Model comparison
- Forecast performance
- Error analysis
- Prediction uncertainty
- Discussion of findings

## Chapter 7 — Decision Support

- Analytical rules
- Scenario modelling
- Risk interpretation
- Recommendations
- Practical limitations

## Chapter 8 — Implementation and Testing

- Interface design
- Database operations
- Automated scraping
- Scheduler tests
- Model integration
- Reporting system
- System testing

## Chapter 9 — Conclusion and Future Work

- Research achievements
- Measured contributions
- Limitations
- Future improvements

## Appendices

- Selected source code
- Database schema
- API documentation
- Data dictionary
- Additional research tables
- Reproducibility instructions

Do not invent experimental results, academic references, or thesis findings.

# 18. SEVEN-DAY IMPLEMENTATION SCHEDULE

## Day 1 — October 25

**Goal: Project foundation**

Complete:

- Repository initialization.
- Architecture selection.
- Python/Node environments.
- Backend and frontend foundations.
- Neon schema.
- Source inventory.
- Data dictionary.
- Existing-code audit.

**Acceptance:** Backend health endpoint, successful Neon connection, migration execution and source discovery test.

## Day 2 — October 26

**Goal: BPDB ingestion system**

Complete:

- Source discovery.
- Original PDF downloads.
- Available PDF parsers.
- Validation.
- Deduplication.
- Versioning.
- Backfill.
- CSV export.

**Acceptance:** Independently verify a sample of extracted measurements against original PDFs. Repeat ingestion without duplicate active records.

## Day 3 — October 27

**Goal: Scheduler and analytical infrastructure**

Complete:

- 12 PM daily scheduling.
- Failure handling.
- Run monitoring.
- Historical aggregation.
- Data quality calculations.
- Generation, demand and cost analytics APIs.

**Acceptance:** Test scheduled execution logic and validate analytics against independently calculated values.

## Day 4 — October 28

**Goal: Forecasting research**

Complete:

- Monthly cost forecast.
- Daily demand forecast.
- Load-shedding feasibility audit.
- Baseline models.
- Walk-forward testing.
- Evaluation artifacts.
- Saved model metadata.

**Acceptance:** Reproducible experimental results and clearly documented limitations.

## Day 5 — October 29

**Goal: Dashboard**

Complete:

- Responsive application shell.
- Overview.
- Collection monitor.
- Master dataset.
- Analytics.
- Model evaluation.
- Forecasting.
- Decision support.

**Acceptance:** All implemented views load verified backend data with functioning filters and appropriate failure states.

## Day 6 — October 30

**Goal: Research reporting**

Complete:

- PDF report generation.
- Figures and statistical tables.
- Research methodology documentation.
- Thesis draft.
- Results interpretation.
- References and appendices.

**Acceptance:** An end-to-end PDF report using recorded analytical snapshots with no fabricated results.

## Day 7 — October 31

**Goal: Integration, testing and finalization**

Complete:

- Full system validation.
- Live collection test.
- Duplicate handling test.
- Model reproducibility check.
- PDF validation.
- Deployment verification.
- README and documentation.
- Thesis draft final review.
- Defense presentation material.

**Acceptance:** Demonstrable end-to-end prototype and documented research results.

If some noncritical functionality remains unfinished, prioritize data integrity, the primary forecast, reproducibility, the dashboard's essential research views, and the final thesis draft.

# 19. TESTING REQUIREMENTS

Create automated tests for:

- BPDB archive discovery.
- PDF parsing.
- Missing and malformed documents.
- Report date handling.
- Duplicate detection.
- Official document corrections.
- Transactional database updates.
- Historical backfill.
- CSV consistency.
- Data aggregation.
- Forecast target shifting.
- Feature leakage prevention.
- Chronological validation.
- Model serialization and inference.
- API response validation.
- Report reproducibility.
- PDF rendering.

Where real live-source verification is required, clearly identify that automated unit tests alone are insufficient.

# 20. SECURITY AND OPERATIONS

Implement:

- Environment-variable configuration.
- Secure database connections.
- Secret-free logging.
- Authenticated administrative endpoints.
- Protected manual collection and model-training controls.
- Input validation.
- Rate limiting where appropriate.
- Restricted cross-origin access.
- Database backup and recovery strategy.
- Persistent raw document storage.
- Structured error logging.
- Safe handling of failed or interrupted jobs.

Respect the official website's access requirements and use reasonable request rates. Avoid unnecessarily downloading unchanged files repeatedly.

# 21. PROJECT MANAGEMENT RULES

Maintain the following files:

```text
docs/PROJECT_STATUS.md
docs/DECISIONS.md
docs/DATA_DICTIONARY.md
docs/KNOWN_ISSUES.md
docs/RESEARCH_RESULTS.md
docs/IMPLEMENTATION_CHECKLIST.md
```

After each implementation step, record:

- Files created or modified.
- Features implemented.
- Tests performed.
- Observed results.
- Known limitations.
- Remaining tasks.
- Next recommended development step.

Use exact commands for Windows CMD or PowerShell and clearly indicate which shell each command is intended for.

Do not mark a feature as complete unless the relevant acceptance tests pass.

# 22. INSTRUCTIONS FOR WORKING WITH ME

I want to build the complete project with you, step by step.

At the start of each major phase:

1. Explain the objective.
2. Identify relevant existing files.
3. Present the files that need to be created or changed.
4. Implement the complete phase.
5. Provide the exact installation or execution commands.
6. Run available tests.
7. Explain how I can verify the result locally.
8. Identify any problems.
9. Update the progress checklist.
10. Continue with the next dependency in the project plan.

When I provide terminal errors, analyze the actual error rather than restarting the project unnecessarily.

When I provide existing source code, inspect it before modifying it.

When an implementation requires an external credential, provide an `.env.example` and explain how I should configure the secret locally without exposing it.

Avoid repeatedly asking for information already available in the project.

Do not provide pseudocode when I have requested a real implementation.

Do not replace a functioning implementation with an incomplete example.

If an issue is too complex to finish within the remaining schedule, implement the highest-value working version and document what remains.

# 23. DEFINITION OF DONE

The complete project is considered ready for thesis demonstration when:

- The source collector can retrieve authentic BPDB reports.
- New observations are validated and saved reliably.
- Duplicate active report dates are prevented.
- Historical source files and corrections remain traceable.
- Neon contains the authoritative master records.
- A valid master CSV can be exported.
- The scheduled daily process is configured and verifiable.
- Core historical analytics are correct.
- At least one primary machine-learning forecast has defensible chronological evaluation.
- Other predictive modules are implemented only where the data supports them.
- The dashboard displays real data and results.
- The thesis PDF generator works.
- The full thesis draft uses verified research outputs.
- Installation and demonstration procedures are documented.

# 24. START THE PROJECT NOW

Begin with **Day 1 — Complete Project Foundation and Architecture**.

First inspect any available project files, current source collection scripts, BPDB datasets and previous machine-learning experiments.

Then:

1. Produce the definitive architecture.
2. Identify reusable versus replaceable components.
3. Define the relational database schema.
4. Define the data ingestion and canonical-record rules.
5. Create the repository structure.
6. Implement the FastAPI foundation.
7. Establish the Neon connection and initial migrations.
8. Implement the initial source discovery service.
9. Create the project configuration and environment examples.
10. Provide the exact Windows setup commands.
11. Run the initial tests.
12. Record the Day 1 deliverables and remaining work.

Do not start with dashboard decoration. Establish the data and backend foundation first.

**Our final objective is a fully integrated, automated and scientifically defensible BPDB research platform that can continuously update its historical dataset and generate trustworthy predictions and thesis-quality research reports on demand.**