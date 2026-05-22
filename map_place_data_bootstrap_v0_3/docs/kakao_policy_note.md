# Kakao API Policy Note

Kakao Local/Map API는 이 프로젝트에서 canonical bulk-ingestion source로 사용하지 않습니다.

## 금지

```text
Kakao Local API 호출
  -> 장소명/주소/전화번호/좌표 저장
  -> places canonical DB 구축
```

## 허용

```text
- 사용자의 실시간 장소 검색
- 지도 표시 보조
- Kakao Map 랜딩 링크
- 운영자 검수 화면에서 실시간 확인
```

## Source policy

Kakao를 data_sources에 등록하더라도 기본 정책은 다음이어야 합니다.

```text
source_type = KAKAO
source_policy = realtime_only
canonical_use_allowed = false
```

법무/제휴 승인 전까지 `storable`로 변경하지 않습니다.
