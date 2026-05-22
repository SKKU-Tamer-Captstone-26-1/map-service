from __future__ import annotations

if __package__ in {None, ""}:
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[2]))

import argparse
from pathlib import Path

from scripts.map_place_ingestion.cli_common import DEFAULT_BOOTSTRAP_ROOT, add_bootstrap_arg, print_json_report


EXPECTED_FILES = [
    "manifest.json",
    "data/source_registry.csv",
    "data/seoul_hangang_outdoor_spot_seed_candidates.csv",
    "data/category_mapping_seed.csv",
    "data/data_quality_rules.csv",
    "sql/seed_data_sources.sql",
    "sql/seed_basic_tags.sql",
]

EXPECTED_DIRS = ["data", "templates", "docs", "sql"]


def validate_package(root: Path) -> dict[str, object]:
    missing_files = [path for path in EXPECTED_FILES if not (root / path).is_file()]
    missing_dirs = [path for path in EXPECTED_DIRS if not (root / path).is_dir()]
    return {
        "package_root": str(root),
        "package_root_exists": root.is_dir(),
        "missing_files": missing_files,
        "missing_dirs": missing_dirs,
        "ok": root.is_dir() and not missing_files and not missing_dirs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the extracted map/place bootstrap package.")
    add_bootstrap_arg(parser)
    parser.add_argument("--input", type=Path, help="Alias for --bootstrap-root.")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Validation only. This command never writes.")
    args = parser.parse_args()
    print_json_report(validate_package(args.input or args.bootstrap_root or DEFAULT_BOOTSTRAP_ROOT))


if __name__ == "__main__":
    main()
