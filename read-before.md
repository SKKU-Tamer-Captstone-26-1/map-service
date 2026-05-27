# Read Before: map-service DB 사용 순서

작성일: 2026-05-27

이 문서는 팀원이 현재 map-service 지도 DB를 로컬에서 바로 쓰기 위한 순서입니다. 아래 순서대로 하면 작성자가 Docker Hub에 올린 seeded DB image에서 현재 preview marker snapshot을 받아 사용할 수 있습니다.

## 1. 먼저 알아야 할 것

현재 Docker Hub에 올라간 DB image는 다음입니다.

```text
image   hunbot/map-service-db-seed:2026-05-27
digest  sha256:8b76571fb7cee28a78d624bb113c82d1118f39d48d47a8908bfb4ab7c6fd1767
```

이 image에는 `map_view` schema와 marker snapshot이 들어 있습니다.

```text
map_view.marker_layers              7
map_view.markers               13,234
map_view.marker_publication_events  0
```

marker 구성은 다음과 같습니다.

```text
smba_public_data_preview  13,229개
local_dev_seed                 5개
total                     13,234개
```

중요한 점:

- 이 DB는 프론트엔드 지도 개발용 preview/read model입니다.
- canonical place DB가 아닙니다.
- production publish DB가 아닙니다.
- 기존 `postgis/postgis:16-3.5`만 실행하면 빈 DB입니다.
- 현재 데이터를 쓰려면 반드시 `docker-compose.seeded-db.yml`을 사용해야 합니다.

## 2. 처음 받는 팀원이 실행할 순서

1. repo를 받은 뒤 project root로 이동합니다.

```bash
cd map-service
```

2. Docker Desktop을 켜고 seeded DB를 실행합니다.

```bash
docker compose -f docker-compose.seeded-db.yml up -d db
```

3. DB가 떠 있는지 확인합니다.

```bash
docker ps --filter name=map-service-postgis-dev
```

정상이라면 `map-service-postgis-dev` 컨테이너가 `Up` 상태여야 합니다.

4. DB readiness를 확인합니다.

```bash
docker exec map-service-postgis-dev pg_isready -U map_user -d map_service
```

정상 결과:

```text
/var/run/postgresql:5432 - accepting connections
```

5. row 수를 확인합니다.

```bash
docker exec map-service-postgis-dev psql -U map_user -d map_service -v ON_ERROR_STOP=1 -c "
SELECT 'map_view.marker_layers' AS table_name, count(*) AS rows FROM map_view.marker_layers
UNION ALL
SELECT 'map_view.markers', count(*) FROM map_view.markers
UNION ALL
SELECT 'map_view.marker_publication_events', count(*) FROM map_view.marker_publication_events
ORDER BY table_name;
"
```

기대 결과:

```text
map_view.marker_layers              7
map_view.markers               13,234
map_view.marker_publication_events  0
```

6. source별 marker 수를 확인합니다.

```bash
docker exec map-service-postgis-dev psql -U map_user -d map_service -v ON_ERROR_STOP=1 -c "
SELECT
  COALESCE(filter_json->>'source', '(missing)') AS source,
  count(*) AS rows
FROM map_view.markers
GROUP BY 1
ORDER BY 1;
"
```

기대 결과:

```text
local_dev_seed                5
smba_public_data_preview  13229
```

7. Python dependency를 설치합니다.

```bash
python3 -m pip install -r requirements.txt
```

8. read-only map API를 실행합니다.

```bash
python3 -m scripts.api.map_read_api
```

기본 API 주소:

```text
http://127.0.0.1:8088
```

9. API를 확인합니다.

```bash
curl http://127.0.0.1:8088/healthz
curl http://127.0.0.1:8088/v1/map/layers
```

marker 조회 예시:

```text
GET /v1/map/markers?bbox=126.70,37.40,127.20,37.75&layers=bar,pub,liquor_shop&limit=500&offset=0
```

## 3. 기존 DB가 이미 있으면 먼저 확인할 것

`/docker-entrypoint-initdb.d` 초기화는 빈 Postgres volume을 처음 만들 때만 실행됩니다. 이미 같은 이름의 DB container나 volume이 있으면 seeded image를 실행해도 snapshot이 안 들어갈 수 있습니다.

1. 기존 컨테이너를 확인합니다.

```bash
docker ps -a --filter name=map-service-postgis-dev
```

2. 기존 로컬 DB가 필요 없을 때만 삭제합니다.

기존에 `docker-compose.seeded-db.yml`로 만든 DB를 지우는 경우:

```bash
docker compose -f docker-compose.seeded-db.yml down -v
```

기존에 빈 DB용 `docker-compose.db.yml`로 만든 DB를 지우는 경우:

```bash
docker compose -f docker-compose.db.yml down -v
```

3. 다시 seeded DB를 실행합니다.

```bash
docker compose -f docker-compose.seeded-db.yml up -d db
```

삭제 후에는 반드시 2번 섹션의 row 수 확인까지 다시 진행합니다.

## 4. 연결 정보

팀원이 로컬 앱이나 API에서 DB에 붙을 때 쓰는 값은 다음입니다.

```text
host      127.0.0.1
port      55433
database  map_service
user      map_user
password  map_pass
url       postgresql://map_user:map_pass@127.0.0.1:55433/map_service
```

## 5. 데이터 경계

현재 `map_view.markers`에 있는 데이터는 지도 화면 개발용 preview marker입니다.

할 수 있는 일:

- 지도 marker 렌더링 개발
- bbox 조회 테스트
- layer filter 테스트
- pagination 테스트
- 서울 전체 bar/pub/liquor_shop marker UX 확인

하면 안 되는 일:

- canonical place로 간주
- production DB로 간주
- 운영자가 승인한 장소 원본처럼 수정
- 공공데이터나 Kakao 데이터를 검수 없이 canonical로 저장

특히 SMBA preview row는 다음 flag를 가지고 있습니다.

```text
filter_json.source=smba_public_data_preview
filter_json.preview_only=true
filter_json.canonical=false
filter_json.review_required=true
```

## 6. Docker Hub pull이 안 될 때

`docker compose -f docker-compose.seeded-db.yml up -d db`에서 pull permission 문제가 나면 Docker Hub 접근 권한 문제입니다.

확인할 것:

1. Docker Desktop에 로그인했는지 확인합니다.
2. `hunbot/map-service-db-seed` Docker Hub repo 접근 권한이 있는지 확인합니다.
3. repo가 private이면 작성자에게 Docker Hub 권한을 요청합니다.

## 7. seeded image를 쓰지 않는 fallback

Docker Hub image를 못 쓰는 경우에만 직접 seed를 다시 생성합니다. 이 방식은 live public API를 다시 호출하므로 row 수가 현재 snapshot과 달라질 수 있습니다.

1. 빈 PostGIS DB 실행

```bash
docker compose -f docker-compose.db.yml up -d db
```

2. dependency 설치

```bash
python3 -m pip install -r requirements.txt
```

3. schema 적용

```bash
python3 scripts/db/apply_migrations.py
```

4. local dev marker 5개 생성

```bash
python3 scripts/db/seed_dev_map_markers.py --apply
```

5. `.env`에 data.go.kr service key 설정

```text
DATA_GO_KR_SERVICE_KEY=...
```

6. SMBA 서울 preview marker 생성

```bash
python3 scripts/db/seed_seoul_preview_markers_from_smba.py \
  --all-pages \
  --replace-preview \
  --apply \
  --ack-public-data-preview
```

이 fallback은 seeded Docker Hub image를 쓰는 기본 경로가 막혔을 때만 사용합니다.
