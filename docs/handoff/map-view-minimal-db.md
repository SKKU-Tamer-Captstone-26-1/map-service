# Map View Minimal DB

## TL;DR

`map_view`는 지도 UI가 마커를 그리기 위한 published read model입니다.

이 DB는 장소 원본을 소유하지 않습니다. 상호명, 주소, 영업상태, 운영시간, 메뉴, 재고, 가격, 사장님 요청, 운영자 승인, audit는 `admin_ops` 쪽 canonical DB가 소유합니다.

원칙은 아래 하나입니다.

```text
Map DB stores what to draw.
Admin/Place DB owns what the place is.
```

## Source Of Truth

이번 작업의 기준 파일은 repo root의 `map_view.dbml`입니다.

요청서에 나온 `map_view_minimal_erd_v0_8.md`는 현재 repo에 없고, 같은 내용을 설명하는 `map_view.md`를 equivalent 문서로 사용합니다.

## map_view가 소유하는 것

| Table | Purpose | Writer | Reader | Notes |
|---|---|---|---|---|
| `map_view.marker_layers` | 지도 레이어와 기본 아이콘 설정 | publish/config workflow | Map UI, cache/sync | 장소 카테고리의 canonical owner가 아님 |
| `map_view.markers` | 지도에 표시할 published marker projection | publish workflow | Map UI | `label`, `location`은 승인된 복사본 |
| `map_view.marker_publication_events` | 마커 변경 이벤트 기록 | publish workflow | cache/sync, observability | 추천/캐시 동기화 입력으로 사용 가능 |

## map_view가 소유하지 않는 것

아래 데이터는 `map_view`에 넣지 않습니다.

| Data | Owner | Reason |
|---|---|---|
| places / place details | `admin_ops` | canonical 장소 원본 |
| address / business status | `admin_ops` | 운영자 승인과 lifecycle 대상 |
| business hours / special hours | `admin_ops` | 상세 정보 API 대상 |
| menu / inventory / price | `admin_ops` | 점주/운영자 변경 workflow 대상 |
| business claims / managers | `admin_ops` | 권한과 승인 workflow 대상 |
| change requests / publish jobs | `admin_ops` | 운영 workflow 대상 |
| audit logs | `admin_ops` | canonical write audit |
| import batches / candidates | ingest/admin workflow | 후보 데이터 staging |
| recommendation snapshots | recommendation-service | 추천 read model |
| Kakao Local/Map data | external realtime support only | canonical bulk persistence 금지 |

## Column Mapping

`map_view.dbml`의 이름을 우선합니다.

| Concept in task prompt | Actual DBML column | Notes |
|---|---|---|
| `display_name` | `label_ko`, `label_en` | 레이어 표시명 |
| `default_icon_key` | `icon_key` | 레이어 기본 아이콘 |
| `sort_order` | `display_order` | 레이어 표시 순서 |
| `default_visibility` | `default_visible` | 기본 표시 여부 |
| dotted event type | underscore enum value | DB enum은 `marker_published` 형식 |

## Read/Write Boundary

Map UI는 아래만 읽습니다.

```text
map_view.marker_layers
map_view.markers
```

Map UI는 `map_view`를 직접 쓰지 않습니다.

발행 흐름은 다음처럼 의도합니다.

```text
admin_ops.places
admin_ops.place_map_settings
admin_ops.publish_jobs
        ↓
publish worker/API
        ↓
map_view.markers upsert
map_view.marker_publication_events append
```

이번 작업에서는 publish worker/API를 구현하지 않습니다.

## Local Verification

비파괴 검증:

```bash
python3 scripts/db/verify_map_view_schema.py
```

clean rebaseline 여부까지 확인할 때:

```bash
python3 scripts/db/verify_map_view_schema.py --strict-clean-db
```

clean map_view-only DB에서는 `--strict-clean-db`가 통과해야 합니다. 이전 oversized migration을 이미 적용한 local DB에서는 기존 `public` tables 때문에 실패할 수 있으며, 이 경우 DB reset/drop은 별도 승인 후 처리합니다.
