from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import dict_row


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.db.verify_map_view_schema import resolve_database_url


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8088
DEFAULT_LIMIT = 200
MAX_LIMIT = 500
MAX_OFFSET = 100000
ALLOWED_LAYER_CODES = {
    "bar",
    "pub",
    "liquor_shop",
    "outdoor_spot",
    "restaurant",
    "convenience_store",
    "other",
}


class ApiError(Exception):
    def __init__(self, status: HTTPStatus, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


@dataclass(frozen=True)
class MarkerQuery:
    bbox: tuple[float, float, float, float]
    layers: tuple[str, ...]
    limit: int
    offset: int


def json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError(f"{type(value).__name__} is not JSON serializable")


def parse_bbox(raw_values: list[str] | None) -> tuple[float, float, float, float]:
    if not raw_values:
        raise ApiError(HTTPStatus.BAD_REQUEST, "bbox_required", "bbox query parameter is required")
    raw = raw_values[-1]
    parts = [part.strip() for part in raw.split(",")]
    if len(parts) != 4:
        raise ApiError(HTTPStatus.BAD_REQUEST, "bbox_invalid", "bbox must be minLon,minLat,maxLon,maxLat")

    try:
        min_lon, min_lat, max_lon, max_lat = (float(part) for part in parts)
    except ValueError as error:
        raise ApiError(HTTPStatus.BAD_REQUEST, "bbox_invalid", "bbox values must be numbers") from error

    if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
        raise ApiError(HTTPStatus.BAD_REQUEST, "bbox_invalid", "longitude must be between -180 and 180")
    if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
        raise ApiError(HTTPStatus.BAD_REQUEST, "bbox_invalid", "latitude must be between -90 and 90")
    if min_lon >= max_lon or min_lat >= max_lat:
        raise ApiError(HTTPStatus.BAD_REQUEST, "bbox_invalid", "bbox min values must be smaller than max values")

    return min_lon, min_lat, max_lon, max_lat


def parse_layers(raw_values: list[str] | None) -> tuple[str, ...]:
    if not raw_values:
        return ()
    layer_codes = tuple(
        layer.strip()
        for value in raw_values
        for layer in value.split(",")
        if layer.strip()
    )
    unknown = sorted(set(layer_codes) - ALLOWED_LAYER_CODES)
    if unknown:
        raise ApiError(HTTPStatus.BAD_REQUEST, "layers_invalid", f"unknown layer codes: {unknown}")
    return layer_codes


def parse_limit(raw_values: list[str] | None) -> int:
    if not raw_values:
        return DEFAULT_LIMIT
    raw = raw_values[-1].strip()
    try:
        limit = int(raw)
    except ValueError as error:
        raise ApiError(HTTPStatus.BAD_REQUEST, "limit_invalid", "limit must be an integer") from error
    if limit < 1 or limit > MAX_LIMIT:
        raise ApiError(HTTPStatus.BAD_REQUEST, "limit_invalid", f"limit must be between 1 and {MAX_LIMIT}")
    return limit


def parse_offset(raw_values: list[str] | None) -> int:
    if not raw_values:
        return 0
    raw = raw_values[-1].strip()
    try:
        offset = int(raw)
    except ValueError as error:
        raise ApiError(HTTPStatus.BAD_REQUEST, "offset_invalid", "offset must be an integer") from error
    if offset < 0 or offset > MAX_OFFSET:
        raise ApiError(HTTPStatus.BAD_REQUEST, "offset_invalid", f"offset must be between 0 and {MAX_OFFSET}")
    return offset


def parse_marker_query(query_params: dict[str, list[str]]) -> MarkerQuery:
    return MarkerQuery(
        bbox=parse_bbox(query_params.get("bbox")),
        layers=parse_layers(query_params.get("layers")),
        limit=parse_limit(query_params.get("limit")),
        offset=parse_offset(query_params.get("offset")),
    )


class MapViewRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def list_layers(self) -> list[dict[str, Any]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT code, label_ko, label_en, icon_key, display_order, default_visible, is_active
                    FROM map_view.marker_layers
                    WHERE is_active = true
                    ORDER BY display_order, code
                    """
                )
                return [dict(row) for row in cursor.fetchall()]

    def add_review(self, marker_id: str, review: dict[str, Any]) -> None:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE map_view.markers
                    SET filter_json = jsonb_set(
                        filter_json,
                        '{reviews}',
                        COALESCE(filter_json->'reviews', '[]'::jsonb) || %s::jsonb,
                        true
                    ),
                    updated_at = now()
                    WHERE id = %s::uuid AND visibility = 'visible'
                    """,
                    (json.dumps([review], ensure_ascii=False), marker_id),
                )
                if cursor.rowcount == 0:
                    raise ApiError(HTTPStatus.NOT_FOUND, "not_found", "marker not found")
            connection.commit()

    def delete_review(self, marker_id: str, review_id: str) -> None:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE map_view.markers
                    SET filter_json = jsonb_set(
                        filter_json,
                        '{reviews}',
                        COALESCE(
                            (
                                SELECT jsonb_agg(r)
                                FROM jsonb_array_elements(
                                    COALESCE(filter_json->'reviews', '[]'::jsonb)
                                ) AS r
                                WHERE r->>'review_id' != %s
                            ),
                            '[]'::jsonb
                        ),
                        true
                    ),
                    updated_at = now()
                    WHERE id = %s::uuid AND visibility = 'visible'
                    """,
                    (review_id, marker_id),
                )
                if cursor.rowcount == 0:
                    raise ApiError(HTTPStatus.NOT_FOUND, "not_found", "marker not found")
            connection.commit()

    def list_snapshot_events(
        self,
        *,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[dict[str, Any]], str | None, bool]:
        """Return (markers, next_cursor, has_more) for snapshot feed pagination.

        cursor is an ISO-8601 timestamp; returns markers with updated_at > cursor,
        ordered by (updated_at ASC, id ASC).  Returns at most limit + 1 rows to
        detect whether a next page exists.
        """
        params: list[Any] = []
        cursor_clause = ""
        if cursor:
            try:
                cursor_dt = datetime.fromisoformat(cursor.replace("Z", "+00:00"))
            except ValueError as error:
                raise ApiError(
                    HTTPStatus.BAD_REQUEST, "cursor_invalid", "cursor must be an ISO-8601 timestamp"
                ) from error
            cursor_clause = "AND m.updated_at > %s"
            params.append(cursor_dt)
        params.append(limit + 1)

        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor_obj:
                cursor_obj.execute(
                    f"""
                    SELECT
                      m.id::text AS id,
                      m.place_ref::text AS place_ref,
                      m.layer_code,
                      m.label,
                      ST_Y(m.location::geometry) AS latitude,
                      ST_X(m.location::geometry) AS longitude,
                      m.visibility::text AS visibility,
                      m.filter_json,
                      m.published_revision,
                      m.published_at,
                      m.updated_at
                    FROM map_view.markers m
                    JOIN map_view.marker_layers l ON l.code = m.layer_code
                    WHERE m.visibility = 'visible'
                      AND l.is_active = true
                      {cursor_clause}
                    ORDER BY m.updated_at ASC, m.id ASC
                    LIMIT %s
                    """,
                    params,
                )
                rows = [dict(row) for row in cursor_obj.fetchall()]

        has_more = len(rows) > limit
        page = rows[:limit]
        next_cursor: str | None = None
        if has_more and page:
            last_updated = page[-1]["updated_at"]
            if isinstance(last_updated, datetime):
                next_cursor = last_updated.isoformat()
            else:
                next_cursor = str(last_updated)
        return page, next_cursor, has_more

    def search_markers(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                      m.id::text AS id,
                      m.place_ref::text AS place_ref,
                      m.layer_code,
                      m.label,
                      ST_Y(m.location::geometry) AS latitude,
                      ST_X(m.location::geometry) AS longitude,
                      COALESCE(m.icon_key, l.icon_key) AS icon_key,
                      m.visibility::text AS visibility,
                      m.filter_json,
                      m.published_revision,
                      m.published_at,
                      m.updated_at
                    FROM map_view.markers m
                    JOIN map_view.marker_layers l ON l.code = m.layer_code
                    WHERE m.visibility = 'visible'
                      AND l.is_active = true
                      AND m.label ILIKE %s
                    ORDER BY m.published_revision DESC, m.label
                    LIMIT %s
                    """,
                    (f"%{query}%", limit),
                )
                return [dict(row) for row in cursor.fetchall()]

    def list_markers(self, query: MarkerQuery) -> list[dict[str, Any]]:
        min_lon, min_lat, max_lon, max_lat = query.bbox
        params: list[Any] = [min_lon, min_lat, max_lon, max_lat]
        layer_clause = ""
        if query.layers:
            layer_clause = "AND m.layer_code = ANY(%s)"
            params.append(list(query.layers))
        params.extend([query.limit, query.offset])

        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT
                      m.id::text AS id,
                      m.place_ref::text AS place_ref,
                      m.layer_code,
                      m.label,
                      ST_Y(m.location::geometry) AS latitude,
                      ST_X(m.location::geometry) AS longitude,
                      COALESCE(m.icon_key, l.icon_key) AS icon_key,
                      m.visibility::text AS visibility,
                      m.filter_json,
                      m.published_revision,
                      m.published_at,
                      m.updated_at
                    FROM map_view.markers m
                    JOIN map_view.marker_layers l ON l.code = m.layer_code
                    WHERE m.visibility = 'visible'
                      AND l.is_active = true
                      AND ST_Intersects(m.location, ST_MakeEnvelope(%s, %s, %s, %s, 4326)::geography)
                      {layer_clause}
                    ORDER BY m.published_revision DESC, m.published_at DESC, m.id
                    LIMIT %s
                    OFFSET %s
                    """,
                    params,
                )
                return [dict(row) for row in cursor.fetchall()]


_KST = ZoneInfo("Asia/Seoul")


def _parse_minutes(t: str) -> int:
    h, m = map(int, t.split(":"))
    return h * 60 + m


def _compute_is_open(open_time: str | None, close_time: str | None) -> bool | None:
    if not open_time or not close_time:
        return None
    try:
        now = datetime.now(_KST)
        now_min = now.hour * 60 + now.minute
        open_min = _parse_minutes(open_time)
        close_min = _parse_minutes(close_time)
        if close_min <= open_min:  # crosses midnight (e.g. 18:00-02:00)
            return now_min >= open_min or now_min < close_min
        return open_min <= now_min < close_min
    except Exception:
        return None


def _format_time(t: str) -> str:
    h, m = map(int, t.split(":"))
    return f"{h % 24:02d}:{m:02d}"


def _format_date(dt: datetime) -> str:
    return dt.strftime("%b ") + str(dt.day) + dt.strftime(", %Y")


def _compute_rating(reviews: list[dict[str, Any]]) -> float | None:
    valid = [r["rating"] for r in reviews if isinstance(r.get("rating"), (int, float))]
    if not valid:
        return None
    return round(sum(valid) / len(valid), 1)


def marker_response(marker: dict[str, Any]) -> dict[str, Any]:
    f: dict[str, Any] = marker.get("filter_json") or {}
    reviews: list[dict[str, Any]] = f.get("reviews") or []

    raw_address = f.get("road_address") or f.get("address") or ""
    address = (
        raw_address
        .removeprefix("서울특별시 ")
        .removeprefix("경기도 ")
        .strip()
    )

    open_time: str | None = f.get("open_time")
    close_time: str | None = f.get("close_time")
    hours = (
        f"{_format_time(open_time)} - {_format_time(close_time)}"
        if open_time and close_time
        else ""
    )

    # Image URLs: prefer array field; fall back to legacy scalar
    raw_urls = f.get("image_urls")
    if isinstance(raw_urls, list):
        image_urls = [u for u in raw_urls if isinstance(u, str) and u][:10]
    elif f.get("image_url"):
        image_urls = [f["image_url"]]
    else:
        image_urls = []

    return {
        "id": marker["id"],
        "placeRef": marker["place_ref"],
        "layerCode": marker["layer_code"],
        "label": marker["label"],
        "latitude": marker["latitude"],
        "longitude": marker["longitude"],
        "iconKey": marker["icon_key"],
        "visibility": marker["visibility"],
        "imageUrls": image_urls,
        "imageUrl": image_urls[0] if image_urls else "",
        "address": address,
        "hours": hours,
        "isOpen": _compute_is_open(open_time, close_time),
        "rating": _compute_rating(reviews),
        "reviewCount": len(reviews) if reviews else None,
        "menu": f.get("menu") or [],
        "inventory": f.get("inventory") or [],
        "reviews": reviews,
        "publishedRevision": marker["published_revision"],
        "publishedAt": marker["published_at"],
        "updatedAt": marker["updated_at"],
    }


def _short_hash(value: str) -> str:
    return hashlib.sha1(value.encode()).hexdigest()[:12]


def _inventory_items(filter_json: dict[str, Any], place_revision: str) -> list[dict[str, Any]]:
    items = filter_json.get("inventory") or []
    result = []
    for item in items:
        if not isinstance(item, dict):
            continue
        source_id = str(item.get("source_beverage_id") or item.get("name_ko") or "")
        inv_rev = f"inv_{_short_hash(source_id + place_revision)}"
        result.append({
            "inventory_revision": inv_rev,
            "source_beverage_id": source_id or None,
            "beverage_item_id": None,
            "availability_status": "available",
            "confidence": 0.9,
            "last_seen_at": None,
            "expires_at": None,
        })
    return result


def _menu_items(filter_json: dict[str, Any], place_revision: str) -> list[dict[str, Any]]:
    items = filter_json.get("menu") or []
    result = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        menu_id = f"menu_{_short_hash(name + str(i) + place_revision)}"
        result.append({
            "menu_item_id": menu_id,
            "menu_revision": f"mrev_{_short_hash(place_revision + str(i))}",
            "menu_name": name or f"Item {i + 1}",
            "status": "active",
        })
    return result


def snapshot_event(marker: dict[str, Any]) -> dict[str, Any]:
    f: dict[str, Any] = marker.get("filter_json") or {}
    place_id = marker["id"]
    pub_rev = str(marker.get("published_revision") or "0")
    place_revision = f"rev_{pub_rev}"
    updated_at = marker.get("updated_at") or marker.get("published_at")
    published_at = marker.get("published_at")
    occurred_at = (
        updated_at.isoformat() if isinstance(updated_at, datetime) else str(updated_at or "")
    )
    event_type = "place.updated" if updated_at != published_at else "place.published"
    event_id = f"evt_{_short_hash(place_id + place_revision)}"
    address = (
        (f.get("road_address") or f.get("address") or "")
        .removeprefix("서울특별시 ")
        .removeprefix("경기도 ")
        .strip()
    )
    return {
        "contract_version": "map_snapshot_event_v1",
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at": occurred_at,
        "place_id": place_id,
        "place_revision": place_revision,
        "venue": {
            "name": marker["label"],
            "place_type": marker["layer_code"],
            "status": "active",
            "publication_status": "published",
            "lat": marker["latitude"],
            "lng": marker["longitude"],
            "address": address or None,
        },
        "inventory": _inventory_items(f, place_revision),
        "menus": _menu_items(f, place_revision),
        "prices": [],
    }


def layer_response(layer: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": layer["code"],
        "labelKo": layer["label_ko"],
        "labelEn": layer["label_en"],
        "iconKey": layer["icon_key"],
        "displayOrder": layer["display_order"],
        "defaultVisible": layer["default_visible"],
        "isActive": layer["is_active"],
    }


def success(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    return HTTPStatus.OK, {"ok": True, **payload}


def error_payload(error: ApiError) -> tuple[int, dict[str, Any]]:
    return error.status, {"ok": False, "error": {"code": error.code, "message": error.message}}


_REVIEW_PATH_RE = re.compile(r"^/v1/map/markers/([0-9a-f-]+)/reviews$")
_REVIEW_DELETE_RE = re.compile(r"^/v1/map/markers/([0-9a-f-]+)/reviews/([0-9a-f-]+)$")


class MapReadApi:
    def __init__(self, repository: MapViewRepository) -> None:
        self.repository = repository

    def handle(
        self,
        method: str,
        path: str,
        query_params: dict[str, list[str]],
        *,
        body: dict[str, Any] | None = None,
    ) -> tuple[int, dict[str, Any]]:
        if method == "OPTIONS":
            return HTTPStatus.NO_CONTENT, {}
        if method not in ("GET", "POST", "DELETE"):
            raise ApiError(HTTPStatus.METHOD_NOT_ALLOWED, "method_not_allowed", "only GET, POST, and DELETE are supported")

        if path == "/healthz":
            return success({"service": "map-service", "status": "ok"})
        if path == "/v1/map/layers":
            return success({"layers": [layer_response(layer) for layer in self.repository.list_layers()]})
        if path == "/v1/map/markers":
            query = parse_marker_query(query_params)
            markers = self.repository.list_markers(query)
            return success(
                {
                    "markers": [marker_response(marker) for marker in markers],
                    "meta": {
                        "bbox": query.bbox,
                        "layers": query.layers,
                        "limit": query.limit,
                        "offset": query.offset,
                        "count": len(markers),
                    },
                }
            )

        if path == "/internal/v1/recommendation/map-snapshot-events":
            raw_cursor = query_params.get("cursor", [None])
            cursor_val = raw_cursor[-1] if raw_cursor else None
            raw_limit = query_params.get("limit", ["100"])
            try:
                snap_limit = max(1, min(int(raw_limit[-1]), 500))
            except (ValueError, IndexError):
                snap_limit = 100
            markers, next_cursor, has_more = self.repository.list_snapshot_events(
                cursor=cursor_val,
                limit=snap_limit,
            )
            watermark = datetime.now(_KST).isoformat()
            return success({
                "cursor": cursor_val,
                "next_cursor": next_cursor,
                "has_more": has_more,
                "snapshot_watermark": watermark,
                "events": [snapshot_event(m) for m in markers],
            })

        if path == "/v1/map/search":
            raw_q = query_params.get("q", [""])
            q = (raw_q[-1] if raw_q else "").strip()
            if not q:
                return success({"markers": [], "meta": {"q": "", "count": 0}})
            markers = self.repository.search_markers(q)
            return success({
                "markers": [marker_response(marker) for marker in markers],
                "meta": {"q": q, "count": len(markers)},
            })

        review_match = _REVIEW_PATH_RE.match(path)
        if review_match and method == "POST":
            marker_id = review_match.group(1)
            data = body or {}
            author_id = str(data.get("author_id") or "").strip()
            is_anonymous = bool(data.get("is_anonymous", False))
            author = str(data.get("author") or "Anonymous").strip()[:50] or "Anonymous"
            profile_image_url = str(data.get("profile_image_url") or "").strip() or None
            rating = data.get("rating")
            review_body = str(data.get("body") or "").strip()
            if not isinstance(rating, int) or not 1 <= rating <= 5:
                raise ApiError(HTTPStatus.BAD_REQUEST, "rating_invalid", "rating must be 1-5")
            if not review_body:
                raise ApiError(HTTPStatus.BAD_REQUEST, "body_required", "body is required")
            review = {
                "review_id": str(uuid.uuid4()),
                "author_id": author_id,
                "author": author,
                "is_anonymous": is_anonymous,
                "profile_image_url": profile_image_url,
                "rating": rating,
                "body": review_body,
                "date_label": _format_date(datetime.now(_KST)),
            }
            self.repository.add_review(marker_id, review)
            return success({"review": review})

        delete_match = _REVIEW_DELETE_RE.match(path)
        if delete_match and method == "DELETE":
            marker_id = delete_match.group(1)
            review_id = delete_match.group(2)
            self.repository.delete_review(marker_id, review_id)
            return success({"deleted": True})

        raise ApiError(HTTPStatus.NOT_FOUND, "not_found", "route not found")


def make_handler(api: MapReadApi, cors_origin: str) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_OPTIONS(self) -> None:
            self.respond(*api.handle("OPTIONS", self.path_only(), self.query_params()))

        def do_GET(self) -> None:
            try:
                self.respond(*api.handle("GET", self.path_only(), self.query_params(), body=None))
            except ApiError as error:
                self.respond(*error_payload(error))
            except Exception:
                self.respond(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"ok": False, "error": {"code": "internal_error", "message": "internal server error"}},
                )

        def do_POST(self) -> None:
            try:
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length) if length > 0 else b""
                body = json.loads(raw) if raw else {}
                if not isinstance(body, dict):
                    body = {}
                self.respond(*api.handle("POST", self.path_only(), self.query_params(), body=body))
            except ApiError as error:
                self.respond(*error_payload(error))
            except Exception:
                self.respond(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"ok": False, "error": {"code": "internal_error", "message": "internal server error"}},
                )

        def do_DELETE(self) -> None:
            try:
                self.respond(*api.handle("DELETE", self.path_only(), self.query_params(), body=None))
            except ApiError as error:
                self.respond(*error_payload(error))
            except Exception:
                self.respond(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"ok": False, "error": {"code": "internal_error", "message": "internal server error"}},
                )

        def path_only(self) -> str:
            return urlparse(self.path).path

        def query_params(self) -> dict[str, list[str]]:
            return parse_qs(urlparse(self.path).query, keep_blank_values=True)

        def respond(self, status: int, payload: dict[str, Any]) -> None:
            body = b"" if status == HTTPStatus.NO_CONTENT else json.dumps(
                payload,
                ensure_ascii=False,
                default=json_default,
            ).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", cors_origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:
            if os.environ.get("MAP_SERVICE_API_LOGS", "false").lower() == "true":
                super().log_message(format, *args)

    return Handler


def run_server(*, host: str, port: int, database_url: str, cors_origin: str) -> None:
    api = MapReadApi(MapViewRepository(database_url))
    server = ThreadingHTTPServer((host, port), make_handler(api, cors_origin))
    print(json.dumps({"ok": True, "service": "map-service", "addr": f"http://{host}:{port}"}, ensure_ascii=False))
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the read-only map_view marker API.")
    parser.add_argument("--host", default=os.environ.get("MAP_SERVICE_API_HOST", DEFAULT_HOST))
    parser.add_argument("--port", type=int, default=int(os.environ.get("MAP_SERVICE_API_PORT", DEFAULT_PORT)))
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--cors-origin", default=os.environ.get("MAP_SERVICE_API_CORS_ORIGIN", "*"))
    args = parser.parse_args()

    run_server(
        host=args.host,
        port=args.port,
        database_url=resolve_database_url(args.database_url),
        cors_origin=args.cors_origin,
    )


if __name__ == "__main__":
    main()
