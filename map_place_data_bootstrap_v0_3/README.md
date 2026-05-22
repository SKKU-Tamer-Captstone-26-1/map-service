# Map / Place Data Bootstrap Package v0.3

생성일: 2026-05-22

이 ZIP은 map-service/place-service DB에 넣을 데이터를 준비하기 위한 **초기 데이터 부트스트랩 패키지**입니다.

## 포함된 것

```text
data/source_registry.csv
data/seoul_hangang_outdoor_spot_seed_candidates.csv
data/category_mapping_seed.csv
data/data_quality_rules.csv
data/mvp_area_seed_plan.csv

templates/*.csv
docs/*.md
sql/*.sql
codex/*.md
```

## 중요한 제한

이 패키지는 대용량 원천 CSV 전체를 포함하지 않습니다.

이유:

1. `소상공인시장진흥공단_상가(상권)정보`는 다운로드 가능한 공공데이터지만 대용량 ZIP이며, 실제 repo/DB 환경에서 지역별 파일을 선택해 ETL로 처리해야 합니다.
2. `서울시 일반음식점 인허가 정보`는 Open API/Sheet 성격이며 좌표가 EPSG:5174라 변환 로직이 필요합니다.
3. Kakao Local/Map API 응답은 canonical bulk DB 구축 원천으로 저장하면 안 됩니다.

## 바로 사용할 수 있는 데이터

`data/seoul_hangang_outdoor_spot_seed_candidates.csv`에는 공식 한강공원 페이지 기준 11개 한강공원 후보가 들어 있습니다.

단, 좌표는 비워두었습니다. 운영자 검수 및 geocoding 후 publish하세요.

## 권장 흐름

```text
공공데이터/운영자 CSV/점주 CSV
    -> place_import_batches
    -> place_import_candidates
    -> normalize
    -> dedupe
    -> review
    -> places
    -> place_outbox_events
    -> recommendation-service snapshot
```

## 다음 액션

1. `docs/source_download_runbook.md`를 따라 원천 CSV를 다운로드합니다.
2. `templates/semas_store_raw_filter_template.csv` 구조에 맞춰 서울 지역 파일을 필터링합니다.
3. `data/category_mapping_seed.csv` 기준으로 후보 타입을 부여합니다.
4. 바로 `places`에 넣지 말고 staging에 넣습니다.
5. 운영자 review 후 publish합니다.
