# Next Codex Prompt: Map / Place DB Verification and First Service Layer

Use this prompt for the next implementation pass after the team reviews the handoff.

```text
You are Codex working in the map-service repository.

Read first:
- docs/handoff/map-place-db-handoff.md
- docs/handoff/map-place-migration-review.md
- docs/handoff/map-place-next-steps.md
- docs/handoff/map-place-api-draft.md
- docs/handoff/map-place-admin-permission-matrix.md
- docs/handoff/map-place-recommendation-sync-draft.md
- docs/handoff/map-place-data-ingestion-followups.md
- migrations/*.sql

Task:
Perform the P0 verification work for the map/place DB migration.

Scope:
- Run the six migrations on a clean local/dev PostgreSQL database with PostGIS.
- Verify `postgis` and `pgcrypto` extensions.
- Verify all MVP tables, indexes, enum types, foreign keys, unique constraints, and check constraints.
- Verify no cross-service DB foreign keys to auth-service, recommendation-service, catalog-service, or user tables.
- Verify optional tables are still deferred.
- Produce a short verification report under `docs/handoff/map-place-db-verification-report.md`.

Do not:
- Modify existing migrations unless explicitly approved after documenting the issue.
- Add new migrations.
- Implement APIs.
- Implement Admin UI.
- Implement Kakao ingestion.
- Implement recommendation scoring or RAG.
- Seed production-like data.
- Drop/reset any non-disposable database.

If a migration fails:
- Stop.
- Document the exact failing migration, SQL error, likely cause, and proposed patch.
- Do not apply the patch unless it is clearly requested.
```
