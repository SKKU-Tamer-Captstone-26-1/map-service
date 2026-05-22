# Map View FK Rules

## 핵심 규칙

`map_view`의 실제 DB foreign key는 `map_view` 내부 관계에만 둡니다.

`map_view`는 published read model이므로 canonical DB와 느슨하게 연결되어야 합니다. 나중에 별도 DB, cache, search index로 분리될 수 있기 때문입니다.

## Allowed Physical FKs

| From | To | Required | Notes |
|---|---|---:|---|
| `map_view.markers.layer_code` | `map_view.marker_layers.code` | Yes | 마커가 속한 지도 레이어 |
| `map_view.marker_publication_events.marker_id` | `map_view.markers.id` | Yes, nullable | 삭제/제거 이벤트 보존을 위해 `ON DELETE SET NULL` |

## Logical Only Relationships

아래 관계는 실제 DB FK로 만들지 않습니다.

| Source | Target | Physical FK | Reason |
|---|---|---:|---|
| `map_view.markers.place_ref` | `admin_ops.places.id` | No | publish workflow가 일관성을 책임짐 |
| `admin_ops.places.display_name` | `map_view.markers.label` | No | 승인된 값의 read-model copy |
| `admin_ops.places.location` | `map_view.markers.location` | No | 승인된 좌표의 read-model copy |
| `admin_ops.place_map_settings.layer_code` | `map_view.markers.layer_code` | No | publish 시점 검증 대상 |
| `admin_ops.publish_jobs` | `map_view.marker_publication_events` | No | app workflow 관계 |

## Forbidden FKs

`map_view`에서 아래 대상에 대한 DB FK를 만들지 않습니다.

```text
admin_ops.places
auth-service tables
recommendation-service tables
survey-service tables
chatbot-service tables
catalog/RAG tables
```

Auth user id나 catalog id가 필요해도 `map_view`에는 넣지 않는 것이 기본입니다. 필요성이 생기면 먼저 read-model payload 요구사항을 다시 검토합니다.

## Verification

`scripts/db/verify_map_view_schema.py`는 다음을 확인합니다.

```text
- PostGIS extension exists
- map_view schema exists
- marker_layers / markers / marker_publication_events exist
- markers.location is geography(Point,4326)
- markers.location has GiST index
- only allowed internal map_view FKs exist
- map_view does not contain admin/import/menu/audit tables
- old public oversized tables are reported as legacy
```

`--strict-clean-db`는 old public oversized tables가 남아 있으면 실패합니다. clean map_view-only DB에서는 통과해야 하며, 이전 local DB에 이미 old tables가 적용되어 있다면 DB cleanup/reset 승인이 필요한 상태로 봅니다.
