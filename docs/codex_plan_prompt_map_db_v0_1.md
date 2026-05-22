# Codex Plan Prompt: Map / Place DB v0.1

Use plan mode first.

Read:

```text
AGENTS.md
.agent/HARNESS.md
.agent/DOMAIN_BOUNDARIES.md
docs/map-place/erd.md
docs/map-place/data-ingestion.md
```

Task:

Create additive PostgreSQL migrations for the map-service/place-service DB from ERD v0.2.

Do not implement APIs, UI, ingestion jobs, recommendation logic, or Kakao integration.

Mandatory boundaries:

```text
- Admin Page is not a data owner.
- map-service/place-service owns places, menu, inventory, price, claims, publication state, audit logs.
- recommendation-service consumes snapshots/events/internal APIs only.
- Kakao API is not a canonical bulk ingestion source.
- No cross-service DB foreign keys to auth-service or recommendation-service/catalog-service.
```

Before editing, produce a plan that includes:

```text
1. Files to inspect
2. Migration files to create
3. Tables per migration
4. Indexes and constraints
5. Verification steps
6. Deferred items
```

After plan approval, execute only the migration work.
