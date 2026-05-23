# Map Read API

This is the read-only API contract for frontend map work.

The API reads only from `map_view`:

```text
map_view.marker_layers
map_view.markers
```

It does not read canonical place tables, public-data candidate tables, Kakao APIs, or admin workflow state.

## Run Locally

```bash
python3 scripts/db/apply_migrations.py
python3 scripts/db/seed_dev_map_markers.py --apply
python3 -m scripts.api.map_read_api
```

Default address:

```text
http://127.0.0.1:8088
```

The dev marker seed is synthetic local fixture data only. It does not insert canonical places or public/open data.

## Health

```http
GET /healthz
```

Response:

```json
{
  "ok": true,
  "service": "map-service",
  "status": "ok"
}
```

## Layers

```http
GET /v1/map/layers
```

Response:

```json
{
  "ok": true,
  "layers": [
    {
      "code": "pub",
      "labelKo": "펍",
      "labelEn": "Pub",
      "iconKey": "beer",
      "displayOrder": 20,
      "defaultVisible": true,
      "isActive": true
    }
  ]
}
```

## Markers

```http
GET /v1/map/markers?bbox=126.88,37.53,126.97,37.59&layers=bar,pub&limit=200
```

Query parameters:

| Name | Required | Meaning |
|---|---:|---|
| `bbox` | yes | `minLon,minLat,maxLon,maxLat` in WGS84 |
| `layers` | no | comma-separated layer codes |
| `limit` | no | `1..500`, default `200` |

Response:

```json
{
  "ok": true,
  "markers": [
    {
      "id": "10000000-0000-4000-8000-000000000001",
      "placeRef": "20000000-0000-4000-8000-000000000001",
      "layerCode": "pub",
      "label": "DEV 홍대 펍 샘플",
      "latitude": 37.5563,
      "longitude": 126.9229,
      "iconKey": "beer",
      "visibility": "visible",
      "filter": {
        "fixture": true,
        "source": "local_dev_seed"
      },
      "publishedRevision": 1,
      "publishedAt": "2026-05-23T00:00:00+09:00",
      "updatedAt": "2026-05-23T00:00:00+09:00"
    }
  ],
  "meta": {
    "bbox": [126.88, 37.53, 126.97, 37.59],
    "layers": ["bar", "pub"],
    "limit": 200,
    "count": 1
  }
}
```

Only `visible` markers from active layers are returned.

## Errors

Error response shape:

```json
{
  "ok": false,
  "error": {
    "code": "bbox_required",
    "message": "bbox query parameter is required"
  }
}
```

Common codes:

```text
bbox_required
bbox_invalid
layers_invalid
limit_invalid
not_found
method_not_allowed
internal_error
```

## Frontend Boundary

Frontend may use this API for marker rendering and layer toggles.

Frontend must not assume:

- marker rows are canonical place records
- public/open data has been approved
- Kakao API responses are persisted
- `placeRef` is backed by a local DB foreign key
