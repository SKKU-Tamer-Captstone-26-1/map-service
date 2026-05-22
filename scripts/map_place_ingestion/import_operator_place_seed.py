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
    load_source_registry,
    print_json_report,
    read_csv_rows,
    require_columns,
)
from scripts.map_place_ingestion.normalize import (
    clean_text,
    normalize_address,
    normalize_place_name,
    normalize_place_type,
    normalize_review_status,
    normalize_source_policy,
    normalize_source_type,
    parse_lat_lng,
)
from scripts.map_place_ingestion.quality_rules import evaluate_place_candidate, final_decision
from scripts.map_place_ingestion.staging import CandidateInsert, apply_candidate_import


ALLOWED_SOURCE_TYPES = {"OPERATOR", "FIELD_RESEARCH"}


def build_candidates(
    rows: list[dict[str, str]],
    source_registry: dict[str, dict[str, str]],
    input_path: Path,
    default_source_code: str | None,
) -> tuple[list[CandidateInsert], list[str], list[str]]:
    errors = require_columns(rows, ["candidate_place_type", "canonical_name"], input_path)
    warnings: list[str] = []
    candidates: list[CandidateInsert] = []
    seen_external_ids: set[str] = set()
    for index, row in enumerate(rows, start=2):
        row_errors: list[str] = []
        source_code = clean_text(row.get("source_code")) or default_source_code or "OPERATOR_FIELD_RESEARCH"
        registry_row = source_registry.get(source_code)
        if not registry_row:
            row_errors.append(f"row {index}: source_code not found in source registry: {source_code}")
            source_type = "OPERATOR"
            source_policy = "STORABLE"
        else:
            source_type = normalize_source_type(registry_row.get("source_type"))
            source_policy = normalize_source_policy(registry_row.get("source_policy"))
        if source_type not in ALLOWED_SOURCE_TYPES:
            row_errors.append(f"row {index}: operator seed source must be OPERATOR or FIELD_RESEARCH, got {source_type}")
        try:
            place_type = normalize_place_type(row.get("candidate_place_type"))
        except ValueError as exc:
            row_errors.append(f"row {index}: {exc}")
            place_type = "OTHER"
        coords = parse_lat_lng(row.get("lat"), row.get("lng"))
        review_status = normalize_review_status(row.get("review_status"), default="PENDING")
        if review_status == "APPROVED":
            warnings.append(f"row {index}: APPROVED input is still staged only; no canonical publish is performed")
        findings = evaluate_place_candidate(
            {**row, "candidate_place_type": place_type},
            source_type=source_type,
            source_policy=source_policy,
            seen_external_ids=seen_external_ids,
        )
        if final_decision(findings) == "reject_candidate":
            row_errors.extend(f"row {index}: {finding.rule_code}: {finding.message}" for finding in findings if finding.decision == "reject_candidate")
        if row_errors:
            errors.extend(row_errors)
            continue
        missing_coords = coords.latitude is None or coords.longitude is None
        candidates.append(
            CandidateInsert(
                source_code=source_code,
                external_source_id=clean_text(row.get("external_source_id")),
                raw_payload=row,
                normalized_name=normalize_place_name(row.get("normalized_name") or row.get("canonical_name")),
                normalized_address=normalize_address(row.get("road_address") or row.get("address")),
                source_category_name=clean_text(row.get("candidate_place_type")),
                candidate_place_type=place_type,
                latitude=coords.latitude,
                longitude=coords.longitude,
                review_status=review_status,
                metadata={
                    "canonical_name": clean_text(row.get("canonical_name")),
                    "recommendation_eligible_input": clean_text(row.get("recommendation_eligible")) or "YES_AFTER_REVIEW",
                    "operator_comment": clean_text(row.get("operator_comment")),
                    "source_url": clean_text(row.get("source_url")),
                    "geocode_required": missing_coords,
                    "quality_findings": [finding.__dict__ for finding in findings],
                },
                review_task_type="VERIFY_LOCATION" if missing_coords else "VERIFY_NEW_PLACE",
                review_priority=70 if review_status == "APPROVED" else 100,
            )
        )
    return candidates, errors, warnings


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate/import operator-curated place seed CSV into staging only.")
    add_input_arg(parser, default=DEFAULT_BOOTSTRAP_ROOT / "templates/operator_place_seed_template.csv")
    parser.add_argument("--source-registry", type=Path, default=DEFAULT_BOOTSTRAP_ROOT / "data/source_registry.csv")
    parser.add_argument("--source-code", help="Default source_code when the CSV row does not include one.")
    add_dry_run_apply_args(parser)
    args = parser.parse_args()

    rows = read_csv_rows(args.input)
    registry = load_source_registry(args.source_registry)
    candidates, errors, warnings = build_candidates(rows, registry, args.input, args.source_code)
    source_codes = sorted({candidate.source_code for candidate in candidates})
    report: dict[str, Any] = {
        "input": str(args.input),
        "dry_run": not args.apply,
        "staging_only": True,
        "canonical_places_created": 0,
        "rows_read": len(rows),
        "valid_candidates": len(candidates),
        "source_codes": source_codes,
        "warnings": warnings,
        "errors": errors,
        "preview": [candidate.metadata for candidate in candidates[:5]],
    }
    if args.apply:
        if errors:
            report["applied"] = False
            print_json_report(report)
            raise SystemExit(1)
        report["apply_results"] = [
            apply_candidate_import(
                database_url=args.database_url,
                input_path=args.input,
                source_code=source_code,
                import_type="OPERATOR_MANUAL",
                candidates=[candidate for candidate in candidates if candidate.source_code == source_code],
                batch_metadata={"importer": "import_operator_place_seed", "staging_only": True},
            )
            for source_code in source_codes
        ]
    print_json_report(report)


if __name__ == "__main__":
    main()
