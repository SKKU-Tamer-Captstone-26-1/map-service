# Codex Task: Create Map / Place DB Migrations from ERD v0.1

## 0. Task Summary

Create initial PostgreSQL migrations for the `map-service` / `place-service` database based on the ERD v0.2 documentation.

This task creates database schema only.

Do not implement runtime APIs, admin screens, ingestion jobs, recommendation logic, or Kakao integration.

## 1. Required Reading

Read in this order:

```text
AGENTS.md
.agent/HARNESS.md
.agent/DOMAIN_BOUNDARIES.md
docs/map-place/ownership.md
docs/map-place/erd.md
docs/map-place/data-ingestion.md
```

If file names differ, locate the equivalent documents before implementing.

## 2. Target Service

```text
map-service / place-service
```

This service is the canonical owner of:

```text
- places
- venues
- locations
- menu items
- inventory
- price offers
- business claims
- publication state
- operator overrides
- place audit logs
- source/import/review metadata
```

## 3. Scope

Allowed:

```text
- Create PostgreSQL migrations for map/place DB
- Add enum types or equivalent check constraints
- Enable required extensions
- Create source/import/staging tables
- Create canonical place tables
- Create admin/governance tables
- Create menu/inventory/price tables
- Create outdoor spot table
- Create outbox events table
- Create required indexes
- Add migration tests/dry-run if the repo supports it
```

Not allowed:

```text
- Do not implement REST/gRPC APIs
- Do not implement Admin Page UI
- Do not implement Kakao ingestion
- Do not call Kakao API
- Do not seed production data
- Do not create recommendation-service tables
- Do not add cross-service DB foreign keys to auth-service
- Do not add cross-service DB foreign keys to recommendation-service/catalog-service
- Do not make recommendation-service read map-service DB directly
```

## 4. Ownership Rules

Must preserve:

```text
Admin Page is not a data owner.
Admin Page writes through service APIs only.
```

```text
map-service/place-service owns canonical place/menu/inventory/price data.
```

```text
recommendation-service consumes snapshots/events/internal APIs only.
```

```text
Kakao API is realtime/restricted by default and must not be treated as canonical bulk-ingestion source.
```

## 5. Required Migration Plan

Create migrations in additive order.

Recommended order:

```text
001_enable_extensions
002_create_source_import_staging
003_create_place_core
004_create_admin_governance
005_create_menu_inventory_price
006_create_outdoor_and_outbox
007_create_optional_map_display_tables
008_create_optional_route_cache
```

If the repo has a different migration naming convention, follow the repo convention while preserving the order.

## 6. Migration Details

### 6.1 `001_enable_extensions`

Required:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

If the repo uses UUID generation from application code instead of `gen_random_uuid()`, document the difference and adjust defaults accordingly.

### 6.2 `002_create_source_import_staging`

Create:

```text
data_sources
place_import_batches
place_import_candidates
place_dedupe_matches
place_review_tasks
```

Purpose:

```text
- Source policy tracking
- Public data import batch tracking
- Candidate staging
- Dedupe suggestions
- Operator review queue
```

### 6.3 `003_create_place_core`

Create:

```text
places
place_source_refs
```

Required behavior:

```text
- places must have lifecycle status
- places must have publication_status
- places must have revision
- places must support PostGIS location
- place_source_refs must track source_policy
```

### 6.4 `004_create_admin_governance`

Create:

```text
business_claims
place_managers
place_change_requests
place_overrides
place_audit_logs
```

Required behavior:

```text
- auth-service user ids are stored as text/string only
- no auth-service DB foreign keys
- sensitive owner changes go through place_change_requests
- operator override exists separately from source data
- audit log exists for admin/operator/owner/system writes
```

### 6.5 `005_create_menu_inventory_price`

Create:

```text
venue_menu_items
venue_inventory_items
venue_price_offers
```

Required behavior:

```text
- beverage_catalog_ref_id is a text/string external ref only
- no recommendation-service/catalog-service DB foreign keys
- inventory has last_seen_at, expires_at, stock_confidence
- price has valid_from, valid_until, confidence
- menu/inventory/price have revision fields
```

### 6.6 `006_create_outdoor_and_outbox`

Create:

```text
outdoor_spot_profiles
place_outbox_events
```

Required behavior:

```text
- outdoor_spot_profiles uses place_id as PK/FK
- place_outbox_events supports pending/published/failed/skipped
- outbox events include aggregate_revision and payload_json
```

### 6.7 `007_create_optional_map_display_tables`

Create if included in MVP:

```text
tags
place_tags
place_media
place_business_hours
place_special_hours
place_reports
```

If not included, document as deferred.

### 6.8 `008_create_optional_route_cache`

Create only if route cache is in MVP:

```text
route_estimate_cache
```

Otherwise document as deferred.

## 7. Required Indexes

At minimum:

```sql
CREATE INDEX idx_places_location_gist
ON places
USING GIST (location);
```

```sql
CREATE INDEX idx_places_public_active_published
ON places (place_type, updated_at)
WHERE status = 'ACTIVE'
  AND publication_status = 'PUBLISHED';
```

```sql
CREATE INDEX idx_places_recommendation_eligible
ON places (place_type, updated_at)
WHERE status = 'ACTIVE'
  AND publication_status = 'PUBLISHED'
  AND recommendation_eligible = true;
```

```sql
CREATE INDEX idx_import_candidates_location_gist
ON place_import_candidates
USING GIST (location);
```

Also add indexes for:

```text
- source lookup
- candidate review queue
- dedupe queue
- place managers by user_id/status
- pending change requests
- active overrides
- menu by place/status
- inventory by place/beverage_catalog_ref_id
- inventory expiration
- price by place/beverage_catalog_ref_id
- price validity
- outbox pending events
```

## 8. Constraints

Required:

```text
- unique(source_type, source_name) on data_sources
- unique(source_id, external_source_id) on place_source_refs when external_source_id is not null
- unique(place_id, user_id) on place_managers
- unique(place_id, day_of_week) on place_business_hours if included
- unique(place_id, target_date) on place_special_hours if included
- unique(place_id, tag_id) on place_tags if included
```

Use check constraints where appropriate:

```text
- price_krw >= 0
- price_level between 1 and 5 when not null
- latitude/longitude ranges if stored separately
- confidence values between 0 and 1
```

## 9. Verification Requirements

Run or explain:

```text
- migration generation check
- migration dry-run against local PostgreSQL if available
- unit tests if migrations/models have tests
- lint/typecheck if repo requires it
```

If a check cannot be run, report:

```text
Not run: <check>
Reason: <reason>
```

Never claim tests passed unless they were actually run.

## 10. Acceptance Criteria

```text
- [ ] PostGIS extension migration exists or is confirmed already present
- [ ] Source/import/staging tables exist
- [ ] Core place tables exist
- [ ] Admin/governance tables exist
- [ ] Menu/inventory/price tables exist
- [ ] Outdoor spot table exists
- [ ] Outbox table exists
- [ ] Required indexes exist
- [ ] No cross-service DB FKs to auth-service
- [ ] No cross-service DB FKs to recommendation-service/catalog-service
- [ ] Inventory includes freshness/confidence fields
- [ ] Price includes validity/confidence fields
- [ ] Places use lifecycle status instead of hard delete
- [ ] Outbox supports recommendation snapshot sync
- [ ] Verification results are reported truthfully
```

## 11. Final Response Format

Codex final response must include:

```text
Summary
Changed files
Verification
Risks / Follow-ups
```

Example:

```text
Summary
- Added additive migrations for map/place database core.
- Added staging/import tables before canonical places.
- Added menu/inventory/price and outbox tables.

Changed files
- migrations/001_enable_extensions.sql
- migrations/002_create_source_import_staging.sql
- migrations/003_create_place_core.sql
...

Verification
- Ran migration dry-run on local PostgreSQL: passed.
- Ran unit tests: passed.

Risks / Follow-ups
- Kakao API storage policy still requires legal/partnership confirmation before any ingestion implementation.
- route_estimate_cache was deferred.
```
