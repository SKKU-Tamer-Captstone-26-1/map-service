# Data Ingestion Plan

## 목표

지도 DB는 직접 `places`에 원천 데이터를 넣는 구조가 아니라, staging과 review를 거쳐 canonical place를 생성해야 합니다.

```text
storage-permitted public data
operator field research
owner submitted data
user reports
        ↓
place_import_batches
        ↓
place_import_candidates
        ↓
normalize
        ↓
dedupe
        ↓
place_review_tasks
        ↓
operator approval
        ↓
places
        ↓
place_outbox_events
        ↓
recommendation-service snapshot
```

## 원칙

- source_policy가 `REALTIME_ONLY` 또는 `RESTRICTED`면 canonical 저장 금지
- public data라도 바로 publish 금지
- 좌표 누락/업종 애매함/폐업 상태/중복 가능성은 review task 생성
- 운영자 override가 source보다 우선
- closed/archived/duplicate_merged 장소는 ingestion으로 자동 재활성화 금지

## Staging candidate 최소 필드

```text
source_code
external_source_id
raw_payload_json
candidate_place_type
canonical_name
normalized_name
address
road_address
lat
lng
review_status
confidence
operator_comment
```

## Publish 전 필수 검수

```text
- 장소명
- 장소 타입
- 주소
- 좌표
- 폐업/영업상태
- 중복 여부
- 앱 타깃 적합성
- 추천 노출 가능 여부
```
