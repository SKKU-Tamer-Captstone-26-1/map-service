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
| 단란주점/유흥주점 | `storable` source, product risk | `excluded` |

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
