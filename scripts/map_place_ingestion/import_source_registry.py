from __future__ import annotations

if __package__ in {None, ""}:
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[2]))

import argparse
from pathlib import Path
from typing import Any

from scripts.map_place_ingestion.cli_common import (
    DEFAULT_BOOTSTRAP_ROOT,
    add_dry_run_apply_args,
    add_input_arg,
    json_dumps,
    print_json_report,
    read_csv_rows,
    require_columns,
)
from scripts.map_place_ingestion.db import connect
from scripts.map_place_ingestion.normalize import clean_text, normalize_source_type, validate_source_policy


TRUST_LEVELS = {
    "OPERATOR": 100,
    "OWNER": 85,
    "FIELD_RESEARCH": 80,
    "PUBLIC_DATA": 70,
    "USER_REPORT": 40,
    "KAKAO": 0,
    "SYSTEM": 90,
}


def build_source_records(rows: list[dict[str, str]], input_path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    errors = require_columns(rows, ["source_code", "source_name_ko", "source_type", "source_policy"], input_path)
    records: list[dict[str, Any]] = []
    seen_codes: set[str] = set()
    for index, row in enumerate(rows, start=2):
        source_code = clean_text(row.get("source_code"))
        if not source_code:
            errors.append(f"row {index}: source_code is required")
            continue
        if source_code in seen_codes:
            errors.append(f"row {index}: duplicate source_code in CSV: {source_code}")
            continue
        seen_codes.add(source_code)
        source_name = clean_text(row.get("source_name_ko"))
        if not source_name:
            errors.append(f"row {index}: source_name_ko is required")
            continue
        try:
            source_type = normalize_source_type(row.get("source_type"))
            source_policy = validate_source_policy(source_type, row.get("source_policy"))
        except ValueError as exc:
            errors.append(f"row {index}: {exc}")
            continue
        metadata = dict(row)
        metadata.update(
            {
                "source_code": source_code,
                "canonical_use_allowed": clean_text(row.get("canonical_use_allowed")),
                "review_required": clean_text(row.get("review_required")),
                "default_target": clean_text(row.get("default_target")),
            }
        )
        records.append(
            {
                "source_code": source_code,
                "source_name": source_name,
                "source_type": source_type,
                "source_policy": source_policy,
                "license_name": clean_text(row.get("license_or_terms")) or None,
                "license_url": clean_text(row.get("url")) or None,
                "trust_level": TRUST_LEVELS.get(source_type, 0),
                "metadata": metadata,
            }
        )
    return records, errors


def apply_records(records: list[dict[str, Any]], database_url: str | None) -> int:
    with connect(database_url) as connection:
        with connection.cursor() as cursor:
            for record in records:
                cursor.execute(
                    """
                    INSERT INTO data_sources (
                      source_type,
                      source_name,
                      source_policy,
                      license_name,
                      license_url,
                      trust_level,
                      active,
                      metadata_json
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, true, %s::jsonb)
                    ON CONFLICT (source_type, source_name)
                    DO UPDATE SET
                      source_policy = EXCLUDED.source_policy,
                      license_name = EXCLUDED.license_name,
                      license_url = EXCLUDED.license_url,
                      trust_level = EXCLUDED.trust_level,
                      active = true,
                      metadata_json = data_sources.metadata_json || EXCLUDED.metadata_json,
                      updated_at = now()
                    """,
                    (
                        record["source_type"],
                        record["source_name"],
                        record["source_policy"],
                        record["license_name"],
                        record["license_url"],
                        record["trust_level"],
                        json_dumps(record["metadata"]),
                    ),
                )
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser(description="Safely import data/source_registry.csv into data_sources.")
    add_input_arg(parser, default=DEFAULT_BOOTSTRAP_ROOT / "data/source_registry.csv")
    add_dry_run_apply_args(parser)
    args = parser.parse_args()

    rows = read_csv_rows(args.input)
    records, errors = build_source_records(rows, args.input)
    report: dict[str, Any] = {
        "input": str(args.input),
        "dry_run": not args.apply,
        "target_table": "data_sources",
        "rows_read": len(rows),
        "valid_records": len(records),
        "errors": errors,
        "preview": records[:5],
    }
    if args.apply:
        if errors:
            report["applied"] = False
            print_json_report(report)
            raise SystemExit(1)
        report["applied_records"] = apply_records(records, args.database_url)
    print_json_report(report)


if __name__ == "__main__":
    main()
