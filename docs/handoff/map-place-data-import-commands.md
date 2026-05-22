# Map / Place Data Import Commands

모든 명령은 repo root에서 `python3 -m` 형태로 실행합니다.

## 1. Bootstrap Package Validation

```bash
python3 -m scripts.map_place_ingestion.validate_bootstrap_package
```

확인 항목:

- package root exists.
- `manifest.json` exists.
- `data/source_registry.csv` exists.
- `data/seoul_hangang_outdoor_spot_seed_candidates.csv` exists.
- `data/category_mapping_seed.csv` exists.
- `data/data_quality_rules.csv` exists.
- `templates/` exists.
- `sql/seed_data_sources.sql` exists.
- `sql/seed_basic_tags.sql` exists.

## 2. Source Registry Dry-run

```bash
python3 -m scripts.map_place_ingestion.import_source_registry \
  --input map_place_data_bootstrap_v0_3/data/source_registry.csv
```

동작:

- `source_type`, `source_policy`를 migration enum 값으로 normalize합니다.
- `KAKAO + STORABLE`은 reject합니다.
- `PUBLIC_PAGE`는 현재 schema에 맞춰 `PUBLIC_DATA`로 매핑합니다.
- `STORABLE_WITH_ATTRIBUTION`은 `STORABLE`로 매핑하고 license metadata를 보존합니다.
- dry-run은 DB에 쓰지 않습니다.

Apply:

```bash
python3 -m scripts.map_place_ingestion.import_source_registry \
  --input map_place_data_bootstrap_v0_3/data/source_registry.csv \
  --apply \
  --database-url "$DATABASE_URL"
```

`--apply`는 `data_sources`에 upsert합니다. `source_code`는 `metadata_json.source_code`로 저장합니다.

## 3. Outdoor Spot Candidate Dry-run

```bash
python3 -m scripts.map_place_ingestion.import_outdoor_spot_candidates \
  --input map_place_data_bootstrap_v0_3/data/seoul_hangang_outdoor_spot_seed_candidates.csv
```

동작:

- 한강공원 후보 11개를 staging 후보로 검증합니다.
- 좌표가 없으면 `metadata_json.geocode_required = true`로 표시합니다.
- `review_status=needs_review`는 DB enum에 맞춰 `PENDING`으로 매핑합니다.
- canonical `places`는 생성하지 않습니다.

Apply:

```bash
python3 -m scripts.map_place_ingestion.import_outdoor_spot_candidates \
  --input map_place_data_bootstrap_v0_3/data/seoul_hangang_outdoor_spot_seed_candidates.csv \
  --apply \
  --database-url "$DATABASE_URL"
```

`--apply`는 `place_import_batches`, `place_import_candidates`, `place_review_tasks`에만 씁니다.

## 4. Operator Place Seed

```bash
python3 -m scripts.map_place_ingestion.import_operator_place_seed \
  --input operator_place_seed.csv \
  --source-code OPERATOR_FIELD_RESEARCH
```

검증:

- name required.
- place_type required.
- address or coordinates required.
- coordinates must be valid if provided.
- source must be `OPERATOR` or `FIELD_RESEARCH`.
- `review_status=approved`가 있어도 자동 publish하지 않습니다.

Apply는 staging tables only입니다.

## 5. Public Store Candidate Import

SEMAS/store data:

```bash
python3 -m scripts.map_place_ingestion.import_public_store_candidates \
  --input semas_store_raw_filter.csv \
  --category-mapping map_place_data_bootstrap_v0_3/data/category_mapping_seed.csv
```

Local license data:

```bash
python3 -m scripts.map_place_ingestion.import_public_store_candidates \
  --input seoul_license_raw_filter.csv \
  --source-code SEOUL_GENERAL_RESTAURANT_LICENSE
```

동작:

- source registry policy를 확인합니다.
- category mapping으로 `candidate_place_type`을 추정합니다.
- 폐업/말소/취소 상태는 review task 대상입니다.
- public data는 canonical `places`에 직접 publish하지 않습니다.

## 6. Owner Menu / Inventory / Price Validation

```bash
python3 -m scripts.map_place_ingestion.import_owner_menu_items \
  --input owner_menu_items.csv

python3 -m scripts.map_place_ingestion.import_owner_inventory_items \
  --input owner_inventory_items.csv

python3 -m scripts.map_place_ingestion.import_owner_price_offers \
  --input owner_price_offers.csv
```

현재 상태:

- dry-run validation only.
- canonical apply is blocked.
- 이유: CLI에는 auth/manager permission, audit log, outbox event 생성이 아직 없습니다.

## Forbidden Commands

현재 workflow에는 다음이 없습니다.

- Kakao API call.
- Kakao bulk ingestion.
- direct canonical `places` import from public data.
- production seed import.
- destructive DB command.
