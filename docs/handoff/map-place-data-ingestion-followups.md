# Map / Place Data Ingestion Follow-ups

## Intended Flow

```text
storage-permitted public data / field research / owner input / user reports
        ↓
place_import_batches
        ↓
place_import_candidates
        ↓
normalization
        ↓
dedupe matching
        ↓
place_review_tasks
        ↓
canonical places
        ↓
publish
        ↓
place_outbox_events
        ↓
recommendation snapshot
```

## Seed Candidate Sources

| Source | Can Seed Candidates | Can Become Canonical | Review Required | Notes |
|---|---:|---:|---:|---|
| Storage-permitted public data | Yes | Yes, after review | Yes | License and storage rights must be recorded in `data_sources` |
| Field research | Yes | Yes | Yes | Higher trust, still operator-reviewed |
| Owner input | Yes | Yes | Yes for sensitive fields | Menu/inventory/price can be direct if manager policy allows |
| User reports | Yes | No direct canonical write | Yes | Use as review signal |
| Operator manual input | Yes | Yes | Operator action itself | Highest trust within map-service |
| Kakao API | Realtime reference only by default | No by default | Legal/policy approval required for persistence | Use `REALTIME_ONLY` or `RESTRICTED` source policy unless approved |

## Normalization Follow-ups

- Normalize names without destroying meaningful branch names such as `강남점` or `역삼점`.
- Normalize road address first, then fallback to parcel address.
- Preserve raw source payload in `raw_payload_json`.
- Store source category name and map it to internal `place_type`.
- Generate PostGIS point only when coordinate confidence is acceptable.

## Dedupe Follow-ups

Suggested matching signals:

- `source_external_id`.
- normalized name + normalized address.
- normalized name + distance radius.
- phone number.
- operator manual match.

Do not auto-merge by default. Even high-confidence matches should become review suggestions unless product explicitly approves automatic behavior.

## Review Before Publishing

Operators should verify:

- Place actually exists.
- Business category matches the app target.
- Location is accurate enough for map/recommendation use.
- Public data license permits storage and commercial use.
- Source conflict is resolved.
- Closed/archived/duplicate state is not accidentally overwritten.
- `publication_status` and `published_at` are intentionally set.

## Kakao Policy

Kakao Local/Map API must not be treated as canonical bulk ingestion by default.

Allowed by default:

- Realtime user search.
- Map display support.
- Operator verification support.
- External Kakao map link.
- Address/coordinate check as non-canonical support.

Forbidden by default:

- Bulk collection of Kakao Local API results.
- Long-term canonical storage of Kakao place names, addresses, coordinates, or phone numbers.
- Building a local POI search DB from Kakao.
- Reactivating closed/archived/merged places from Kakao results alone.

## Closed / Archived / Duplicate Rules

Never automatically reactivate places with these states:

- `CLOSED`
- `ARCHIVED`
- `DUPLICATE_MERGED`

If new source data conflicts with those states, create a `place_review_tasks` record and require operator review.

## Open Follow-ups

- Decide MVP region and initial source list.
- Confirm public data license/storage policy.
- Define stale inventory/price policy by category.
- Define owner claim evidence requirements.
- Decide review UI scope and queue priority logic.
- Define how ingestion workers create audit logs and outbox events after canonical changes.
