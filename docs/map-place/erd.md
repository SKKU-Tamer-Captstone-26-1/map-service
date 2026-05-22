# Map/Place ERD

## Source Of Truth

The current `map_view` ERD source of truth is:

- [../../map_view.dbml](../../map_view.dbml)
- [../../map_view.md](../../map_view.md)

## Current Physical Schema

```text
map_view.marker_layers
map_view.markers
map_view.marker_publication_events
```

Allowed physical FKs:

```text
map_view.markers.layer_code -> map_view.marker_layers.code
map_view.marker_publication_events.marker_id -> map_view.markers.id
```

Forbidden physical FKs:

```text
map_view.markers.place_ref -> admin_ops.places.id
map_view -> auth-service tables
map_view -> recommendation-service tables
map_view -> survey-service tables
map_view -> chat-service tables
```

## Non-Goal ERDs

The older public place/admin/import tables are not the desired `map_view` ERD.

The admin operations draft files at repo root are reference material only until an `admin_ops` task is explicitly approved.
