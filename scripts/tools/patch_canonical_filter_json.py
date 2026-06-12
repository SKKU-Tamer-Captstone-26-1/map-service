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


# Single source of truth for canonical marker filter_json overrides.
#
# Each entry has:
#   "set"    — fields to merge (overwrite) via jsonb ||
#   "remove" — keys to delete after merge (e.g. "rating" not applicable to a venue)
#
# open_time / close_time: "HH:MM" 24h. "24:00" = midnight.
# image_urls: placeholder empty list; fill via admin web / GCS after upload.
# menu: [{"name", "desc", "price_krw", "image_url"?}]  — bar / pub. image_url is optional.
# inventory: [{"beverage_id", "name_ko", "name_en", "price_krw", "image_url"?}]  — liquor_shop
#            beverage_id references recommendation-service.beverage_items.id
#            image_url is optional (whiskies/{beverage_id}/... in on-the-block-product-media)

PATCHES: list[dict] = [
    {
        "id": "055be570-86b9-547b-9972-8aa73e5326e3",  # 호빈 (bar)
        "set": {
            "rating": 4.2, "review_count": 18,
            "open_time": "23:00",
            "close_time": "06:00",
            "description": "The latest close bar in Seoul",
            "image_urls": [],
            "menu": [
                {"name": "Jameson Highball", "desc": "Jameson based highball", "price_krw": 11000,
                 "image_url": "https://storage.googleapis.com/on-the-block-place-media/menu/055be570-86b9-547b-9972-8aa73e5326e3/1f602f02-0480-431d-aedf-be8d8f374d85.jpg"},
                {"name": "Jameson Shot",     "desc": "Jameson Shot",           "price_krw": 10000},
                {"name": "Beer",             "desc": "Bottled Beer",           "price_krw": 10000},
            ],
        },
        "remove": [],
    },
    {
        "id": "d6cf7a04-2ff8-53f8-9079-dbd2d9bd5bef",  # 앨리스 (bar)
        "set": {
            "rating": 4.0, "review_count": 12,
            "open_time": "19:00",
            "close_time": "02:00",
            "road_address": "서울특별시 강남구 도산대로55길 47 지하 1층",
            "description": "The Bar in wonderland",
            "image_urls": [],
            "menu": [
                {"name": "Foggy Fongo", "desc": "", "price_krw": 27000},
                {"name": "Zolla GGUL",  "desc": "", "price_krw": 27000},
            ],
        },
        "remove": [],
    },
    {
        "id": "6f18761d-f009-5469-9f65-947523c6b0c0",  # 제스트 (bar)
        "set": {
            "rating": 4.5, "review_count": 31,
            "open_time": "19:00",
            "close_time": "02:00",
            "image_urls": [],
            "menu": [
                {"name": "Z&T",               "desc": "", "price_krw": 25000},
                {"name": "City Bee's Knees",   "desc": "", "price_krw": 25000},
            ],
        },
        "remove": [],
    },
    {
        "id": "05835c27-7fe8-5265-9a05-c5b59198259d",  # 파인앤코 (bar)
        "set": {
            "rating": 4.4, "review_count": 27,
            "open_time": "18:00",
            "close_time": "02:00",
            "image_urls": [],
            "menu": [
                {"name": "Nuruk",  "desc": "", "price_krw": 26000},
                {"name": "Yogurt", "desc": "", "price_krw": 26000},
            ],
        },
        "remove": [],
    },
    {
        "id": "ac64748c-1cbd-577c-a314-af3d59946355",  # 비바라비다 (bar)
        "set": {
            "rating": 4.3, "review_count": 15,
            "open_time": "19:00",
            "close_time": "02:00",
            "image_urls": [],
            "menu": [],
        },
        "remove": [],
    },
    {
        "id": "bb145fb3-6232-5155-9c16-eaa01e67c7b2",  # 빌라레코드 (bar)
        "set": {
            "rating": 4.6, "review_count": 43,
            "open_time": "19:00",
            "close_time": "02:00",
            "image_urls": [],
            "menu": [
                {"name": "Molecular Cocktails", "desc": "", "price_krw": 25000},
                {"name": "Classical Cocktails", "desc": "", "price_krw": 25000},
            ],
        },
        "remove": [],
    },
    {
        "id": "92c27fd6-b5d3-5bcb-963a-d5edd3987398",  # 크리켓서울 (bar)
        "set": {
            "rating": 4.2, "review_count": 19,
            "open_time": "19:00",
            "close_time": "02:00",
            "image_urls": [],
            "menu": [
                {"name": "GGeek Beer", "desc": "", "price_krw": 15000},
            ],
        },
        "remove": [],
    },
    {
        "id": "86633237-8df0-5a5d-ac9a-ab4f91a35fff",  # 더몰트샵 (liquor_shop)
        "set": {
            "open_time": "10:00",
            "close_time": "22:00",
            "image_urls": [],
            # beverage_id → recommendation-service.beverage_items.id (canonical)
            "inventory": [
                {"beverage_id": "846aab49-a7d0-5bfb-b987-acf20abe8015",
                 "name_ko": "더 맥캘란 12년 더블 캐스크",
                 "name_en": "The Macallan 12 Years Double Cask",
                 "price_krw": 128000},
                {"beverage_id": "8c3dbc78-e8c9-5187-ad08-cf0b5416995d",
                 "name_ko": "글렌피딕 12년",
                 "name_en": "Glenfiddich 12 Year Old",
                 "price_krw": 115000,
                 "image_url": "https://storage.googleapis.com/on-the-block-product-media/whiskies/8c3dbc78-e8c9-5187-ad08-cf0b5416995d/58501296-5a88-4dc4-a285-1d360317bd0e.jpg"},
                {"beverage_id": "d8ec2f75-f3b7-50b9-8be8-9dd8de031a54",
                 "name_ko": "라프로익 10년",
                 "name_en": "Laphroaig 10 Year Old",
                 "price_krw": 119000},
                {"beverage_id": "17efb137-cdbb-5ca1-8734-f5705b50081b",
                 "name_ko": "버팔로 트레이스 버번",
                 "name_en": "Buffalo Trace Bourbon",
                 "price_krw": 89000},
                {"beverage_id": "2ac1b120-0319-5017-bea6-65b443e50acf",
                 "name_ko": "제임슨 아이리시 위스키",
                 "name_en": "Jameson Irish Whiskey",
                 "price_krw": 79000,
                 "image_url": "https://storage.googleapis.com/on-the-block-product-media/whiskies/2ac1b120-0319-5017-bea6-65b443e50acf/00708b83-2e3c-4998-b43a-75c890189264.png"},
            ],
        },
        "remove": ["rating", "review_count"],
    },
    {
        "id": "bf053be4-8e98-57ea-91cd-4e9c6b451e69",  # 서울집시 (pub)
        "set": {
            "rating": 4.1, "review_count": 22,
            "open_time": "17:00",
            "close_time": "01:00",
            "image_urls": [],
            "menu": [
                {"name": "Craft Beers", "desc": "", "price_krw": 0},
            ],
        },
        "remove": [],
    },
    {
        "id": "d7984c6a-d17c-585d-8e2c-14daf0c7975a",  # 만리199 (pub)
        "set": {
            "rating": 4.0, "review_count": 11,
            "open_time": "17:00",
            "close_time": "24:00",
            "image_urls": [],
            "menu": [
                {"name": "Craft Beers", "desc": "", "price_krw": 0},
            ],
        },
        "remove": [],
    },
]


def run(database_url: str, *, dry_run: bool) -> None:
    with psycopg.connect(database_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            for entry in PATCHES:
                marker_id = entry["id"]
                patch = json.dumps(entry["set"], ensure_ascii=False)
                remove_keys = entry.get("remove", [])

                if dry_run:
                    print(f"[dry-run] {marker_id}: set={list(entry['set'])} remove={remove_keys}")
                    continue

                remove_clause = " ".join(f"- '{k}'" for k in remove_keys)
                cur.execute(
                    f"""
                    UPDATE map_view.markers
                    SET filter_json = (filter_json || %s::jsonb) {remove_clause},
                        updated_at  = now()
                    WHERE id = %s::uuid
                    """,
                    (patch, marker_id),
                )
                print(f"patched {marker_id} ({cur.rowcount} row)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Overwrite canonical marker filter_json with the authoritative seed data."
    )
    parser.add_argument("--database-url")
    parser.add_argument("--apply", action="store_true", help="Write to DB (default: dry-run)")
    args = parser.parse_args()
    run(resolve_database_url(args.database_url), dry_run=not args.apply)


if __name__ == "__main__":
    main()
