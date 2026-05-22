from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import psycopg


REPO_ROOT = Path(__file__).resolve().parents[2]
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


def mask_database_url(database_url: str) -> str:
    password = os.environ.get("MAP_SERVICE_DB_PASSWORD", "map_pass")
    return database_url.replace(password, "***")


def migration_files(migrations_dir: Path) -> list[Path]:
    files = sorted(migrations_dir.glob("*.sql"))
    if not files:
        raise RuntimeError(f"no migration files found in {migrations_dir}")
    return files


def apply_migrations(database_url: str, migrations_dir: Path, *, dry_run: bool = False) -> list[str]:
    files = migration_files(migrations_dir)
    if dry_run:
        return [path.name for path in files]

    applied: list[str] = []
    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            for path in files:
                cursor.execute(path.read_text(encoding="utf-8"))
                applied.append(path.name)
    return applied


def print_report(report: dict[str, Any]) -> None:
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply SQL migrations to a local/dev map_view PostGIS database.")
    parser.add_argument("--database-url", help="PostgreSQL connection URL. Defaults to DATABASE_URL or local .env defaults.")
    parser.add_argument("--migrations-dir", type=Path, default=DEFAULT_MIGRATIONS_DIR)
    parser.add_argument("--dry-run", action="store_true", help="List migration files without writing to the database.")
    args = parser.parse_args()

    database_url = resolve_database_url(args.database_url)
    report = {
        "database_url": mask_database_url(database_url),
        "dry_run": args.dry_run,
        "migrations": apply_migrations(database_url, args.migrations_dir, dry_run=args.dry_run),
    }
    print_report(report)


if __name__ == "__main__":
    main()
