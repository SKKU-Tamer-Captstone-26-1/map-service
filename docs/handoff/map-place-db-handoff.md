# Map / Place DB Handoff

## TL;DR

이번 migration은 `map-service/place-service`가 장소, 위치, 메뉴, 재고, 가격, 점주 claim, 운영자 override, 감사 로그, outbox event를 canonical하게 소유하기 위한 초기 PostgreSQL schema입니다.

Admin Page는 DB owner가 아니라 privileged UI client입니다. Admin Page는 map DB를 직접 수정하지 않고, auth-service와 map-service admin API를 통해서만 쓰기 작업을 해야 합니다.

Recommendation-service는 map DB를 직접 읽거나 쓰면 안 됩니다. `place_outbox_events`, internal snapshot API, sync job을 통해 published snapshot/read model만 소비해야 합니다.

아직 구현하면 안 되는 것은 API, Admin UI, Kakao ingestion, recommendation scoring, RAG, seed data, cross-service DB foreign key, route optimization입니다.

## Source Files Checked

요청된 경로 중 실제로 존재한 closest equivalent는 다음입니다.

| Requested | Actual | Note |
|---|---|---|
| `AGENTS.md` | Not found | Repo root에 없음 |
| `.agent/HARNESS.md` | Not found | `.agent/` 없음 |
| `.agent/DOMAIN_BOUNDARIES.md` | Not found | `.agent/` 없음 |
| `docs/README.md` | Not found | `README.md`만 존재 |
| `docs/architecture.md` | Not found | 별도 architecture doc 없음 |
| `docs/map-place/ownership.md` | `docs/docs_map_place_erd_v0_1.md` | ownership section 포함 |
| `docs/map-place/database.md` | `map_place_service_erd_v0_1.dbml` | DBML이 schema source 역할 |
| `docs/map-place/erd.md` | `docs/docs_map_place_erd_v0_1.md` | flattened path |
| `docs/map-place/data-ingestion.md` | `docs/docs_map_place_data_ingestion_v0_1.md` | flattened path |
| `docs/integrations/kakao-api-policy.md` | `docs/docs_map_place_data_ingestion_v0_1.md` | Kakao policy section 포함 |
| `docs/recommendation/map-read-model.md` | `docs/docs_map_place_erd_v0_1.md` | recommendation snapshot section 포함 |

No migration metadata files, ORM model files, generated Alembic files, or runtime DB model files were found.

## Service Ownership Summary

| Data | Canonical Owner | Writers | Readers | Notes |
|---|---|---|---|---|
| users / roles | auth-service | auth-service only | Admin Page, services via token/API | Map DB stores auth user IDs as `text`; no DB FK |
| places | map-service/place-service | operator API, reviewed owner/system flows | public map API, internal snapshot API | `places` is canonical |
| locations | map-service/place-service | operator API, reviewed change requests, reviewed ingestion | map queries, recommendation snapshots | PostGIS `location` plus lat/lng |
| business status | map-service/place-service | operator API, approved sensitive changes | public map, recommendation snapshots | lifecycle uses `status` enum |
| menu items | map-service/place-service | operator, owner/manager APIs | place detail, recommendation snapshots | beverage catalog refs are external text |
| inventory | map-service/place-service | operator, owner/manager/staff APIs | place detail, recommendation snapshots | freshness via `last_seen_at`, `expires_at`, confidence |
| price offers | map-service/place-service | operator, owner/manager APIs | place detail, recommendation snapshots | validity via `valid_from`, `valid_until`, confidence |
| business claims | map-service/place-service | owner submit, operator review | admin API | auth user ID is text only |
| operator overrides | map-service/place-service | operator API only | map-service resolution logic | override data is separate from source data |
| audit logs | map-service/place-service | map-service write path | admin/security review | append-only application behavior still needs implementation |
| recommendation snapshots | recommendation-service | recommendation sync consumer | recommendation-service | Built from map events/API, not direct DB reads |
| beverage knowledge | recommendation-service/catalog-service | catalog/recommendation tooling | recommendation/RAG | Map DB only stores menu/inventory/price association |
| RAG chunks | recommendation-service/RAG service | ingestion/RAG pipeline | chatbot/recommendation | Map DB must not own explanatory beverage knowledge |

## Migration Inventory

| Migration | Purpose | Tables Created | Indexes Created | Constraints Created | Extensions | Rollback Notes |
|---|---|---|---|---|---|---|
| `001_enable_extensions.sql` | Enable required DB features and enum types | None | None | 34 enum types, duplicate-safe via `DO` blocks | `postgis`, `pgcrypto` | No down migration; rollback would drop dependent tables first |
| `002_create_source_import_staging.sql` | Source tracking, import batches, staging candidates, dedupe, review queue | `data_sources`, `place_import_batches`, `place_import_candidates`, `place_dedupe_matches`, `place_review_tasks` | source lookup, import status/time, candidate source/name/address/status/location, dedupe candidate/place/status/confidence, review queue | source uniqueness, count nonnegative checks, lat/lng checks, confidence checks, FK to source/import tables | None | No down migration; dropping requires dependent FK order |
| `003_create_place_core.sql` | Canonical place records and source references | `places`, `place_source_refs` | normalized name, geohash, public query, recommendation query, source, merge target, GiST location, partial published/recommendation indexes, source ref indexes | lat/lng checks, price level check, revision positive, self FK for merge, source ref confidence check, partial unique source external ref, deferred FKs from staging to `places` | None | No down migration; core dependency for later migrations |
| `004_create_admin_governance.sql` | Claims, managers, sensitive changes, overrides, audit logs | `business_claims`, `place_managers`, `place_change_requests`, `place_overrides`, `place_audit_logs` | claims by place/requester/status, managers by user/status and place/status, change request queue, override active field, audit target/actor/action | manager uniqueness, override priority check, FKs to `places` only | None | No down migration; preserve audit data before rollback |
| `005_create_menu_inventory_price.sql` | Menu, stock, and price data owned by map/place service | `venue_menu_items`, `venue_inventory_items`, `venue_price_offers` | menu place/status/ref/name/signature, inventory place/ref/availability/expiry/menu item, price place/ref/menu item/validity/amount | price nonnegative, confidence range, revision positive, FKs to `places` and local menu items only | None | No down migration; consider outbox/audit consistency before rollback |
| `006_create_outdoor_and_outbox.sql` | Outdoor spot profile and event sync outbox | `outdoor_spot_profiles`, `place_outbox_events` | outbox pending queue, aggregate lookup, idempotency | outdoor PK/FK to place, outbox aggregate revision positive | None | No down migration; pending outbox events should be drained or archived first |

## Table Inventory

| Table | Purpose | Owner | Writer | Reader | MVP/Optional | Notes |
|---|---|---|---|---|---|---|
| `data_sources` | Source and policy registry | map-service | operator/system config | ingestion/review | MVP | Tracks `source_type`, `source_policy`, license, trust |
| `place_import_batches` | Import run tracking | map-service | ingestion worker/operator | admin review | MVP | No production seed data added |
| `place_import_candidates` | Candidate staging before canonical place | map-service | ingestion worker/operator | review flow | MVP | Has raw payload, normalized fields, PostGIS location |
| `place_dedupe_matches` | Candidate-to-place dedupe suggestions | map-service | dedupe worker/operator | review flow | MVP | Existing place FK added after `places` exists |
| `place_review_tasks` | Operator review queue | map-service | system/operator | admin review | MVP | Supports candidate and place review |
| `places` | Canonical place/location/business state | map-service | operator/reviewed flows | public/internal APIs | MVP | Has lifecycle, publication, revision, PostGIS |
| `place_source_refs` | Source references for canonical places | map-service | ingestion/operator | audit/review | MVP | Source policy retained per ref |
| `business_claims` | Owner claim requests | map-service | owner submit/operator review | admin API | MVP | User IDs as text |
| `place_managers` | Owner/manager/staff association | map-service | operator/claim approval | admin/owner APIs | MVP | User IDs as text; no auth FK |
| `place_change_requests` | Sensitive owner-submitted changes | map-service | owner/manager submit/operator review | admin API | MVP | Required for name/address/location/type/closure/reopen/merge |
| `place_overrides` | Operator override layer | map-service | operator API | map-service resolution | MVP | Separate from source data |
| `place_audit_logs` | Audit records for writes | map-service | map-service write path | admin/security | MVP | Table exists; middleware/service still needed |
| `place_reports` | User reports | map-service | public/owner/admin future API | review flow | Optional phase 2 | Not created intentionally |
| `place_business_hours` | Regular hours | map-service | owner/operator future API | place detail | Optional phase 2 | Not created intentionally |
| `place_special_hours` | Holiday/special hours | map-service | owner/operator future API | place detail | Optional phase 2 | Not created intentionally |
| `tags` | Controlled tag catalog | map-service | operator future API | map/recommendation | Optional phase 2 | Enum type exists; table deferred |
| `place_tags` | Place-tag assignment | map-service | operator/reviewed flows | map/recommendation | Optional phase 2 | Deferred with tags |
| `place_media` | Place images/media | map-service | owner/operator future API | place detail | Optional phase 2 | Media enums exist; table deferred |
| `venue_menu_items` | Menu/signature menu | map-service | owner/operator APIs | place detail/recommendation | MVP | External beverage ref only |
| `venue_inventory_items` | Availability and stock freshness | map-service | owner/operator/staff APIs | place detail/recommendation | MVP | Has confidence, `last_seen_at`, `expires_at`, revision |
| `venue_price_offers` | Price offers and validity | map-service | owner/operator APIs | place detail/recommendation | MVP | Has validity period, confidence, revision |
| `outdoor_spot_profiles` | Outdoor drinking-place profile | map-service | operator/field research | map/recommendation | MVP | `place_id` is PK/FK |
| `place_outbox_events` | Event/snapshot sync outbox | map-service | map-service write path | sync worker | MVP | Recommendation must consume via this/API, not DB tables |
| `route_estimate_cache` | Route/transit estimate cache | map-service or route component | future route worker | map/recommendation | Optional phase 2 | Not created intentionally |

## ERD-to-Migration Comparison

| Item | Expected | Actual | Status | Comment |
|---|---|---|---|---|
| PostGIS extension | `CREATE EXTENSION IF NOT EXISTS postgis` | Present in `001` | OK | Requires DB with PostGIS installed |
| Places location point | `geography(Point, 4326)` or `geometry(Point, 4326)` | `geography(Point, 4326)` | OK | Also stores lat/lng |
| Spatial index | GiST on `places.location` | `idx_places_location_gist` | OK | Candidate location GiST also exists |
| Lifecycle status | draft/active/hidden/temporarily_closed/closed/duplicate_merged/rejected/archived | `place_status` enum with all values | OK | Values are uppercase enum labels |
| Publication status | `publication_status`, `published_at` | Both present | OK | Public query partial index added |
| Recommendation eligibility | `recommendation_eligible` | Present | OK | Partial index added |
| Source tracking | source registry and source refs | `data_sources`, `place_source_refs` | OK | Source policy retained |
| Operator override support | separate override table | `place_overrides` | OK | Write logic not implemented |
| Owner claim support | claim table | `business_claims` | OK | Approval logic not implemented |
| Owner/manager role support | manager table with roles | `place_managers` | OK | Auth IDs text only |
| Sensitive change request flow | change request table | `place_change_requests` | OK | Approval API not implemented |
| Audit log | actor/action/target before/after | `place_audit_logs` | OK | Application append behavior still needed |
| Menu table | menu/signature support | `venue_menu_items` | OK | External beverage ref only |
| Inventory table | freshness/confidence/revision | `venue_inventory_items` | OK | Has `last_seen_at`, `expires_at`, `stock_confidence` |
| Price table | validity/confidence/revision | `venue_price_offers` | OK | Has `valid_from`, `valid_until`, `confidence` |
| Outdoor spot support | profile by `place_id` | `outdoor_spot_profiles` | OK | PK/FK to `places` |
| Outbox events | event payload/revision/status | `place_outbox_events` | OK | Consumer not implemented |
| Optional display tables | tags/media/hours/reports | Not created | Deferred | Intentional MVP defer |
| Route cache optionality | `route_estimate_cache` optional | Not created | Deferred | Keep phase 2+ |

## Boundary Validation

1. Cross-service DB FKs to auth-service: No. User IDs are `text`.
2. Cross-service DB FKs to recommendation-service: No. Beverage refs are `text`; no recommendation tables are referenced.
3. Recommendation-service directly owns place data: No. Migration creates map-service tables and an outbox for sync.
4. Admin Page directly writes DB: No implication in migration. Docs must continue to state API-only writes.
5. Kakao canonical bulk ingestion: No. `source_type = KAKAO` exists, but `source_policy` is explicit and no seed or ingestion logic exists.
6. Soft-delete/archive instead of hard-delete: Yes. `places.status` includes `CLOSED`, `DUPLICATE_MERGED`, `REJECTED`, `ARCHIVED`.
7. Auditability for admin/operator/owner writes: Table support exists via `place_audit_logs`; application write path must emit rows.
8. Freshness/TTL for inventory and price: Inventory supports `last_seen_at`, `expires_at`, `stock_confidence`; price supports `valid_from`, `valid_until`, `confidence`.

## Admin Permission Matrix

See [map-place-admin-permission-matrix.md](./map-place-admin-permission-matrix.md).

Default approval-required sensitive changes: business name, address, coordinates, business type, closure, reopening, ownership transfer, duplicate merge.

## API Draft

See [map-place-api-draft.md](./map-place-api-draft.md).

This is a contract draft only. Do not implement APIs from this handoff without a separate implementation task.

## Recommendation Sync Draft

See [map-place-recommendation-sync-draft.md](./map-place-recommendation-sync-draft.md).

The key rule is unchanged: recommendation-service consumes outbox events, internal APIs, or snapshots only. It must not query map-service tables directly.

## Data Ingestion Follow-ups

See [map-place-data-ingestion-followups.md](./map-place-data-ingestion-followups.md).

Public data, field research, owner input, and user reports flow through staging and review before becoming canonical. Kakao is realtime/restricted by default.

## Risks / Open Questions

| Category | Risk / Question | Current Position |
|---|---|---|
| Legal/Policy | Kakao data storage policy needs confirmation before persistence | Keep Kakao realtime/restricted unless explicitly approved |
| Data | Public data may be outdated, noisy, duplicated, or closed | Stage candidates and require review |
| Operations | Inventory and price freshness require operational discipline | Use `last_seen_at`, `expires_at`, confidence, and stale-data policy |
| Admin UX | Owner claims need fraud/abuse handling | Require evidence and operator approval |
| Recommendation | Recommendation quality depends on snapshot freshness | Implement robust outbox processing and lag monitoring |
| Engineering | Migration has not been dry-run on PostGIS locally | P0 verification before merge/deploy |
| Product | Optional hours/media/tags/reports are deferred | Decide phase 2 scope before public UX depends on them |
| Operations | Audit table exists but append-only enforcement is application-level | Implement audit middleware/service |
| Engineering | No down migrations exist | Decide migration rollback convention |
| Recommendation | Route/transit optimization is not in MVP schema | Keep route cache phase 2+ |

## Next Steps for Teammate

| Priority | Task | Owner | Expected Output | Acceptance Criteria |
|---|---|---|---|---|
| P0 | Verify migration can run on a clean local DB | Backend | Clean PostgreSQL+PostGIS dry-run result | All six migrations apply with `ON_ERROR_STOP=1` |
| P0 | Verify PostGIS extension and spatial index | Backend/DB | DB inspection notes | `postgis` exists and GiST indexes are present |
| P0 | Verify no cross-service FK exists | Backend/DB | Constraint audit | No FK to auth/recommendation/catalog/user tables |
| P0 | Verify lifecycle/status/check constraints | Backend/DB | Constraint audit | Required enum/check constraints exist |
| P1 | Implement map-service model layer | Backend | Models/repositories | Matches migration and ownership boundaries |
| P1 | Implement admin permission checks | Backend | Role policy module | Sensitive changes require approval |
| P1 | Implement audit logging middleware/service | Backend | Audit rows for writes | All write paths produce `place_audit_logs` |
| P1 | Implement place outbox event creation | Backend | Outbox writes in transactions | Published/updated/closed/menu/inventory/price changes emit events |
| P1 | Implement public map read APIs | Backend | Search/detail/nearby endpoints | Public results require active + published |
| P2 | Implement owner claim workflow | Backend/Admin | Claim submit/review APIs | Approved claim grants manager record |
| P2 | Implement menu/inventory/price owner APIs | Backend | Owner write APIs | Freshness/confidence/revision updated |
| P2 | Implement recommendation snapshot sync | Backend/Recommendation | Sync worker/read models | No direct map DB reads by recommendation-service |
| P2 | Implement import staging workflow | Backend/Data | Import/candidate/review pipeline | No direct publish from raw imports |
| P3 | Add route estimate cache | Backend/Product | Optional migration/API design | Only after route product scope is confirmed |
| P3 | Add outdoor spot enrichment | Data/Ops | Curated outdoor profiles | Operator-reviewed data only |
| P3 | Add data quality dashboard | Admin/Data | Review metrics | Tracks stale inventory, noisy imports, review backlog |

## Next Codex Prompt

See [map-place-next-codex-prompt.md](./map-place-next-codex-prompt.md).
