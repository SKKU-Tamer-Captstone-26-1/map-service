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
    parse_bool,
    parse_lat_lng,
)
from scripts.map_place_ingestion.quality_rules import evaluate_place_candidate, final_decision
from scripts.map_place_ingestion.staging import CandidateInsert, apply_candidate_import


def build_candidates(rows: list[dict[str, str]], source_registry: dict[str, dict[str, str]], input_path: Path) -> tuple[list[CandidateInsert], list[str], list[str]]:
    errors = require_columns(rows, ["external_source_id", "source_code", "candidate_place_type", "canonical_name"], input_path)
    warnings: list[str] = []
    candidates: list[CandidateInsert] = []
    seen_external_ids: set[str] = set()
    for index, row in enumerate(rows, start=2):
        row_errors: list[str] = []
        source_code = clean_text(row.get("source_code"))
        registry_row = source_registry.get(source_code)
        if not registry_row:
            row_errors.append(f"row {index}: source_code not found in source registry: {source_code}")
            source_type = "PUBLIC_DATA"
            source_policy = "RESTRICTED"
        else:
            source_type = normalize_source_type(registry_row.get("source_type"))
            source_policy = normalize_source_policy(registry_row.get("source_policy"))
        try:
            place_type = normalize_place_type(row.get("candidate_place_type"))
        except ValueError as exc:
            row_errors.append(f"row {index}: {exc}")
            place_type = "OUTDOOR_SPOT"
        coords = parse_lat_lng(row.get("lat"), row.get("lng"))
        geocode_required = parse_bool(row.get("geocode_required")) or coords.latitude is None or coords.longitude is None
        normalized_name = normalize_place_name(row.get("normalized_name") or row.get("canonical_name"))
        normalized_address = normalize_address(row.get("road_address") or row.get("address"))
        review_status = normalize_review_status(row.get("review_status"), default="PENDING")
        findings = evaluate_place_candidate(
            {**row, "candidate_place_type": place_type},
            source_type=source_type,
            source_policy=source_policy,
            seen_external_ids=seen_external_ids,
        )
        if geocode_required:
            warnings.append(f"row {index}: coordinates missing; geocode_required metadata will be set")
        if final_decision(findings) == "reject_candidate":
            row_errors.extend(f"row {index}: {finding.rule_code}: {finding.message}" for finding in findings if finding.decision == "reject_candidate")
        if row_errors:
            errors.extend(row_errors)
            continue
        candidates.append(
            CandidateInsert(
                source_code=source_code,
                external_source_id=clean_text(row.get("external_source_id")),
                raw_payload=row,
                normalized_name=normalized_name,
                normalized_address=normalized_address,
                source_category_name="outdoor_spot",
                candidate_place_type=place_type,
                latitude=coords.latitude,
                longitude=coords.longitude,
                review_status=review_status,
                metadata={
                    "canonical_name": clean_text(row.get("canonical_name")),
                    "geocode_required": geocode_required,
                    "operator_comment": clean_text(row.get("operator_comment")),
                    "source_url": clean_text(row.get("source_url")),
                    "quality_findings": [finding.__dict__ for finding in findings],
                },
                review_task_type="VERIFY_LOCATION" if geocode_required else "VERIFY_NEW_PLACE",
                review_priority=80 if geocode_required else 100,
            )
        )
    return candidates, errors, warnings


def main() -> None:
    parser = argparse.ArgumentParser(description="Import outdoor spot seed candidates into staging/review tables only.")
    add_input_arg(parser, default=DEFAULT_BOOTSTRAP_ROOT / "data/seoul_hangang_outdoor_spot_seed_candidates.csv")
    parser.add_argument("--source-registry", type=str, default=str(DEFAULT_BOOTSTRAP_ROOT / "data/source_registry.csv"))
    add_dry_run_apply_args(parser)
    args = parser.parse_args()

    rows = read_csv_rows(args.input)
    registry = load_source_registry(args.input.parent / "source_registry.csv" if args.source_registry == "AUTO" else Path(args.source_registry))
    candidates, errors, warnings = build_candidates(rows, registry, args.input)
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
        apply_results = []
        for source_code in source_codes:
            source_candidates = [candidate for candidate in candidates if candidate.source_code == source_code]
            apply_results.append(
                apply_candidate_import(
                    database_url=args.database_url,
                    input_path=args.input,
                    source_code=source_code,
                    import_type="PUBLIC_DATA_FILE",
                    candidates=source_candidates,
                    batch_metadata={"importer": "import_outdoor_spot_candidates", "staging_only": True},
                )
            )
        report["apply_results"] = apply_results
    print_json_report(report)


if __name__ == "__main__":
    main()
