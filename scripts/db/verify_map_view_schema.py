from __future__ import annotations

import argparse
import json
import os
from typing import Any

import psycopg


EXPECTED_MAP_VIEW_TABLES = {
    "marker_layers",
    "marker_publication_events",
    "markers",
}

EXPECTED_ENUMS = {
    "marker_publication_event_type": [
        "marker_published",
        "marker_hidden",
        "marker_moved",
        "marker_layer_changed",
        "marker_deleted",
    ],
    "marker_visibility_state": ["visible", "hidden"],
}

EXPECTED_INDEXES = {
    "idx_marker_events_consumed_at",
    "idx_marker_events_created_at",
    "idx_marker_events_marker_id",
    "idx_marker_events_place_ref",
    "idx_marker_events_place_revision",
    "idx_marker_layers_active",
    "idx_marker_layers_display_order",
    "idx_markers_geohash",
    "idx_markers_layer_code",
    "idx_markers_layer_visibility",
    "idx_markers_location_gist",
    "idx_markers_published_revision",
    "idx_markers_visibility",
    "uq_markers_place_ref",
}

EXPECTED_MARKER_LAYERS = {
    "bar": {"icon_key": "bar", "display_order": 10, "default_visible": True, "is_active": True},
    "pub": {"icon_key": "beer", "display_order": 20, "default_visible": True, "is_active": True},
    "liquor_shop": {"icon_key": "bottle", "display_order": 30, "default_visible": True, "is_active": True},
    "outdoor_spot": {"icon_key": "trees", "display_order": 40, "default_visible": True, "is_active": True},
    "restaurant": {"icon_key": "utensils", "display_order": 50, "default_visible": False, "is_active": True},
    "convenience_store": {"icon_key": "store", "display_order": 60, "default_visible": False, "is_active": True},
    "other": {"icon_key": "map-pin", "display_order": 90, "default_visible": False, "is_active": True},
}

EXPECTED_FKS = {
    ("fk_markers_layer_code", "map_view.markers", "map_view.marker_layers"),
    ("fk_marker_events_marker_id", "map_view.marker_publication_events", "map_view.markers"),
}

LEGACY_PUBLIC_APP_TABLES = {
    "business_claims",
    "data_sources",
    "outdoor_spot_profiles",
    "place_audit_logs",
    "place_change_requests",
    "place_dedupe_matches",
    "place_import_batches",
    "place_import_candidates",
    "place_managers",
    "place_outbox_events",
    "place_overrides",
    "place_review_tasks",
    "place_source_refs",
    "places",
    "venue_inventory_items",
    "venue_menu_items",
    "venue_price_offers",
}

FORBIDDEN_MAP_VIEW_TABLE_TOKENS = {
    "audit",
    "business_claim",
    "change_request",
    "claim",
    "dedupe",
    "import",
    "inventory",
    "manager",
    "menu",
    "outbox",
    "override",
    "place_",
    "price",
    "source",
}


def resolve_database_url(explicit_url: str | None) -> str:
    if explicit_url:
        return explicit_url
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    if os.environ.get("MAP_SERVICE_DATABASE_URL"):
        return os.environ["MAP_SERVICE_DATABASE_URL"]
    host = os.environ.get("MAP_SERVICE_DB_HOST", "127.0.0.1")
    port = os.environ.get("MAP_SERVICE_DB_PORT", "55433")
    name = os.environ.get("MAP_SERVICE_DB_NAME", "map_service")
    user = os.environ.get("MAP_SERVICE_DB_USER", "map_user")
    password = os.environ.get("MAP_SERVICE_DB_PASSWORD", "map_pass")
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


def fetch_all(cursor: Any, sql: str, params: tuple[Any, ...] = ()) -> list[Any]:
    cursor.execute(sql, params)
    return cursor.fetchall()


def verify(database_url: str, *, strict_clean_db: bool = False) -> dict[str, Any]:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            extensions = {
                row[0]
                for row in fetch_all(
                    cursor,
                    "SELECT extname FROM pg_extension WHERE extname IN ('postgis', 'pgcrypto')",
                )
            }
            schemas = {
                row[0]
                for row in fetch_all(
                    cursor,
                    "SELECT nspname FROM pg_namespace WHERE nspname IN ('map_view', 'public')",
                )
            }
            map_view_tables = {
                row[0]
                for row in fetch_all(
                    cursor,
                    """
                    SELECT tablename
                    FROM pg_tables
                    WHERE schemaname = 'map_view'
                    ORDER BY tablename
                    """,
                )
            }
            public_tables = {
                row[0]
                for row in fetch_all(
                    cursor,
                    """
                    SELECT tablename
                    FROM pg_tables
                    WHERE schemaname = 'public'
                    ORDER BY tablename
                    """,
                )
            }
            enums = {
                row[0]: row[1]
                for row in fetch_all(
                    cursor,
                    """
                    SELECT t.typname, array_agg(e.enumlabel ORDER BY e.enumsortorder)
                    FROM pg_type t
                    JOIN pg_namespace n ON n.oid = t.typnamespace
                    JOIN pg_enum e ON e.enumtypid = t.oid
                    WHERE n.nspname = 'map_view'
                    GROUP BY t.typname
                    ORDER BY t.typname
                    """,
                )
            }
            indexes = {
                row[0]: row[1]
                for row in fetch_all(
                    cursor,
                    """
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE schemaname = 'map_view'
                    ORDER BY indexname
                    """,
                )
            }
            constraints = {
                row[0]
                for row in fetch_all(
                    cursor,
                    """
                    SELECT conname
                    FROM pg_constraint con
                    JOIN pg_class rel ON rel.oid = con.conrelid
                    JOIN pg_namespace ns ON ns.oid = rel.relnamespace
                    WHERE ns.nspname = 'map_view'
                    ORDER BY conname
                    """,
                )
            }
            fks = {
                (row[0], row[1], row[2])
                for row in fetch_all(
                    cursor,
                    """
                    SELECT
                      con.conname,
                      con.conrelid::regclass::text,
                      con.confrelid::regclass::text
                    FROM pg_constraint con
                    JOIN pg_class rel ON rel.oid = con.conrelid
                    JOIN pg_namespace ns ON ns.oid = rel.relnamespace
                    WHERE con.contype = 'f'
                      AND ns.nspname = 'map_view'
                    ORDER BY con.conname
                    """,
                )
            }
            geography_columns_available = bool(
                fetch_all(cursor, "SELECT to_regclass('public.geography_columns') IS NOT NULL")[0][0]
            )
            geography_columns = []
            if geography_columns_available:
                geography_columns = [
                    row[0]
                    for row in fetch_all(
                        cursor,
                        """
                        SELECT f_table_schema || '.' || f_table_name || '.' || f_geography_column || ':' || type || ':' || srid
                        FROM geography_columns
                        WHERE f_table_schema = 'map_view'
                        ORDER BY f_table_name, f_geography_column
                        """,
                    )
                ]
            marker_layers = {}
            if "marker_layers" in map_view_tables:
                marker_layers = {
                    row[0]: {
                        "icon_key": row[1],
                        "display_order": row[2],
                        "default_visible": row[3],
                        "is_active": row[4],
                    }
                    for row in fetch_all(
                        cursor,
                        """
                        SELECT code, icon_key, display_order, default_visible, is_active
                        FROM map_view.marker_layers
                        ORDER BY code
                        """,
                    )
                }

    failures: list[str] = []
    needs_review: list[str] = []

    if "postgis" not in extensions:
        failures.append("missing postgis extension")
    if "pgcrypto" not in extensions:
        failures.append("missing pgcrypto extension")
    if "map_view" not in schemas:
        failures.append("missing map_view schema")

    missing_tables = EXPECTED_MAP_VIEW_TABLES - map_view_tables
    unexpected_tables = map_view_tables - EXPECTED_MAP_VIEW_TABLES
    if missing_tables:
        failures.append(f"missing map_view tables: {sorted(missing_tables)}")
    if unexpected_tables:
        failures.append(f"unexpected map_view tables: {sorted(unexpected_tables)}")

    forbidden_map_view_tables = sorted(
        table
        for table in map_view_tables
        if table not in EXPECTED_MAP_VIEW_TABLES
        or any(token in table for token in FORBIDDEN_MAP_VIEW_TABLE_TOKENS)
    )
    if forbidden_map_view_tables:
        failures.append(f"admin/import-style tables in map_view: {forbidden_map_view_tables}")

    for enum_name, labels in EXPECTED_ENUMS.items():
        if enums.get(enum_name) != labels:
            failures.append(f"enum mismatch for {enum_name}: expected {labels}, actual {enums.get(enum_name)}")

    missing_indexes = EXPECTED_INDEXES - set(indexes)
    if missing_indexes:
        failures.append(f"missing map_view indexes: {sorted(missing_indexes)}")

    location_index = indexes.get("idx_markers_location_gist", "").lower()
    if "using gist" not in location_index or "(location)" not in location_index:
        failures.append("idx_markers_location_gist is not a GiST index on markers.location")

    if "map_view.markers.location:Point:4326" not in geography_columns:
        failures.append("map_view.markers.location geography Point:4326 not found")

    if EXPECTED_FKS - fks:
        failures.append(f"missing map_view FKs: {sorted(EXPECTED_FKS - fks)}")

    unexpected_fk_targets = sorted(
        f"{name}: {source} -> {target}"
        for name, source, target in fks
        if (name, source, target) not in EXPECTED_FKS or not target.startswith("map_view.")
    )
    if unexpected_fk_targets:
        failures.append(f"unexpected or cross-boundary map_view FKs: {unexpected_fk_targets}")

    if "uq_markers_place_ref" not in constraints:
        failures.append("missing uq_markers_place_ref unique constraint")

    missing_marker_layers = sorted(set(EXPECTED_MARKER_LAYERS) - set(marker_layers))
    if missing_marker_layers:
        failures.append(f"missing marker layer seed rows: {missing_marker_layers}")

    marker_layer_mismatches = {
        code: {"expected": expected, "actual": marker_layers.get(code)}
        for code, expected in EXPECTED_MARKER_LAYERS.items()
        if code in marker_layers and marker_layers[code] != expected
    }
    if marker_layer_mismatches:
        failures.append(f"marker layer seed row mismatches: {marker_layer_mismatches}")

    legacy_public_tables = sorted(LEGACY_PUBLIC_APP_TABLES & public_tables)
    if legacy_public_tables:
        needs_review.append(f"legacy public app tables still present: {legacy_public_tables}")
        if strict_clean_db:
            failures.append("legacy public app tables present while --strict-clean-db is enabled")

    return {
        "ok": not failures,
        "strict_clean_db": strict_clean_db,
        "failures": failures,
        "needs_review": needs_review,
        "extensions": sorted(extensions),
        "schemas": sorted(schemas),
        "map_view_tables": sorted(map_view_tables),
        "marker_layers": marker_layers,
        "legacy_public_tables_present": legacy_public_tables,
        "enums": enums,
        "indexes": sorted(indexes),
        "constraints": sorted(constraints),
        "geography_columns": geography_columns,
        "foreign_keys": sorted(f"{name}: {source} -> {target}" for name, source, target in fks),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify the minimal map_view read-model schema.")
    parser.add_argument("--database-url", help="PostgreSQL connection URL. Defaults to DATABASE_URL or local .env defaults.")
    parser.add_argument(
        "--strict-clean-db",
        action="store_true",
        help="Fail if legacy oversized public map/place tables are still present.",
    )
    args = parser.parse_args()

    report = verify(resolve_database_url(args.database_url), strict_clean_db=args.strict_clean_db)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
