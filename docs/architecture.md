# map-service Architecture

## Current Direction

`map-service` currently owns the minimal `map_view` read model for map markers.

```text
map_view
  what the map UI needs to draw published markers

admin_ops / place-service
  canonical place, source, review, publish workflow
```

The current repository should not grow a full canonical place database inside `map_view`.

## Local DB Boundary

The default local DB migration path is:

```bash
python3 scripts/db/apply_migrations.py --migration-set map-view
```

That applies only:

```text
migrations/007_create_map_view_minimal_schema.sql
migrations/008_seed_map_view_marker_layers.sql
```

`008` seeds map display layer configuration only; it does not create places, candidates, markers, or public-data imports.

Historical public place/admin/import migrations remain available through `--migration-set legacy-full` for investigation only.

## map_view Tables

The expected `map_view` app tables are:

```text
map_view.marker_layers
map_view.markers
map_view.marker_publication_events
```

Physical DB foreign keys stay inside `map_view`. `map_view.markers.place_ref` is a logical reference to a canonical place and must not become a cross-service FK.

## Data Flow

Future target flow:

```text
official public/open data
        ↓
candidate staging outside map_view
        ↓
dedupe and operator review
        ↓
canonical place owner
        ↓
publish workflow
        ↓
map_view marker projection
```

Kakao Local/Map API is not part of this bootstrap storage path. It is realtime lookup/display/verification support only unless separate approval exists.

## Verification

Use:

```bash
python3 scripts/db/verify_map_view_schema.py
python3 scripts/db/verify_map_view_schema.py --strict-clean-db
```

`--strict-clean-db` should pass on a clean map-view-only local database. It will fail if legacy public app tables are still present.
