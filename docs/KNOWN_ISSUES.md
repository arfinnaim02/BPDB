# Known issues and limitations — November 1, 2026

1. Only supported national Page 1 metrics are currently canonicalized. Regional/fuel-wise
   analysis and recorded zonal load-shedding models need additional source extraction.
2. Seven historical URLs returned empty PDF bodies. Failed/quarantined extractions and
   the last verified 188 calendar gaps require investigation; gaps do not prove missing reports.
3. The Drive checkpoint archives recent PDFs, not the complete approximately 3.77 GiB local
   collection. Full historical cloud backup and full disaster recovery remain outstanding.
4. Cached URLs are not routinely re-downloaded; same-URL official replacements can be missed.
5. GitHub schedules target noon Bangladesh but can be delayed; November 1 started at 18:15.
6. Drive checkpoint outcome is in GitHub, not the ingestion-run database record. The monitoring
   API explicitly reports that distinction. It never infers storage success from worker status.
7. New monitoring/master routes require live authenticated Neon acceptance. No production
   credentials were used for this update's tests. The opt-in PostgreSQL test was skipped.
8. Schema has no immutable-row privilege/trigger enforcement. Application checks and canonical
   constraints do not substitute for a production permissions and concurrency audit.
9. Each API request uses a consistent PostgreSQL snapshot, but separate pagination requests can
   observe intervening canonical changes. This API is not a frozen research dataset version.
10. Frontend is still the foundation health page; dashboard CSV access and application hosting
    remain to be implemented. No new web deployment is part of this update.
11. `/system` capability flags describe implemented features, not scheduler punctuality or health.
12. Publication/availability timestamps and metric coverage must be audited before forecasting.
    Historical consumed-fuel cost and modern production cost definitions must not be merged blindly.
13. No research models, validated forecast results, decision module, analytical PDF generator or
    complete thesis draft are implemented in the current repository.
14. FastAPI/Starlette TestClient emits an upstream httpx deprecation warning; tests still pass.
