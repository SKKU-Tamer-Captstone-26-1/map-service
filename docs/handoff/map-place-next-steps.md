# Map / Place Next Steps

## Prioritized Task List

| Priority | Task | Owner | Expected Output | Acceptance Criteria |
|---|---|---|---|---|
| P0 | Run clean DB migration dry-run | Backend/DB | `psql -v ON_ERROR_STOP=1` output | All six migrations apply on PostgreSQL with PostGIS |
| P0 | Inspect DB extensions and indexes | Backend/DB | DB inspection notes | `postgis`, `pgcrypto`, GiST indexes, partial indexes exist |
| P0 | Confirm FK boundaries | Backend/DB | Constraint query output | No FK to auth/recommendation/catalog/user tables |
| P0 | Confirm lifecycle/check constraints | Backend/DB | Constraint query output | Status enums and range/confidence checks exist |
| P0 | Decide rollback convention | Backend lead | Migration policy note | Down migration or forward-only policy documented |
| P1 | Add map-service persistence/model layer | Backend | Repository/model code | Models match SQL names/types and do not add cross-service FKs |
| P1 | Add permission policy module | Backend | Role/action policy | Sensitive changes require operator approval |
| P1 | Add audit logging service | Backend | Shared write audit helper | Admin/operator/owner/system writes create audit records |
| P1 | Add outbox event creation | Backend | Transactional outbox writer | Place/menu/inventory/price changes create idempotent outbox events |
| P1 | Add public map read APIs | Backend | Search/nearby/detail APIs | Only `ACTIVE` + `PUBLISHED` + `published_at` records are public |
| P2 | Add owner claim workflow | Backend/Admin | Submit/review/approve APIs | Approval creates/updates `place_managers` |
| P2 | Add owner menu/inventory/price APIs | Backend | Owner/manager write APIs | Revision, freshness, confidence, and audit updated correctly |
| P2 | Add recommendation sync worker | Backend/Recommendation | Outbox or snapshot consumer | Recommendation-service does not query map DB directly |
| P2 | Add import staging workflow | Backend/Data | Batch/candidate/dedupe/review pipeline | Raw import never publishes directly |
| P3 | Add optional display tables | Backend/Product | Follow-up migration | Only after tags/media/hours/reporting MVP scope is confirmed |
| P3 | Add route estimate cache | Backend/Product | Follow-up migration/design | Route cache remains phase 2+ |
| P3 | Add data quality dashboard | Admin/Data | Review/staleness dashboard | Operators can see review backlog and stale inventory/price |

## Do Not Implement Yet

- Kakao bulk ingestion.
- Recommendation scoring, ranking, or explanation logic.
- RAG document ingestion or beverage knowledge storage in map-service.
- Admin UI direct DB writes.
- Production-like seed data.
- Kafka/Redis/Airflow/ML serving infrastructure unless separately scoped.
- Route/transit optimization before phase 2 product decision.

## First Verification SQL Ideas

Use these only on a disposable local/dev DB after PostgreSQL + PostGIS is available.

```sql
SELECT extname FROM pg_extension WHERE extname IN ('postgis', 'pgcrypto');

SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

SELECT conname, contype
FROM pg_constraint
WHERE connamespace = 'public'::regnamespace
ORDER BY conname;

SELECT indexname
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY indexname;
```
