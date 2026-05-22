# map-service Docs

## 핵심 문서

| Path | Purpose |
|---|---|
| [architecture.md](architecture.md) | 전체 DB/service boundary |
| [map-place/ownership.md](map-place/ownership.md) | map_view, admin_ops, external source ownership |
| [map-place/database.md](map-place/database.md) | local DB와 migration set 기준 |
| [map-place/erd.md](map-place/erd.md) | ERD source of truth |
| [map-place/data-ingestion.md](map-place/data-ingestion.md) | public data candidate policy |
| [integrations/kakao-api-policy.md](integrations/kakao-api-policy.md) | Kakao realtime-only policy |
| [runbooks/local-db-rebaseline.md](runbooks/local-db-rebaseline.md) | local clean DB rebaseline procedure |

## Research Outputs

Research-only docs live under [research/](research/).

Bootstrap CSV drafts live under [../data/bootstrap/](../data/bootstrap/).

These artifacts do not authorize canonical ingestion or marker publish. They define source policy, category mapping, and future candidate staging inputs.
