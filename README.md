# map-service

Minimal `map_view` database draft for the map marker read model.

The current direction is:

```text
map_view
= what the map UI needs to draw published markers

admin_ops
= canonical place/admin operations DB, handled separately
```

This repository is being cleaned around the minimal `map_view` direction. Legacy data-ingestion/bootstrap docs and scripts from the previous oversized map/place design have been removed from the working tree.

## Current Status
로컬 백엔드 기반은 준비되었습니다.

현재 준비된 것:

- 로컬 PostGIS `map_view` read model
- marker layer seed: `bar`, `pub`, `liquor_shop`, `outdoor_spot`, `restaurant`, `convenience_store`, `other`
- read-only map API: health, layer list, bbox marker query
- whole-Seoul marker paging through `limit` + `offset`
- official SMBA public API based local preview markers for Seoul bar/pub/liquor shop data
- source policy docs: public data is evidence/preview, Kakao is realtime only, canonical requires review/publish workflow

현재 로컬 DB preview marker 규모:

```text
bar         10,193
pub          2,643
liquor_shop    393
total       13,229
```

중요한 경계:

- 이 13,229개 row는 프론트엔드 지도 개발을 위한 preview marker입니다.
- 아직 canonical place가 아닙니다.
- production publish도 아닙니다.
- 실제 서비스 데이터로 확정하려면 candidate staging, dedupe, review, approval, publish workflow가 필요합니다.

다음 큰 작업은 이 API를 사용하는 실제 frontend map 구현입니다.

## 지금까지 한 작업

이 저장소는 현재 프론트엔드 지도 구현을 시작할 수 있는 최소 백엔드 기반까지 정리되어 있습니다.

완료한 범위:

- `map_view` 전용 PostGIS read model을 정리했습니다.
- 기본 migration set을 `map-view`로 고정해 legacy public place/admin/import table을 기본 경로에서 제외했습니다.
- pre-deploy용 marker layer seed를 추가했습니다.
- strict schema verifier와 read-only pre-deploy check를 추가했습니다.
- 공공데이터 source policy, category mapping, MVP data plan 초안을 정리했습니다.
- Kakao는 realtime/display/operator verification only로 고정했습니다.
- 소상공인/행안부 공공데이터는 canonical place가 아니라 candidate evidence로만 다루도록 문서화했습니다.
- 로컬 frontend 개발용 synthetic `map_view.markers` seed를 추가했습니다.
- 프론트엔드가 바로 붙을 수 있는 read-only map API를 추가했습니다.
- 서울 전체 바/펍/주류판매점 로컬 preview marker seed를 추가했습니다.

현재 API 범위:

```text
GET /healthz
GET /v1/map/layers
GET /v1/map/markers?bbox=126.88,37.53,126.97,37.59&layers=bar,pub&limit=200&offset=0
```

아직 하지 않은 것:

- canonical place DB 구현
- candidate staging DB 구현
- publish workflow 구현
- Kakao ingestion 또는 Kakao 응답 저장
- 공공데이터를 canonical place 또는 production `map_view`로 직접 적재
- production DB 작업

즉, 현재 상태는 `map_view` read model + 안전한 source policy + read-only map API + 로컬 preview marker까지 완료된 단계입니다. 다음 큰 작업은 이 API를 사용하는 실제 frontend map 구현입니다.

### Canonical 의미

이 프로젝트에서 `canonical`은 서비스가 최종적으로 신뢰하고 운영 기준으로 삼는 확정 장소 데이터를 뜻합니다. 예를 들어 canonical place는 운영자가 검토하고 승인한 장소명, 주소, 좌표, 카테고리, 표시 여부를 가진 원본 record입니다.

`map_view`는 canonical DB가 아닙니다. `map_view`는 프론트엔드 지도를 빠르게 그리기 위한 read model입니다. 그래서 `map_view.markers`에 있는 `label`, `location`, `layer_code`는 사용자가 직접 수정하는 원본 데이터가 아니라, 나중에 canonical place 또는 publish workflow에서 승인된 값을 복사해 온 표시용 projection이어야 합니다.

공공데이터와 Kakao도 canonical이 아닙니다.

- 공공데이터는 후보 근거(candidate evidence)로만 사용합니다.
- Kakao는 realtime lookup, 지도 표시, 운영자 검증 보조로만 사용합니다.
- 공공데이터나 Kakao 응답을 바로 canonical place로 만들지 않습니다.
- canonical 승격은 별도의 candidate staging, dedupe, review, approval, publish workflow가 생긴 뒤에만 가능합니다.

따라서 현재 단계에서 만든 dev marker seed와 read-only map API는 프론트엔드 개발용 기반입니다. 이것은 실제 장소 원본을 확정했다는 의미가 아닙니다.

즉, 데이터를 모으고 검수를 마친 애들이 canonical이 되는 것입니다.

## Repository Layout

```text
migrations/                    PostgreSQL schema migrations, including additive map_view migration
scripts/db/                    Local DB apply/verify helpers
docs/README.md                 Docs index
docs/architecture.md           Service/database boundary overview
docs/map-place/                Map/place ownership, DB, ERD, ingestion boundary
docs/integrations/             External API policy notes
docs/research/                 Public/open data source research drafts
docs/runbooks/                 Local operational runbooks
data/bootstrap/                Research-only bootstrap CSV drafts
data/samples/                  Synthetic public-data-shaped sample fixtures
docs/handoff/                  Handoff docs for map_view and legacy map/place drafts
map_view.dbml                  Source of truth for the minimal map_view ERD
map_view.md                    Korean explanation of the minimal map_view design
```

Some legacy migration files can still exist until DB history is explicitly rebaselined. Do not treat those old public place/admin/import tables as the desired `map_view` schema.

## Local DB Quick Start

```bash
cp .env.example .env
python3 -m pip install -r requirements.txt
docker compose -f docker-compose.db.yml up -d db
python3 scripts/db/apply_migrations.py
python3 scripts/db/verify_map_view_schema.py --strict-clean-db
```

`apply_migrations.py` defaults to the `map-view` migration set. That set applies only the minimal read-model migration:

```text
migrations/007_create_map_view_minimal_schema.sql
migrations/008_seed_map_view_marker_layers.sql
```

This is the expected clean local/dev and pre-deploy readiness path. It does not apply the older public place/admin/import migrations. The seed migration inserts only `map_view.marker_layers` display configuration; it does not insert places, candidates, markers, or public data.

Dry-run the default path:

```bash
python3 scripts/db/apply_migrations.py --dry-run
```

Run the read-only pre-deploy database gate:

```bash
python3 scripts/db/predeploy_check.py
```

This checks the `map-view` migration plan, validates research source policy files, and verifies the local DB with `--strict-clean-db`.

The old full replay is still available only when explicitly requested:

```bash
python3 scripts/db/apply_migrations.py --migration-set legacy-full --dry-run
```

`legacy-full` replays all files under `migrations/` in lexical order and will create deprecated public place/admin/import tables. Use it only for historical investigation until a proper migration runner or rebaseline is introduced.

`--strict-clean-db` should pass on a clean `map_view`-only database. It will fail on an older local DB if oversized public tables were already applied. See [docs/runbooks/local-db-rebaseline.md](docs/runbooks/local-db-rebaseline.md) before any local reset.

## Bootstrap Research Validation

Validate the research-only source policy CSVs:

```bash
python3 scripts/bootstrap/validate_research_package.py
```

This command does not call external APIs and does not write to the database.

Run the bootstrap policy regression tests:

```bash
python3 -m unittest tests.test_bootstrap_policy tests.test_map_read_api tests.test_seoul_preview_seed
```

These tests keep Kakao realtime-only, unknown sources review-only, restricted adult nightlife excluded, ambiguous pub/bar categories out of automatic category promotion, and the read-only map API response contract stable.

Dry-run normalize a local sample file into candidate JSON:

```bash
python3 scripts/bootstrap/normalize_public_data_sample.py \
  --source-name "소상공인시장진흥공단_상가(상권)정보_API" \
  --input data/samples/smba_store_sample.csv
```

```bash
python3 scripts/bootstrap/normalize_public_data_sample.py \
  --source-name "행정안전부_식품_일반음식점 조회서비스" \
  --input data/samples/mois_food_general_sample.csv
```

The sample normalizer reads local fixture CSVs only. It does not call external APIs, does not write to the database, and does not create canonical places.

Fetch a small real public-data page into ignored dry-run files:

```bash
python3 scripts/bootstrap/fetch_public_data_dry_run.py \
  --source-name "소상공인시장진흥공단_상가(상권)정보_API" \
  --div-id signguCd \
  --area-key 11440 \
  --inds-lcls-cd I2 \
  --num-rows 10
```

`I2` is the confirmed 소상공인 large industry code for `음식`. The fetcher writes raw responses under `data/raw/` and normalized candidate JSON under `data/normalized/`. Both directories are ignored by Git. It does not write to PostGIS and does not publish markers.

## Read-Only Map API

Run the local read-only map API for frontend development:

```bash
python3 scripts/db/apply_migrations.py
python3 scripts/db/seed_dev_map_markers.py --apply
python3 -m scripts.api.map_read_api
```

Default URL:

```text
http://127.0.0.1:8088
```

Useful endpoints:

```text
GET /healthz
GET /v1/map/layers
GET /v1/map/markers?bbox=126.88,37.53,126.97,37.59&layers=bar,pub&limit=200&offset=0
```

The API reads only from `map_view`. The dev seed inserts synthetic local `map_view.markers` fixtures only; it does not insert canonical places, public-data candidates, or Kakao data.

## Seoul Preview Markers

로컬 프론트엔드 지도에서 서울 전체 바, 펍, 주류 판매점을 확인하려면 승인된 소상공인시장진흥공단 API key가 들어 있는 `.env`를 준비한 뒤 아래 명령을 실행합니다.

```bash
python3 scripts/db/seed_seoul_preview_markers_from_smba.py \
  --all-pages \
  --replace-preview \
  --apply \
  --ack-public-data-preview
```

이 명령은 소상공인시장진흥공단 상가 API의 서울특별시(`ctprvnCd=11`) 데이터만 사용합니다.

2026-05-23 로컬 실행 결과:

```text
I21104 요리 주점     -> bar          10,193
I21103 생맥주 전문   -> pub           2,643
G20602 주류 소매업   -> liquor_shop     393
total                              13,229
```

현재 로컬 preview에 포함하는 source category:

- `I21103` 생맥주 전문 -> `pub`
- `I21104` 요리 주점 -> `bar`
- `G20602` 주류 소매업 -> `liquor_shop`

`유흥` category token이 들어간 row는 제외합니다. 그래서 `I21101` 일반 유흥 주점, `I21102` 무도 유흥 주점은 로컬 preview에도 넣지 않습니다.

이 preview seed는 `map_view.markers`에 row를 넣지만 canonical publish가 아닙니다. 모든 row는 `filter_json.source=smba_public_data_preview`, `filter_json.preview_only=true`, `filter_json.canonical=false`, `filter_json.review_required=true`로 표시됩니다. 즉 프론트엔드 지도를 실제 서울 데이터 크기로 그려보기 위한 임시 표시 데이터입니다.

서울 전체를 한 번에 볼 때는 API limit이 있으므로 `offset`으로 page를 넘겨야 합니다.

```text
GET /v1/map/markers?bbox=126.70,37.40,127.20,37.75&layers=bar,pub,liquor_shop&limit=500&offset=0
GET /v1/map/markers?bbox=126.70,37.40,127.20,37.75&layers=bar,pub,liquor_shop&limit=500&offset=500
```

## Production API (Cloud Run)

배포된 read-only API 엔드포인트:

```
Base URL: https://map-service-44649239380.asia-northeast3.run.app
```

```text
GET /healthz
GET /v1/map/layers
GET /v1/map/markers?bbox=minLon,minLat,maxLon,maxLat&layers=bar,pub&limit=200&offset=0
GET /v1/map/search?q=검색어
```

인프라:
- Cloud Run (asia-northeast3, min-instances=0, max-instances=3)
- Cloud SQL PostgreSQL 16 + PostGIS (`on-the-block-2026:asia-northeast3:map-service-db`)
- GCS 이미지 버킷: `gs://on-the-block-place-media/venues/{place_id}/`

로컬 개발은 기존 `run-client-map-dev.ps1` 사용. Cloud Run 연결은 `run-client-map-prod.ps1` 사용.

---

## 외부 서비스 연동 가이드

### Flutter 클라이언트

REST API를 직접 호출합니다. DB 직접 접근 금지.

```
GET /v1/map/markers  → 지도 마커 표시 (bbox 기반)
GET /v1/map/search   → 장소 텍스트 검색
```

marker 응답의 `filter_json` 기반 필드:

| 필드 | 타입 | 내용 |
|---|---|---|
| `imageUrls` | `string[]` | 장소 사진 URL 목록 (최대 10장) |
| `address` | `string` | 도로명 주소 (시도 접두어 제거) |
| `hours` | `string` | 영업시간 표시용 (예: `19:00 - 02:00`) |
| `isOpen` | `bool?` | 서버 KST 기준 실시간 계산 |
| `rating` | `number?` | 평점 (bar/pub만, liquor_shop/outdoor 없음) |
| `reviewCount` | `int?` | 리뷰 수 (bar/pub만) |
| `menu` | `object[]` | 메뉴 항목 — bar/pub 전용 |
| `inventory` | `object[]` | 재고 항목 — liquor_shop 전용 |

### 관리자 웹 (Admin Web)

**현재 (Write API 미구현):** `scripts/tools/patch_canonical_filter_json.py` 스크립트로 직접 DB 패치.

**향후 Write API 구현 예정 엔드포인트:**

```
PATCH /v1/map/markers/{id}           → 영업시간·메뉴·재고 수정
POST  /v1/map/markers/{id}/images/upload-url  → GCS Signed URL 발급
PATCH /v1/map/markers/{id}/images    → image_urls 목록 업데이트
PATCH /v1/map/markers/{id}/visibility → visible ↔ hidden 전환
```

**이미지 업로드 흐름 (Write API 구현 후):**

```
1. Admin Web → POST /v1/map/markers/{id}/images/upload-url
   ← GCS Signed URL 반환

2. Admin Web → GCS 직접 업로드 (map-service 거치지 않음)
   gs://on-the-block-place-media/venues/{place_id}/{uuid}.jpg

3. Admin Web → PATCH /v1/map/markers/{id}/images
   body: { "image_urls": ["https://storage.googleapis.com/..."] }
   ← filter_json.image_urls 업데이트
```

**제약:**
- Admin Web은 map-service DB에 직접 접근하지 않습니다.
- 모든 쓰기는 Write API를 통해서만 수행합니다.

### 추천 시스템 (Recommendation Service)

map-service DB에 직접 접근하지 않습니다. REST API 또는 이벤트 기반 동기화만 허용됩니다.

**현재 구현된 연동 방식:**

`scripts/seed_venue_inventory.py` — 로컬 개발용 단방향 시드:
- map-service DB에서 `visibility=visible` liquor_shop 마커 조회
- recommendation-service `venue_snapshots` + `venue_inventory_snapshots` 생성
- `inventory.beverage_id` → recommendation-service `beverage_items.id` (canonical 음료 UUID)

**향후 동기화 방식 (계획):**

```
map-service
  └─ 마커 데이터 변경 시 이벤트 발행 (map_view.marker_publication_events)
       ↓
recommendation-service
  └─ MapSnapshotImportService.import_snapshot_event()
       └─ venue_snapshots 업데이트
       └─ venue_inventory_snapshots 업데이트 (beverage_id 참조)
```

**재고 데이터 구조 (liquor_shop filter_json.inventory):**

```json
[
  {
    "beverage_id": "846aab49-...",
    "name_ko": "더 맥캘란 12년 더블 캐스크",
    "name_en": "The Macallan 12 Years Double Cask",
    "price_krw": 128000
  }
]
```

`beverage_id`는 recommendation-service `beverage_items.id` (canonical UUID)를 참조합니다. 동일한 술이 여러 리쿼샵에 있어도 `beverage_id`가 동일하므로 크로스 벤뉴 검색/비교가 가능합니다.

**제약:**
- recommendation-service는 map-service DB에 직접 읽기/쓰기 금지.
- recommendation-service가 보유한 venue 데이터는 map-service snapshot의 파생(derived) 데이터이며 canonical이 아닙니다.

---

## Canonical 마커 데이터 관리

현재 canonical(visibility=visible) 마커 10개의 데이터는 `scripts/tools/patch_canonical_filter_json.py`가 단일 소스입니다.

DB 초기화 또는 Cloud SQL 재배포 후 데이터 복원:

```bash
python -m scripts.tools.patch_canonical_filter_json --apply
```

Dry-run 확인:

```bash
python -m scripts.tools.patch_canonical_filter_json
```

`filter_json` 구조 요약:

| 레이어 | 필드 |
|---|---|
| 공통 | `open_time`, `close_time`, `image_urls`, `description`, `road_address` |
| bar / pub | + `menu: [{name, desc, price_krw}]` |
| liquor_shop | + `inventory: [{beverage_id, name_ko, name_en, price_krw}]` |

---

## Data Bootstrap Direction

Research artifacts under `docs/research/` and `data/bootstrap/` are proposals only. Public/open data can enter candidate staging for later admin review, but must not be inserted directly into canonical places or `map_view`.

Kakao Local/Map API data is `realtime_only` unless separate legal or partnership approval is documented. Do not bulk-ingest Kakao API responses as canonical or storable place data.

## Safety Notes

- `map_view` stores marker read-model data only.
- Do not put admin workflow, canonical place details, menu, inventory, price, audit, or import staging tables in `map_view`.
- Do not create a DB FK from `map_view.markers.place_ref` to `admin_ops.places.id`.
- Do not drop or reset legacy tables until local/dev cleanup is explicitly approved.
- Do not bulk-ingest Kakao Local/Map API data as canonical place data.
- Do not insert public/open data directly into production `map_view`; the SMBA Seoul preview seed is local-only, explicitly acknowledged, non-canonical marker data.
- Do not publish markers without an explicit reviewed canonical source.
- Do not let Admin Page write directly to the database.
- Do not let recommendation-service directly read or write map-service tables.
