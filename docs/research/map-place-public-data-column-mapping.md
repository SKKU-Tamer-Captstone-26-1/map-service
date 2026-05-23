# Public Data Column Mapping

## 목적

공개 데이터의 컬럼을 ONTHEBLOCK 내부 후보 모델로 옮길 때의 보수적 매핑 초안입니다.

이 문서는 DB migration이 아닙니다. `map_view` schema에 import/source/candidate 컬럼을 추가하지 않습니다.

## 공통 Candidate Fields

| Candidate Field | Meaning | Notes |
|---|---|---|
| `source_name` | 출처명 | source registry 값 |
| `external_source_id` | 출처의 원본 식별자 | 없으면 source + normalized fields hash 필요 |
| `raw_payload_json` | 원본 payload | 공개 데이터만 저장, Kakao는 저장 금지 기본값 |
| `normalized_name` | 정규화한 상호/시설명 | canonical name 아님 |
| `normalized_address` | 정규화한 주소 | canonical address 아님 |
| `source_category_name` | 원본 업종/분류명 | 내부 category 아님 |
| `candidate_place_type` | 보수 매핑한 후보 category | `needs_review` 가능 |
| `latitude` | WGS84 위도 | 좌표계 변환 후 품질 확인 |
| `longitude` | WGS84 경도 | 좌표계 변환 후 품질 확인 |
| `location` | geography point | WGS84 검증 후 생성 |
| `review_status` | 후보 리뷰 상태 | 기본 `PENDING` |
| `metadata_json` | 기준일, fetched_at, attribution | 출처표시와 재현성 보존 |

## 소상공인시장진흥공단 상가정보

| Source Column | Candidate Field | Notes |
|---|---|---|
| `상가업소번호` | `external_source_id` | primary source id |
| `상호명` | `normalized_name` | 원문도 raw payload에 보존 |
| `상권업종대분류명` / `상권업종중분류명` / `상권업종소분류명` | `source_category_name` | 계층을 `>`로 결합 가능 |
| `표준산업분류명` | `metadata_json.standard_industry_name` | 보조 근거 |
| `도로명주소` | `normalized_address` | 지번 주소가 더 정확하면 함께 보존 |
| `경도` | `longitude` | WGS84 경도로 가정하되 범위 검증 |
| `위도` | `latitude` | WGS84 위도로 가정하되 범위 검증 |

## 행정안전부 일반음식점/휴게음식점

| Source Column | Candidate Field | Notes |
|---|---|---|
| `관리번호` | `external_source_id` | 없거나 불안정하면 source + address hash 보조 |
| `영업상태명` / `상세영업상태명` | `metadata_json.business_status` | 정상/영업만 후보 |
| `사업장명` | `normalized_name` | canonical name 아님 |
| `소재지전체주소` / `도로명전체주소` | `normalized_address` | 도로명 주소 우선 검토 |
| `업태구분명` | `source_category_name` | category 자동 확정 금지 |
| `좌표정보(X)` | `metadata_json.source_x` | EPSG:5174 안내, 변환 필요 |
| `좌표정보(Y)` | `metadata_json.source_y` | EPSG:5174 안내, 변환 필요 |
| transformed lon/lat | `longitude` / `latitude` | 변환 후 서울 bounding box 검증 |

## 전국도시공원정보표준데이터

현재 source policy는 `unknown_needs_review`입니다. 아래 컬럼 매핑은 라이선스/사용 조건을 재확인한 뒤에만 후보 staging 설계에 사용할 수 있습니다.

| Source Column | Candidate Field | Notes |
|---|---|---|
| `관리번호` | `external_source_id` | source id |
| `공원명` | `normalized_name` | 시설명 |
| `공원구분` | `source_category_name` | 현재는 `needs_review`; 재확인 전 `outdoor_spot` 자동 매핑 금지 |
| `소재지도로명주소` / `소재지지번주소` | `normalized_address` | 주소 보존 |
| `위도` | `latitude` | WGS84로 보이지만 라이선스와 함께 재확인 |
| `경도` | `longitude` | WGS84로 보이지만 라이선스와 함께 재확인 |
| 시설 항목 | `metadata_json.facilities` | 편익/운동/유희시설 등 |

## Category Mapping Draft

| Source Pattern | Target Category | Confidence | Notes |
|---|---|---:|---|
| 소상공인 업종 contains `편의점` | `convenience_store` | medium | 후보로만 사용 |
| 소상공인 음식 업종 in 백반/한정식, 구이/찜, 분식, 탕/찌개, 중식, 경양식, 치킨, 국수, 횟집 등 | `restaurant` | medium | Mapo I2 local dry-run 관측값 기반, 후보로만 사용 |
| 소상공인 음식 업종 in 카페, 떡/한과, 기타 간이 음식점 | `other` | low | 핵심 category가 아니므로 리뷰 필요 |
| 소상공인 업종 contains `유흥` | `excluded` | high | adult nightlife product policy |
| 소상공인 업종 contains `맥주`, `호프`, `생맥주`, `주점`, `바` | `needs_review` | low | source category만으로 `pub/bar` 확정 금지 |
| 행안부 일반음식점 업태 in `한식`, `중식`, `일식`, `경양식` | `restaurant` | medium | 영업상태 정상만 |
| 행안부 일반음식점 업태 contains `호프`, `주점`, `바`, `통닭` | `needs_review` | low | restaurant/alcohol venue가 섞일 수 있음 |
| 행안부 휴게음식점 | `other` 또는 `needs_review` | low | 서비스 정책에 맞춰 재검토 |
| 행안부 단란주점영업 | `excluded` | high | API access approved, product policy review required |
| 행안부 유흥주점영업 | `excluded` | high | API access approved, adult nightlife policy review required |
| 도시공원 공원구분 exists | `needs_review` | none | 라이선스/사용 조건 재확인 전 outdoor_spot 금지 |

## Quality Checks

- 위도는 `-90..90`, 경도는 `-180..180` 범위여야 합니다.
- 서울 MVP에서는 서울 bounding box 밖 좌표를 `needs_review`로 둡니다.
- 같은 source의 같은 `external_source_id`는 중복 후보로 넣지 않습니다.
- 서로 다른 source가 같은 장소를 가리킬 수 있으므로 dedupe confidence는 자동 publish에 사용하지 않습니다.
- source category만으로 `bar` 또는 `pub`을 확정하지 않습니다.
