# Map / Place Local DB Setup

이 문서는 map-service/place-service의 local/dev PostgreSQL + PostGIS DB를 반복 가능하게 띄우고 검증하는 절차입니다.

## TL;DR

```bash
cp .env.example .env
docker compose -f docker-compose.db.yml up -d db
python3 scripts/db/apply_migrations.py
python3 scripts/db/verify_schema.py
```

선택적으로 staging seed까지 넣을 수 있습니다.

```bash
python3 scripts/db/apply_migrations.py \
  --load-source-registry \
  --load-outdoor-candidates
python3 scripts/db/verify_schema.py
```

이 선택 seed는 `data_sources`, `place_import_batches`, `place_import_candidates`, `place_review_tasks`만 사용해야 합니다. canonical `places`는 기본적으로 생성하지 않습니다.

## Added Files

| File | Purpose |
|---|---|
| `docker-compose.db.yml` | Local/dev PostGIS DB service |
| `.env.example` | Local DB env template |
| `scripts/db/apply_migrations.py` | Applies SQL migrations in filename order |
| `scripts/db/verify_schema.py` | Verifies extensions, tables, indexes, constraints, FKs, counts |
| `docs/handoff/map-place-local-db-setup.md` | This setup guide |

## Docker Compose

The compose service uses:

```text
image: postgis/postgis:16-3.5
platform: linux/amd64 by default
host port: 55433
database: map_service
user: map_user
password: map_pass
```

`platform: linux/amd64` is set because this image was verified successfully under Docker emulation on the current machine. If your machine supports a native PostGIS image, you may override `DOCKER_DEFAULT_PLATFORM` in `.env`.

## Environment

Copy the template:

```bash
cp .env.example .env
```

Default URLs:

```text
DATABASE_URL=postgresql://map_user:map_pass@127.0.0.1:55433/map_service
MAP_SERVICE_DATABASE_URL=postgresql://map_user:map_pass@127.0.0.1:55433/map_service
```

`.env` is ignored by git.

## Start / Stop DB

Start:

```bash
docker compose -f docker-compose.db.yml up -d db
```

Check:

```bash
docker compose -f docker-compose.db.yml ps
```

Stop without deleting data:

```bash
docker compose -f docker-compose.db.yml stop db
```

Remove container but keep volume:

```bash
docker compose -f docker-compose.db.yml down
```

Destructive reset for local/dev only:

```bash
docker compose -f docker-compose.db.yml down -v
```

Do not run destructive reset against any shared database.

## Apply Migrations

Apply all SQL files in `migrations/`:

```bash
python3 scripts/db/apply_migrations.py
```

Dry-run list:

```bash
python3 scripts/db/apply_migrations.py --dry-run
```

Use an explicit URL:

```bash
python3 scripts/db/apply_migrations.py \
  --database-url postgresql://map_user:map_pass@127.0.0.1:55433/map_service
```

Important:

- The migration set is intended for a clean DB.
- There is no migration metadata table yet.
- Re-running against an already-migrated DB can fail because tables already exist.

## Verify Schema

```bash
python3 scripts/db/verify_schema.py
```

The verifier checks:

- `postgis` and `pgcrypto`.
- 17 MVP tables.
- deferred optional tables are absent.
- key GiST and partial indexes.
- key unique/check constraints.
- `places.location` and `place_import_candidates.location` are geography Point 4326.
- no FK targets that look like auth/recommendation/catalog/survey/chatbot/user tables.
- staging/canonical table counts.

## Optional Staging Seed

Load source registry only:

```bash
python3 scripts/db/apply_migrations.py --load-source-registry
```

Load source registry and outdoor candidates:

```bash
python3 scripts/db/apply_migrations.py \
  --load-source-registry \
  --load-outdoor-candidates
```

Expected result after outdoor staging seed:

```text
data_sources=9
place_import_batches=1
place_import_candidates=11
place_review_tasks=11
places=0
place_source_refs=0
place_outbox_events=0
```

If `places` is not zero after this step, stop and investigate.

## Safety Boundaries

- No Kakao bulk ingestion.
- No public data direct publish to `places`.
- No production-like seed data.
- No cross-service DB foreign keys.
- No recommendation-service direct DB access.
- No Admin Page direct DB writes.

## Next Step After Local DB

Implement the reviewed publish workflow separately:

```text
approved place_import_candidate
  -> places
  -> place_source_refs
  -> place_audit_logs
  -> place_outbox_events
```

That workflow must remain explicit, reviewed, audited, and idempotent.
