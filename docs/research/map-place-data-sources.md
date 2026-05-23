# Map/Place Public Data Sources

## 목적

이 문서는 map/place bootstrap 후보로 검토한 공식 공개 데이터 출처를 정리합니다.

현재 repo의 DB 경계는 명확합니다.

```text
map_view = published marker read model
admin_ops / ingest workflow = source registry, import batches, candidates, review, canonical places
```

따라서 아래 출처는 `map_view`에 직접 적재하지 않습니다. 공개 데이터는 먼저 후보 staging인 `place_import_candidates` 성격으로 들어가야 하며, canonical place 또는 marker publish는 별도 review/publish workflow 이후에만 가능합니다.

## Approved Development API Access

사용자가 2026-05-22에 아래 공공데이터포털 개발계정 활용신청 승인을 확인했습니다. 만료예정일은 2028-05-22입니다.

| Source | Approval Scope | Default Target |
|---|---|---|
| 소상공인시장진흥공단_상가(상권)정보_API | 개발계정 승인 | `place_import_candidates` |
| 행정안전부_식품_일반음식점 조회서비스 | 개발계정 승인 | `place_import_candidates` |
| 행정안전부_식품_휴게음식점 조회서비스 | 개발계정 승인 | `place_import_candidates` |
| 행정안전부_식품_단란주점영업 조회서비스 | 개발계정 승인 | `excluded` |
| 행정안전부_식품_유흥주점영업 조회서비스 | 개발계정 승인 | `excluded` |

승인은 API 호출 권한입니다. canonical 저장, 자동 승인, marker publish 승인으로 해석하지 않습니다.

## 1순위 후보 출처

### 소상공인시장진흥공단 상가(상권)정보 API

- URL: https://www.data.go.kr/data/15012005/openapi.do
- 제공기관: 소상공인시장진흥공단
- 제공형태: REST API, JSON/XML
- 주요 항목: 상가업소번호, 상호명, 주소, 상권업종명, 표준산업분류명, 경도, 위도
- 라이선스/이용허락: 이용허락범위 제한 없음
- 비용: 무료
- 업데이트: 실시간
- API 승인: 개발계정 승인 확인, 2026-05-22 ~ 2028-05-22
- 기본 target: `place_import_candidates`
- 판단: 서울 MVP 후보 POI의 primary evidence로 적합합니다.

주의사항:
- 업종분류는 canonical category가 아닙니다.
- 상호/주소/좌표는 후보 근거로 저장하고, 운영자 또는 publish workflow 검증 전에는 canonical place로 승격하지 않습니다.
- 출처 URL, fetched_at, 데이터 기준일 또는 API 응답 기준 정보를 보존합니다.

### 행정안전부 식품 일반음식점 조회서비스

- URL: https://www.data.go.kr/data/15154916/openapi.do
- 제공기관: 행정안전부
- 제공형태: REST API, JSON/XML
- 주요 항목: 인허가일자, 영업상태, 사업장명, 소재지주소, 좌표
- 라이선스/이용허락: 이용허락범위 제한 없음
- 비용: 무료
- 업데이트: 일간
- 좌표계: 보정계수 없는 Bessel 중부원점 TM, EPSG:5174로 안내됨
- API 승인: 개발계정 승인 확인, 2026-05-22 ~ 2028-05-22
- 기본 target: `place_import_candidates`
- 판단: `restaurant` 후보의 보조 근거로 적합합니다. 술집/호프/바 계열은 `needs_review`로만 둡니다.

주의사항:
- 영업상태 정상/영업 데이터만 후보로 사용합니다.
- EPSG:5174 좌표는 WGS84 경위도 변환 후 품질 검증이 필요합니다.
- 일반음식점은 술집 여부를 보장하지 않으므로 `pub/bar` 자동 승격은 금지합니다.

### 행정안전부 식품 휴게음식점 조회서비스

- URL: https://www.data.go.kr/data/15154921/openapi.do
- 제공기관: 행정안전부
- 제공형태: REST API, JSON/XML
- 주요 항목: 인허가일자, 영업상태, 사업장명, 소재지주소, 좌표
- 라이선스/이용허락: 이용허락범위 제한 없음
- 비용: 무료
- 업데이트: 일간
- 좌표계: 보정계수 없는 Bessel 중부원점 TM, EPSG:5174로 안내됨
- API 승인: 개발계정 승인 확인, 2026-05-22 ~ 2028-05-22
- 기본 target: `place_import_candidates`
- 판단: 카페/패스트푸드/간편식 계열 후보의 보조 근거로만 사용합니다.

주의사항:
- 서비스 핵심 카테고리와 다를 수 있어 기본 매핑은 `restaurant`, `other`, 또는 `needs_review`로 보수 처리합니다.

## 보류 또는 제한 출처

### 전국도시공원정보표준데이터

- URL: https://www.data.go.kr/data/15012890/standard.do
- 주요 항목: 관리번호, 공원명, 공원구분, 주소, 위도, 경도, 시설 항목
- 기본 target: `needs_review`
- 판단: `outdoor_spot` 후보로 유용할 수 있지만, 라이선스/사용 조건 재확인 전에는 후보 staging에도 넣지 않습니다.
- 현재 정책 상태: `unknown_needs_review`

주의사항:
- 조사 시점의 텍스트 화면에서 이용허락 필드를 명확히 확인하지 못했습니다.
- 구현 전 개별 다운로드/API 화면의 이용허락 필드를 재확인해야 합니다.

### 행정안전부 단란주점영업 조회서비스

- 추적 URL: https://www.data.go.kr/data/15045017/fileData.do
- API 승인: 개발계정 승인 확인, 2026-05-22 ~ 2028-05-22
- 라이선스/이용허락: 이용허락범위 제한 없음으로 확인되는 데이터가 있음
- 기본 target: `excluded`
- 저장 정책: `restricted`
- 판단: 데이터 이용허락과 별개로 단란주점/adult nightlife product policy에 의해 기본 제외합니다.

주의사항:
- canonical 후보, 자동 승인, marker publish 근거로 쓰지 않습니다.
- 필요한 경우 별도 정책/법무 검토 후 `needs_review`로만 다룹니다.
- 공공데이터포털 승인 화면의 정확한 OpenAPI 상세 URL은 구현 전 캡처합니다.

### 행정안전부 유흥주점영업 조회서비스

- 추적 URL: https://www.data.go.kr/data/15045018/fileData.do
- API 승인: 개발계정 승인 확인, 2026-05-22 ~ 2028-05-22
- 라이선스/이용허락: 이용허락범위 제한 없음으로 확인되는 데이터가 있음
- 기본 target: `excluded`
- 저장 정책: `restricted`
- 판단: 데이터 이용허락과 별개로 유흥주점/adult nightlife product policy에 의해 기본 제외합니다.

주의사항:
- canonical 후보, 자동 승인, marker publish 근거로 쓰지 않습니다.
- 필요한 경우 별도 정책/법무 검토 후 `needs_review`로만 다룹니다.
- 공공데이터포털 승인 화면의 정확한 OpenAPI 상세 URL은 구현 전 캡처합니다.

### Kakao Local/Map API

- Local API: https://developers.kakao.com/docs/latest/ko/local/common
- Map API: https://developers.kakao.com/docs/latest/ko/kakaomap
- Terms: https://developers.kakao.com/terms/ko/site-terms
- Quota: https://developers.kakao.com/docs/latest/ko/getting-started/quota
- 기본 target: `realtime_lookup`
- 저장 정책: `realtime_only`

허용 용도:
- 실시간 검색/조회
- 지도 표시 지원
- 운영자 검증 보조
- 외부 Kakao map link 지원

금지 기본값:
- bulk ingestion
- canonical place source로 사용
- Kakao API 응답을 storable bootstrap source로 저장
- 검색엔진/디렉터리 성격의 DB 구축에 사용

별도 legal/partnership approval이 문서화되기 전까지 위 금지 기본값을 유지합니다.
