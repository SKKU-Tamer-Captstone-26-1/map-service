# Map / Place Migration Review

## Review Summary

현재 migration은 MVP 범위의 schema-only 작업으로 적절합니다. `map-service/place-service`가 canonical place/menu/inventory/price 데이터를 소유하고, Admin Page와 recommendation-service가 DB를 직접 소유하지 않는 경계를 유지합니다.

가장 큰 남은 리스크는 실제 PostgreSQL + PostGIS 환경에서 dry-run이 아직 수행되지 않았다는 점입니다.

## Files Reviewed

| File | Role |
|---|---|
| `docs/codex_map_db_migration_task_v0_1.md` | Migration task and acceptance criteria |
| `docs/codex_plan_prompt_map_db_v0_1.md` | Original plan prompt and boundaries |
| `docs/docs_map_place_erd_v0_1.md` | Ownership, ERD, MVP/deferred scope |
| `docs/docs_map_place_data_ingestion_v0_1.md` | Ingestion and Kakao policy |
| `map_place_service_erd_v0_1.dbml` | DBML schema source |
| `migrations/001_enable_extensions.sql` | Extensions and enum types |
| `migrations/002_create_source_import_staging.sql` | Source/import/staging tables |
| `migrations/003_create_place_core.sql` | Canonical places and source refs |
| `migrations/004_create_admin_governance.sql` | Claims/managers/change requests/overrides/audit |
| `migrations/005_create_menu_inventory_price.sql` | Menu/inventory/price |
| `migrations/006_create_outdoor_and_outbox.sql` | Outdoor profile and outbox |

## Acceptance Criteria Review

| Criterion | Status | Evidence |
|---|---|---|
| PostGIS extension migration exists | OK | `001_enable_extensions.sql` has `CREATE EXTENSION IF NOT EXISTS postgis` |
| Source/import/staging tables exist | OK | `data_sources`, `place_import_batches`, `place_import_candidates`, `place_dedupe_matches`, `place_review_tasks` |
| Core place tables exist | OK | `places`, `place_source_refs` |
| Admin/governance tables exist | OK | `business_claims`, `place_managers`, `place_change_requests`, `place_overrides`, `place_audit_logs` |
| Menu/inventory/price tables exist | OK | `venue_menu_items`, `venue_inventory_items`, `venue_price_offers` |
| Outdoor spot table exists | OK | `outdoor_spot_profiles` |
| Outbox table exists | OK | `place_outbox_events` |
| Required indexes exist | OK | GiST, public partial, recommendation partial, queue/lookup indexes present |
| No cross-service FK to auth-service | OK | User IDs are `text`; no auth references |
| No cross-service FK to recommendation/catalog | OK | `beverage_catalog_ref_id` is `text`; no external FK |
| Inventory freshness/confidence fields | OK | `last_seen_at`, `expires_at`, `stock_confidence`, `revision` |
| Price validity/confidence fields | OK | `valid_from`, `valid_until`, `confidence`, `revision` |
| Lifecycle status instead of hard delete | OK | `place_status` enum |
| Outbox supports recommendation sync | OK | aggregate fields, status, idempotency, payload |
| Verification results truthful | Needs Review | Static checks only; no PostGIS dry-run yet |

## Detailed Migration Notes

### `001_enable_extensions.sql`

- Enables `postgis` and `pgcrypto`.
- Creates enum types for source, import, review, place, governance, menu, inventory, price, outbox, and optional future tables.
- Note: optional enum types such as `media_type`, `report_type`, `tag_type`, `travel_mode` exist even though corresponding tables are deferred. This is acceptable but should be documented as forward-compatible schema surface.

### `002_create_source_import_staging.sql`

- Creates the staging pipeline before canonical `places`.
- `place_import_candidates.location` uses `geography(Point, 4326)` with GiST index.
- `matched_place_id`, `existing_place_id`, and `place_id` are created before `places` exists, then FKs are added in migration `003`.
- Important checks: lat/lng range, confidence range, nonnegative row/error counts.

### `003_create_place_core.sql`

- Creates canonical `places` and `place_source_refs`.
- `places.location` uses `geography(Point, 4326)` with GiST index.
- Public exposure is supported by status + publication fields and partial indexes.
- `place_source_refs` retains `source_policy`, which is required for Kakao/public-data policy handling.
- Partial unique index on `(source_id, external_source_id)` applies only when external ID is not null.

### `004_create_admin_governance.sql`

- Creates owner claim, manager, sensitive change request, override, and audit tables.
- Auth user references are stored as `text`.
- Sensitive change approval flow is represented by `place_change_requests`.
- Audit table exists, but application-level audit emission is not implemented yet.

### `005_create_menu_inventory_price.sql`

- Creates menu, inventory, and price tables.
- `beverage_catalog_ref_id` is a plain text external reference with no DB FK.
- Inventory includes freshness/TTL and confidence.
- Price includes validity window and confidence.

### `006_create_outdoor_and_outbox.sql`

- `outdoor_spot_profiles.place_id` is both PK and FK.
- `place_outbox_events` supports `PENDING`, `PUBLISHED`, `FAILED`, `SKIPPED`.
- Outbox includes `aggregate_revision`, `payload_json`, `idempotency_key`.

## ERD-to-Migration Comparison

| Item | Expected | Actual | Status | Comment |
|---|---|---|---|---|
| PostGIS extension | Enabled | Enabled | OK | Needs DB dry-run |
| `places.location` | PostGIS point | `geography(Point, 4326)` | OK | Matches design |
| Spatial index | GiST | Present | OK | Also for candidates |
| Lifecycle status | Enum/check | Enum | OK | Required values present |
| Publication | `publication_status`, `published_at` | Present | OK | Query index present |
| Recommendation eligibility | Boolean | Present | OK | Partial index present |
| Source policy | Source and refs | Present | OK | Kakao can be restricted |
| Owner claims | Claim table | Present | OK | Workflow not implemented |
| Manager roles | Role table | Present | OK | No auth FK |
| Sensitive changes | Request table | Present | OK | Approval API future |
| Overrides | Operator override table | Present | OK | Resolution logic future |
| Audit | Audit log table | Present | OK | Write middleware future |
| Menu | Venue menu table | Present | OK | Revision present |
| Inventory | Freshness/confidence | Present | OK | TTL present |
| Price | Validity/confidence | Present | OK | Validity present |
| Outdoor profile | Place-scoped profile | Present | OK | Operator curated |
| Outbox | Event table | Present | OK | Sync worker future |
| Display tables | Optional | Deferred | Deferred | tags/media/hours/reports |
| Route cache | Optional | Deferred | Deferred | phase 2+ |

## Boundary Findings

- No cross-service DB FK to auth-service was found.
- No cross-service DB FK to recommendation-service or catalog-service was found.
- No recommendation-service-owned table was created.
- No Admin Page direct-write mechanism was created.
- No Kakao ingestion or seed data was created.
- Kakao is represented only as a `source_type`; persistence policy is controlled by `source_policy`.
- Soft-delete/archive is supported through lifecycle status values.
- Auditability is structurally supported, but not enforced until application write paths are implemented.

## Needs Review Before Merge / Deploy

| Area | Review Needed | Reason |
|---|---|---|
| DB runtime | Run all migrations on clean PostgreSQL with PostGIS | Static inspection cannot prove SQL applies |
| Rollback | Decide down migration convention | Current migrations are forward-only |
| Audit behavior | Define required audit emission per write API | Table exists, behavior not implemented |
| Outbox behavior | Define transactional write and retry policy | Table exists, worker not implemented |
| Optional enum surface | Decide whether unused optional enums are acceptable in `001` | Tables are deferred but enum types exist |
| Kakao policy | Legal/partnership confirmation before persistence | Avoid accidental bulk canonical ingestion |
