from __future__ import annotations

if __package__ in {None, ""}:
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[2]))

import argparse
import uuid
from decimal import Decimal, InvalidOperation
from typing import Any

from scripts.map_place_ingestion.cli_common import DEFAULT_BOOTSTRAP_ROOT, add_dry_run_apply_args, add_input_arg, print_json_report, read_csv_rows, require_columns
from scripts.map_place_ingestion.normalize import clean_text, normalize_item_status, normalize_menu_type, normalize_source_type, parse_bool


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


def validate_rows(rows: list[dict[str, str]], input_path: object) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    errors = require_columns(rows, ["place_id_or_external_ref", "menu_name", "menu_type", "source_type"], input_path)  # type: ignore[arg-type]
    warnings: list[str] = []
    valid: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=2):
        row_errors: list[str] = []
        place_ref = clean_text(row.get("place_id_or_external_ref"))
        if not place_ref:
            row_errors.append(f"row {index}: place_id_or_external_ref is required")
        elif not _is_uuid(place_ref):
            warnings.append(f"row {index}: place_id_or_external_ref is not a UUID; apply would need an application-level lookup")
        if not clean_text(row.get("menu_name")):
            row_errors.append(f"row {index}: menu_name is required")
        try:
            menu_type = normalize_menu_type(row.get("menu_type"))
            source_type = normalize_source_type(row.get("source_type"))
            status = normalize_item_status(row.get("status"), default="ACTIVE")
        except ValueError as exc:
            row_errors.append(f"row {index}: {exc}")
            menu_type = ""
            source_type = ""
            status = ""
        base_price_text = clean_text(row.get("base_price_krw"))
        if base_price_text:
            try:
                if int(base_price_text) < 0:
                    row_errors.append(f"row {index}: base_price_krw must be nonnegative")
            except ValueError:
                row_errors.append(f"row {index}: base_price_krw must be an integer")
        confidence_text = clean_text(row.get("confidence"))
        if confidence_text:
            try:
                confidence = Decimal(confidence_text)
                if not (Decimal("0") <= confidence <= Decimal("1")):
                    row_errors.append(f"row {index}: confidence must be between 0 and 1")
            except InvalidOperation:
                row_errors.append(f"row {index}: confidence must be numeric")
        if row_errors:
            errors.extend(row_errors)
            continue
        valid.append(
            {
                "place_ref": place_ref,
                "menu_name": clean_text(row.get("menu_name")),
                "normalized_menu_name": clean_text(row.get("normalized_menu_name")) or clean_text(row.get("menu_name")).lower(),
                "menu_type": menu_type,
                "source_type": source_type,
                "status": status,
                "is_signature": parse_bool(row.get("is_signature")),
                "beverage_catalog_ref_id": clean_text(row.get("beverage_catalog_ref_id")) or None,
            }
        )
    return valid, errors, warnings


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate owner/operator menu item CSV. Canonical apply is intentionally blocked.")
    add_input_arg(parser, default=DEFAULT_BOOTSTRAP_ROOT / "templates/owner_menu_items_template.csv")
    parser.add_argument("--operator-mode", action="store_true", help="Acknowledge this is an operator-controlled import context.")
    add_dry_run_apply_args(parser)
    args = parser.parse_args()

    rows = read_csv_rows(args.input)
    valid, errors, warnings = validate_rows(rows, args.input)
    if args.apply:
        errors.append("--apply is blocked for menu items until service-level permission, audit, and outbox writes are implemented")
        if not args.operator_mode:
            errors.append("--operator-mode is required for any future canonical owner CSV apply path")
    print_json_report(
        {
            "input": str(args.input),
            "dry_run": not args.apply,
            "canonical_apply_supported": False,
            "rows_read": len(rows),
            "valid_rows": len(valid),
            "warnings": warnings,
            "errors": errors,
            "preview": valid[:5],
        }
    )
    if errors:
        raise SystemExit(1 if args.apply else 0)


if __name__ == "__main__":
    main()
