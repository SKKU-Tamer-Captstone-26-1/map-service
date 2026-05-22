# map-service

Map/place service database and ingestion workflow draft.

## Repository Layout

```text
migrations/                    PostgreSQL schema migrations for map/place DB
docs/                          Planning, ERD, handoff, and data workflow docs
docs/handoff/                  Team handoff packages and next-task prompts
docs/map-place/                Map/place-specific follow-up docs
scripts/map_place_ingestion/   Safe dry-run-first CSV ingestion utilities
tests/                         Unit tests for ingestion utilities
map_place_data_bootstrap_v0_3/ Extracted bootstrap data package
map_place_service_erd_v0_1.dbml DBML source for the current ERD draft
```

## Safety Notes

- Public/operator/bootstrap data must go to staging/review first.
- Do not bulk-ingest Kakao Local/Map API data as canonical place data.
- Do not let Admin Page write directly to the database.
- Do not let recommendation-service directly read or write map-service tables.
