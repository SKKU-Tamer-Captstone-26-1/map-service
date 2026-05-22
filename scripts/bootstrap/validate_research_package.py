from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BOOTSTRAP_DIR = REPO_ROOT / "data" / "bootstrap"

SOURCE_REGISTRY_FILE = "source_registry_research.csv"
CATEGORY_MAPPING_FILE = "category_mapping_research.csv"
DOWNLOAD_PLAN_FILE = "public_data_download_plan.csv"

SOURCE_REGISTRY_COLUMNS = {
    "source_name",
    "source_type",
    "official_url",
    "license_or_usage_terms",
    "storage_policy",
    "canonical_use_allowed",
    "default_target",
    "review_required",
    "expected_columns",
    "refresh_frequency",
    "notes",
}

CATEGORY_MAPPING_COLUMNS = {
    "source_name",
    "source_category_pattern",
    "target_category",
    "confidence",
    "review_required",
    "notes",
}

DOWNLOAD_PLAN_COLUMNS = {
    "step",
    "area_scope",
    "source_name",
    "official_url",
    "access_method",
    "policy_status",
    "storage_policy",
    "output_target",
    "preconditions",
    "notes",
}

STORAGE_POLICIES = {
    "storable",
    "restricted",
    "realtime_only",
    "unknown_needs_review",
}

DEFAULT_TARGETS = {
    "excluded",
    "needs_review",
    "place_import_candidates",
    "realtime_lookup",
}

TARGET_CATEGORIES = {
    "bar",
    "pub",
    "liquor_shop",
    "bottle_shop",
    "restaurant",
    "outdoor_spot",
    "convenience_store",
    "other",
    "excluded",
    "needs_review",
    "realtime_lookup",
}

CONFIDENCE_VALUES = {
    "none",
    "low",
    "medium",
    "high",
}

BOOLEAN_VALUES = {"true", "false"}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise RuntimeError(f"missing file: {path}")

    with path.open(encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None:
            raise RuntimeError(f"missing header: {path}")
        return [dict(row) for row in reader]


def missing_columns(rows: list[dict[str, str]], required: set[str]) -> list[str]:
    if not rows:
        return sorted(required)
    return sorted(required - set(rows[0]))


def is_kakao(row: dict[str, str]) -> bool:
    values = " ".join(row.values()).lower()
    return "kakao" in values or "카카오" in values


def check_bool(value: str) -> bool:
    return value.strip().lower() in BOOLEAN_VALUES


def validate_source_registry(rows: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    missing = missing_columns(rows, SOURCE_REGISTRY_COLUMNS)
    if missing:
        return [f"{SOURCE_REGISTRY_FILE}: missing columns: {missing}"]

    seen_names: set[str] = set()
    for index, row in enumerate(rows, start=2):
        source_name = row["source_name"].strip()
        storage_policy = row["storage_policy"].strip()
        canonical_use_allowed = row["canonical_use_allowed"].strip().lower()
        default_target = row["default_target"].strip()
        review_required = row["review_required"].strip().lower()

        if not source_name:
            errors.append(f"{SOURCE_REGISTRY_FILE}:{index}: source_name is required")
        elif source_name in seen_names:
            errors.append(f"{SOURCE_REGISTRY_FILE}:{index}: duplicate source_name: {source_name}")
        seen_names.add(source_name)

        if not row["official_url"].strip().startswith("https://"):
            errors.append(f"{SOURCE_REGISTRY_FILE}:{index}: official_url must be https")
        if storage_policy not in STORAGE_POLICIES:
            errors.append(f"{SOURCE_REGISTRY_FILE}:{index}: invalid storage_policy: {storage_policy}")
        if default_target not in DEFAULT_TARGETS:
            errors.append(f"{SOURCE_REGISTRY_FILE}:{index}: invalid default_target: {default_target}")
        if not check_bool(canonical_use_allowed):
            errors.append(f"{SOURCE_REGISTRY_FILE}:{index}: canonical_use_allowed must be true or false")
        if not check_bool(review_required):
            errors.append(f"{SOURCE_REGISTRY_FILE}:{index}: review_required must be true or false")
        if canonical_use_allowed == "true":
            errors.append(f"{SOURCE_REGISTRY_FILE}:{index}: canonical_use_allowed must remain false for research sources")
        if storage_policy == "realtime_only" and default_target != "realtime_lookup":
            errors.append(f"{SOURCE_REGISTRY_FILE}:{index}: realtime_only sources must target realtime_lookup")
        if is_kakao(row):
            if storage_policy != "realtime_only":
                errors.append(f"{SOURCE_REGISTRY_FILE}:{index}: Kakao source must be realtime_only")
            if canonical_use_allowed != "false":
                errors.append(f"{SOURCE_REGISTRY_FILE}:{index}: Kakao canonical_use_allowed must be false")

    return errors


def validate_category_mapping(rows: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    missing = missing_columns(rows, CATEGORY_MAPPING_COLUMNS)
    if missing:
        return [f"{CATEGORY_MAPPING_FILE}: missing columns: {missing}"]

    for index, row in enumerate(rows, start=2):
        target_category = row["target_category"].strip()
        confidence = row["confidence"].strip()
        review_required = row["review_required"].strip().lower()

        if not row["source_name"].strip():
            errors.append(f"{CATEGORY_MAPPING_FILE}:{index}: source_name is required")
        if target_category not in TARGET_CATEGORIES:
            errors.append(f"{CATEGORY_MAPPING_FILE}:{index}: invalid target_category: {target_category}")
        if confidence not in CONFIDENCE_VALUES:
            errors.append(f"{CATEGORY_MAPPING_FILE}:{index}: invalid confidence: {confidence}")
        if not check_bool(review_required):
            errors.append(f"{CATEGORY_MAPPING_FILE}:{index}: review_required must be true or false")
        if is_kakao(row) and target_category != "realtime_lookup":
            errors.append(f"{CATEGORY_MAPPING_FILE}:{index}: Kakao category target must be realtime_lookup")

    return errors


def validate_download_plan(rows: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    missing = missing_columns(rows, DOWNLOAD_PLAN_COLUMNS)
    if missing:
        return [f"{DOWNLOAD_PLAN_FILE}: missing columns: {missing}"]

    seen_steps: set[str] = set()
    for index, row in enumerate(rows, start=2):
        step = row["step"].strip()
        storage_policy = row["storage_policy"].strip()
        output_target = row["output_target"].strip()

        if not step:
            errors.append(f"{DOWNLOAD_PLAN_FILE}:{index}: step is required")
        elif step in seen_steps:
            errors.append(f"{DOWNLOAD_PLAN_FILE}:{index}: duplicate step: {step}")
        seen_steps.add(step)

        if not row["official_url"].strip().startswith("https://"):
            errors.append(f"{DOWNLOAD_PLAN_FILE}:{index}: official_url must be https")
        if storage_policy not in STORAGE_POLICIES:
            errors.append(f"{DOWNLOAD_PLAN_FILE}:{index}: invalid storage_policy: {storage_policy}")
        if output_target not in DEFAULT_TARGETS:
            errors.append(f"{DOWNLOAD_PLAN_FILE}:{index}: invalid output_target: {output_target}")
        if storage_policy == "realtime_only" and output_target != "realtime_lookup":
            errors.append(f"{DOWNLOAD_PLAN_FILE}:{index}: realtime_only sources must target realtime_lookup")
        if is_kakao(row):
            if storage_policy != "realtime_only":
                errors.append(f"{DOWNLOAD_PLAN_FILE}:{index}: Kakao source must be realtime_only")
            if output_target != "realtime_lookup":
                errors.append(f"{DOWNLOAD_PLAN_FILE}:{index}: Kakao output_target must be realtime_lookup")

    return errors


def validate(bootstrap_dir: Path) -> dict[str, Any]:
    source_registry = read_csv(bootstrap_dir / SOURCE_REGISTRY_FILE)
    category_mapping = read_csv(bootstrap_dir / CATEGORY_MAPPING_FILE)
    download_plan = read_csv(bootstrap_dir / DOWNLOAD_PLAN_FILE)

    errors = [
        *validate_source_registry(source_registry),
        *validate_category_mapping(category_mapping),
        *validate_download_plan(download_plan),
    ]

    return {
        "ok": not errors,
        "bootstrap_dir": str(bootstrap_dir),
        "files": {
            SOURCE_REGISTRY_FILE: len(source_registry),
            CATEGORY_MAPPING_FILE: len(category_mapping),
            DOWNLOAD_PLAN_FILE: len(download_plan),
        },
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate research-only map/place bootstrap CSV policy files.")
    parser.add_argument("--bootstrap-dir", type=Path, default=DEFAULT_BOOTSTRAP_DIR)
    args = parser.parse_args()

    report = validate(args.bootstrap_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
