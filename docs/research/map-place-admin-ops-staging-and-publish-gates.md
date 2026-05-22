# Admin Ops, Staging, And Publish Gates

## Boundary

`map_view`는 장소 원본을 소유하지 않습니다.

```text
map_view
  marker_layers
  markers
  marker_publication_events

admin_ops / ingest workflow
  source registry
  import batches
  import candidates
  dedupe matches
  review tasks
  canonical places
  publish jobs
```

이 repo의 현재 안전한 구현 범위는 `map_view` local DB setup과 research package입니다. `admin_ops` schema는 별도 task로 설계해야 합니다.

## Candidate Staging Requirements

후보 staging은 `map_view` 밖에 있어야 합니다.

필수 개념:

| Concept | Requirement |
|---|---|
| source registry | source policy, license, URL, storage policy 기록 |
| import batch | source, fetched_at, checksum, row counts 기록 |
| import candidate | raw payload, normalized fields, source category, coordinates |
| dedupe match | 후보와 기존 canonical place의 가능 매칭 |
| review task | 운영자 검토/승인/거절 상태 |
| audit | 누가 언제 어떤 값을 승인했는지 기록 |

## Publish Preconditions

`map_view.markers`에 쓰기 전 반드시 아래 조건을 만족해야 합니다.

1. 후보 데이터가 source policy를 통과했습니다.
2. Kakao API 응답이 canonical source로 사용되지 않았습니다.
3. canonical place owner가 `admin_ops` 또는 별도 place-service로 명확합니다.
4. 운영자 또는 승인 workflow가 name/location/category를 확정했습니다.
5. publish job이 idempotent key와 source revision을 가집니다.
6. `map_view.markers.place_ref`는 logical reference로만 저장되고 cross-service FK를 만들지 않습니다.

## Publish Output Shape

승인된 canonical data만 `map_view` projection으로 복사합니다.

| map_view Column | Source |
|---|---|
| `place_ref` | canonical place id logical reference |
| `layer_code` | approved map layer |
| `label` | approved display label copy |
| `location` | approved WGS84 point copy |
| `geohash` | derived from approved location |
| `icon_key` | approved override or layer default |
| `visibility` | approved marker state |
| `filter_json` | published UI filter payload |
| `published_revision` | canonical place or publish revision |

## Explicit Non-Goals For Now

- Publish worker/API implementation
- Admin Page direct DB writes
- Canonical place schema migration in `map_view`
- Candidate staging tables in `map_view`
- Kakao data persistence as canonical source

## First Safe Publish-Related Task Later

After candidate staging and canonical owner are approved, the first publish-related implementation should be a dry-run contract checker:

```text
input: approved canonical place snapshot
output: proposed map_view marker mutation
side effects: none
```

Only after that dry-run checker is reviewed should an idempotent publish write path be implemented.
