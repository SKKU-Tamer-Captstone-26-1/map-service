# Map / Place API Draft

This is a draft only. Do not implement APIs from this document without a separate implementation task.

## Shared Rules

- Public APIs must expose only places where `status = ACTIVE`, `publication_status = PUBLISHED`, and `published_at IS NOT NULL`.
- Admin/operator writes must create audit records.
- Owner/manager writes must be authorized through `place_managers`.
- Sensitive owner changes must create `place_change_requests` and wait for operator approval.
- Recommendation-service must use internal sync APIs/events only, not direct DB access.

## Public Map APIs

| API | Caller | Auth | Role | Request Shape | Response Shape | Idempotency | Audit Event | Major Error Cases |
|---|---|---|---|---|---|---|---|---|
| `SearchPlaces` | Mobile/web client | Optional | Public | `{ query, place_type?, center?, radius_m?, limit?, cursor? }` | `{ places[], next_cursor }` | Read-only | None | invalid query, invalid radius |
| `GetNearbyPlaces` | Mobile/web client | Optional | Public | `{ lat, lng, radius_m, place_type?, recommendation_eligible? }` | `{ places[] }` | Read-only | None | invalid coordinate, radius too large |
| `GetPlaceDetail` | Mobile/web client | Optional | Public | `{ place_id }` | `{ place, source_summary?, menu[], inventory[], price_offers[], outdoor_profile? }` | Read-only | None | not found, unpublished, hidden/closed |

## Admin Operator APIs

| API | Caller | Auth | Role | Request Shape | Response Shape | Idempotency | Audit Event | Major Error Cases |
|---|---|---|---|---|---|---|---|---|
| `CreatePlace` | Admin Page | Required | Operator | `{ place_type, canonical_name, address?, road_address?, location?, source_id?, idempotency_key }` | `{ place_id, revision, status }` | Required by `idempotency_key` | `PLACE_CREATED` | duplicate candidate, invalid location, unauthorized |
| `UpdatePlaceCore` | Admin Page | Required | Operator | `{ place_id, fields, expected_revision? }` | `{ place_id, revision }` | Optional request ID | `PLACE_UPDATED` | not found, revision conflict, invalid field |
| `PublishPlace` | Admin Page | Required | Operator | `{ place_id, expected_revision? }` | `{ place_id, status, publication_status, published_at, revision }` | Optional request ID | `PLACE_PUBLISHED` | missing required fields, already merged/archived |
| `HidePlace` | Admin Page | Required | Operator | `{ place_id, reason }` | `{ place_id, status, revision }` | Optional request ID | `PLACE_HIDDEN` | not found, invalid state |
| `ClosePlace` | Admin Page | Required | Operator | `{ place_id, reason, closed_at? }` | `{ place_id, status, closed_at, revision }` | Optional request ID | `PLACE_CLOSED` | not found, already closed |
| `MergePlaces` | Admin Page | Required | Operator | `{ source_place_id, target_place_id, reason }` | `{ source_place_id, merged_into_place_id, revision }` | Required by pair + request ID | `PLACE_MERGED` | same place, target invalid, source archived |
| `ReviewPlaceChangeRequest` | Admin Page | Required | Operator | `{ request_id, decision, review_note }` | `{ request_id, status, place_revision? }` | Decision is single-use | `CHANGE_REQUEST_APPROVED` or audit note for rejection | not found, already decided |
| `ApproveBusinessClaim` | Admin Page | Required | Operator | `{ claim_id, manager_role }` | `{ claim_id, status, manager_id }` | Decision is single-use | `CLAIM_APPROVED` | invalid evidence, already decided |
| `CreateOperatorOverride` | Admin Page | Required | Operator | `{ place_id, field_name, override_value_json, reason, expires_at? }` | `{ override_id }` | Optional request ID | `OVERRIDE_CREATED` | invalid field, not found |

## Owner / Store Manager APIs

| API | Caller | Auth | Role | Request Shape | Response Shape | Idempotency | Audit Event | Major Error Cases |
|---|---|---|---|---|---|---|---|---|
| `SubmitBusinessClaim` | Owner portal/Admin Page | Required | User | `{ place_id, requester_name?, requester_phone?, evidence_document_refs, idempotency_key }` | `{ claim_id, claim_status }` | Required | `CHANGE_REQUEST_CREATED` or claim audit | duplicate pending claim, invalid evidence |
| `UpdateMenuItem` | Owner/manager UI | Required | Owner/Manager | `{ place_id, menu_item_id?, menu_name, menu_type, base_price_krw?, is_signature?, status? }` | `{ menu_item_id, revision }` | Optional request ID | `MENU_CREATED` or `MENU_UPDATED` | unauthorized manager, invalid price |
| `UpdateInventory` | Owner/manager/staff UI | Required | Owner/Manager/Staff | `{ place_id, menu_item_id?, beverage_catalog_ref_id?, availability_status, stock_confidence?, quantity_text?, last_seen_at?, expires_at? }` | `{ inventory_item_id, revision }` | Optional request ID | `INVENTORY_UPDATED` | stale write, invalid confidence |
| `UpdatePriceOffer` | Owner/manager UI | Required | Owner/Manager | `{ place_id, menu_item_id?, price_krw, price_type, valid_from?, valid_until?, confidence? }` | `{ price_offer_id, revision }` | Optional request ID | `PRICE_UPDATED` | invalid price, invalid validity window |
| `SubmitSensitiveChangeRequest` | Owner/manager UI | Required | Owner/Manager | `{ place_id, change_type, current_value_json?, requested_value_json, idempotency_key }` | `{ request_id, status }` | Required | `CHANGE_REQUEST_CREATED` | unsupported change type, duplicate pending request |

## Internal Sync APIs

| API | Caller | Auth | Role | Request Shape | Response Shape | Idempotency | Audit Event | Major Error Cases |
|---|---|---|---|---|---|---|---|---|
| `GetPublishedPlaceSnapshot` | recommendation sync/search sync | Service auth | Internal service | `{ place_id, min_revision? }` | `{ place_snapshot, menu[], inventory[], price_offers[], revision }` | Read-only | None | not found, not published |
| `ListPlaceChangesSince` | recommendation sync/search sync | Service auth | Internal service | `{ since, limit, cursor? }` | `{ events_or_snapshots[], next_cursor }` | Read-only | None | invalid cursor |
| `GetPlaceOutboxEvents` | sync worker | Service auth | Internal service | `{ status: PENDING, limit }` | `{ events[] }` | Read-only claim should be separate if needed | None | worker auth failure |
| `AckPlaceOutboxEvent` | sync worker | Service auth | Internal service | `{ event_id, status, error_message? }` | `{ event_id, status, published_at? }` | Idempotent by `event_id` | None | invalid transition, event not found |

## Error Policy Draft

| Error | Meaning |
|---|---|
| `UNAUTHENTICATED` | Missing or invalid auth token |
| `PERMISSION_DENIED` | Caller lacks required role |
| `NOT_FOUND` | Resource does not exist or is not visible to caller |
| `INVALID_ARGUMENT` | Bad field, coordinate, price, confidence, or enum |
| `FAILED_PRECONDITION` | Invalid lifecycle transition |
| `ABORTED` | Revision conflict or concurrent update |
| `ALREADY_EXISTS` | Duplicate claim, source ref, manager, or idempotent create |
