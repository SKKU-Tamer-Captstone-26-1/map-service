# Map / Place Ingestion Schema Mapping

현재 migration 기준으로 bootstrap/import workflow가 사용할 conceptual table과 실제 table을 매핑한 문서입니다.

| Conceptual Table | Actual Table | Status | Notes |
|---|---|---|---|
| `data_sources` | `data_sources` | OK | `source_code`는 전용 컬럼이 없으므로 `metadata_json.source_code`에 저장합니다. |
| `place_import_batches` | `place_import_batches` | OK | CSV import 실행 단위입니다. |
| `place_import_candidates` | `place_import_candidates` | OK | canonical `places`로 직접 넣지 않고 후보를 저장합니다. |
| `place_dedupe_matches` | `place_dedupe_matches` | OK | 현재 scripts는 dedupe utility만 제공하고 DB insert는 follow-up입니다. |
| `place_review_tasks` | `place_review_tasks` | OK | staging apply 시 후보별 review task를 생성합니다. |
| `places` | `places` | OK | import scripts는 기본적으로 직접 insert하지 않습니다. |
| `place_source_refs` | `place_source_refs` | OK | publish-approved workflow에서 생성해야 합니다. 현재 import scripts는 생성하지 않습니다. |
| `business_claims` | `business_claims` | OK | CSV ingestion 대상 아님. |
| `place_managers` | `place_managers` | OK | owner CSV 권한 확인에 필요하지만 현재 CLI에는 auth context가 없습니다. |
| `place_change_requests` | `place_change_requests` | OK | 민감 변경 요청용. 현재 seed import 대상 아님. |
| `place_overrides` | `place_overrides` | OK | operator override용. 현재 seed import 대상 아님. |
| `place_audit_logs` | `place_audit_logs` | OK | table은 있으나 import scripts의 canonical write가 막혀 있어 아직 쓰지 않습니다. |
| `place_reports` | None | Deferred | optional phase 2로 migration에 없습니다. |
| `venue_menu_items` | `venue_menu_items` | OK | owner menu CSV는 dry-run validation만 지원합니다. canonical apply는 audit/outbox 구현 후. |
| `venue_inventory_items` | `venue_inventory_items` | OK | owner inventory CSV는 dry-run validation만 지원합니다. |
| `venue_price_offers` | `venue_price_offers` | OK | owner price CSV는 dry-run validation만 지원합니다. |
| `outdoor_spot_profiles` | `outdoor_spot_profiles` | OK | publish 후 operator-curated enrichment에서 사용해야 합니다. seed 후보 import는 staging only입니다. |
| `place_outbox_events` | `place_outbox_events` | OK | publish-approved workflow에서 생성해야 합니다. 현재 staging import는 생성하지 않습니다. |
| `tags` | None | Deferred | `seed_basic_tags.sql`는 현재 migration과 맞지 않습니다. tags table 추가 후 사용해야 합니다. |
| `place_tags` | None | Deferred | optional phase 2입니다. |

## Important Mappings

| CSV Field | Migration Field | Notes |
|---|---|---|
| `source_code` | `data_sources.metadata_json->>'source_code'` | 전용 컬럼이 없어서 metadata에 저장/조회합니다. |
| `source_policy` | `data_sources.source_policy`, `place_import_candidates.source_policy` | aliases are normalized to DB enum values. |
| `canonical_name` | `place_import_candidates.raw_payload_json.canonical_name` | 후보 table에 canonical name 전용 컬럼이 없어 raw payload에 보존합니다. |
| `normalized_name` | `place_import_candidates.normalized_name` | 없으면 importer가 normalize합니다. |
| `road_address` / `address` | `place_import_candidates.normalized_address` and raw payload | canonical address는 publish 단계에서 결정합니다. |
| `lat` / `lng` | `latitude`, `longitude`, `location` | apply 시 좌표가 있으면 PostGIS point도 생성합니다. |
| `geocode_required` | `metadata_json.geocode_required` | 전용 컬럼이 없어 metadata에 저장합니다. |
| `review_status=needs_review` | `review_status=PENDING` | DB enum에 `NEEDS_REVIEW`가 없어서 pending review로 매핑합니다. |

## Known Gaps

- `tags` and `place_tags` are deferred, so `map_place_data_bootstrap_v0_3/sql/seed_basic_tags.sql` must not be run yet.
- publish-approved workflow does not exist yet. It must create/update `places`, `place_source_refs`, `place_audit_logs`, and `place_outbox_events` in one reviewed flow.
- owner menu/inventory/price CLI apply is intentionally blocked until permission, audit, and outbox behavior are implemented.
