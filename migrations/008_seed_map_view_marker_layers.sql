BEGIN;

INSERT INTO map_view.marker_layers (
  code,
  label_ko,
  label_en,
  icon_key,
  display_order,
  default_visible,
  is_active
)
VALUES
  ('bar', '바', 'Bar', 'bar', 10, true, true),
  ('pub', '펍', 'Pub', 'beer', 20, true, true),
  ('liquor_shop', '주류 판매점', 'Liquor shop', 'bottle', 30, true, true),
  ('outdoor_spot', '야외 장소', 'Outdoor spot', 'trees', 40, true, true),
  ('restaurant', '음식점', 'Restaurant', 'utensils', 50, false, true),
  ('convenience_store', '편의점', 'Convenience store', 'store', 60, false, true),
  ('other', '기타', 'Other', 'map-pin', 90, false, true)
ON CONFLICT (code) DO UPDATE
SET
  label_ko = EXCLUDED.label_ko,
  label_en = EXCLUDED.label_en,
  icon_key = EXCLUDED.icon_key,
  display_order = EXCLUDED.display_order,
  default_visible = EXCLUDED.default_visible,
  is_active = EXCLUDED.is_active,
  updated_at = now();

COMMIT;
