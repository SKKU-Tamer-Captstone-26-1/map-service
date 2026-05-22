-- Seed source registry for map-service/place-service.
-- Review table/column names before executing against your actual migration.
-- Uses gen_random_uuid(); enable pgcrypto if needed.

INSERT INTO data_sources (id, source_type, source_name, source_policy, trust_level, active, metadata_json, created_at, updated_at)
VALUES
  (gen_random_uuid(), 'PUBLIC_DATA', '소상공인시장진흥공단_상가(상권)정보_20260331', 'storable', 70, true,
   '{"source_code":"SEMAS_STORE_20260331","url":"https://www.data.go.kr/data/15083033/fileData.do","review_required":true}'::jsonb, now(), now()),
  (gen_random_uuid(), 'PUBLIC_DATA', '서울시 일반음식점 인허가 정보', 'storable_with_attribution', 75, true,
   '{"source_code":"SEOUL_GENERAL_RESTAURANT_LICENSE","url":"https://data.seoul.go.kr/dataList/OA-16094/S/1/datasetView.do","review_required":true,"coordinate_system":"EPSG:5174"}'::jsonb, now(), now()),
  (gen_random_uuid(), 'PUBLIC_DATA', '서울특별시_한강공원_힌강이용안내_20240831', 'storable', 75, true,
   '{"source_code":"SEOUL_HANGANG_GUIDE_20240831","url":"https://www.data.go.kr/data/15134888/fileData.do","review_required":true}'::jsonb, now(), now()),
  (gen_random_uuid(), 'OPERATOR', '운영자 현장조사/수기 입력', 'storable', 100, true,
   '{"source_code":"OPERATOR_FIELD_RESEARCH","review_required":false}'::jsonb, now(), now()),
  (gen_random_uuid(), 'OWNER', '점주/매장 관리자 입력', 'storable', 85, true,
   '{"source_code":"OWNER_SUBMITTED","review_required":"field_dependent"}'::jsonb, now(), now()),
  (gen_random_uuid(), 'USER_REPORT', '사용자 제보', 'storable', 40, true,
   '{"source_code":"USER_REPORT","review_required":true}'::jsonb, now(), now()),
  (gen_random_uuid(), 'KAKAO', 'Kakao Local/Map API', 'realtime_only', 0, true,
   '{"source_code":"KAKAO_LOCAL_MAP_API","canonical_use_allowed":false,"bulk_ingestion_allowed":false}'::jsonb, now(), now());
