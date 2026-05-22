# Map / Place Data Quality Rules

이 문서는 `map_place_data_bootstrap_v0_3/data/data_quality_rules.csv`와 import utilities의 현재 rule behavior를 설명합니다.

## Rule Outcomes

| Outcome | Meaning |
|---|---|
| `accept_candidate` | 후보로 받을 수 있음 |
| `needs_review` | staging 후보로 받되 운영자 검수 필요 |
| `reject_candidate` | 현재 row는 import하면 안 됨 |
| `defer` | 추가 데이터나 정책 확인 전까지 보류 |

## Implemented Rules

| Rule | Trigger | Result | Notes |
|---|---|---|---|
| `MISSING_NAME` | 장소명/상호명이 없음 | `reject_candidate` | public/operator/outdoor 후보에 적용 |
| `MISSING_ADDRESS_AND_COORDS` | 주소와 좌표가 모두 없음 | `reject_candidate` | 최소 위치 단서 필요 |
| `MISSING_COORDS` | 주소는 있지만 좌표가 없음 | `needs_review` | `metadata_json.geocode_required=true`로 표현 |
| `INVALID_LAT_LNG` | 위도/경도 범위 오류 | `reject_candidate` | WGS84 lat/lng 기준 |
| `DUP_SOURCE_EXTERNAL_ID` | import 내 source external id 중복 | `needs_review` | DB-level global dedupe는 follow-up |
| `AMBIGUOUS_BUSINESS_TYPE` | 타입이 없거나 `OTHER` | `needs_review` | category mapping으로 보완 |
| `RESTRICTED_SOURCE_POLICY` | restricted/realtime source를 canonical 저장하려는 시도 | `reject_candidate` | staging은 가능할 수 있으나 publish 금지 |
| `KAKAO_PERSISTENCE_ATTEMPT` | Kakao를 canonical bulk 저장하려는 시도 | `reject_candidate` | 절대 기본 허용하지 않음 |
| `CLOSED_LICENSE_STATUS` | 인허가 상태가 폐업/말소/취소/폐쇄 | `needs_review` | 자동 close 금지 |
| `OUTDATED_INVENTORY` | inventory가 stale/expired | `needs_review` | 추천에서 감점/제외 정책 필요 |
| `EXPIRED_PRICE_OFFER` | price `valid_until`이 과거 | `reject_candidate` | 재입력 필요 |

## Category Mapping Behavior

`category_mapping_seed.csv`는 clear category도 대부분 `needs_review`로 둡니다. 이유는 공공데이터 업종명이 앱 타깃 적합성을 보장하지 않기 때문입니다.

Examples:

- `와인샵` -> `BOTTLE_SHOP`
- `한강공원` -> `OUTDOOR_SPOT`
- `일반음식점` -> `RESTAURANT`, but review required
- `단란주점`, `유흥주점` -> `OTHER`, exclude/review by default

## Kakao Rule

Kakao data cannot become canonical bulk-ingestion data by default.

If a CSV row or source registry row attempts:

```text
source_type = KAKAO
source_policy = STORABLE
```

the import must fail validation.

## Follow-up Rules Not Yet DB-backed

- Nearby duplicate check against existing `places`.
- Dedupe match insertion into `place_dedupe_matches`.
- Coordinate distance scoring against DB records.
- License status matching against existing canonical places.
- Inventory stale policy by product category.
- Price validity policy by offer type.
