# Local DB Rebaseline Runbook

## 목적

이 문서는 local/dev PostGIS DB를 `map_view` 전용 clean 상태로 다시 만드는 절차를 정리합니다.

현재 기본 개발 경로는 아래 migration set입니다.

```bash
python3 scripts/db/apply_migrations.py --migration-set map-view
python3 scripts/db/verify_map_view_schema.py --strict-clean-db
```

`map-view` set은 아래 파일만 적용합니다.

```text
migrations/007_create_map_view_minimal_schema.sql
migrations/008_seed_map_view_marker_layers.sql
```

`008`은 `map_view.marker_layers` 표시 설정만 넣는 idempotent seed입니다. canonical place, marker, public-data candidate를 넣지 않습니다.

## 현재 알려진 문제

기존 local DB에 과거 oversized migration이 이미 적용된 경우 `public` schema에 아래 계열 테이블이 남아 있을 수 있습니다.

```text
places
data_sources
place_import_candidates
business_claims
venue_menu_items
venue_inventory_items
venue_price_offers
place_outbox_events
```

이 상태에서도 `map_view` 자체 검증은 통과할 수 있지만, clean DB 검증은 실패해야 정상입니다.

```bash
python3 scripts/db/verify_map_view_schema.py --strict-clean-db
```

## 절대 자동 실행하지 않는 작업

아래 작업은 local/dev 전용이어도 데이터 삭제가 발생합니다. 사용자가 명시적으로 승인한 경우에만 실행합니다.

```text
DESTRUCTIVE_LOCAL_DB_REBASELINE
```

이 이름 없이 reset, drop, truncate, volume remove를 수행하지 않습니다.

## 승인 후 수동 절차

아래 절차는 local/dev DB 전용입니다. production 또는 shared DB에 사용하지 않습니다.

1. 현재 DB가 local compose DB인지 확인합니다.

```bash
docker ps --filter name=map-service-postgis-dev
```

2. 사용자에게 아래 작업명을 명시적으로 승인받습니다.

```text
DESTRUCTIVE_LOCAL_DB_REBASELINE
```

3. 승인 후 local compose DB와 named volume을 제거합니다.

```bash
docker compose -f docker-compose.db.yml down
docker volume rm map-service-dev_map_service_postgis_data
```

4. local DB를 다시 만들고 `map_view`만 적용합니다.

```bash
docker compose -f docker-compose.db.yml up -d db
python3 scripts/db/apply_migrations.py --migration-set map-view
python3 scripts/db/verify_map_view_schema.py --strict-clean-db
```

## 금지 사항

- production DB에 연결하지 않습니다.
- legacy public table을 자동 drop하지 않습니다.
- `map_view`에 import/source/candidate table을 만들지 않습니다.
- `admin_ops` rebaseline을 이 runbook에 섞지 않습니다.
- Kakao Local/Map API 응답을 canonical 또는 storable bootstrap data로 저장하지 않습니다.

## 성공 기준

- `map_view.marker_layers`, `map_view.markers`, `map_view.marker_publication_events`만 `map_view` app table로 존재합니다.
- `map_view.marker_layers`에 pre-deploy 기본 layer config가 존재합니다.
- `postgis`, `pgcrypto` extension이 존재합니다.
- `markers.location`은 `geography(Point,4326)`입니다.
- `idx_markers_location_gist`가 GiST index입니다.
- `map_view` FK는 내부 FK만 존재합니다.
- `verify_map_view_schema.py --strict-clean-db`가 통과합니다.
