from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.bootstrap.normalize_public_data_sample import (
    DEFAULT_BOOTSTRAP_DIR,
    SMBA_SOURCE,
    SOURCE_CONFIGS,
    choose_address,
    coordinates,
    ensure_source_allowed,
    is_kakao_source,
    load_category_mappings,
    load_source_registry,
    map_category,
    normalize_text,
)


DEFAULT_RAW_DIR = REPO_ROOT / "data" / "raw"
DEFAULT_NORMALIZED_DIR = REPO_ROOT / "data" / "normalized"
DEFAULT_ENV_PATH = REPO_ROOT / ".env"
SERVICE_KEY_ENV = "DATA_GO_KR_SERVICE_KEY"
PLACEHOLDER_KEY = "replace-with-local-data-go-kr-service-key"

SMBA_STORE_LIST_IN_DONG_URL = "https://apis.data.go.kr/B553077/api/open/sdsc2/storeListInDong"
DEFAULT_SOURCE = SMBA_SOURCE
DEFAULT_DIV_ID = "signguCd"
DEFAULT_AREA_KEY = "11440"


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


def resolve_service_key(explicit_key: str | None, env_path: Path) -> str:
    load_env_file(env_path)
    service_key = explicit_key or os.environ.get(SERVICE_KEY_ENV, "")
    service_key = service_key.strip()
    if not service_key or service_key == PLACEHOLDER_KEY:
        raise RuntimeError(
            f"missing {SERVICE_KEY_ENV}. Put your real key in local .env or pass --service-key. "
            "Never commit the real key."
        )
    return service_key


def slugify(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z._-]+", "_", value).strip("_") or "source"


def timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def request_json(url: str, params: dict[str, str], timeout: int) -> tuple[str, dict[str, Any]]:
    query = urllib.parse.urlencode(params, safe="%")
    request_url = f"{url}?{query}"
    request = urllib.request.Request(request_url, headers={"User-Agent": "map-service-dry-run-fetcher/1.0"})
    with urllib.request.urlopen(request, timeout=timeout, context=ssl_context()) as response:
        body = response.read().decode("utf-8")
    return request_url, json.loads(body)


def ssl_context() -> ssl.SSLContext:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def mask_url(url: str, service_key: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    masked_query = urllib.parse.urlencode(
        [
            (key, "***" if key == "serviceKey" else value)
            for key, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        ],
        safe="*",
    )
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, masked_query, parsed.fragment))


def smba_items(response_json: dict[str, Any]) -> list[dict[str, Any]]:
    body = response_json.get("body")
    if not isinstance(body, dict):
        return []
    items = body.get("items")
    if items is None:
        return []
    if isinstance(items, dict):
        return [items]
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    return []


def normalize_api_row(
    *,
    row: dict[str, Any],
    row_number: int,
    source_name: str,
    source: dict[str, str],
    mappings: list[dict[str, str]],
) -> dict[str, Any]:
    config = SOURCE_CONFIGS[source_name]
    canonical_row = canonicalize_api_row(row, source_name)
    string_row = {key: "" if value is None else str(value) for key, value in canonical_row.items()}
    source_category_name = normalize_text(string_row.get(config.category_column))
    category = map_category(source_category_name, mappings)
    latitude, longitude, location_status, coordinate_metadata = coordinates(string_row, config)

    return {
        "source_name": source_name,
        "source_policy": normalize_text(source.get("storage_policy")),
        "default_target": normalize_text(source.get("default_target")),
        "external_source_id": normalize_text(string_row.get(config.id_column)),
        "raw_payload_json": row,
        "normalized_name": normalize_text(string_row.get(config.name_column)),
        "normalized_address": choose_address(string_row, config),
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
        "metadata_json": {
            "input_row_number": row_number,
            "official_url": normalize_text(source.get("official_url")),
            "license_or_usage_terms": normalize_text(source.get("license_or_usage_terms")),
            "sample_fixture": False,
            **coordinate_metadata,
        },
    }


def first_value(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = row.get(key)
        if normalize_text(None if value is None else str(value)):
            return value
    return ""


def canonicalize_api_row(row: dict[str, Any], source_name: str) -> dict[str, Any]:
    if source_name != SMBA_SOURCE:
        return row

    canonical = dict(row)
    canonical.update(
        {
            "상가업소번호": first_value(row, ("상가업소번호", "bizesId")),
            "상호명": first_value(row, ("상호명", "bizesNm")),
            "상권업종명": first_value(row, ("상권업종명", "indsSclsNm", "indsMclsNm", "indsLclsNm")),
            "도로명주소": first_value(row, ("도로명주소", "rdnmAdr", "lnoAdr")),
            "경도": first_value(row, ("경도", "lon")),
            "위도": first_value(row, ("위도", "lat")),
        }
    )
    return canonical


def ensure_supported_source(source_name: str) -> None:
    if source_name != SMBA_SOURCE:
        raise RuntimeError(f"real fetch currently supports only {SMBA_SOURCE}; got {source_name}")
    if is_kakao_source(source_name):
        raise RuntimeError("Kakao sources are realtime_only and cannot be fetched into candidate payloads")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def collect_smba(
    *,
    service_key: str,
    source_name: str,
    div_id: str,
    area_key: str,
    inds_lcls_cd: str | None,
    inds_mcls_cd: str | None,
    inds_scls_cd: str | None,
    page_no: int,
    num_rows: int,
    bootstrap_dir: Path,
    raw_dir: Path,
    normalized_dir: Path,
    timeout: int,
) -> dict[str, Any]:
    ensure_supported_source(source_name)
    source_registry = load_source_registry(bootstrap_dir)
    source = ensure_source_allowed(source_name, source_registry)
    mappings = load_category_mappings(bootstrap_dir, source_name)

    requested_at = timestamp()
    params = {
        "serviceKey": service_key,
        "divId": div_id,
        "key": area_key,
        "pageNo": str(page_no),
        "numOfRows": str(num_rows),
        "type": "json",
    }
    if inds_lcls_cd:
        params["indsLclsCd"] = inds_lcls_cd
    if inds_mcls_cd:
        params["indsMclsCd"] = inds_mcls_cd
    if inds_scls_cd:
        params["indsSclsCd"] = inds_scls_cd

    request_url, response_json = request_json(SMBA_STORE_LIST_IN_DONG_URL, params, timeout)
    items = smba_items(response_json)
    candidates = [
        normalize_api_row(
            row=item,
            row_number=index,
            source_name=source_name,
            source=source,
            mappings=mappings,
        )
        for index, item in enumerate(items, start=1)
    ]

    source_slug = slugify(source_name)
    filter_slug = "_".join(
        slugify(value)
        for value in (inds_lcls_cd or "", inds_mcls_cd or "", inds_scls_cd or "")
        if value
    )
    area_slug = f"{div_id}_{area_key}"
    if filter_slug:
        area_slug = f"{area_slug}_{filter_slug}"
    run_slug = f"{requested_at}_{source_slug}_{area_slug}_p{page_no}_n{num_rows}"
    raw_path = raw_dir / f"{run_slug}.json"
    normalized_path = normalized_dir / f"{run_slug}.candidates.json"

    raw_payload = {
        "dry_run": True,
        "source_name": source_name,
        "requested_at": requested_at,
        "request_url_masked": mask_url(request_url, service_key),
        "params": {**params, "serviceKey": "***"},
        "response_json": response_json,
    }
    normalized_payload = {
        "dry_run": True,
        "source_name": source_name,
        "requested_at": requested_at,
        "raw_path": str(raw_path),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "warnings": [
            f"candidate {candidate['external_source_id']}: location_status={candidate['location_status']}"
            for candidate in candidates
            if candidate["location_status"] != "wgs84_valid"
        ],
    }

    write_json(raw_path, raw_payload)
    write_json(normalized_path, normalized_payload)

    return {
        "ok": True,
        "dry_run": True,
        "source_name": source_name,
        "requested_at": requested_at,
        "request_url_masked": mask_url(request_url, service_key),
        "raw_path": str(raw_path),
        "normalized_path": str(normalized_path),
        "item_count": len(items),
        "candidate_count": len(candidates),
        "warnings": normalized_payload["warnings"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch official public data into ignored dry-run files.")
    parser.add_argument("--source-name", default=DEFAULT_SOURCE)
    parser.add_argument("--div-id", default=DEFAULT_DIV_ID, help="SMBA area divider, e.g. signguCd.")
    parser.add_argument("--area-key", default=DEFAULT_AREA_KEY, help="SMBA area code. Default is Seoul Mapo-gu.")
    parser.add_argument("--inds-lcls-cd", help="Optional SMBA large industry code filter.")
    parser.add_argument("--inds-mcls-cd", help="Optional SMBA medium industry code filter.")
    parser.add_argument("--inds-scls-cd", help="Optional SMBA small industry code filter.")
    parser.add_argument("--page-no", type=int, default=1)
    parser.add_argument("--num-rows", type=int, default=10)
    parser.add_argument("--bootstrap-dir", type=Path, default=DEFAULT_BOOTSTRAP_DIR)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--normalized-dir", type=Path, default=DEFAULT_NORMALIZED_DIR)
    parser.add_argument("--env-path", type=Path, default=DEFAULT_ENV_PATH)
    parser.add_argument("--service-key", help="Optional override. Prefer DATA_GO_KR_SERVICE_KEY in local .env.")
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()

    try:
        service_key = resolve_service_key(args.service_key, args.env_path)
        report = collect_smba(
            service_key=service_key,
            source_name=args.source_name,
            div_id=args.div_id,
            area_key=args.area_key,
            inds_lcls_cd=args.inds_lcls_cd,
            inds_mcls_cd=args.inds_mcls_cd,
            inds_scls_cd=args.inds_scls_cd,
            page_no=args.page_no,
            num_rows=args.num_rows,
            bootstrap_dir=args.bootstrap_dir,
            raw_dir=args.raw_dir,
            normalized_dir=args.normalized_dir,
            timeout=args.timeout,
        )
    except Exception as error:
        report = {
            "ok": False,
            "dry_run": True,
            "source_name": normalize_text(args.source_name),
            "errors": [str(error)],
        }

    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
