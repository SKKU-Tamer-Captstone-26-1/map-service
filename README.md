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
```

This is the expected clean local/dev path. It does not apply the older public place/admin/import migrations.

Dry-run the default path:

```bash
python3 scripts/db/apply_migrations.py --dry-run
```

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

## Data Bootstrap Direction

Research artifacts under `docs/research/` and `data/bootstrap/` are proposals only. Public/open data can enter candidate staging for later admin review, but must not be inserted directly into canonical places or `map_view`.

Kakao Local/Map API data is `realtime_only` unless separate legal or partnership approval is documented. Do not bulk-ingest Kakao API responses as canonical or storable place data.

## Safety Notes

- `map_view` stores marker read-model data only.
- Do not put admin workflow, canonical place details, menu, inventory, price, audit, or import staging tables in `map_view`.
- Do not create a DB FK from `map_view.markers.place_ref` to `admin_ops.places.id`.
- Do not drop or reset legacy tables until local/dev cleanup is explicitly approved.
- Do not bulk-ingest Kakao Local/Map API data as canonical place data.
- Do not insert public/open data directly into `map_view`.
- Do not publish markers without an explicit reviewed canonical source.
- Do not let Admin Page write directly to the database.
- Do not let recommendation-service directly read or write map-service tables.
