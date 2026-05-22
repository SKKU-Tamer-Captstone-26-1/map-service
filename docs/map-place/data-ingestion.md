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
