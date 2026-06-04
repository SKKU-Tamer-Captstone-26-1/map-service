from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import psycopg


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.db.verify_map_view_schema import resolve_database_url


# open_time / close_time: "HH:MM" (24h). "24:00" = midnight without crossing-midnight ambiguity.
# menu items: [{"name": str, "desc": str, "price_krw": int}]
# image_urls: list of photo URLs (filled via admin web; empty array = no photos yet)
PATCHES = {
    "055be570-86b9-547b-9972-8aa73e5326e3": {  # 호빈 (bar)
        "open_time": "18:00", "close_time": "02:00",
        "rating": 4.2, "review_count": 18, "image_urls": [],
        "menu": [
            {"name": "하이볼", "desc": "산토리 위스키 베이스", "price_krw": 9000},
            {"name": "모히또", "desc": "민트, 라임, 럼", "price_krw": 12000},
            {"name": "소곱창볶음", "desc": "안주 대표 메뉴", "price_krw": 18000},
        ],
    },
    "d6cf7a04-2ff8-53f8-9079-dbd2d9bd5bef": {  # 앨리스 (bar)
        "open_time": "17:00", "close_time": "01:00",
        "rating": 4.0, "review_count": 12, "image_urls": [],
        "menu": [
            {"name": "Alice in Wonderland", "desc": "블루 큐라소, 버터플라이피", "price_krw": 19000},
            {"name": "Mad Hatter", "desc": "얼그레이 인퓨즈드 진, 레몬", "price_krw": 18000},
            {"name": "White Rabbit", "desc": "코코넛 럼, 패션후르츠", "price_krw": 16000},
        ],
    },
    "6f18761d-f009-5469-9f65-947523c6b0c0": {  # 제스트 (bar)
        "open_time": "19:00", "close_time": "03:00",
        "rating": 4.5, "review_count": 31, "image_urls": [],
        "menu": [
            {"name": "Zest Signature", "desc": "유자 인퓨즈드 진, 통카빈", "price_krw": 19000},
            {"name": "Old Fashioned", "desc": "버번, 앙고스투라 비터스", "price_krw": 18000},
            {"name": "Paloma", "desc": "테킬라, 자몽, 소금", "price_krw": 16000},
        ],
    },
    "86633237-8df0-5a5d-ac9a-ab4f91a35fff": {  # 더몰트샵 (liquor_shop)
        "open_time": "10:00", "close_time": "22:00",
        "rating": 4.3, "review_count": 9, "image_urls": [],
    },
    "bf053be4-8e98-57ea-91cd-4e9c6b451e69": {  # 서울집시 (pub)
        "open_time": "17:00", "close_time": "01:00",
        "rating": 4.1, "review_count": 22, "image_urls": [],
        "menu": [
            {"name": "기네스 파인트", "desc": "아이리시 스타우트", "price_krw": 12000},
            {"name": "하이네켄 파인트", "desc": "네덜란드 라거", "price_krw": 10000},
            {"name": "피쉬 앤 칩스", "desc": "타르타르소스 포함", "price_krw": 18000},
        ],
    },
    "05835c27-7fe8-5265-9a05-c5b59198259d": {  # 파인앤코 (bar)
        "open_time": "18:00", "close_time": "02:00",
        "rating": 4.4, "review_count": 27, "image_urls": [],
        "menu": [
            {"name": "Fine & Co. Martini", "desc": "드라이 진, 올리브 워터", "price_krw": 24000},
            {"name": "Negroni", "desc": "진, 캄파리, 스위트 베르무트", "price_krw": 20000},
            {"name": "Whiskey Sour", "desc": "버번, 레몬, 에그화이트", "price_krw": 19000},
        ],
    },
    "ac64748c-1cbd-577c-a314-af3d59946355": {  # 비바라비다 (bar)
        "open_time": "18:00", "close_time": "02:00",
        "rating": 4.3, "review_count": 15, "image_urls": [],
        "menu": [
            {"name": "Margarita", "desc": "블랑코 테킬라, 라임, 소금 테두리", "price_krw": 16000},
            {"name": "Viva Signature", "desc": "메스칼, 히비스커스, 아과 프레스카", "price_krw": 20000},
            {"name": "Mojito", "desc": "럼, 민트, 라임, 소다", "price_krw": 15000},
        ],
    },
    "bb145fb3-6232-5155-9c16-eaa01e67c7b2": {  # 빌라레코드 (bar)
        "open_time": "19:00", "close_time": "03:00",
        "rating": 4.6, "review_count": 43, "image_urls": [],
        "menu": [
            {"name": "Villa Signature", "desc": "스모크드 로즈마리, 프로프라이어터리 진 블렌드", "price_krw": 22000},
            {"name": "Old Fashioned", "desc": "아티산 비터스, 핸드 카빙 아이스", "price_krw": 18000},
            {"name": "Macallan 18yo", "desc": "싱글 몰트, 셰리 오크 캐스크", "price_krw": 35000},
        ],
    },
    "92c27fd6-b5d3-5bcb-963a-d5edd3987398": {  # 크리켓서울 (bar)
        "open_time": "18:00", "close_time": "02:00",
        "rating": 4.2, "review_count": 19, "image_urls": [],
        "menu": [
            {"name": "Cricket Highball", "desc": "산토리 토키, 탄산수", "price_krw": 15000},
            {"name": "Classic Martini", "desc": "런던 드라이 진, 드라이 베르무트", "price_krw": 18000},
            {"name": "Aperol Spritz", "desc": "아페롤, 프로세코, 소다", "price_krw": 16000},
        ],
    },
    "d7984c6a-d17c-585d-8e2c-14daf0c7975a": {  # 만리199 (pub)
        "open_time": "17:00", "close_time": "24:00",
        "rating": 4.0, "review_count": 11, "image_urls": [],
        "menu": [
            {"name": "크래프트 맥주", "desc": "오늘의 생맥주 (탭 변동)", "price_krw": 10000},
            {"name": "감자튀김", "desc": "사이드 안주", "price_krw": 8000},
            {"name": "피자", "desc": "치즈 마르게리타", "price_krw": 20000},
        ],
    },
}


def run(database_url: str, *, dry_run: bool) -> None:
    with psycopg.connect(database_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            for marker_id, patch in PATCHES.items():
                if dry_run:
                    print(f"[dry-run] {marker_id}: {patch}")
                    continue
                cur.execute(
                    """
                    UPDATE map_view.markers
                    SET filter_json = filter_json || %s::jsonb,
                        updated_at  = now()
                    WHERE id = %s::uuid
                    """,
                    (json.dumps(patch, ensure_ascii=False), marker_id),
                )
                print(f"patched {marker_id} ({cur.rowcount} row)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Add hours/rating/review_count to canonical marker filter_json.")
    parser.add_argument("--database-url")
    parser.add_argument("--apply", action="store_true", help="Write to DB (default: dry-run)")
    args = parser.parse_args()
    run(resolve_database_url(args.database_url), dry_run=not args.apply)


if __name__ == "__main__":
    main()
