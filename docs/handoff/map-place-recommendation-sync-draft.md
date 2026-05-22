# Map / Place Recommendation Sync Draft

Recommendation-service must not directly read or write map-service tables. It consumes map-service data through outbox events, internal APIs, snapshots, or sync jobs.

## Outbox Contract

Source table: `place_outbox_events`.

| Field | Meaning |
|---|---|
| `event_type` | Domain event name such as `place.updated` |
| `aggregate_type` | `place`, `menu_item`, `inventory_item`, `price_offer`, `business_claim` |
| `aggregate_id` | UUID of the aggregate |
| `aggregate_revision` | Revision at event creation |
| `idempotency_key` | Stable key for dedupe and retry |
| `payload_json` | Snapshot or delta payload |
| `status` | `PENDING`, `PUBLISHED`, `FAILED`, `SKIPPED` |
| `created_at` | Event creation time |
| `published_at` | Successful publish/ack time |

## Event Drafts

| event_type | aggregate_type | aggregate_id | aggregate_revision | idempotency_key | Payload Fields | Consumer Behavior |
|---|---|---|---|---|---|---|
| `place.published` | `place` | `place_id` | `place.revision` | `place:{id}:{revision}:published` | `place_id`, `revision`, `place_type`, `name`, `location`, `status`, `publication_status`, `published_at`, `recommendation_eligible`, `price_level` | Create/update `venue_snapshots`; eligible for recommendation if published and active |
| `place.updated` | `place` | `place_id` | `place.revision` | `place:{id}:{revision}:updated` | core place fields, changed fields, source summary | Update snapshot if revision is newer |
| `place.hidden` | `place` | `place_id` | `place.revision` | `place:{id}:{revision}:hidden` | `place_id`, `revision`, `status`, `publication_status` | Mark snapshot hidden/unavailable |
| `place.closed` | `place` | `place_id` | `place.revision` | `place:{id}:{revision}:closed` | `place_id`, `revision`, `status`, `closed_at` | Exclude from recommendation; preserve history |
| `place.merged` | `place` | source `place_id` | `place.revision` | `place:{id}:{revision}:merged` | `place_id`, `merged_into_place_id`, `revision` | Redirect/merge read model; do not resurrect source |
| `menu.created` | `menu_item` | `menu_item_id` | `menu.revision` | `menu:{id}:{revision}:created` | `place_id`, `menu_item_id`, `menu_name`, `menu_type`, `is_signature`, `beverage_catalog_ref_id` | Add menu snapshot for place |
| `menu.updated` | `menu_item` | `menu_item_id` | `menu.revision` | `menu:{id}:{revision}:updated` | menu fields, status, revision | Update menu snapshot if newer |
| `menu.discontinued` | `menu_item` | `menu_item_id` | `menu.revision` | `menu:{id}:{revision}:discontinued` | `place_id`, `menu_item_id`, `status`, `revision` | Mark item unavailable for recommendation |
| `inventory.updated` | `inventory_item` | `inventory_item_id` | `inventory.revision` | `inventory:{id}:{revision}:updated` | `place_id`, `menu_item_id`, `beverage_catalog_ref_id`, `availability_status`, `stock_confidence`, `last_seen_at`, `expires_at`, `revision` | Update `venue_inventory_snapshots`; apply stale/expiry policy |
| `price.updated` | `price_offer` | `price_offer_id` | `price.revision` | `price:{id}:{revision}:updated` | `place_id`, `menu_item_id`, `beverage_catalog_ref_id`, `price_krw`, `price_type`, `valid_from`, `valid_until`, `confidence`, `revision` | Update `venue_price_snapshots`; apply validity policy |

## Read Model Expectations

### `venue_snapshots`

Expected fields:

- `place_id`
- `place_revision`
- `place_type`
- `canonical_name`
- `location`
- `status`
- `publication_status`
- `recommendation_eligible`
- `snapshot_json`
- `synced_at`

### `venue_inventory_snapshots`

Expected fields:

- `place_id`
- `inventory_item_id`
- `inventory_revision`
- `menu_item_id`
- `beverage_catalog_ref_id`
- `availability_status`
- `stock_confidence`
- `last_seen_at`
- `expires_at`
- `synced_at`

### `venue_price_snapshots`

Expected fields:

- `place_id`
- `price_offer_id`
- `price_revision`
- `menu_item_id`
- `beverage_catalog_ref_id`
- `price_krw`
- `price_type`
- `valid_from`
- `valid_until`
- `confidence`
- `synced_at`

## Recommendation Log Rule

Recommendation logs must store:

- `place_revision`
- `inventory_revision`
- `price_revision`
- score breakdown JSON
- reason codes

This lets a future explanation or audit reconstruct which map/place data version influenced a recommendation.

## Consumer Safety Rules

- Ignore stale events where `aggregate_revision` is older than the current snapshot revision.
- Treat `FAILED` events as retryable unless the payload is invalid.
- Treat `SKIPPED` events as explicitly not needed, not as successful publish.
- Never use direct SQL reads against map-service production tables as a sync shortcut.
