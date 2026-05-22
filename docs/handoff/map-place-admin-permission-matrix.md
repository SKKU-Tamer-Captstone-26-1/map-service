# Map / Place Admin Permission Matrix

Admin Page is a privileged UI client, not a data owner. Every write must go through a service API and must be authorized by map-service/place-service policy.

| Action | Operator | Owner | Manager | Staff | Requires Approval | Audit Required | Notes |
|---|---:|---:|---:|---:|---:|---:|---|
| create place | Yes | No | No | No | No | Yes | Owner-submitted new place should enter review/import candidate flow |
| publish place | Yes | No | No | No | Yes | Yes | Public visibility requires operator decision |
| hide place | Yes | No | No | No | Yes | Yes | Use lifecycle/publication state, not hard delete |
| close place | Yes | Request only | Request only | No | Yes | Yes | Owner/manager submits `place_change_requests` |
| reopen place | Yes | Request only | Request only | No | Yes | Yes | Never auto-reactivate closed/archived/merged places |
| merge duplicate place | Yes | Request only | Request only | No | Yes | Yes | Use `merged_into_place_id` and `DUPLICATE_MERGED` |
| edit name | Yes | Request only | Request only | No | Yes for owner/manager | Yes | Sensitive owner change |
| edit address | Yes | Request only | Request only | No | Yes for owner/manager | Yes | Sensitive owner change |
| edit coordinates | Yes | Request only | Request only | No | Yes for owner/manager | Yes | Sensitive owner change |
| edit place type | Yes | Request only | Request only | No | Yes for owner/manager | Yes | Sensitive owner change |
| update business hours | Yes | Yes when table/API exists | Yes when table/API exists | No | Usually no | Yes | Table is deferred in current MVP migration |
| upload media | Yes | Yes when table/API exists | Yes when table/API exists | No | Review may be required | Yes | Table is deferred in current MVP migration |
| create menu item | Yes | Yes | Yes | No | No | Yes | Writes `venue_menu_items` |
| update menu item | Yes | Yes | Yes | No | No | Yes | Revision should increment |
| mark signature menu | Yes | Yes | Yes | No | No | Yes | `is_signature` on menu item |
| update inventory | Yes | Yes | Yes | Yes | No | Yes | Staff can update availability/stock freshness |
| update price | Yes | Yes | Yes | No | No | Yes | Price validity and confidence required |
| submit business claim | No | Yes | No | No | Yes | Yes | Any authenticated user may claim as future owner |
| approve business claim | Yes | No | No | No | Yes | Yes | Creates or updates `place_managers` |
| revoke manager | Yes | Owner for lower roles | No | No | Conditional | Yes | Operator can revoke any; owner can revoke manager/staff if policy allows |
| create operator override | Yes | No | No | No | No | Yes | Operator-only override layer |

## Sensitive Changes Requiring Approval

- Business name change.
- Address change.
- Coordinate change.
- Business type change.
- Closure.
- Reopening.
- Ownership transfer.
- Duplicate merge.
- Publication state changes from non-operator callers.

## Audit Defaults

- All admin/operator writes require audit.
- All owner/manager/staff writes to menu, inventory, price, and change requests require audit.
- System/ingestion writes that create candidates, review tasks, or canonical changes require audit.
- Reads do not require audit by default, except future sensitive admin data access can be logged separately.
