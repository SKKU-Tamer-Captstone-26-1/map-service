# Map/Place Ownership

## map_view Owns

`map_view` owns only published marker projection data.

| Data | Owner |
|---|---|
| marker layers | `map_view` |
| visible/hidden marker projection | `map_view` |
| marker publication events | `map_view` |

## map_view Does Not Own

| Data | Expected Owner |
|---|---|
| canonical place name/address/location | `admin_ops` or place-service |
| source registry | ingest/admin workflow |
| import batches/candidates | ingest/admin workflow |
| dedupe/review tasks | ingest/admin workflow |
| menu/inventory/price | `admin_ops` or venue owner workflow |
| owner claims/managers | `admin_ops` |
| canonical audit | `admin_ops` |

## External Source Ownership

Official public/open data remains external evidence until reviewed.

Kakao Local/Map API results are realtime support only. They must not be treated as canonical storable place data unless separate legal or partnership approval is documented.

## Publish Ownership

Only an approved publish workflow may write to `map_view.markers`.

Admin Page and recommendation-service must not write directly to map-service tables.
