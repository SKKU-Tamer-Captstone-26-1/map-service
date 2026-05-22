# Map / Place Data Ingestion Strategy v0.1

## 0. 결론

지도 DB의 데이터는 하나의 source에서 가져오면 안 됩니다.

권장 흐름은 다음입니다.

```text
1. 저장 가능한 공공데이터 → 장소 후보 seed
2. 운영자/현장조사 데이터 → 검수 및 canonical 확정
3. 점주/관리자 Admin 입력 → 메뉴, 재고, 가격, 시그니처 메뉴
4. 사용자 제보 → pending review
5. Kakao API → 실시간 검색/지도 링크/검증 보조용
```

핵심 원칙:

```text
Kakao is not canonical by default.
Public/field/owner/operator data can become canonical only after source policy and review.
Menu, inventory, and price require owner/operator/field input and freshness tracking.
```

## 1. 데이터 흐름

```text
[공공데이터 / 현장조사 / 점주 입력 / 사용자 제보]
        ↓
place_import_batches
        ↓
place_import_candidates
        ↓
normalize / geocode / category mapping
        ↓
dedupe / source matching
        ↓
place_review_tasks
        ↓
operator review
        ↓
places + place_source_refs
        ↓
published place
        ↓
place_outbox_events
        ↓
지도 화면 + 추천 서비스 snapshot + 챗봇 map-service tool/API
```

## 2. Source별 역할

| Source | 역할 | Canonical 가능 여부 | 비고 |
|---|---|---:|---|
| 운영자 입력 | 최종 검수/수정 | 가능 | 가장 높은 우선순위 |
| 점주 입력 | 메뉴/재고/가격/영업정보 | 가능 | 민감 변경은 승인 필요 |
| 현장조사 | 장소 품질/실재 여부 검증 | 가능 | 운영자가 검수 |
| 저장 가능한 공공데이터 | 장소 후보 seed | 가능 | 라이선스/저장 가능 여부 확인 필요 |
| 사용자 제보 | 오류/폐업/가격/재고 신고 | 직접 불가 | review 후 반영 |
| Kakao API | 실시간 조회/검증/지도 링크 | 기본 불가 | 별도 승인 전까지 realtime/restricted |

## 3. 공공데이터 Seed 전략

### 3.1 소상공인 상가(상권)정보

장소 후보 seed로 가장 먼저 검토합니다.

활용 목적:

```text
- bar/pub/liquor_shop 후보 추출
- 상호명/주소/업종/위경도 기반 draft candidate 생성
- place_import_candidates에 저장
- 운영자 review 후 places로 승격
```

주의:

```text
- 공공데이터라고 해서 바로 published 처리하지 않는다.
- 업종 분류가 앱 타깃과 정확히 맞지 않을 수 있다.
- 중복/폐업/좌표 오류가 있을 수 있다.
- source license와 저장 가능 여부를 data_sources에 기록한다.
```

예상 필터 키워드:

```text
bar/pub 후보:
- 바
- 펍
- 호프
- 맥주
- 와인
- 칵테일
- 이자카야
- 주점

liquor_shop 후보:
- 주류판매
- 주류점
- 와인샵
- 보틀샵
- 리큐르샵
- 리커샵
- 세계주류
```

### 3.2 인허가 / 영업상태 데이터

장소 후보의 영업상태 검증에 사용합니다.

활용 목적:

```text
- 현재 영업/폐업/말소 상태 확인
- 폐업 후보 review_task 생성
- 업종/영업 형태 검증
```

주의:

```text
- 인허가 데이터만으로 좋은 바/펍인지 판단하지 않는다.
- 폐업 상태로 보이면 자동 반영하지 말고 review_task를 생성한다.
- 운영자가 이미 CLOSED/ARCHIVED/DUPLICATE_MERGED로 처리한 장소는 자동 재활성화하지 않는다.
```

### 3.3 공원 / 야외 장소 데이터

야외 장소는 일반 매장과 다릅니다.

활용 목적:

```text
- 한강공원/공원/피크닉 장소 후보 생성
- outdoor_spot_profiles 작성
- 주변 편의점/주류점/바와 결합해 추천
```

야외 장소 추천은 다음 구조입니다.

```text
마시기 좋은 장소
+ 근처 구매 후보
+ 거리/가격/재고
+ 날씨/혼잡도/동선
```

## 4. Kakao API 정책

Kakao Local/Map API는 기본적으로 canonical bulk-ingestion source로 사용하지 않습니다.

기본 허용:

```text
- 사용자의 실시간 장소 검색
- 지도 화면 표시 보조
- 운영자 검수 시 보조 확인
- 카카오맵 외부 링크 제공
- 주소/좌표 확인 보조
```

기본 금지:

```text
- Kakao Local API 결과를 대량 수집
- Kakao 응답 장소명/주소/좌표/전화번호를 canonical DB로 장기 저장
- Kakao 데이터를 기반으로 자체 POI 검색 DB 구축
- CLOSED/ARCHIVED/DUPLICATE_MERGED 장소를 Kakao 결과만 보고 자동 재활성화
```

Kakao 관련 source는 기본적으로 다음 중 하나로 기록합니다.

```text
source_type = KAKAO
source_policy = REALTIME_ONLY | RESTRICTED
```

저장 가능한 범위가 법무/제휴/정책 검토로 명확해진 경우에만 `STORABLE`로 변경할 수 있습니다.

참고용 정책 확인 링크:

```text
https://devtalk.kakao.com/t/faq-api/125610
https://devtalk.kakao.com/t/api/148194
https://developers.kakao.com/docs/ko/local/dev-guide
```

## 5. Staging 테이블 사용 방법

### 5.1 `place_import_batches`

하나의 import 실행 단위입니다.

예:

```text
source: 소상공인 상가정보
import_type: PUBLIC_DATA_FILE
file_name: store_2026_Q1_seoul.csv
status: RUNNING → COMPLETED
row_count: 120000
success_count: 118000
error_count: 2000
```

### 5.2 `place_import_candidates`

각 row를 canonical 장소 후보로 저장합니다.

필수 처리:

```text
- raw_payload_json 저장
- normalized_name 생성
- normalized_address 생성
- candidate_place_type 추론
- latitude/longitude/location 생성
- source_policy 복사
```

### 5.3 `place_dedupe_matches`

후보와 기존 장소의 중복 가능성을 저장합니다.

dedupe strategy 예:

```text
source_external_id
normalized_name + normalized_address
normalized_name + distance radius
phone number
operator manual match
```

자동 병합은 피합니다.

```text
confidence >= 0.95: auto-suggest, not auto-merge by default
0.70 <= confidence < 0.95: review required
confidence < 0.70: new candidate or low priority review
```

### 5.4 `place_review_tasks`

운영자 review queue입니다.

생성 조건:

```text
- 새 장소 후보
- 중복 후보
- 좌표 불확실
- 폐업 가능성
- source 간 상호명/주소 충돌
- 점주 민감 변경 요청
- 사용자 제보
```

## 6. Normalization 규칙

### 6.1 이름 정규화

예상 처리:

```text
- trim
- lower-case where applicable
- 특수문자 단순화
- 지점명 패턴 보존
- 괄호 안 지점명 분리 보조
- 공백 중복 제거
```

주의:

```text
"바밤바" 같은 상호명을 잘못 분해하지 않는다.
"강남점", "역삼점" 같은 지점명은 dedupe에서 중요한 signal이다.
```

### 6.2 주소 정규화

예상 처리:

```text
- 도로명주소 우선
- 지번주소 fallback
- 시/구/동 분리
- 상세주소와 건물명 분리
- 좌표가 있으면 PostGIS location 생성
```

### 6.3 Category Mapping

공공데이터 업종명/상호명에서 앱 내부 `place_type`으로 mapping합니다.

```text
BAR
PUB
LIQUOR_SHOP
BOTTLE_SHOP
RESTAURANT
OUTDOOR_SPOT
CONVENIENCE_STORE
OTHER
```

초기에는 rule-based mapping으로 충분합니다.

향후 운영자 review 결과를 쌓아 mapping 품질을 개선합니다.

## 7. Publication 규칙

`places`에 생성되었다고 바로 지도에 노출하지 않습니다.

지도 화면 노출 조건:

```text
status = ACTIVE
publication_status = PUBLISHED
published_at IS NOT NULL
```

추천 후보 조건:

```text
status = ACTIVE
publication_status = PUBLISHED
recommendation_eligible = true
```

## 8. 폐업 / 중복 / 재활성화 정책

절대 자동 재활성화하지 않는 상태:

```text
CLOSED
ARCHIVED
DUPLICATE_MERGED
```

규칙:

```text
if place.status in ["CLOSED", "ARCHIVED", "DUPLICATE_MERGED"]:
    ingestion_worker must not reactivate automatically
    create review_task instead
```

## 9. 메뉴 / 재고 / 가격 데이터 수집

공공데이터나 Kakao API로는 매장별 현재 재고, 가격, 시그니처 메뉴를 안정적으로 얻기 어렵습니다.

따라서 다음 경로로 입력합니다.

```text
1. 점주 Admin 입력
2. 운영자 입력
3. 현장조사 입력
4. 사용자 제보 → pending review
5. POS/매장 시스템 연동, 향후
```

### 9.1 메뉴

입력 주체:

```text
owner
operator
field_research
```

핵심 필드:

```text
menu_name
menu_type
base_price_krw
is_signature
status
last_verified_at
```

### 9.2 재고

핵심 필드:

```text
availability_status
stock_confidence
last_seen_at
expires_at
```

추천 confidence 정책 예시:

```text
updated <= 3 days: high confidence
updated <= 7 days: medium confidence
updated >= 30 days: low confidence or exclude from recommendation
```

### 9.3 가격

핵심 필드:

```text
price_krw
price_type
valid_from
valid_until
confidence
```

가격은 이벤트/해피아워/기간 한정이 있을 수 있으므로 `valid_until`이 중요합니다.

## 10. 추천 서비스와 연결

map-service는 다음 이벤트를 발행합니다.

```text
place.published
place.updated
place.hidden
place.closed
place.merged
menu.created
menu.updated
menu.discontinued
inventory.updated
price.updated
```

recommendation-service는 직접 map DB를 읽지 않습니다.

대신 다음 read model을 만듭니다.

```text
venue_snapshots
venue_inventory_snapshots
venue_price_snapshots
```

추천 로그에는 다음 revision을 남깁니다.

```text
place_revision
inventory_revision
price_revision
```

## 11. MVP 수집 순서

전국 단위로 시작하지 않습니다.

권장 MVP 지역:

```text
- 강남 / 신논현 / 역삼
- 홍대 / 연남 / 합정
- 이태원 / 한남
- 성수
- 을지로 / 종로
- 여의도 / 한강 인근
```

권장 순서:

```text
Step 1. 공공데이터로 후보 추출
Step 2. 업종명/상호명으로 bar/pub/liquor_shop 후보 필터링
Step 3. 영업상태/인허가 source로 폐업/영업 여부 검증
Step 4. 운영자가 핵심 매장 100~300개 검수
Step 5. Admin Page로 메뉴/재고/가격 입력
Step 6. 점주 claim 기능 오픈
Step 7. 추천 서비스에 published snapshot 제공
```

## 12. Codex 구현 시 금지사항

```text
- Kakao API 결과를 canonical DB로 대량 저장하지 말 것
- 공공데이터 후보를 바로 published 처리하지 말 것
- recommendation-service가 map DB를 직접 읽거나 쓰게 하지 말 것
- auth-service user table에 DB FK를 걸지 말 것
- 점주가 상호명/주소/좌표/폐업을 바로 수정하게 하지 말 것
- CLOSED/ARCHIVED/DUPLICATE_MERGED 장소를 자동 재활성화하지 말 것
- 재고/가격에 freshness/confidence 없이 추천에 쓰지 말 것
```

## 13. 남은 확인 사항

```text
1. 각 공공데이터 source의 저장/재배포/상업적 이용 가능 여부
2. Kakao API 저장 가능 범위에 대한 법무/제휴 검토
3. MVP 지역과 검수 인력 범위
4. 점주 claim 인증 방식
5. 메뉴/재고/가격 갱신 주기와 알림 정책
6. 운영자 review UI 1차 범위
```
