-- Optional basic tags for places.
-- Review table/column names before executing against your actual migration.

INSERT INTO tags (id, tag_type, code, name_ko, name_en, active, created_at, updated_at)
VALUES
  (gen_random_uuid(), 'category', 'whiskey_bar', '위스키바', 'Whiskey Bar', true, now(), now()),
  (gen_random_uuid(), 'category', 'cocktail_bar', '칵테일바', 'Cocktail Bar', true, now(), now()),
  (gen_random_uuid(), 'category', 'wine_bar', '와인바', 'Wine Bar', true, now(), now()),
  (gen_random_uuid(), 'category', 'craft_beer', '수제맥주', 'Craft Beer', true, now(), now()),
  (gen_random_uuid(), 'category', 'bottle_shop', '보틀샵', 'Bottle Shop', true, now(), now()),
  (gen_random_uuid(), 'category', 'liquor_shop', '주류점', 'Liquor Shop', true, now(), now()),
  (gen_random_uuid(), 'atmosphere', 'quiet', '조용한', 'Quiet', true, now(), now()),
  (gen_random_uuid(), 'atmosphere', 'date_spot', '데이트', 'Date Spot', true, now(), now()),
  (gen_random_uuid(), 'atmosphere', 'group_friendly', '단체 가능', 'Group Friendly', true, now(), now()),
  (gen_random_uuid(), 'amenity', 'outdoor_seating', '야외 좌석', 'Outdoor Seating', true, now(), now()),
  (gen_random_uuid(), 'local', 'hanriver_picnic', '한강 피크닉', 'Han River Picnic', true, now(), now());
