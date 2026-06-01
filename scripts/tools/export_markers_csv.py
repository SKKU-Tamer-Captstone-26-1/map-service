from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.db.verify_map_view_schema import resolve_database_url


COLUMNS = [
    "id",
    "label",
    "layer_code",
    "latitude",
    "longitude",
    "road_address",
    "lot_address",
    "district",
    "administrative_dong",
    "source_category_name",
    "source_medium_category_name",
    "source_id",
    "canonical",
    "preview_only",
    "review_status",
    "published_revision",
    "visibility",
    "promote_to_canonical",  # 편집용 빈 컬럼
    "notes",                 # 편집용 빈 컬럼
]

COLUMN_HEADERS = {
    "id":                       "마커 ID",
    "label":                    "장소명",
    "layer_code":               "레이어",
    "latitude":                 "위도",
    "longitude":                "경도",
    "road_address":             "도로명 주소",
    "lot_address":              "지번 주소",
    "district":                 "구",
    "administrative_dong":      "행정동",
    "source_category_name":     "소분류 (소상공인)",
    "source_medium_category_name": "중분류 (소상공인)",
    "source_id":                "소상공인 ID",
    "canonical":                "canonical 여부",
    "preview_only":             "preview 전용",
    "review_status":            "검토 상태",
    "published_revision":       "게시 리비전",
    "visibility":               "노출 여부",
    "promote_to_canonical":     "canonical 승격 (편집)",
    "notes":                    "메모 (편집)",
}


def fetch_markers(database_url: str, layer: str | None) -> list[dict]:
    layer_clause = "AND m.layer_code = %(layer)s" if layer else ""
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    m.id::text                                          AS id,
                    m.label,
                    m.layer_code,
                    ST_Y(m.location::geometry)                          AS latitude,
                    ST_X(m.location::geometry)                         AS longitude,
                    COALESCE(
                      m.filter_json->>'road_address',
                      m.filter_json->>'address'
                    )                                                   AS road_address,
                    m.filter_json->>'lot_address'                       AS lot_address,
                    m.filter_json->>'district'                          AS district,
                    m.filter_json->>'administrative_dong'               AS administrative_dong,
                    m.filter_json->>'source_category_name'              AS source_category_name,
                    m.filter_json->>'source_medium_category_name'       AS source_medium_category_name,
                    m.filter_json->>'source_id'                         AS source_id,
                    COALESCE(m.filter_json->>'canonical', 'false')      AS canonical,
                    COALESCE(m.filter_json->>'preview_only', 'false')   AS preview_only,
                    COALESCE(m.filter_json->>'review_status', '')       AS review_status,
                    m.published_revision,
                    m.visibility::text                                  AS visibility
                FROM map_view.markers m
                {layer_clause}
                ORDER BY m.layer_code, district, administrative_dong, m.label
                """,
                {"layer": layer} if layer else {},
            )
            rows = [dict(r) for r in cur.fetchall()]
    for row in rows:
        row["promote_to_canonical"] = ""
        row["notes"] = ""
    return rows


def write_csv(rows: list[dict], output_path: Path) -> None:
    with output_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=COLUMNS,
            extrasaction="ignore",
        )
        writer.writerow({col: COLUMN_HEADERS.get(col, col) for col in COLUMNS})
        writer.writerows(rows)


def open_file(path: Path) -> None:
    try:
        if sys.platform == "win32":
            os.startfile(str(path))
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=True)
        else:
            subprocess.run(["xdg-open", str(path)], check=True)
    except Exception as exc:
        print(f"자동 열기 실패: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="map_view.markers 데이터를 CSV로 내보냅니다. Excel에서 바로 열립니다."
    )
    parser.add_argument("--database-url", help="PostgreSQL 접속 URL")
    parser.add_argument(
        "--output", type=Path, default=Path("markers_export.csv"),
        help="출력 파일 경로 (기본값: markers_export.csv)"
    )
    parser.add_argument(
        "--layer",
        choices=["bar", "pub", "liquor_shop", "outdoor_spot", "restaurant", "convenience_store", "other"],
        help="특정 레이어만 내보낼 경우 지정"
    )
    parser.add_argument("--no-open", action="store_true", help="완료 후 파일 자동 열기 안 함")
    args = parser.parse_args()

    database_url = resolve_database_url(args.database_url)

    layer_info = f" (레이어: {args.layer})" if args.layer else ""
    print(f"DB에서 마커 조회 중{layer_info}...")
    rows = fetch_markers(database_url, args.layer)
    print(f"{len(rows):,}개 로드 완료")

    output_path = args.output.resolve()
    write_csv(rows, output_path)
    print(f"CSV 저장: {output_path}")

    if not args.no_open:
        open_file(output_path)


if __name__ == "__main__":
    main()
