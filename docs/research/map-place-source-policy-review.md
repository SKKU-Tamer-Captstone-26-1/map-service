# Map/Place Source Policy Review

## 기본 원칙

이 문서는 법적 승인서가 아닙니다. 구현 전 출처별 최신 이용약관, 데이터 상세 페이지, 라이선스 표시, API 승인 조건을 다시 확인해야 합니다.

정책 기본값은 보수적으로 둡니다.

```text
public/open data -> place_import_candidates
canonical places -> explicit review/publish workflow only
map_view -> published marker read model only
Kakao -> realtime_only
```

## Storage Policy Values

| Value | Meaning | Default Target |
|---|---|---|
| `storable` | 공식 페이지에서 재사용/저장 가능한 공개 데이터로 볼 근거가 있음 | `place_import_candidates` |
| `restricted` | 저장 또는 재사용 제한이 있거나 product policy상 제외해야 함 | `excluded` 또는 `needs_review` |
| `realtime_only` | 실시간 조회/표시/검증 보조만 허용 | `realtime_lookup` |
| `unknown_needs_review` | 이용허락 또는 저장 정책 확인이 부족함 | `needs_review` |

## Source Findings

### 승인된 공공데이터포털 개발 API

사용자가 2026-05-22에 아래 개발계정 활용신청 승인을 확인했습니다. 만료예정일은 2028-05-22입니다.

| Source | Storage Policy | Canonical Use | Default Target |
|---|---|---:|---|
| 소상공인시장진흥공단_상가(상권)정보_API | `storable` | No | `place_import_candidates` |
| 행정안전부_식품_일반음식점 조회서비스 | `storable` | No | `place_import_candidates` |
| 행정안전부_식품_휴게음식점 조회서비스 | `storable` | No | `place_import_candidates` |
| 행정안전부_식품_단란주점영업 조회서비스 | `storable` | No | `excluded` |
| 행정안전부_식품_유흥주점영업 조회서비스 | `storable` | No | `excluded` |

API 활용 승인은 호출 권한과 quota 전제일 뿐입니다. canonical place 저장, 자동 승인, marker publish, product policy 승인을 의미하지 않습니다.

### 공공데이터포털 공통 정책

- URL: https://www.data.go.kr/ugs/selectPortalPolicyView.do
- 공공데이터는 데이터별 이용허락범위와 공공누리 유형을 확인해야 합니다.
- 제3자 권리가 포함될 수 있으므로 개별 데이터 상세의 라이선스가 우선입니다.
- `이용허락범위 제한 없음`이라도 출처, 데이터 기준일, 다운로드/API 호출 시각은 보존합니다.

### 서울 열린데이터광장 공통 정책

- URL: https://data.seoul.go.kr/etc/openInfo.do
- 데이터별 메타정보 상세 화면의 이용허락 조건을 확인해야 합니다.
- 공공누리 유형이 붙은 경우 유형별 출처표시, 상업 이용, 변경 가능 여부를 따라야 합니다.
- 공공누리가 부착되지 않은 자료는 사전 협의가 필요할 수 있습니다.

### 공공누리 1유형

- 공식 안내: https://www.kogl.or.kr/info/license.do
- 출처표시 조건이 붙습니다.
- 상업/비상업 이용과 2차 저작물 작성이 가능한 유형입니다.
- 출처표시 문구에는 발행연도, 기관명, URL, 작성자가 있으면 작성자를 포함합니다.

### Kakao Local/Map

- Local API: https://developers.kakao.com/docs/latest/ko/local/common
- Map API: https://developers.kakao.com/docs/latest/ko/kakaomap
- Terms: https://developers.kakao.com/terms/ko/site-terms
- Quota: https://developers.kakao.com/docs/latest/ko/getting-started/quota

Kakao는 현재 `realtime_only`로 둡니다.

허용:
- 사용자가 요청한 검색 결과 실시간 표시
- 운영자 검증 화면에서 외부 근거 링크 또는 실시간 lookup
- 지도 SDK 표시

금지:
- Kakao 검색 결과 bulk 저장
- canonical place bootstrap
- 자체 POI directory 생성을 위한 복제
- source registry에서 `canonical_use_allowed=true`로 표기

## Approval Gate

아래 조건을 만족하지 않으면 canonical publish를 구현하지 않습니다.

1. source registry에 출처별 storage policy가 기록됨
2. import batch와 candidate staging이 map_view 밖에 존재함
3. dedupe/review status가 명확함
4. canonical place owner가 결정됨
5. publish workflow가 `admin_ops` 또는 별도 owner에서 승인된 값만 `map_view`로 복사함
6. Kakao는 realtime-only 예외 승인 없이는 canonical source가 아님
