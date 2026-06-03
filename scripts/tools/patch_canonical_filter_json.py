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
PATCHES = {
    "055be570-86b9-547b-9972-8aa73e5326e3": {  # 호빈 (bar)
        "open_time": "18:00", "close_time": "02:00",
        "rating": 4.2, "review_count": 18, "image_url": "",
    },
    "d6cf7a04-2ff8-53f8-9079-dbd2d9bd5bef": {  # 앨리스 (bar)
        "open_time": "17:00", "close_time": "01:00",
        "rating": 4.0, "review_count": 12, "image_url": "",
    },
    "6f18761d-f009-5469-9f65-947523c6b0c0": {  # 제스트 (bar)
        "open_time": "19:00", "close_time": "03:00",
        "rating": 4.5, "review_count": 31, "image_url": "",
    },
    "86633237-8df0-5a5d-ac9a-ab4f91a35fff": {  # 더몰트샵 (liquor_shop)
        "open_time": "10:00", "close_time": "22:00",
        "rating": 4.3, "review_count": 9, "image_url": "",
    },
    "bf053be4-8e98-57ea-91cd-4e9c6b451e69": {  # 서울집시 (pub)
        "open_time": "17:00", "close_time": "01:00",
        "rating": 4.1, "review_count": 22, "image_url": "",
    },
    "05835c27-7fe8-5265-9a05-c5b59198259d": {  # 파인앤코 (bar)
        "open_time": "18:00", "close_time": "02:00",
        "rating": 4.4, "review_count": 27, "image_url": "",
    },
    "ac64748c-1cbd-577c-a314-af3d59946355": {  # 비바라비다 (bar)
        "open_time": "18:00", "close_time": "02:00",
        "rating": 4.3, "review_count": 15, "image_url": "",
    },
    "bb145fb3-6232-5155-9c16-eaa01e67c7b2": {  # 빌라레코드 (bar)
        "open_time": "19:00", "close_time": "03:00",
        "rating": 4.6, "review_count": 43, "image_url": "",
    },
    "92c27fd6-b5d3-5bcb-963a-d5edd3987398": {  # 크리켓서울 (bar)
        "open_time": "18:00", "close_time": "02:00",
        "rating": 4.2, "review_count": 19, "image_url": "",
    },
    "d7984c6a-d17c-585d-8e2c-14daf0c7975a": {  # 만리199 (pub)
        "open_time": "17:00", "close_time": "24:00",
        "rating": 4.0, "review_count": 11, "image_url": "",
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
