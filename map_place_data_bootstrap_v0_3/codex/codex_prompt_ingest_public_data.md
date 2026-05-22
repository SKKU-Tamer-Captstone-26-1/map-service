# Codex Task: Import Map/Place Public Data into Staging

You are Codex working in the map-service/place-service repository.

The user has provided a data bootstrap package. Your task is to wire it into the existing ingestion flow safely.

## Required Reading

Read:

```text
AGENTS.md
.agent/HARNESS.md
docs/map-place/ownership.md
docs/map-place/data-ingestion.md
docs/handoff/map-place-db-handoff.md
```

Also read from this package:

```text
README.md
docs/source_download_runbook.md
docs/data_ingestion_plan.md
data/source_registry.csv
data/category_mapping_seed.csv
data/data_quality_rules.csv
templates/*.csv
```

## Scope

Allowed:

```text
- Import CSV into staging tables only.
- Add dry-run import command if missing.
- Add mapping from package CSV headers to existing staging models.
- Add tests for normalization/category mapping/dedupe helpers.
- Add docs showing how to run import.
```

Not allowed:

```text
- Do not insert public data directly into places.
- Do not publish candidates automatically.
- Do not call or scrape Kakao.
- Do not store Kakao Local/Map API responses.
- Do not modify recommendation-service DB.
- Do not add cross-service FKs.
```

## First Data to Import

Start with:

```text
data/seoul_hangang_outdoor_spot_seed_candidates.csv
```

This should create staging candidates only.

Expected behavior:

```text
- review_status = needs_review
- geocode_required = YES
- no automatic publish
- no place_outbox_events until approved/published
```

## Final Response

Respond in Korean with:

```text
Summary
Changed files
Verification
Imported rows
Not imported / deferred
Risks / Follow-ups
```
