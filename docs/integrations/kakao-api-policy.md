# Kakao API Policy

## Scope

This document covers Kakao Local/Map API usage in map-service.

References:

- https://developers.kakao.com/docs/latest/ko/local/common
- https://developers.kakao.com/docs/latest/ko/kakaomap
- https://developers.kakao.com/docs/latest/ko/getting-started/quota
- https://developers.kakao.com/terms/ko/site-terms

## Default Classification

```text
storage_policy = realtime_only
canonical_use_allowed = false
default_target = realtime_lookup
review_required = true
```

## Allowed Uses

- realtime user or operator lookup
- map display support through Kakao Map SDK
- operator verification support
- external Kakao place/map link support
- quota-monitored API calls in approved environments

## Disallowed Uses Without Separate Approval

- bulk place bootstrap
- storing Kakao Local search responses as canonical place data
- using Kakao as source registry `canonical_use_allowed=true`
- building a POI directory from copied Kakao results
- replacing public/open-data source review with Kakao lookup

## Implementation Rules

- Do not commit Kakao app keys.
- Do not log request headers containing credentials.
- Do not persist raw Kakao API responses in bootstrap data.
- Store only operator decisions that are independently approved, not Kakao payloads as canonical source.
- Keep quota errors visible to operators; do not retry aggressively.

## Approval Gate

Any exception to `realtime_only` requires written legal/partnership approval and an updated source policy document before implementation.
