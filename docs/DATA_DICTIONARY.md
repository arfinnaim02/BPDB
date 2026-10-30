# Data dictionary — foundation

## Implemented provenance fields

| Field | Type | Meaning / rule |
|---|---|---|
| original_url | text | Original official document address; retained per content revision |
| category | text | Page category; unknown if not confidently identified |
| sha256 | 64-character text | Digest of exact original bytes; downloader pending |
| storage_key | text | Immutable raw storage location; storage implementation pending |
| retrieved_at | timezone timestamp | When the source was collected |
| published_at | nullable timezone timestamp | Official publication time if actually known |
| archive_date_hint | nullable date | Archive row date; not proof of operational date |
| report_date | nullable source date / required report date | Operational date confirmed from PDF |
| parser_version | text | Extractor identity for reproducibility |
| available_at | nullable timezone timestamp | Conservative information-availability bound; NULL means ineligible for as-of training until resolved |
| quality_status | enum-like checked text | validated, partial, quarantined or conflict |
| value | nullable Numeric(24,6) | Original supported numeric measurement; NULL is missing |
| unit | text | Exact unit supported by original source |
| zone / period / fuel | text | Observation dimensions, never inferred neighbourhood coverage |
| source_page / raw_text | nullable number / text | Extraction evidence |
| member_version_ids | JSON list | Frozen snapshot of report version identities |

## Candidate research variables — legacy CSV column names exist; original PDF units NOT verified

| Candidate | Possible source unit to inspect | State |
|---|---|---|
| Day/evening generation peak | MW | Pending PDF inspection |
| Day/evening demand peak | MW | Pending PDF inspection |
| Generated/demanded/unserved energy | MWh or million kWh, as reported | Pending PDF inspection |
| Fuel generation | Source-specific energy or power unit | Pending PDF inspection |
| Fuel production cost / total production cost | Exact currency denomination must be confirmed | Pending PDF inspection |
| Cost per unit | Exact currency/kWh denomination must be confirmed | Pending PDF inspection |
| Zonal load shedding | Power/energy unit and reporting interval must be confirmed | Pending PDF inspection |
| Gas supply / temperature | Source-specific unit | Pending PDF inspection |

No conversion factors, measurement definitions or statistical findings have been assumed.
A zero must be explicitly supported by the source. Do not sum MW across time as energy.
