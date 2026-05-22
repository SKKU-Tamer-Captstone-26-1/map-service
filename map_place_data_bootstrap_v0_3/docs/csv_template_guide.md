# CSV Template Guide

## operator_place_seed_template.csv

운영자가 직접 seed 후보를 넣을 때 사용합니다.

주요 컬럼:

```text
candidate_place_type: bar | pub | liquor_shop | bottle_shop | restaurant | outdoor_spot | convenience_store | other
review_status: needs_review | approved | rejected
recommendation_eligible: YES | NO | YES_AFTER_REVIEW
```

## owner_menu_items_template.csv

점주가 메뉴를 입력할 때 사용합니다.

```text
menu_type: bottle | glass | cocktail | beer | wine | whiskey | food | food_pairing | corkage | event
is_signature: true | false
```

## owner_inventory_items_template.csv

재고/판매 가능 여부를 입력할 때 사용합니다.

```text
availability_status: in_stock | low_stock | out_of_stock | unknown | discontinued
expires_at: TTL 적용 필수
```

## owner_price_offers_template.csv

가격 정보를 입력할 때 사용합니다.

```text
price_type: bottle | glass | cocktail | corkage | set | event | happy_hour | pickup
valid_until: 가격 유효기간
```

## outdoor_spot_seed_template.csv

야외 장소 후보를 입력할 때 사용합니다.

```text
weather_sensitive: true | false
policy_notes: 음주/피크닉/취식/쓰레기/운영정책 메모
```
