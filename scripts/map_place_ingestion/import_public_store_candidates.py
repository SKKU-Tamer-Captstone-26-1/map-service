from __future__ import annotations

if __package__ in {None, ""}:
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[2]))

import argparse
from pathlib import Path
from typing import Any

from scripts.map_place_ingestion.category_mapping import load_category_mapping, map_category_to_place_type
from scripts.map_place_ingestion.cli_common import (
    DEFAULT_BOOTSTRAP_ROOT,
    add_dry_run_apply_args,
    add_input_arg,
    load_source_registry,
    print_json_report,
    read_csv_rows,
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


def infer_source_code(row: dict[str, str], explicit_source_code: str | None) -> str:
    if explicit_source_code:
        return explicit_source_code
    if clean_text(row.get("상가업소번호")):
        return "SEMAS_STORE_20260331"
    if clean_text(row.get("MGTNO")):
        return "SEOUL_GENERAL_RESTAURANT_LICENSE"
    return "SEMAS_STORE_20260331"


def build_candidates(
    rows: list[dict[str, str]],
    source_registry: dict[str, dict[str, str]],
    input_path: Path,
    category_mapping_path: Path,
    explicit_source_code: str | None,
) -> tuple[list[CandidateInsert], list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    candidates: list[CandidateInsert] = []
    seen_external_ids: set[str] = set()
    rules = load_category_mapping(category_mapping_path)
    for index, row in enumerate(rows, start=2):
        row_errors: list[str] = []
        source_code = infer_source_code(row, explicit_source_code)
        registry_row = source_registry.get(source_code)
        if not registry_row:
            row_errors.append(f"row {index}: source_code not found in source registry: {source_code}")
            source_type = "PUBLIC_DATA"
            source_policy = "RESTRICTED"
        else:
            source_type = normalize_source_type(registry_row.get("source_type"))
            source_policy = normalize_source_policy(registry_row.get("source_policy"))
        if source_type != "PUBLIC_DATA":
            row_errors.append(f"row {index}: public candidate import requires PUBLIC_DATA source, got {source_type}")

        category_values = [
            row.get("candidate_place_type"),
            row.get("상권업종대분류명"),
            row.get("상권업종중분류명"),
            row.get("상권업종소분류명"),
            row.get("표준산업분류명"),
            row.get("DTLSTATENM"),
        ]
        if clean_text(row.get("candidate_place_type")):
            try:
                place_type = normalize_place_type(row.get("candidate_place_type"))
                mapping_notes = "candidate_place_type supplied by CSV"
                mapping_action = "needs_review"
            except ValueError as exc:
                row_errors.append(f"row {index}: {exc}")
                place_type = "OTHER"
                mapping_notes = str(exc)
                mapping_action = "needs_review"
        else:
            mapping = map_category_to_place_type(category_values, rules)
            place_type = mapping.place_type
            mapping_notes = mapping.notes or f"matched={mapping.matched_keyword}"
            mapping_action = mapping.action

        name = clean_text(row.get("canonical_name") or row.get("상호명") or row.get("BPLCNM"))
        address = clean_text(row.get("road_address") or row.get("도로명주소") or row.get("RDNWHLADDR") or row.get("address") or row.get("지번주소") or row.get("SITEWHLADDR"))
        lat_value = row.get("lat") or row.get("위도")
        lng_value = row.get("lng") or row.get("경도")
        coords = parse_lat_lng(lat_value, lng_value)
        review_status = normalize_review_status(row.get("review_status"), default="PENDING")
        quality_row = {**row, "canonical_name": name, "road_address": address, "candidate_place_type": place_type, "lat": lat_value, "lng": lng_value}
        findings = evaluate_place_candidate(
            quality_row,
            source_type=source_type,
            source_policy=source_policy,
            seen_external_ids=seen_external_ids,
        )
        if mapping_action in {"exclude_by_default", "optional_review"}:
            warnings.append(f"row {index}: category mapping action={mapping_action}; candidate remains staged for review")
        if final_decision(findings) == "reject_candidate":
            row_errors.extend(f"row {index}: {finding.rule_code}: {finding.message}" for finding in findings if finding.decision == "reject_candidate")
        if row_errors:
            errors.extend(row_errors)
            continue

        external_source_id = clean_text(row.get("external_source_id") or row.get("상가업소번호") or row.get("MGTNO"))
        missing_coords = coords.latitude is None or coords.longitude is None
        candidates.append(
            CandidateInsert(
                source_code=source_code,
                external_source_id=external_source_id,
                raw_payload=row,
                normalized_name=normalize_place_name(name),
                normalized_address=normalize_address(address),
                source_category_name=" / ".join(clean_text(value) for value in category_values if clean_text(value)) or None,
                candidate_place_type=place_type,
                latitude=coords.latitude,
                longitude=coords.longitude,
                review_status=review_status,
                metadata={
                    "canonical_name": name,
                    "geocode_required": missing_coords,
                    "mapping_action": mapping_action,
                    "mapping_notes": mapping_notes,
                    "operator_comment": clean_text(row.get("operator_comment")),
                    "quality_findings": [finding.__dict__ for finding in findings],
                },
                review_task_type="VERIFY_CLOSED" if any("CLOSED_LICENSE_STATUS" == finding.rule_code for finding in findings) else ("VERIFY_LOCATION" if missing_coords else "VERIFY_NEW_PLACE"),
                review_priority=60 if any("CLOSED_LICENSE_STATUS" == finding.rule_code for finding in findings) else 100,
            )
        )
    return candidates, errors, warnings


def main() -> None:
    parser = argparse.ArgumentParser(description="Import storage-permitted public data candidates into staging only.")
    add_input_arg(parser, default=DEFAULT_BOOTSTRAP_ROOT / "templates/semas_store_raw_filter_template.csv")
    parser.add_argument("--kind", choices=["semas", "seoul-license"], help="Compatibility hint for the CSV shape. Source is still inferred from rows unless --source-code is provided.")
    parser.add_argument("--source-registry", type=Path, default=DEFAULT_BOOTSTRAP_ROOT / "data/source_registry.csv")
    parser.add_argument("--category-mapping", type=Path, default=DEFAULT_BOOTSTRAP_ROOT / "data/category_mapping_seed.csv")
    parser.add_argument("--source-code", help="Override source_code for all rows.")
    add_dry_run_apply_args(parser)
    args = parser.parse_args()

    rows = read_csv_rows(args.input)
    registry = load_source_registry(args.source_registry)
    source_code = args.source_code
    if not source_code and args.kind == "seoul-license":
        source_code = "SEOUL_GENERAL_RESTAURANT_LICENSE"
    if not source_code and args.kind == "semas":
        source_code = "SEMAS_STORE_20260331"
    candidates, errors, warnings = build_candidates(rows, registry, args.input, args.category_mapping, source_code)
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
                import_type="PUBLIC_DATA_FILE",
                candidates=[candidate for candidate in candidates if candidate.source_code == source_code],
                batch_metadata={"importer": "import_public_store_candidates", "staging_only": True},
            )
            for source_code in source_codes
        ]
    print_json_report(report)


if __name__ == "__main__":
    main()
