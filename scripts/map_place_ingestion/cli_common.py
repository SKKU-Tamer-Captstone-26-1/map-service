from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BOOTSTRAP_ROOT = REPO_ROOT / "map_place_data_bootstrap_v0_3"


def add_dry_run_apply_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dry-run", action="store_true", default=True, help="Validate and preview only. This is the default.")
    parser.add_argument("--apply", action="store_true", help="Write to the database. Requires an explicit DB URL for DB-backed commands.")
    parser.add_argument("--database-url", help="PostgreSQL connection URL. Required with --apply for DB-backed commands.")


def add_input_arg(parser: argparse.ArgumentParser, *, default: Path | None = None, help_text: str = "CSV input path.") -> None:
    parser.add_argument("--input", type=path_arg, default=default, help=help_text)


def add_bootstrap_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--bootstrap-root",
        type=path_arg,
        default=DEFAULT_BOOTSTRAP_ROOT,
        help="Extracted bootstrap package root.",
    )


def effective_dry_run(args: argparse.Namespace) -> bool:
    return not bool(getattr(args, "apply", False))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [{key: (value or "").strip() for key, value in row.items()} for row in reader]


def require_columns(rows: list[dict[str, str]], columns: Iterable[str], path: Path) -> list[str]:
    if rows:
        header = set(rows[0].keys())
    else:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            header = set(next(reader, []))
    missing = [column for column in columns if column not in header]
    if missing:
        return [f"{path}: missing required columns: {', '.join(missing)}"]
    return []


def load_source_registry(path: Path) -> dict[str, dict[str, str]]:
    rows = read_csv_rows(path)
    registry: dict[str, dict[str, str]] = {}
    for row in rows:
        source_code = (row.get("source_code") or "").strip()
        if source_code:
            registry[source_code] = row
    return registry


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def print_json_report(report: dict[str, Any]) -> None:
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


def fail(message: str, code: int = 2) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def path_arg(value: str) -> Path:
    return Path(value).expanduser().resolve()
