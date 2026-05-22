from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import psycopg


EXPECTED_TABLES = {
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

DEFERRED_TABLES = {
    "tags",
    "place_tags",
    "route_estimate_cache",
    "place_reports",
    "place_media",
    "place_business_hours",
    "place_special_hours",
}

EXPECTED_INDEXES = {
    "idx_import_candidates_location_gist",
    "idx_outbox_pending",
    "idx_places_location_gist",
    "idx_places_public_active_published",
    "idx_places_recommendation_eligible",
    "uq_place_source_refs_source_external",
}

EXPECTED_CONSTRAINTS = {
    "ck_inventory_stock_confidence_range",
    "ck_places_price_level_range",
    "ck_price_offers_confidence_range",
    "uq_data_sources_type_name",
    "uq_place_managers_place_user",
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
    return [row[0] for row in cursor.fetchall()]


def verify(database_url: str) -> dict[str, Any]:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            extensions = set(
                fetch_all(
                    cursor,
                    "SELECT extname FROM pg_extension WHERE extname IN ('postgis', 'pgcrypto')",
                )
            )
            tables = set(
                fetch_all(
                    cursor,
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public'",
                )
            )
            indexes = set(
                fetch_all(
                    cursor,
                    "SELECT indexname FROM pg_indexes WHERE schemaname = 'public'",
                )
            )
            constraints = set(
                fetch_all(
                    cursor,
                    "SELECT conname FROM pg_constraint WHERE connamespace = 'public'::regnamespace",
                )
            )
            geography_columns = fetch_all(
                cursor,
                """
                SELECT f_table_name || '.' || f_geography_column || ':' || type || ':' || srid
                FROM geography_columns
                WHERE f_table_schema = 'public'
                ORDER BY f_table_name
                """,
            )
            fks = fetch_all(
                cursor,
                """
                SELECT conname || ' -> ' || confrelid::regclass::text
                FROM pg_constraint
                WHERE contype = 'f'
                  AND connamespace = 'public'::regnamespace
                ORDER BY conname
                """,
            )
            counts = {}
            for table in [
                "data_sources",
                "place_import_batches",
                "place_import_candidates",
                "place_review_tasks",
                "places",
                "place_source_refs",
                "place_outbox_events",
            ]:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cursor.fetchone()[0]

    forbidden_fk_targets = [
        fk
        for fk in fks
        if any(token in fk.lower() for token in ("auth", "recommendation", "catalog", "survey", "chatbot", "users"))
    ]
    failures: list[str] = []
    if {"postgis", "pgcrypto"} - extensions:
        failures.append("missing required extensions")
    if EXPECTED_TABLES - tables:
        failures.append(f"missing MVP tables: {sorted(EXPECTED_TABLES - tables)}")
    if DEFERRED_TABLES & tables:
        failures.append(f"deferred optional tables unexpectedly present: {sorted(DEFERRED_TABLES & tables)}")
    if EXPECTED_INDEXES - indexes:
        failures.append(f"missing required indexes: {sorted(EXPECTED_INDEXES - indexes)}")
    if EXPECTED_CONSTRAINTS - constraints:
        failures.append(f"missing required constraints: {sorted(EXPECTED_CONSTRAINTS - constraints)}")
    if "places.location:Point:4326" not in geography_columns:
        failures.append("places.location geography Point:4326 not found")
    if "place_import_candidates.location:Point:4326" not in geography_columns:
        failures.append("place_import_candidates.location geography Point:4326 not found")
    if forbidden_fk_targets:
        failures.append(f"forbidden cross-service FK target detected: {forbidden_fk_targets}")

    return {
        "ok": not failures,
        "failures": failures,
        "extensions": sorted(extensions),
        "mvp_tables_count": len(EXPECTED_TABLES & tables),
        "deferred_tables_present": sorted(DEFERRED_TABLES & tables),
        "key_indexes_present": sorted(EXPECTED_INDEXES & indexes),
        "key_constraints_present": sorted(EXPECTED_CONSTRAINTS & constraints),
        "geography_columns": geography_columns,
        "foreign_keys": fks,
        "counts": counts,
        "canonical_places_count": counts.get("places", 0),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify local/dev map-place DB schema and staging safety.")
    parser.add_argument("--database-url", help="PostgreSQL connection URL. Defaults to DATABASE_URL or local .env defaults.")
    args = parser.parse_args()
    database_url = resolve_database_url(args.database_url)
    report = verify(database_url)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
