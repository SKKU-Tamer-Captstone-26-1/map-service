# Map / Place Ingestion Scripts

These scripts are safe-by-default import helpers for the extracted bootstrap package and operator CSVs.

Rules:

- Dry-run is the default.
- DB writes require `--apply`.
- DB-backed `--apply` commands require `--database-url` or `DATABASE_URL`.
- Place imports write staging/review tables only.
- No script writes canonical `places`.
- No script calls Kakao or downloads external public data.

## Commands

```bash
python3 scripts/map_place_ingestion/validate_bootstrap_package.py
python3 scripts/map_place_ingestion/import_source_registry.py
python3 scripts/map_place_ingestion/import_outdoor_spot_candidates.py
python3 scripts/map_place_ingestion/import_operator_place_seed.py --input operator_place_seed.csv
python3 scripts/map_place_ingestion/import_public_store_candidates.py --kind semas --input semas_store_filtered.csv
python3 scripts/map_place_ingestion/import_public_store_candidates.py --kind seoul-license --input seoul_license_filtered.csv
python3 scripts/map_place_ingestion/import_owner_menu_items.py --input owner_menu_items.csv
python3 scripts/map_place_ingestion/import_owner_inventory_items.py --input owner_inventory_items.csv
python3 scripts/map_place_ingestion/import_owner_price_offers.py --input owner_price_offers.csv
```

## Apply Examples

Apply is intentionally explicit:

```bash
python3 scripts/map_place_ingestion/import_source_registry.py --apply --database-url "$DATABASE_URL"
python3 scripts/map_place_ingestion/import_outdoor_spot_candidates.py --apply --database-url "$DATABASE_URL"
```

Owner menu/inventory/price imports are validation-only right now. `--apply` is intentionally blocked until service-level permission checks, audit logs, and outbox events exist.
