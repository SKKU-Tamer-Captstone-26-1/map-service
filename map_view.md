# Map View Minimal ERD v0.8

## 결론

지도 DB가 테이블 1개인 구조도 가능하지만, 실제 서비스 운영과 팀 인수인계를 생각하면 **너무 극단적인 단순화**입니다.

다만 이전처럼 지도 DB에 상호명, 주소, 운영시간, 가격, 메뉴, 재고, 사장님 요청, 운영자 승인, audit, import staging까지 모두 넣는 것도 과합니다.

따라서 권장 구조는 다음입니다.

```text
admin_ops / place-admin
= canonical owner
= 상호명, 주소, 업종, 운영시간, 메뉴, 가격, 재고, 사장님 요청, 운영자 승인, audit 관리

map_view
= published marker read model
= 지도 UI가 마커를 그리는 데 필요한 최소 데이터만 보유
```

핵심은 **데이터를 어디에 저장하느냐**보다 **누가 소유하고 누가 수정할 수 있느냐**입니다.

`map_view`에 `label`, `location`, `layer_code` 같은 값이 있어도, 이것들은 지도에서 수정하는 값이 아닙니다. 운영자 승인 후 `admin_ops`에서 발행된 결과를 복제한 **읽기 전용 projection**입니다.

---

## 왜 1개 테이블은 너무 단순한가?

이전 v0.6처럼 `markers` 하나만 두면 지도 마커를 찍는 것은 가능합니다.

하지만 아래 요구가 생기면 바로 애매해집니다.

```text
- 바 / 펍 / 주류점 / 야외장소 레이어 토글
- 마커 아이콘 종류 관리
- 추천 서비스나 캐시가 변경 이벤트를 받아야 함
- 특정 publish revision 기준으로 지도 상태를 추적해야 함
- 지도 클라이언트가 hidden/visible 상태를 안정적으로 필터링해야 함
```

그래서 최소한 아래 3개 테이블은 두는 것이 좋습니다.

```text
map_view.marker_layers
map_view.markers
map_view.marker_publication_events
```

---

## 테이블 역할

### 1. `map_view.marker_layers`

지도 레이어와 아이콘 구성을 관리합니다.

예:

```text
bar
pub
liquor_shop
outdoor_spot
```

이 테이블은 장소 상세정보가 아니라 **지도 표현 설정**입니다.

---

### 2. `map_view.markers`

지도에 실제로 찍히는 마커입니다.

포함하는 값:

```text
- place_ref
- layer_code
- label
- location
- geohash
- icon_key
- visibility
- filter_json
- published_revision
- published_at
```

여기서 `label`은 상호명을 map_view가 소유한다는 뜻이 아닙니다.

```text
admin_ops.places.display_name
  -> 운영자 승인
  -> publish workflow
  -> map_view.markers.label
```

즉 `label`은 지도 렌더링을 위한 published copy입니다.

지도에서는 이 값을 수정할 수 없습니다.

---

### 3. `map_view.marker_publication_events`

지도 마커가 발행/숨김/이동/삭제되었을 때 이벤트를 남깁니다.

용도:

```text
- 추천 서비스 snapshot sync
- 지도 캐시 invalidation
- 운영자가 publish한 지도 변경 추적
```

이 테이블이 부담된다면 MVP에서는 admin_ops의 publish event를 그대로 써도 됩니다. 하지만 map_view가 독립적인 read model이 된다면 남겨두는 편이 좋습니다.

---

## 제외되는 항목

아래는 `map_view`에 넣지 않습니다.

```text
- 상호명 원본
- 주소 원본
- 상세주소
- 전화번호
- 웹사이트
- 인스타그램
- 업종 원본
- 영업상태 원본
- 운영시간
- 메뉴
- 가격
- 재고
- 점주 요청
- 운영자 승인
- business claim
- audit log
- import staging
- Kakao source data
```

이 값들은 `admin_ops` 또는 place/admin service에서 소유하고, 지도에는 승인된 결과 중 지도 렌더링에 필요한 일부만 publish합니다.

---

## 마커 클릭 시 상세정보는 어디서 가져오나?

지도 DB에서 가져오지 않습니다.

```text
Map UI
  -> map_view.markers로 마커 렌더링
  -> marker tap
  -> Place Detail API 호출
  -> admin/place service의 published detail 반환
```

즉 지도 DB는 상세정보 DB가 아니라 마커 read model입니다.

---

## 권장 흐름

```text
Owner / Manager
  -> Admin Page
  -> Admin API
  -> admin_ops.change_requests
  -> operator approval
  -> admin_ops.publish_jobs
  -> map_view.markers 갱신
  -> map_view.marker_publication_events 생성
  -> Map UI / Recommendation snapshot sync
```

---

## MVP 판단

### 정말 최소 MVP

```text
map_view.markers
```

가능은 합니다.

조건:

```text
- 레이어/아이콘 설정은 코드 상수로 관리
- 이벤트/outbox는 admin_ops에서 처리
- 지도는 마커만 찍고 상세는 API로 조회
```

### 권장 MVP

```text
map_view.marker_layers
map_view.markers
map_view.marker_publication_events
```

이 정도가 가장 균형이 좋습니다.

지도 DB는 여전히 작고, Admin/Place DB와 책임도 분리되며, 팀원이 “이게 왜 테이블 하나뿐이지?”라고 혼란스러워하지 않습니다.

---

## 최종 원칙

```text
Map DB stores what to draw.
Admin/Place DB owns what the place is.
```

지도 DB는 마커를 그리는 데 필요한 published projection만 보유합니다.
운영자와 사장님이 수정하는 원본 데이터는 admin/place 쪽에 둡니다.
