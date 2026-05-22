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
docs/handoff/                  Handoff docs for map_view and legacy map/place drafts
map_view.dbml                  Source of truth for the minimal map_view ERD
map_view.md                    Korean explanation of the minimal map_view design
```

Some legacy migration files can still exist until DB history is explicitly rebaselined. Do not treat those old public place/admin/import tables as the desired `map_view` schema.

## Local DB Quick Start

```bash
cp .env.example .env
docker compose -f docker-compose.db.yml up -d db
python3 scripts/db/apply_migrations.py
python3 scripts/db/verify_map_view_schema.py
```

`apply_migrations.py` applies SQL files in lexical order and does not keep migration metadata. Use a clean local/dev database for full replay until a proper migration runner is introduced.

Strict clean check:

```bash
python3 scripts/db/verify_map_view_schema.py --strict-clean-db
```

`--strict-clean-db` should pass on a clean map_view-only database. It will fail on an older local DB if oversized public tables were already applied.

## Safety Notes

- `map_view` stores marker read-model data only.
- Do not put admin workflow, canonical place details, menu, inventory, price, audit, or import staging tables in `map_view`.
- Do not create a DB FK from `map_view.markers.place_ref` to `admin_ops.places.id`.
- Do not drop or reset legacy tables until local/dev cleanup is explicitly approved.
- Do not bulk-ingest Kakao Local/Map API data as canonical place data.
- Do not let Admin Page write directly to the database.
- Do not let recommendation-service directly read or write map-service tables.
