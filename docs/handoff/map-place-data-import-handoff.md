# Map / Place Data Import Handoff

## TL;DR

bootstrap package를 기반으로 안전한 dry-run-first import workflow를 추가했습니다.

현재 지원되는 것은 다음입니다.

- bootstrap package 구조 검증.
- `source_registry.csv` 검증 및 `data_sources` apply-gated upsert.
- 한강공원 outdoor spot 후보 dry-run 및 staging apply.
- operator/public CSV 후보 dry-run 및 staging apply.
- owner menu/inventory/price CSV dry-run validation.
- normalization, category mapping, quality rules, deterministic dedupe utility.

현재 지원하지 않는 것은 다음입니다.

- Kakao bulk ingestion.
- public data direct publish to `places`.
- canonical publish workflow.
- owner menu/inventory/price canonical apply.
- recommendation scoring.
- Admin UI.

## Bootstrap Package Used

Path used:

```text
map_place_data_bootstrap_v0_3/
```

The package contains the expected `manifest.json`, `data/`, `templates/`, `docs/`, `sql/`, and `codex/` files.

## What Was Implemented

| Area | Implemented |
|---|---|
| Package validation | `validate_bootstrap_package.py` |
| Source registry import | `import_source_registry.py` |
| Outdoor spot candidates | `import_outdoor_spot_candidates.py` |
| Operator place seed | `import_operator_place_seed.py` |
| Public store/license candidates | `import_public_store_candidates.py` |
| Owner menu validation | `import_owner_menu_items.py` |
| Owner inventory validation | `import_owner_inventory_items.py` |
| Owner price validation | `import_owner_price_offers.py` |
| Normalization | `normalize.py` |
| Category mapping | `category_mapping.py` |
| Quality rules | `quality_rules.py` |
| Dedupe scoring | `dedupe.py` |
| Tests | `tests/test_map_place_ingestion.py` |

## What Was Not Implemented

- No real data was imported during this task.
- No production DB write was run.
- No canonical `places` publish was implemented.
- No Kakao API call or Kakao ingestion was implemented.
- No new migration was created.
- No existing migration was modified.
- No cross-service DB foreign key was introduced.

## Safe Flow

```text
source CSV
  -> package/script validation
  -> place_import_batches
  -> place_import_candidates
  -> normalization metadata
  -> review task
  -> operator review
  -> future publish-approved workflow
  -> places / place_source_refs / audit_logs / outbox_events
```

## Kakao Exclusion

Kakao Local/Map API is excluded from canonical ingestion.

The source registry command rejects `source_type=KAKAO` with `source_policy=STORABLE`.

Allowed future Kakao usage remains limited to realtime lookup, map display support, Kakao map links, and operator verification support.

## Staging Apply Requirements

Staging apply commands require:

- `--apply`
- `--database-url`, `DATABASE_URL`, or `MAP_SERVICE_DATABASE_URL`
- `psycopg` or `psycopg2` installed
- migrations already applied to PostgreSQL with PostGIS

Only these workflows write to DB:

- `import_source_registry.py` -> `data_sources`
- `import_outdoor_spot_candidates.py` -> staging/review tables
- `import_operator_place_seed.py` -> staging/review tables
- `import_public_store_candidates.py` -> staging/review tables

## Owner Menu / Inventory / Price

Owner CSV commands validate only.

Reason:

- The repo does not yet have auth context.
- The repo does not yet have service-level manager permission checks.
- Canonical writes should create audit logs and outbox events.
- Writing these tables directly from CLI would bypass intended service behavior.

## Production Readiness Checklist

- Run all migrations on clean PostgreSQL + PostGIS.
- Apply `source_registry.csv` to a disposable DB.
- Apply outdoor spot candidates to staging in a disposable DB.
- Confirm no rows are inserted into `places` by staging imports.
- Confirm review tasks are created for candidates.
- Implement publish-approved workflow separately.
- Implement audit/outbox behavior before any canonical write CLI.
- Review Kakao/legal policy before any persistence.

## Related Docs

- [Schema mapping](./map-place-ingestion-schema-mapping.md)
- [Commands](./map-place-data-import-commands.md)
- [Data quality rules](../map-place/data-quality-rules.md)
- [Previous DB handoff](./map-place-db-handoff.md)
