# Map View Refactor From Old Map DB

## 현재 상태

이 repo에는 이전에 만든 oversized map/place 설계의 흔적이 있었습니다. 이번 cleanup에서 오래된 handoff docs, bootstrap package, ingestion scripts/tests, old oversized ERD는 제거했습니다.

현재 전략은 여전히 **Two-stage**입니다.

1. `map_view` minimal read model을 비파괴적으로 추가한다.
2. repo의 오래된 docs/files는 제거한다.
3. DB migration history pruning 또는 local/dev reset은 별도 승인 후 진행한다.

이번 단계에서는 table drop, database reset, 적용된 DB의 old public table 삭제를 하지 않습니다.

## Existing Tables Classification

| Existing table | Classification | map_view action | Notes |
|---|---|---|---|
| `places` | `admin_ops`로 이동 | deprecated in map_view | canonical place 원본 |
| `place_source_refs` | `admin_ops`로 이동 | deprecated in map_view | source reference 원본 |
| `business_claims` | `admin_ops`로 이동 | deprecated in map_view | owner claim workflow |
| `place_managers` | `admin_ops`로 이동 | deprecated in map_view | owner/manager 권한 |
| `place_change_requests` | `admin_ops`로 이동 | deprecated in map_view | 민감 변경 요청 |
| `place_overrides` | `admin_ops`로 이동 | deprecated in map_view | operator override |
| `place_audit_logs` | `admin_ops`로 이동 | deprecated in map_view | canonical write audit |
| `venue_menu_items` | `admin_ops`로 이동 | deprecated in map_view | 메뉴 원본 |
| `venue_inventory_items` | `admin_ops`로 이동 | deprecated in map_view | 재고 원본 |
| `venue_price_offers` | `admin_ops`로 이동 | deprecated in map_view | 가격 원본 |
| `outdoor_spot_profiles` | `admin_ops`로 이동 | deprecated in map_view | 야외 장소 상세 |
| `place_outbox_events` | `admin_ops` publish/outbox | deprecated in map_view | map_view는 `marker_publication_events`만 보유 |
| `data_sources` | ingest/admin workflow | deprecated in map_view | source registry |
| `place_import_batches` | ingest/admin workflow | deprecated in map_view | import staging |
| `place_import_candidates` | ingest/admin workflow | deprecated in map_view | candidate staging |
| `place_dedupe_matches` | ingest/admin workflow | deprecated in map_view | dedupe review |
| `place_review_tasks` | ingest/admin workflow | deprecated in map_view | operator review queue |

## map_view Target Tables

최종 `map_view` schema는 아래 3개 app table만 가져야 합니다.

```text
map_view.marker_layers
map_view.markers
map_view.marker_publication_events
```

`map_view` 안에 아래 성격의 table이 있으면 mismatch입니다.

```text
places
business claims
managers
change requests
audit logs
import staging
menu
inventory
price
place outbox
```

## Migration Strategy

현재 migration strategy는 안전성을 우선합니다.

```text
migrations/007_create_map_view_minimal_schema.sql
migrations/008_seed_map_view_marker_layers.sql
```

이 migration set은 다음만 생성하거나 설정합니다.

```text
map_view schema
map_view enum types
map_view.marker_layers
map_view.markers
map_view.marker_publication_events
internal map_view FKs
map_view indexes
map_view.marker_layers 기본 표시 설정
```

아래는 아직 하지 않습니다.

```text
DROP TABLE
TRUNCATE
database reset
admin_ops schema 생성
admin_ops migration 생성
public oversized table 이동
old migration history 강제 rebase
```

## Cleanup Completed

다음 repo artifact는 map_view 방향과 맞지 않아 제거했습니다.

| Path / Area | Action | Reason |
|---|---|---|
| `docs/handoff/map-place-*` | removed | oversized map/place handoff |
| `docs/codex_*`, `docs/docs_map_place_*` | removed | old prompt/ERD/data ingestion drafts |
| `docs/map-place/` | removed | old ingestion data-quality draft |
| `scripts/map_place_ingestion/` | removed | old staging/import workflow |
| `tests/test_map_place_ingestion.py` | removed | tests for removed ingestion scripts |
| `map_place_data_bootstrap_v0_3/` | removed | old bootstrap data package |
| `map_place_service_erd_v0_1.dbml` | removed | old oversized ERD |

## Still Needs Explicit Approval

아래 항목은 더 위험도가 높아 이번 cleanup에서 강제 처리하지 않습니다.

| Area | Reason |
|---|---|
| legacy migration files | DB evolution history와 clean replay 전략을 확정해야 함 |
| already-applied local DB old public tables | 실제 DB drop/reset은 명시 승인 필요 |
| admin_ops schema | 별도 task |

## Recommended Next Cleanup Task

local/dev 전용 DB cleanup 또는 migration rebaseline을 승인받은 뒤 별도 작업으로 진행합니다.

Acceptance criteria:

```text
- clean local DB reset 승인 확인
- map_view-only migration baseline 확정
- old public app tables 제거 또는 새 local DB로 재생성
- README와 verifier가 map_view-only 기준으로 정리
- admin_ops는 별도 repo/schema task로 분리
```
