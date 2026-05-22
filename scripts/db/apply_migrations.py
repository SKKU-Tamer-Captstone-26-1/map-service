from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

import psycopg

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.map_place_ingestion.cli_common import DEFAULT_BOOTSTRAP_ROOT, load_source_registry as load_source_registry_csv
from scripts.map_place_ingestion.cli_common import read_csv_rows
from scripts.map_place_ingestion.import_outdoor_spot_candidates import build_candidates as build_outdoor_candidates
from scripts.map_place_ingestion.import_source_registry import apply_records as apply_source_records
from scripts.map_place_ingestion.import_source_registry import build_source_records
from scripts.map_place_ingestion.staging import apply_candidate_import


DEFAULT_MIGRATIONS_DIR = REPO_ROOT / "migrations"


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


def migration_files(migrations_dir: Path) -> list[Path]:
    files = sorted(migrations_dir.glob("*.sql"))
    if not files:
        raise RuntimeError(f"no migration files found in {migrations_dir}")
    return files


def apply_migrations(database_url: str, migrations_dir: Path, *, dry_run: bool = False) -> list[str]:
    files = migration_files(migrations_dir)
    applied: list[str] = []
    if dry_run:
        return [path.name for path in files]

    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            for path in files:
                cursor.execute(path.read_text(encoding="utf-8"))
                applied.append(path.name)
    return applied


def load_source_registry(database_url: str, path: Path, *, dry_run: bool) -> dict[str, Any]:
    rows = read_csv_rows(path)
    records, errors = build_source_records(rows, path)
    result: dict[str, Any] = {
        "path": str(path),
        "rows_read": len(rows),
        "valid_records": len(records),
        "errors": errors,
        "dry_run": dry_run,
    }
    if errors:
        return result
    if not dry_run:
        result["applied_records"] = apply_source_records(records, database_url)
    return result


def load_outdoor_candidates(database_url: str, path: Path, source_registry_path: Path, *, dry_run: bool) -> dict[str, Any]:
    rows = read_csv_rows(path)
    registry = load_source_registry_csv(source_registry_path)
    candidates, errors, warnings = build_outdoor_candidates(rows, registry, path)
    result: dict[str, Any] = {
        "path": str(path),
        "rows_read": len(rows),
        "valid_candidates": len(candidates),
        "warnings": warnings,
        "errors": errors,
        "dry_run": dry_run,
        "staging_only": True,
        "canonical_places_created": 0,
    }
    if errors:
        return result
    if not dry_run:
        apply_results = []
        for source_code in sorted({candidate.source_code for candidate in candidates}):
            apply_results.append(
                apply_candidate_import(
                    database_url=database_url,
                    input_path=path,
                    source_code=source_code,
                    import_type="PUBLIC_DATA_FILE",
                    candidates=[candidate for candidate in candidates if candidate.source_code == source_code],
                    batch_metadata={"importer": "scripts/db/apply_migrations.py", "staging_only": True},
                )
            )
        result["apply_results"] = apply_results
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply map/place SQL migrations to a local/dev PostGIS database.")
    parser.add_argument("--database-url", help="PostgreSQL connection URL. Defaults to DATABASE_URL or local .env defaults.")
    parser.add_argument("--migrations-dir", type=Path, default=DEFAULT_MIGRATIONS_DIR)
    parser.add_argument("--dry-run", action="store_true", help="List migrations and validate optional CSVs without writing.")
    parser.add_argument("--load-source-registry", action="store_true", help="Also load bootstrap source_registry.csv into data_sources.")
    parser.add_argument("--source-registry-path", type=Path, default=DEFAULT_BOOTSTRAP_ROOT / "data/source_registry.csv")
    parser.add_argument("--load-outdoor-candidates", action="store_true", help="Also load outdoor spot seed candidates into staging/review tables.")
    parser.add_argument("--outdoor-candidates-path", type=Path, default=DEFAULT_BOOTSTRAP_ROOT / "data/seoul_hangang_outdoor_spot_seed_candidates.csv")
    args = parser.parse_args()

    database_url = resolve_database_url(args.database_url)
    report: dict[str, Any] = {
        "database_url": database_url.replace(os.environ.get("MAP_SERVICE_DB_PASSWORD", "map_pass"), "***"),
        "dry_run": args.dry_run,
        "migrations": apply_migrations(database_url, args.migrations_dir, dry_run=args.dry_run),
    }

    if args.load_source_registry:
        report["source_registry"] = load_source_registry(database_url, args.source_registry_path, dry_run=args.dry_run)
        if report["source_registry"]["errors"]:
            print_report(report)
            raise SystemExit(1)

    if args.load_outdoor_candidates:
        if not args.load_source_registry and not args.dry_run:
            report["outdoor_candidates"] = {
                "errors": ["--load-outdoor-candidates requires source records already loaded or --load-source-registry in the same command"],
                "staging_only": True,
                "canonical_places_created": 0,
            }
            print_report(report)
            raise SystemExit(1)
        report["outdoor_candidates"] = load_outdoor_candidates(
            database_url,
            args.outdoor_candidates_path,
            args.source_registry_path,
            dry_run=args.dry_run,
        )
        if report["outdoor_candidates"]["errors"]:
            print_report(report)
            raise SystemExit(1)

    print_report(report)


def print_report(report: dict[str, Any]) -> None:
    import json

    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
