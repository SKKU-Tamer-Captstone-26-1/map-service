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
from scripts.map_place_ingestion.normalize import clean_text, normalize_actor_role, normalize_availability_status, normalize_source_type
from scripts.map_place_ingestion.quality_rules import evaluate_inventory_freshness


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


def validate_rows(rows: list[dict[str, str]], input_path: object) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    errors = require_columns(rows, ["place_id_or_external_ref", "availability_status", "source_type"], input_path)  # type: ignore[arg-type]
    warnings: list[str] = []
    valid: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=2):
        row_errors: list[str] = []
        place_ref = clean_text(row.get("place_id_or_external_ref"))
        if not place_ref:
            row_errors.append(f"row {index}: place_id_or_external_ref is required")
        elif not _is_uuid(place_ref):
            warnings.append(f"row {index}: place_id_or_external_ref is not a UUID; apply would need an application-level lookup")
        try:
            availability_status = normalize_availability_status(row.get("availability_status"))
            source_type = normalize_source_type(row.get("source_type"))
            updated_by_role = normalize_actor_role(row.get("updated_by_role"))
        except ValueError as exc:
            row_errors.append(f"row {index}: {exc}")
            availability_status = ""
            source_type = ""
            updated_by_role = None
        confidence_text = clean_text(row.get("stock_confidence")) or "0.500"
        try:
            stock_confidence = Decimal(confidence_text)
            if not (Decimal("0") <= stock_confidence <= Decimal("1")):
                row_errors.append(f"row {index}: stock_confidence must be between 0 and 1")
        except InvalidOperation:
            row_errors.append(f"row {index}: stock_confidence must be numeric")
        freshness_findings = evaluate_inventory_freshness(row)
        warnings.extend(f"row {index}: {finding.rule_code}: {finding.message}" for finding in freshness_findings)
        if row_errors:
            errors.extend(row_errors)
            continue
        valid.append(
            {
                "place_ref": place_ref,
                "menu_item_ref": clean_text(row.get("menu_item_ref")) or None,
                "beverage_catalog_ref_id": clean_text(row.get("beverage_catalog_ref_id")) or None,
                "inventory_name": clean_text(row.get("inventory_name")) or None,
                "availability_status": availability_status,
                "stock_confidence": str(stock_confidence),
                "source_type": source_type,
                "updated_by_role": updated_by_role,
                "last_seen_at": clean_text(row.get("last_seen_at")) or None,
                "expires_at": clean_text(row.get("expires_at")) or None,
            }
        )
    return valid, errors, warnings


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate owner/operator inventory CSV. Canonical apply is intentionally blocked.")
    add_input_arg(parser, default=DEFAULT_BOOTSTRAP_ROOT / "templates/owner_inventory_items_template.csv")
    parser.add_argument("--operator-mode", action="store_true", help="Acknowledge this is an operator-controlled import context.")
    add_dry_run_apply_args(parser)
    args = parser.parse_args()

    rows = read_csv_rows(args.input)
    valid, errors, warnings = validate_rows(rows, args.input)
    if args.apply:
        errors.append("--apply is blocked for inventory until service-level permission, audit, and outbox writes are implemented")
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
