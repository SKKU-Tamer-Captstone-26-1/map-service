# Map/Place Data Ingestion

## Current Status

No production ingestion workflow is implemented in this repo.

The current safe artifacts are research-only:

- [../research/map-place-data-sources.md](../research/map-place-data-sources.md)
- [../research/map-place-source-policy-review.md](../research/map-place-source-policy-review.md)
- [../../data/bootstrap/source_registry_research.csv](../../data/bootstrap/source_registry_research.csv)

## Ingestion Boundary

Public/open data must enter candidate staging outside `map_view`.

```text
public/open source
  -> import batch
  -> import candidate
  -> dedupe/review
  -> canonical place owner
  -> publish to map_view
```

The following are not allowed:

- inserting public/open data directly into `map_view.markers`
- auto-approving candidates
- auto-publishing candidates
- storing Kakao Local/Map responses as canonical bootstrap data
- creating import/source/candidate tables in `map_view`

## Source Policy Defaults

| Source | Storage Policy | Default Target |
|---|---|---|
| 소상공인 상가정보 API | `storable` | `place_import_candidates` |
| 행안부 일반음식점/휴게음식점 | `storable` | `place_import_candidates` |
| 전국도시공원정보표준데이터 | `unknown_needs_review` | `needs_review` |
| Kakao Local API | `realtime_only` | `realtime_lookup` |
| 행안부 단란주점영업 | `storable` source, product risk | `excluded` |
| 행안부 유흥주점영업 | `storable` source, adult nightlife risk | `excluded` |

## Approved API Access

사용자가 2026-05-22에 아래 공공데이터포털 개발계정 활용신청 승인을 확인했습니다. 만료예정일은 2028-05-22입니다.

- 소상공인시장진흥공단_상가(상권)정보_API
- 행정안전부_식품_일반음식점 조회서비스
- 행정안전부_식품_휴게음식점 조회서비스
- 행정안전부_식품_단란주점영업 조회서비스
- 행정안전부_식품_유흥주점영업 조회서비스

승인은 API 호출 권한입니다. `map_view` 적재, canonical place 생성, 자동 승인, marker publish 권한으로 해석하지 않습니다.

## First Safe Implementation Later

The first ingestion-related implementation is a dry-run linter for the research CSVs and source policies:

```bash
python3 scripts/bootstrap/validate_research_package.py
```

It does not call external APIs, write DB rows, or create canonical places.

The next dry-run layer normalizes synthetic local sample files into candidate JSON:

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

The sample files under `data/samples/` are synthetic fixtures shaped like official source schemas. They are not production data.

The normalizer enforces source registry policy before emitting candidates:

- `storage_policy` must be `storable`
- `default_target` must be `place_import_candidates`
- `canonical_use_allowed` must be `false`
- Kakao sources are rejected

행정안전부 인허가 sample rows keep EPSG:5174 source coordinates in metadata and emit `location_status=needs_coordinate_transform`. Those rows must not be published until a WGS84 transform and location quality check are added.

## Real Dry-Run Fetch

The first real fetch path is limited to the approved 소상공인 상가정보 API.

```bash
python3 scripts/bootstrap/fetch_public_data_dry_run.py \
  --source-name "소상공인시장진흥공단_상가(상권)정보_API" \
  --div-id signguCd \
  --area-key 11440 \
  --inds-lcls-cd I2 \
  --num-rows 10
```

`I2` was confirmed against the approved API on 2026-05-22 as the large industry code for `음식`.

Requirements:

- `DATA_GO_KR_SERVICE_KEY` must be set in local `.env` or passed via `--service-key`
- real keys must not be committed
- generated raw output goes to ignored `data/raw/`
- generated normalized candidate output goes to ignored `data/normalized/`
- no DB writes, canonical place writes, or marker publishes occur

행정안전부 APIs are approved but remain blocked from real fetch implementation until their exact 공공데이터포털 API operation URLs are captured and EPSG:5174 conversion is added.
