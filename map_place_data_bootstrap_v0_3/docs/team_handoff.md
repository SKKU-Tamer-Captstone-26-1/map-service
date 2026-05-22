# Team Handoff: Map / Place Initial Data

## TL;DR

이 패키지는 DB에 바로 넣을 완성 데이터셋이 아니라, **안전하게 지도 DB seed를 만들기 위한 데이터 소스/템플릿/검수 기준 패키지**입니다.

바로 사용할 수 있는 실데이터는 `data/seoul_hangang_outdoor_spot_seed_candidates.csv`입니다. 이 파일은 한강공원 11개 후보를 담고 있지만 좌표는 비워두었고 운영자 검수가 필요합니다.

상가/술집/주류점 후보는 `소상공인시장진흥공단_상가(상권)정보`를 공식 포털에서 다운로드한 뒤, `data/category_mapping_seed.csv`로 필터링하여 staging에 넣어야 합니다.

## 절대 하지 말 것

```text
- Kakao Local/Map API 응답을 bulk 저장하지 말 것
- public data를 바로 published places로 넣지 말 것
- recommendation-service가 map DB를 직접 읽게 하지 말 것
- Admin Page가 DB에 직접 UPDATE하게 하지 말 것
```

## 팀원 작업 순서

```text
1. source_registry.csv 확인
2. SEMAS 상가정보 ZIP 다운로드
3. 서울 CSV 추출
4. category_mapping_seed.csv 기준 후보 필터링
5. place_import_candidates에 dry-run import
6. dedupe 결과 확인
7. 운영자 review
8. approved 후보만 places로 publish
9. place_outbox_events 생성 확인
```

## 담당자가 반드시 확인할 것

```text
- migration의 staging table 이름과 CSV header가 맞는가
- PostGIS location 컬럼이 있는가
- 좌표가 WGS84인지 EPSG:5174인지 구분하는가
- inventory/price TTL 정책이 적용되는가
- audit log/outbox가 canonical write와 함께 생성되는가
```
