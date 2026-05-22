from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BOOTSTRAP_DIR = REPO_ROOT / "data" / "bootstrap"

SOURCE_REGISTRY_FILE = "source_registry_research.csv"
CATEGORY_MAPPING_FILE = "category_mapping_research.csv"

SMBA_SOURCE = "소상공인시장진흥공단_상가(상권)정보_API"
MOIS_GENERAL_FOOD_SOURCE = "행정안전부_식품_일반음식점 조회서비스"


@dataclass(frozen=True)
class SourceConfig:
    required_columns: tuple[str, ...]
    id_column: str
    name_column: str
    category_column: str
    address_columns: tuple[str, ...]
    longitude_column: str | None = None
    latitude_column: str | None = None
    source_x_column: str | None = None
    source_y_column: str | None = None
    status_columns: tuple[str, ...] = ()
    coordinate_system: str = "WGS84"


SOURCE_CONFIGS = {
    SMBA_SOURCE: SourceConfig(
        required_columns=("상가업소번호", "상호명", "상권업종명", "도로명주소", "경도", "위도"),
        id_column="상가업소번호",
        name_column="상호명",
        category_column="상권업종명",
        address_columns=("도로명주소",),
        longitude_column="경도",
        latitude_column="위도",
    ),
    MOIS_GENERAL_FOOD_SOURCE: SourceConfig(
        required_columns=(
            "관리번호",
            "영업상태명",
            "상세영업상태명",
            "사업장명",
            "도로명전체주소",
            "소재지전체주소",
            "업태구분명",
            "좌표정보(X)",
            "좌표정보(Y)",
        ),
        id_column="관리번호",
        name_column="사업장명",
        category_column="업태구분명",
        address_columns=("도로명전체주소", "소재지전체주소"),
        source_x_column="좌표정보(X)",
        source_y_column="좌표정보(Y)",
        status_columns=("영업상태명", "상세영업상태명"),
        coordinate_system="EPSG:5174",
    ),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise RuntimeError(f"missing file: {path}")

    with path.open(encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None:
            raise RuntimeError(f"missing header: {path}")
        return [dict(row) for row in reader]


def normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def parse_float(value: str | None) -> float | None:
    text = normalize_text(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def is_kakao_source(source_name: str) -> bool:
    source_name_lower = source_name.lower()
    return "kakao" in source_name_lower or "카카오" in source_name_lower


def load_source_registry(bootstrap_dir: Path) -> dict[str, dict[str, str]]:
    rows = read_csv(bootstrap_dir / SOURCE_REGISTRY_FILE)
    return {normalize_text(row.get("source_name")): row for row in rows}


def load_category_mappings(bootstrap_dir: Path, source_name: str) -> list[dict[str, str]]:
    rows = read_csv(bootstrap_dir / CATEGORY_MAPPING_FILE)
    return [row for row in rows if normalize_text(row.get("source_name")) == source_name]


def ensure_source_allowed(source_name: str, source_registry: dict[str, dict[str, str]]) -> dict[str, str]:
    if source_name not in source_registry:
        raise RuntimeError(f"source not found in registry: {source_name}")
    if is_kakao_source(source_name):
        raise RuntimeError("Kakao sources are realtime_only and cannot be normalized into candidate payloads")
    if source_name not in SOURCE_CONFIGS:
        raise RuntimeError(f"source is not supported by the sample normalizer: {source_name}")

    source = source_registry[source_name]
    storage_policy = normalize_text(source.get("storage_policy"))
    default_target = normalize_text(source.get("default_target"))
    canonical_use_allowed = normalize_text(source.get("canonical_use_allowed")).lower()

    if storage_policy != "storable":
        raise RuntimeError(f"source storage_policy must be storable: {source_name}={storage_policy}")
    if default_target != "place_import_candidates":
        raise RuntimeError(f"source default_target must be place_import_candidates: {source_name}={default_target}")
    if canonical_use_allowed != "false":
        raise RuntimeError(f"source canonical_use_allowed must be false in research mode: {source_name}")

    return source


def validate_columns(rows: list[dict[str, str]], source_name: str, config: SourceConfig) -> list[str]:
    if not rows:
        return [f"{source_name}: input has no rows"]

    actual_columns = set(rows[0])
    missing = [column for column in config.required_columns if column not in actual_columns]
    if missing:
        return [f"{source_name}: missing input columns: {missing}"]
    return []


def match_contains(pattern: str, value: str) -> bool:
    terms = [normalize_text(term) for term in pattern.split(" or ")]
    return any(term and term in value for term in terms)


def match_in(pattern: str, value: str) -> bool:
    terms = [normalize_text(term) for term in pattern.split("|")]
    return value in terms


def mapping_matches(pattern: str, category_value: str) -> bool:
    pattern = normalize_text(pattern)
    if pattern == "any":
        return True
    if " contains " in pattern:
        return match_contains(pattern.split(" contains ", 1)[1], category_value)
    if " in " in pattern:
        return match_in(pattern.split(" in ", 1)[1], category_value)
    if " exists" in pattern:
        return bool(category_value)
    return False


def map_category(category_value: str, mappings: list[dict[str, str]]) -> dict[str, str]:
    for mapping in mappings:
        if mapping_matches(mapping["source_category_pattern"], category_value):
            return {
                "candidate_place_type": normalize_text(mapping.get("target_category")) or "needs_review",
                "mapping_confidence": normalize_text(mapping.get("confidence")) or "none",
                "mapping_review_required": normalize_text(mapping.get("review_required")).lower() != "false",
                "mapping_notes": normalize_text(mapping.get("notes")),
            }

    return {
        "candidate_place_type": "needs_review",
        "mapping_confidence": "none",
        "mapping_review_required": True,
        "mapping_notes": "No category mapping matched",
    }


def is_active_row(row: dict[str, str], config: SourceConfig) -> bool:
    if not config.status_columns:
        return True

    status_text = " ".join(normalize_text(row.get(column)) for column in config.status_columns)
    inactive_tokens = ("폐업", "취소", "말소", "정지")
    active_tokens = ("영업", "정상")
    if any(token in status_text for token in inactive_tokens):
        return False
    return any(token in status_text for token in active_tokens)


def choose_address(row: dict[str, str], config: SourceConfig) -> str:
    for column in config.address_columns:
        address = normalize_text(row.get(column))
        if address:
            return address
    return ""


def coordinates(row: dict[str, str], config: SourceConfig) -> tuple[float | None, float | None, str, dict[str, Any]]:
    metadata: dict[str, Any] = {"coordinate_system": config.coordinate_system}

    if config.coordinate_system == "WGS84":
        longitude = parse_float(row.get(config.longitude_column or ""))
        latitude = parse_float(row.get(config.latitude_column or ""))
        if longitude is None or latitude is None:
            return None, None, "missing_wgs84", metadata
        if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
            return latitude, longitude, "invalid_wgs84_range", metadata
        return latitude, longitude, "wgs84_valid", metadata

    source_x = normalize_text(row.get(config.source_x_column or ""))
    source_y = normalize_text(row.get(config.source_y_column or ""))
    metadata["source_x"] = source_x
    metadata["source_y"] = source_y
    return None, None, "needs_coordinate_transform", metadata


def normalize_row(
    *,
    row: dict[str, str],
    row_number: int,
    source_name: str,
    source: dict[str, str],
    config: SourceConfig,
    mappings: list[dict[str, str]],
) -> dict[str, Any]:
    source_category_name = normalize_text(row.get(config.category_column))
    category = map_category(source_category_name, mappings)
    latitude, longitude, location_status, coordinate_metadata = coordinates(row, config)

    metadata_json = {
        "input_row_number": row_number,
        "official_url": normalize_text(source.get("official_url")),
        "license_or_usage_terms": normalize_text(source.get("license_or_usage_terms")),
        "sample_fixture": True,
        **coordinate_metadata,
    }

    return {
        "source_name": source_name,
        "source_policy": normalize_text(source.get("storage_policy")),
        "default_target": normalize_text(source.get("default_target")),
        "external_source_id": normalize_text(row.get(config.id_column)),
        "raw_payload_json": row,
        "normalized_name": normalize_text(row.get(config.name_column)),
        "normalized_address": choose_address(row, config),
        "source_category_name": source_category_name,
        "candidate_place_type": category["candidate_place_type"],
        "latitude": latitude,
        "longitude": longitude,
        "location_status": location_status,
        "review_status": "PENDING",
        "review_required": True,
        "mapping_confidence": category["mapping_confidence"],
        "mapping_review_required": category["mapping_review_required"],
        "mapping_notes": category["mapping_notes"],
        "metadata_json": metadata_json,
    }


def normalize_sample(
    *,
    input_path: Path,
    source_name: str,
    bootstrap_dir: Path,
    limit: int | None = None,
) -> dict[str, Any]:
    source_name = normalize_text(source_name)
    source_registry = load_source_registry(bootstrap_dir)
    source = ensure_source_allowed(source_name, source_registry)
    config = SOURCE_CONFIGS[source_name]
    mappings = load_category_mappings(bootstrap_dir, source_name)
    rows = read_csv(input_path)
    errors = validate_columns(rows, source_name, config)
    if errors:
        return {
            "ok": False,
            "dry_run": True,
            "source_name": source_name,
            "input_path": str(input_path),
            "errors": errors,
        }

    candidates: list[dict[str, Any]] = []
    skipped_rows: list[dict[str, Any]] = []
    warnings: list[str] = []

    for row_number, row in enumerate(rows, start=2):
        if limit is not None and len(candidates) >= limit:
            break
        if not is_active_row(row, config):
            skipped_rows.append(
                {
                    "input_row_number": row_number,
                    "external_source_id": normalize_text(row.get(config.id_column)),
                    "reason": "inactive_or_closed_status",
                }
            )
            continue

        candidate = normalize_row(
            row=row,
            row_number=row_number,
            source_name=source_name,
            source=source,
            config=config,
            mappings=mappings,
        )
        if candidate["location_status"] != "wgs84_valid":
            warnings.append(
                f"row {row_number}: location_status={candidate['location_status']} "
                "requires review before publish"
            )
        candidates.append(candidate)

    return {
        "ok": True,
        "dry_run": True,
        "source_name": source_name,
        "input_path": str(input_path),
        "bootstrap_dir": str(bootstrap_dir),
        "candidate_count": len(candidates),
        "skipped_count": len(skipped_rows),
        "warnings": warnings,
        "skipped_rows": skipped_rows,
        "candidates": candidates,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize a local public-data sample CSV into candidate JSON.")
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--input", required=True, type=Path, dest="input_path")
    parser.add_argument("--bootstrap-dir", type=Path, default=DEFAULT_BOOTSTRAP_DIR)
    parser.add_argument("--limit", type=int, help="Maximum number of active candidates to emit.")
    args = parser.parse_args()

    try:
        report = normalize_sample(
            input_path=args.input_path,
            source_name=args.source_name,
            bootstrap_dir=args.bootstrap_dir,
            limit=args.limit,
        )
    except RuntimeError as error:
        report = {
            "ok": False,
            "dry_run": True,
            "source_name": normalize_text(args.source_name),
            "input_path": str(args.input_path),
            "bootstrap_dir": str(args.bootstrap_dir),
            "errors": [str(error)],
        }

    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
