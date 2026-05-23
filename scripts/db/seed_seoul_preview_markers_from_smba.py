from __future__ import annotations

import argparse
import json
import sys
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.bootstrap.fetch_public_data_dry_run import (
    DEFAULT_ENV_PATH,
    SERVICE_KEY_ENV,
    SMBA_STORE_LIST_IN_DONG_URL,
    mask_url,
    request_json,
    resolve_service_key,
    smba_items,
)
from scripts.db.verify_map_view_schema import resolve_database_url


SMBA_SOURCE_NAME = "소상공인시장진흥공단_상가(상권)정보_API"
SMBA_OFFICIAL_URL = "https://www.data.go.kr/data/15012005/openapi.do"
SMBA_LICENSE = "이용허락범위 제한 없음"
PREVIEW_SOURCE = "smba_public_data_preview"
SEOUL_CTPRVN_CODE = "11"
DEFAULT_NUM_ROWS = 1000
DEFAULT_MAX_PAGES = 1
USER_AGENT = "map-service-seoul-preview-seed/1.0"

SEOUL_BBOX = (126.70, 37.40, 127.20, 37.75)
EXCLUDED_CATEGORY_TOKENS = ("유흥",)


@dataclass(frozen=True)
class CategoryRule:
    inds_scls_cd: str
    layer_code: str
    source_category_name: str
    review_note: str


CATEGORY_RULES = (
    CategoryRule(
        inds_scls_cd="I21103",
        layer_code="pub",
        source_category_name="생맥주 전문",
        review_note="Alcohol venue preview only; verify before canonical promotion.",
    ),
    CategoryRule(
        inds_scls_cd="I21104",
        layer_code="bar",
        source_category_name="요리 주점",
        review_note="Ambiguous bar/pub preview only; verify before canonical promotion.",
    ),
    CategoryRule(
        inds_scls_cd="G20602",
        layer_code="liquor_shop",
        source_category_name="주류 소매업",
        review_note="Liquor retail preview only; verify active business before canonical promotion.",
    ),
)
CATEGORY_RULES_BY_CODE = {rule.inds_scls_cd: rule for rule in CATEGORY_RULES}


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat()


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def parse_float(value: Any) -> float | None:
    try:
        return float(text(value))
    except ValueError:
        return None


def in_seoul_bbox(*, longitude: float, latitude: float) -> bool:
    min_lon, min_lat, max_lon, max_lat = SEOUL_BBOX
    return min_lon <= longitude <= max_lon and min_lat <= latitude <= max_lat


def source_category_text(row: dict[str, Any]) -> str:
    return " ".join(
        value
        for value in (
            text(row.get("indsLclsNm")),
            text(row.get("indsMclsNm")),
            text(row.get("indsSclsNm")),
        )
        if value
    )


def skip_reason(row: dict[str, Any], rule: CategoryRule) -> str | None:
    source_category = source_category_text(row)
    if any(token in source_category for token in EXCLUDED_CATEGORY_TOKENS):
        return "excluded_adult_nightlife"

    if text(row.get("indsSclsCd")) and text(row.get("indsSclsCd")) != rule.inds_scls_cd:
        return "unexpected_source_category"

    external_id = text(row.get("bizesId"))
    if not external_id:
        return "missing_source_id"

    label = text(row.get("bizesNm"))
    if not label:
        return "missing_label"

    longitude = parse_float(row.get("lon"))
    latitude = parse_float(row.get("lat"))
    if longitude is None or latitude is None:
        return "missing_location"
    if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
        return "invalid_wgs84_location"
    if not in_seoul_bbox(longitude=longitude, latitude=latitude):
        return "outside_seoul_bbox"

    return None


def marker_uuid(source_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"map-service:{PREVIEW_SOURCE}:marker:{source_id}"))


def place_ref_uuid(source_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"map-service:{PREVIEW_SOURCE}:place:{source_id}"))


def build_marker(row: dict[str, Any], rule: CategoryRule, *, fetched_at: str) -> dict[str, Any] | None:
    if skip_reason(row, rule):
        return None

    source_id = text(row.get("bizesId"))
    road_address = text(row.get("rdnmAdr"))
    lot_address = text(row.get("lnoAdr"))
    source_category_code = text(row.get("indsSclsCd")) or rule.inds_scls_cd
    source_category_name = text(row.get("indsSclsNm")) or rule.source_category_name

    return {
        "id": marker_uuid(source_id),
        "place_ref": place_ref_uuid(source_id),
        "layer_code": rule.layer_code,
        "label": text(row.get("bizesNm")),
        "longitude": parse_float(row.get("lon")),
        "latitude": parse_float(row.get("lat")),
        "geohash": None,
        "icon_key": None,
        "filter_json": {
            "source": PREVIEW_SOURCE,
            "source_name": SMBA_SOURCE_NAME,
            "source_id": source_id,
            "source_category_code": source_category_code,
            "source_category_name": source_category_name,
            "source_medium_category_code": text(row.get("indsMclsCd")),
            "source_medium_category_name": text(row.get("indsMclsNm")),
            "source_large_category_code": text(row.get("indsLclsCd")),
            "source_large_category_name": text(row.get("indsLclsNm")),
            "canonical": False,
            "preview_only": True,
            "review_required": True,
            "review_status": "PENDING",
            "review_note": rule.review_note,
            "official_url": SMBA_OFFICIAL_URL,
            "license_or_usage_terms": SMBA_LICENSE,
            "address": road_address or lot_address,
            "road_address": road_address,
            "lot_address": lot_address,
            "district": text(row.get("signguNm")),
            "administrative_dong": text(row.get("adongNm")),
            "fetched_at": fetched_at,
        },
        "published_revision": 1,
    }


def page_total_count(response_json: dict[str, Any], item_count: int) -> int:
    body = response_json.get("body")
    if not isinstance(body, dict):
        return item_count
    try:
        return int(body.get("totalCount") or item_count)
    except (TypeError, ValueError):
        return item_count


def fetch_category_markers(
    *,
    service_key: str,
    rule: CategoryRule,
    all_pages: bool,
    max_pages: int,
    num_rows: int,
    timeout: int,
    fetched_at: str,
) -> dict[str, Any]:
    if num_rows < 1 or num_rows > DEFAULT_NUM_ROWS:
        raise RuntimeError(f"--num-rows must be between 1 and {DEFAULT_NUM_ROWS}")
    if max_pages < 1:
        raise RuntimeError("--max-pages must be at least 1")

    page_no = 1
    markers_by_place_ref: dict[str, dict[str, Any]] = {}
    skipped: Counter[str] = Counter()
    total_count = 0
    request_urls: list[str] = []

    while True:
        params = {
            "serviceKey": service_key,
            "divId": "ctprvnCd",
            "key": SEOUL_CTPRVN_CODE,
            "pageNo": str(page_no),
            "numOfRows": str(num_rows),
            "type": "json",
            "indsSclsCd": rule.inds_scls_cd,
        }
        request_url, response_json = request_json(SMBA_STORE_LIST_IN_DONG_URL, params, timeout)
        request_urls.append(mask_url(request_url, service_key))

        items = smba_items(response_json)
        total_count = max(total_count, page_total_count(response_json, len(items)))
        for item in items:
            reason = skip_reason(item, rule)
            if reason:
                skipped[reason] += 1
                continue
            marker = build_marker(item, rule, fetched_at=fetched_at)
            if marker is None:
                skipped["unmapped"] += 1
                continue
            markers_by_place_ref[marker["place_ref"]] = marker

        if page_no * num_rows >= total_count:
            break
        if not all_pages and page_no >= max_pages:
            break
        page_no += 1

    markers = list(markers_by_place_ref.values())
    return {
        "rule": rule,
        "total_count": total_count,
        "pages_fetched": page_no,
        "request_urls": request_urls,
        "markers": markers,
        "skipped": dict(sorted(skipped.items())),
    }


def ensure_marker_layers(database_url: str, layer_codes: set[str]) -> None:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT code FROM map_view.marker_layers WHERE code = ANY(%s)",
                (list(layer_codes),),
            )
            existing = {row[0] for row in cursor.fetchall()}
    missing = sorted(layer_codes - existing)
    if missing:
        raise RuntimeError(f"missing map_view.marker_layers rows: {missing}. Run migrations first.")


def upsert_markers(database_url: str, markers: list[dict[str, Any]], *, replace_preview: bool) -> dict[str, int]:
    layer_counts: Counter[str] = Counter()
    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            deleted = 0
            if replace_preview:
                cursor.execute(
                    "DELETE FROM map_view.markers WHERE filter_json->>'source' = %s",
                    (PREVIEW_SOURCE,),
                )
                deleted = cursor.rowcount

            for marker in markers:
                cursor.execute(
                    """
                    INSERT INTO map_view.markers (
                      id,
                      place_ref,
                      layer_code,
                      label,
                      location,
                      geohash,
                      icon_key,
                      visibility,
                      filter_json,
                      published_revision
                    )
                    VALUES (
                      %(id)s,
                      %(place_ref)s,
                      %(layer_code)s,
                      %(label)s,
                      ST_SetSRID(ST_MakePoint(%(longitude)s, %(latitude)s), 4326)::geography,
                      %(geohash)s,
                      %(icon_key)s,
                      'visible',
                      %(filter_json)s::jsonb,
                      %(published_revision)s
                    )
                    ON CONFLICT (place_ref) DO UPDATE
                    SET
                      layer_code = EXCLUDED.layer_code,
                      label = EXCLUDED.label,
                      location = EXCLUDED.location,
                      geohash = EXCLUDED.geohash,
                      icon_key = EXCLUDED.icon_key,
                      visibility = EXCLUDED.visibility,
                      filter_json = EXCLUDED.filter_json,
                      published_revision = EXCLUDED.published_revision,
                      updated_at = now()
                    """,
                    {
                        **marker,
                        "filter_json": json.dumps(marker["filter_json"], ensure_ascii=False),
                    },
                )
                layer_counts[marker["layer_code"]] += 1

    return {"deleted_preview_markers": deleted, **dict(sorted(layer_counts.items()))}


def collect_preview_markers(
    *,
    service_key: str,
    rules: tuple[CategoryRule, ...],
    all_pages: bool,
    max_pages: int,
    num_rows: int,
    timeout: int,
    fetched_at: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    category_reports = []
    markers_by_place_ref: dict[str, dict[str, Any]] = {}

    for rule in rules:
        category_report = fetch_category_markers(
            service_key=service_key,
            rule=rule,
            all_pages=all_pages,
            max_pages=max_pages,
            num_rows=num_rows,
            timeout=timeout,
            fetched_at=fetched_at,
        )
        category_reports.append(category_report)
        for marker in category_report["markers"]:
            markers_by_place_ref[marker["place_ref"]] = marker

    return list(markers_by_place_ref.values()), category_reports


def selected_rules(raw_codes: str | None) -> tuple[CategoryRule, ...]:
    if not raw_codes:
        return CATEGORY_RULES
    codes = tuple(code.strip() for code in raw_codes.split(",") if code.strip())
    unknown = sorted(set(codes) - set(CATEGORY_RULES_BY_CODE))
    if unknown:
        raise RuntimeError(f"unsupported category codes: {unknown}")
    return tuple(CATEGORY_RULES_BY_CODE[code] for code in codes)


def report_for_category(category_report: dict[str, Any]) -> dict[str, Any]:
    rule = category_report["rule"]
    return {
        "inds_scls_cd": rule.inds_scls_cd,
        "source_category_name": rule.source_category_name,
        "layer_code": rule.layer_code,
        "total_count": category_report["total_count"],
        "pages_fetched": category_report["pages_fetched"],
        "marker_count": len(category_report["markers"]),
        "skipped": category_report["skipped"],
        "request_urls": category_report["request_urls"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed local-only Seoul bar/pub/liquor_shop preview markers from the official SMBA API."
    )
    parser.add_argument("--database-url", help="PostgreSQL URL. Defaults to DATABASE_URL or local map-service DB env.")
    parser.add_argument("--env-path", type=Path, default=DEFAULT_ENV_PATH)
    parser.add_argument("--service-key", help=f"Optional override. Prefer {SERVICE_KEY_ENV} in local .env.")
    parser.add_argument("--num-rows", type=int, default=DEFAULT_NUM_ROWS)
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    parser.add_argument("--all-pages", action="store_true", help="Fetch every page for each supported Seoul category.")
    parser.add_argument("--categories", help="Comma-separated SMBA small category codes. Defaults to all supported codes.")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--apply", action="store_true", help="Write preview markers to map_view.markers.")
    parser.add_argument(
        "--ack-public-data-preview",
        action="store_true",
        help="Required with --apply. Confirms this is local preview data, not canonical place data.",
    )
    parser.add_argument(
        "--replace-preview",
        action="store_true",
        help=f"Delete existing {PREVIEW_SOURCE} rows before inserting the new preview set.",
    )
    args = parser.parse_args()

    if args.apply and not args.ack_public_data_preview:
        raise RuntimeError("--apply requires --ack-public-data-preview")
    if args.apply and not args.all_pages:
        raise RuntimeError("--apply requires --all-pages so local preview is not accidentally partial")

    rules = selected_rules(args.categories)
    fetched_at = utc_timestamp()
    service_key = resolve_service_key(args.service_key, args.env_path)

    markers, category_reports = collect_preview_markers(
        service_key=service_key,
        rules=rules,
        all_pages=args.all_pages,
        max_pages=args.max_pages,
        num_rows=args.num_rows,
        timeout=args.timeout,
        fetched_at=fetched_at,
    )

    layer_counts = dict(sorted(Counter(marker["layer_code"] for marker in markers).items()))
    apply_result: dict[str, Any] = {}
    if args.apply:
        database_url = resolve_database_url(args.database_url)
        ensure_marker_layers(database_url, {rule.layer_code for rule in rules})
        apply_result = upsert_markers(database_url, markers, replace_preview=args.replace_preview)

    report = {
        "ok": True,
        "dry_run": not args.apply,
        "source": PREVIEW_SOURCE,
        "source_name": SMBA_SOURCE_NAME,
        "official_url": SMBA_OFFICIAL_URL,
        "area": {"ctprvn_cd": SEOUL_CTPRVN_CODE, "name": "서울특별시", "bbox": SEOUL_BBOX},
        "policy": {
            "canonical": False,
            "preview_only": True,
            "review_required": True,
            "excluded_tokens": EXCLUDED_CATEGORY_TOKENS,
        },
        "fetched_at": fetched_at,
        "category_reports": [report_for_category(category_report) for category_report in category_reports],
        "marker_count": len(markers),
        "layer_counts": layer_counts,
        "apply_result": apply_result,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
