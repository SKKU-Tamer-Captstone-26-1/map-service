from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.bootstrap.validate_research_package import DEFAULT_BOOTSTRAP_DIR, validate
from scripts.db.apply_migrations import DEFAULT_MIGRATIONS_DIR, apply_migrations, mask_database_url
from scripts.db.verify_map_view_schema import resolve_database_url, verify


def check_migration_plan(migrations_dir: Path, migration_set: str) -> dict[str, Any]:
    return {
        "ok": True,
        "migration_set": migration_set,
        "migrations_dir": str(migrations_dir),
        "migrations": apply_migrations(
            "dry-run-only",
            migrations_dir,
            migration_set=migration_set,
            dry_run=True,
        ),
    }


def check_research_package(bootstrap_dir: Path) -> dict[str, Any]:
    report = validate(bootstrap_dir)
    return {
        "ok": bool(report["ok"]),
        **report,
    }


def check_schema(database_url: str) -> dict[str, Any]:
    return verify(database_url, strict_clean_db=True)


def run_checks(
    *,
    database_url: str,
    migrations_dir: Path,
    bootstrap_dir: Path,
    migration_set: str,
) -> dict[str, Any]:
    checks: dict[str, Any] = {}

    try:
        checks["migration_plan"] = check_migration_plan(migrations_dir, migration_set)
    except Exception as error:
        checks["migration_plan"] = {"ok": False, "errors": [str(error)]}

    try:
        checks["research_package"] = check_research_package(bootstrap_dir)
    except Exception as error:
        checks["research_package"] = {"ok": False, "errors": [str(error)]}

    try:
        checks["schema"] = check_schema(database_url)
    except Exception as error:
        checks["schema"] = {"ok": False, "errors": [str(error)]}

    ok = all(bool(check.get("ok")) for check in checks.values())
    return {
        "ok": ok,
        "database_url": mask_database_url(database_url),
        "safe_for": "predeploy_map_view_read_model",
        "side_effects": "none",
        "checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run read-only pre-deploy checks for the map_view database package.")
    parser.add_argument("--database-url", help="PostgreSQL URL. Defaults to DATABASE_URL or local map-service DB env.")
    parser.add_argument("--migrations-dir", type=Path, default=DEFAULT_MIGRATIONS_DIR)
    parser.add_argument("--bootstrap-dir", type=Path, default=DEFAULT_BOOTSTRAP_DIR)
    parser.add_argument("--migration-set", default="map-view", choices=["map-view"])
    args = parser.parse_args()

    report = run_checks(
        database_url=resolve_database_url(args.database_url),
        migrations_dir=args.migrations_dir,
        bootstrap_dir=args.bootstrap_dir,
        migration_set=args.migration_set,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
