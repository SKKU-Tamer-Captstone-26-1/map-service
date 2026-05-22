# Map / Place DB Verification Report

Date: 2026-05-22

## Environment

- Disposable DB: Docker container `map-service-postgis-verify`
- Image: `postgis/postgis:16-3.5`
- Platform: `linux/amd64` under Docker emulation
- Database: `map_service`
- Verification target: clean PostgreSQL + PostGIS schema plus staging import workflow

## Migration Verification

Applied migrations in order:

1. `001_enable_extensions.sql`
2. `002_create_source_import_staging.sql`
3. `003_create_place_core.sql`
4. `004_create_admin_governance.sql`
5. `005_create_menu_inventory_price.sql`
6. `006_create_outdoor_and_outbox.sql`

Result: passed.

Confirmed extensions:

```text
pgcrypto
postgis
```

Confirmed MVP tables:

```text
business_claims
data_sources
outdoor_spot_profiles
place_audit_logs
place_change_requests
place_dedupe_matches
place_import_batches
place_import_candidates
place_managers
place_outbox_events
place_overrides
place_review_tasks
place_source_refs
places
venue_inventory_items
venue_menu_items
venue_price_offers
```

Confirmed optional/deferred tables are absent:

```text
tags
place_tags
route_estimate_cache
place_reports
place_media
place_business_hours
place_special_hours
```

Confirmed geography columns:

```text
place_import_candidates.location: Point, SRID 4326
places.location: Point, SRID 4326
```

Confirmed key indexes:

```text
idx_import_candidates_location_gist
idx_outbox_pending
idx_places_location_gist
idx_places_public_active_published
idx_places_recommendation_eligible
uq_place_source_refs_source_external
```

Confirmed key constraints:

```text
ck_inventory_stock_confidence_range
ck_places_price_level_range
ck_price_offers_confidence_range
uq_data_sources_type_name
uq_place_managers_place_user
```

Confirmed foreign key boundary:

- No foreign keys to auth-service tables.
- No foreign keys to recommendation-service tables.
- No foreign keys to catalog-service tables.
- Foreign keys point only to local map/place tables.

## Staging Import Verification

Applied source registry:

```text
python3 -m scripts.map_place_ingestion.import_source_registry \
  --input map_place_data_bootstrap_v0_3/data/source_registry.csv \
  --apply \
  --database-url <disposable local DB>
```

Result:

```text
applied_records=9
errors=0
```

Source policy distribution:

```text
KAKAO:REALTIME_ONLY:1
OPERATOR:STORABLE:1
OWNER:STORABLE:1
PUBLIC_DATA:RESTRICTED:1
PUBLIC_DATA:STORABLE:4
USER_REPORT:STORABLE:1
```

Applied outdoor spot staging import:

```text
python3 -m scripts.map_place_ingestion.import_outdoor_spot_candidates \
  --input map_place_data_bootstrap_v0_3/data/seoul_hangang_outdoor_spot_seed_candidates.csv \
  --apply \
  --database-url <disposable local DB>
```

Result:

```text
inserted_candidates=11
inserted_review_tasks=11
canonical_places_created=0
```

Post-import table counts:

```text
data_sources=9
place_import_batches=1
place_import_candidates=11
place_review_tasks=11
places=0
place_source_refs=0
place_outbox_events=0
```

Candidate status:

```text
PENDING:OUTDOOR_SPOT:RESTRICTED:11
```

Review task status:

```text
PENDING:VERIFY_LOCATION:11
```

Geocode-required candidates:

```text
11
```

Kakao policy check:

```text
KAKAO source_policy = REALTIME_ONLY
```

## Conclusion

The clean migration run passed on a disposable PostgreSQL + PostGIS database.

The staging import workflow behaved safely:

- Source registry import succeeded.
- Outdoor spot candidates were inserted into staging/review tables.
- No canonical `places` rows were created.
- No `place_source_refs` or `place_outbox_events` were created during staging import.
- Kakao remained `REALTIME_ONLY`.

## Follow-ups

- Implement publish-approved-candidates workflow separately.
- Publish workflow must create/update `places`, `place_source_refs`, `place_audit_logs`, and `place_outbox_events`.
- Add DB-backed dedupe insertion into `place_dedupe_matches`.
- Keep owner menu/inventory/price canonical apply blocked until permission, audit, and outbox behavior exist.
