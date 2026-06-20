from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import psycopg


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.db.verify_map_view_schema import resolve_database_url


DEV_MARKERS = [
    {
        "id": "10000000-0000-4000-8000-000000000001",
        "place_ref": "20000000-0000-4000-8000-000000000001",
        "layer_code": "pub",
        "label": "DEV 홍대 펍 샘플",
        "longitude": 126.9229,
        "latitude": 37.5563,
        "geohash": "wydm6",
        "filter_json": {"fixture": True, "source": "local_dev_seed", "neighborhood": "hongdae"},
        "published_revision": 1,
    },
    {
        "id": "10000000-0000-4000-8000-000000000002",
        "place_ref": "20000000-0000-4000-8000-000000000002",
        "layer_code": "bar",
        "label": "DEV 상수 바 샘플",
        "longitude": 126.9236,
        "latitude": 37.5487,
        "geohash": "wydm6",
        "filter_json": {"fixture": True, "source": "local_dev_seed", "neighborhood": "sangsu"},
        "published_revision": 1,
    },
    {
        "id": "10000000-0000-4000-8000-000000000003",
        "place_ref": "20000000-0000-4000-8000-000000000003",
        "layer_code": "liquor_shop",
        "label": "DEV 합정 주류 판매점 샘플",
        "longitude": 126.9139,
        "latitude": 37.5499,
        "geohash": "wydm6",
        "filter_json": {"fixture": True, "source": "local_dev_seed", "neighborhood": "hapjeong"},
        "published_revision": 1,
    },
    {
        "id": "10000000-0000-4000-8000-000000000004",
        "place_ref": "20000000-0000-4000-8000-000000000004",
        "layer_code": "outdoor_spot",
        "label": "망원 한강공원",
        "longitude": 126.8994,
        "latitude": 37.5558,
        "geohash": "wydm6",
        "filter_json": {
            "fixture": True,
            "source": "local_dev_seed",
            "neighborhood": "mangwon",
            "image_urls": [
                "https://storage.googleapis.com/on-the-block-place-media/venues/20000000-0000-4000-8000-000000000004/hangang.jpg"
            ],
        },
        "published_revision": 1,
    },
    {
        "id": "10000000-0000-4000-8000-000000000005",
        "place_ref": "20000000-0000-4000-8000-000000000005",
        "layer_code": "restaurant",
        "label": "DEV 연남 음식점 샘플",
        "longitude": 126.9253,
        "latitude": 37.5627,
        "geohash": "wydm6",
        "filter_json": {"fixture": True, "source": "local_dev_seed", "neighborhood": "yeonnam"},
        "published_revision": 1,
    },
]


def seed_dev_markers(database_url: str, *, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "marker_count": len(DEV_MARKERS),
            "markers": DEV_MARKERS,
        }

    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            for marker in DEV_MARKERS:
                cursor.execute(
                    """
                    INSERT INTO map_view.markers (
                      id,
                      place_ref,
                      layer_code,
                      label,
                      location,
                      geohash,
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

    return {
        "ok": True,
        "dry_run": False,
        "marker_count": len(DEV_MARKERS),
        "note": "Inserted local dev map_view marker fixtures only. No canonical places were inserted.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed local-only synthetic map_view markers for frontend development.")
    parser.add_argument("--database-url", help="PostgreSQL URL. Defaults to DATABASE_URL or local map-service DB env.")
    parser.add_argument("--apply", action="store_true", help="Write synthetic dev marker fixtures to the target DB.")
    args = parser.parse_args()

    report = seed_dev_markers(resolve_database_url(args.database_url), dry_run=not args.apply)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
