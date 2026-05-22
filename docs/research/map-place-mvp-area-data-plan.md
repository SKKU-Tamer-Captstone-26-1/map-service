# Map/Place MVP Area Data Plan

## 목표

서울 MVP 영역에서 지도 후보 데이터를 만들기 위한 보수적 실행 계획입니다.

이 계획은 bootstrap research package입니다. DB write, canonical place 생성, marker publish를 포함하지 않습니다.

## 권장 순서

1. MVP 대상 행정구 또는 bounding box를 확정합니다.
2. 소상공인시장진흥공단 상가정보 API에서 후보 POI를 조회합니다.
3. 행정안전부 일반음식점/휴게음식점 데이터로 영업상태와 주소 근거를 보강합니다.
4. 도시공원 데이터는 라이선스 재확인 후 `outdoor_spot` 후보로 별도 처리합니다.
5. 단란주점/유흥주점 계열은 기본 제외합니다.
6. Kakao Local API는 저장하지 않고 운영자 실시간 검증 보조로만 사용합니다.

## 서울 MVP Source Plan

| Step | Source | Target | Output |
|---:|---|---|---|
| 1 | 소상공인 상가정보 API | `place_import_candidates` | 상호/업종/주소/경위도 후보 |
| 2 | 행안부 일반음식점 | `place_import_candidates` | 인허가/영업상태 보조 후보 |
| 3 | 행안부 휴게음식점 | `place_import_candidates` | 카페/간편식 보조 후보 |
| 4 | 전국도시공원정보표준데이터 | `needs_review` then candidates | 야외 장소 후보 |
| 5 | Kakao Local API | `realtime_lookup` | 운영자 검증 보조 |

## Download/API Plan

| File | Purpose |
|---|---|
| `data/bootstrap/source_registry_research.csv` | 출처별 policy와 target 정리 |
| `data/bootstrap/category_mapping_research.csv` | source category 보수 매핑 |
| `data/bootstrap/public_data_download_plan.csv` | MVP 수집 계획과 승인 조건 |

## Candidate Acceptance Criteria

후보 staging에 넣기 전 최소 조건:

- official URL과 license/usage term 기록
- source name과 fetched_at 기록
- 원본 payload 보존 가능 여부 확인
- Kakao가 아닌 공개 데이터일 것
- 좌표계와 좌표 범위 확인
- category는 보수 매핑
- `review_status=PENDING` 기본값

## Not In Scope

- `map_view` migration 변경
- canonical `places` 생성
- 자동 dedupe 승인
- 자동 publish
- Kakao bulk ingestion
- Admin Page direct DB write

## 다음 구현 단위 제안

1. research CSV를 읽어 source policy를 검증하는 dry-run linter
2. 공개 데이터 sample 파일을 로컬에서 파싱하는 dry-run normalizer
3. 좌표계 변환과 bounding box 검증 유틸
4. 후보 staging schema는 `map_view` 밖에서 별도 승인 후 설계
