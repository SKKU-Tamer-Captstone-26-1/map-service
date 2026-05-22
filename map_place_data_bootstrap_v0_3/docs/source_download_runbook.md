# Source Download Runbook

## 1. 소상공인시장진흥공단_상가(상권)정보

Source URL:

```text
https://www.data.go.kr/data/15083033/fileData.do
```

확인된 메타데이터:

```text
파일데이터명: 소상공인시장진흥공단_상가(상권)정보_20260331
형식: CSV
인코딩: UTF-8
업데이트 주기: 분기
차기 등록 예정일: 2026-08-01
주요 항목: 상호명, 업종코드, 업종명, 지번주소, 도로명주소, 경도, 위도
이용허락범위: 제한 없음
```

권장 사용:

```text
1. 공공데이터포털에서 ZIP 다운로드
2. 압축 해제
3. 서울 CSV만 선택
4. bar/pub/liquor_shop/bottle_shop 후보 필터링
5. place_import_candidates에 적재
6. 운영자 review 후 places로 승격
```

주의:

```text
- 바로 places에 publish하지 말 것
- UTF-8 인코딩 유지
- 중복/폐업/업종 애매함 검수 필요
```

---

## 2. 서울시 일반음식점 인허가 정보

Source URL:

```text
https://data.seoul.go.kr/dataList/OA-16094/S/1/datasetView.do
```

확인된 메타데이터:

```text
설명: 식사와 함께 음주행위가 허용되는 업소정보
갱신주기: 매일
데이터 갱신일: 2026-05-22 확인
라이선스: 공공누리 1유형, 출처표시, 상업적 이용 및 변경 가능
좌표: 중부원점TM(EPSG:5174), 위경도 직접 제공 아님
```

권장 사용:

```text
- 장소 후보 발굴보다는 영업상태/폐업여부 검증용
- 좌표는 EPSG:5174 -> WGS84 변환 필요
- 단란주점/유흥주점 등 앱 타깃에 맞지 않는 카테고리는 제외 또는 운영자 검수
```

---

## 3. 서울특별시_한강공원_힌강이용안내

Source URL:

```text
https://www.data.go.kr/data/15134888/fileData.do
```

확인된 메타데이터:

```text
파일데이터명: 서울특별시_한강공원_힌강이용안내_20240831
전체 행: 159
형식: CSV
수정일: 2025-12-04
이용허락범위: 제한 없음
```

권장 사용:

```text
- outdoor_spot_profiles 설명/정책/시설 안내 보강
- 공식 한강공원 페이지와 대조
- 좌표는 별도 검증
```

---

## 4. Kakao Local/Map API

Kakao는 canonical bulk ingestion source가 아닙니다.

금지:

```text
- Kakao Local API 결과 대량 저장
- Kakao 장소명/주소/전화번호/좌표를 장기 canonical 저장
- Kakao 데이터 기반 POI 검색 DB 구축
```

허용 후보:

```text
- 실시간 검색
- 지도 표시
- Kakao 지도 랜딩 링크
- 운영자 검증 보조
```
