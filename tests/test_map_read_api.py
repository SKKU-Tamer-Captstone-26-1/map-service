from __future__ import annotations

import unittest
from datetime import UTC, datetime
from http import HTTPStatus

from scripts.api.map_read_api import ApiError, MapReadApi, parse_marker_query


class FakeRepository:
    def list_layers(self) -> list[dict[str, object]]:
        return [
            {
                "code": "pub",
                "label_ko": "펍",
                "label_en": "Pub",
                "icon_key": "beer",
                "display_order": 20,
                "default_visible": True,
                "is_active": True,
            }
        ]

    def list_markers(self, query: object) -> list[dict[str, object]]:
        now = datetime(2026, 5, 23, 12, 0, tzinfo=UTC)
        return [
            {
                "id": "10000000-0000-4000-8000-000000000001",
                "place_ref": "20000000-0000-4000-8000-000000000001",
                "layer_code": "pub",
                "label": "DEV 홍대 펍 샘플",
                "latitude": 37.5563,
                "longitude": 126.9229,
                "icon_key": "beer",
                "visibility": "visible",
                "filter_json": {"fixture": True},
                "published_revision": 1,
                "published_at": now,
                "updated_at": now,
            }
        ]


class MapReadApiTest(unittest.TestCase):
    def test_parse_marker_query_requires_valid_bbox(self) -> None:
        query = parse_marker_query({"bbox": ["126.88,37.53,126.97,37.59"], "limit": ["50"], "offset": ["100"]})
        self.assertEqual(query.bbox, (126.88, 37.53, 126.97, 37.59))
        self.assertEqual(query.layers, ())
        self.assertEqual(query.limit, 50)
        self.assertEqual(query.offset, 100)

    def test_parse_marker_query_rejects_unknown_layer(self) -> None:
        with self.assertRaises(ApiError) as context:
            parse_marker_query({"bbox": ["126.88,37.53,126.97,37.59"], "layers": ["pub,kakao"]})
        self.assertEqual(context.exception.status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(context.exception.code, "layers_invalid")

    def test_parse_marker_query_rejects_missing_bbox(self) -> None:
        with self.assertRaises(ApiError) as context:
            parse_marker_query({})
        self.assertEqual(context.exception.status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(context.exception.code, "bbox_required")

    def test_parse_marker_query_rejects_invalid_offset(self) -> None:
        with self.assertRaises(ApiError) as context:
            parse_marker_query({"bbox": ["126.88,37.53,126.97,37.59"], "offset": ["-1"]})
        self.assertEqual(context.exception.status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(context.exception.code, "offset_invalid")

    def test_layers_response_contract(self) -> None:
        status, payload = MapReadApi(FakeRepository()).handle("GET", "/v1/map/layers", {})
        self.assertEqual(status, HTTPStatus.OK)
        self.assertTrue(payload["ok"])
        self.assertEqual(
            payload["layers"][0],
            {
                "code": "pub",
                "labelKo": "펍",
                "labelEn": "Pub",
                "iconKey": "beer",
                "displayOrder": 20,
                "defaultVisible": True,
                "isActive": True,
            },
        )

    def test_markers_response_contract(self) -> None:
        status, payload = MapReadApi(FakeRepository()).handle(
            "GET",
            "/v1/map/markers",
            {"bbox": ["126.88,37.53,126.97,37.59"], "layers": ["pub"], "limit": ["10"], "offset": ["500"]},
        )
        self.assertEqual(status, HTTPStatus.OK)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["meta"]["bbox"], (126.88, 37.53, 126.97, 37.59))
        self.assertEqual(payload["meta"]["layers"], ("pub",))
        self.assertEqual(payload["meta"]["limit"], 10)
        self.assertEqual(payload["meta"]["offset"], 500)
        self.assertEqual(payload["meta"]["count"], 1)
        self.assertEqual(payload["markers"][0]["placeRef"], "20000000-0000-4000-8000-000000000001")
        self.assertEqual(payload["markers"][0]["layerCode"], "pub")
        self.assertEqual(payload["markers"][0]["filter"], {"fixture": True})

    def test_unknown_route_returns_not_found(self) -> None:
        with self.assertRaises(ApiError) as context:
            MapReadApi(FakeRepository()).handle("GET", "/missing", {})
        self.assertEqual(context.exception.status, HTTPStatus.NOT_FOUND)
        self.assertEqual(context.exception.code, "not_found")


if __name__ == "__main__":
    unittest.main()
