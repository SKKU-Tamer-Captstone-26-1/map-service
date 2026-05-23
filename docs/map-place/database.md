# Map/Place Database

## Local PostGIS

Local DB config:

| Setting | Default |
|---|---|
| image | `postgis/postgis:16-3.5` |
| host | `127.0.0.1` |
| port | `55433` |
| db | `map_service` |
| user | `map_user` |

See [../../docker-compose.db.yml](../../docker-compose.db.yml) and [../../.env.example](../../.env.example).

## Default Migration Set

The default migration set is `map-view`.

```bash
python3 scripts/db/apply_migrations.py
```

Equivalent explicit command:

```bash
python3 scripts/db/apply_migrations.py --migration-set map-view
```

This applies:

```text
migrations/007_create_map_view_minimal_schema.sql
migrations/008_seed_map_view_marker_layers.sql
```

`008_seed_map_view_marker_layers.sql` inserts idempotent map display layer configuration only. It does not insert markers, public-data candidates, or canonical places.

## Legacy Migration Set

The historical full replay is explicit:

```bash
python3 scripts/db/apply_migrations.py --migration-set legacy-full
```

Use this only for historical investigation. It creates deprecated public tables for source/import/place/admin/menu/inventory/price workflows and will not pass strict clean verification.

## Strict Clean Verification

```bash
python3 scripts/db/verify_map_view_schema.py --strict-clean-db
```

Expected clean tables:

```text
map_view.marker_layers
map_view.markers
map_view.marker_publication_events
```

No import/source/candidate/canonical tables should live in `map_view`.

Expected pre-deploy layer config:

```text
bar
pub
liquor_shop
outdoor_spot
restaurant
convenience_store
other
```
