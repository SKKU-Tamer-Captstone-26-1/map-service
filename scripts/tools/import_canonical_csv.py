from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import psycopg


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.db.verify_map_view_schema import resolve_database_url


TRUTHY = {"true", "1", "yes", "y", "o", "ok", "v", "TRUE", "YES", "O", "V"}


def is_truthy(val: str) -> bool:
    return val.strip() in TRUTHY


def load_csv(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = [dict(r) for r in reader]
    return rows


def find_promote_column(fieldnames: list[str]) -> str | None:
    for name in fieldnames:
        if "canonical" in name.lower() and "승격" in name:
            return name
        if "promote" in name.lower():
            return name
    return None


def apply_visibility(database_url: str, ids: list[str], *, dry_run: bool) -> int:
    if not ids:
        return 0

    if dry_run:
        print(f"[dry-run] {len(ids)}개 마커를 visibility=visible로 업데이트 예정")
        for mid in ids[:5]:
            print(f"  {mid}")
        if len(ids) > 5:
            print(f"  ... 외 {len(ids)-5}개")
        return len(ids)

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE map_view.markers
                SET
                    visibility = 'visible',
                    updated_at = now()
                WHERE id = ANY(%s::uuid[])
                """,
                (ids,),
            )
            updated = cur.rowcount
        conn.commit()
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CSV에서 canonical 승격 표시된 마커를 DB에 반영합니다."
    )
    parser.add_argument(
        "csv_file",
        type=Path,
        nargs="?",
        default=Path("markers_export.csv"),
        help="export_markers_csv.py로 생성한 CSV 파일 (기본: markers_export.csv)",
    )
    parser.add_argument("--database-url", help="PostgreSQL 접속 URL")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 DB 변경 없이 어떤 마커가 대상인지만 확인",
    )
    args = parser.parse_args()

    csv_path: Path = args.csv_file.resolve()
    if not csv_path.exists():
        print(f"파일 없음: {csv_path}")
        sys.exit(1)

    rows = load_csv(csv_path)
    if not rows:
        print("CSV가 비어 있습니다.")
        sys.exit(0)

    # 승격 컬럼 자동 탐지
    promote_col = find_promote_column(list(rows[0].keys()))
    if not promote_col:
        # 헤더가 한국어인 경우 직접 매핑
        promote_col = "canonical 승격 (편집)"
    if promote_col not in rows[0]:
        print(f"'canonical 승격' 컬럼을 찾을 수 없습니다. 컬럼 목록: {list(rows[0].keys())}")
        sys.exit(1)

    # 마커 ID 컬럼 탐지 (첫 번째 컬럼 또는 '마커 ID')
    id_col = "마커 ID" if "마커 ID" in rows[0] else list(rows[0].keys())[0]

    promote_ids = [
        row[id_col].strip()
        for row in rows
        if is_truthy(row.get(promote_col, ""))
    ]

    total = len(rows)
    print(f"CSV 행 수: {total:,}개")
    print(f"canonical 승격 대상: {len(promote_ids):,}개")

    if not promote_ids:
        print("승격할 마커가 없습니다. CSV의 'canonical 승격 (편집)' 컬럼을 확인하세요.")
        print("  인식하는 값: TRUE, true, 1, Y, y, O, o, V, v, yes")
        sys.exit(0)

    database_url = resolve_database_url(args.database_url)
    updated = apply_visibility(database_url, promote_ids, dry_run=args.dry_run)

    if args.dry_run:
        print("--dry-run 모드: DB 변경 없음")
    else:
        print(f"DB 업데이트 완료: {updated}개 마커 visibility=visible")
        print()
        print("지도 확인:")
        print("  python -m scripts.tools.view_markers")


if __name__ == "__main__":
    main()
