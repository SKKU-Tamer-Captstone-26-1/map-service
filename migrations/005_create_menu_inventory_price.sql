BEGIN;

CREATE TABLE venue_menu_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  place_id uuid NOT NULL REFERENCES places (id),
  beverage_catalog_ref_id text,
  menu_name text NOT NULL,
  normalized_menu_name text NOT NULL,
  menu_type menu_type NOT NULL,
  description text,
  base_price_krw integer,
  is_signature boolean NOT NULL DEFAULT false,
  status item_status NOT NULL DEFAULT 'ACTIVE',
  source_type source_type NOT NULL,
  confidence numeric(4,3),
  last_verified_at timestamptz,
  revision bigint NOT NULL DEFAULT 1,
  created_by_user_id text,
  updated_by_user_id text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_menu_items_base_price_nonnegative CHECK (
    base_price_krw IS NULL OR base_price_krw >= 0
  ),
  CONSTRAINT ck_menu_items_confidence_range CHECK (
    confidence IS NULL OR confidence BETWEEN 0 AND 1
  ),
  CONSTRAINT ck_menu_items_revision_positive CHECK (revision > 0)
);

CREATE INDEX idx_menu_items_place_status ON venue_menu_items (place_id, status);
CREATE INDEX idx_menu_items_beverage_ref
  ON venue_menu_items (beverage_catalog_ref_id);
CREATE INDEX idx_menu_items_normalized_name
  ON venue_menu_items (normalized_menu_name);
CREATE INDEX idx_menu_items_signature ON venue_menu_items (is_signature);

CREATE TABLE venue_inventory_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  place_id uuid NOT NULL REFERENCES places (id),
  menu_item_id uuid REFERENCES venue_menu_items (id),
  beverage_catalog_ref_id text,
  inventory_name text,
  availability_status availability_status NOT NULL DEFAULT 'UNKNOWN',
  stock_confidence numeric(4,3) NOT NULL DEFAULT 0.500,
  quantity_text text,
  last_seen_at timestamptz,
  expires_at timestamptz,
  source_type source_type NOT NULL,
  updated_by_role actor_role,
  revision bigint NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_inventory_stock_confidence_range CHECK (
    stock_confidence BETWEEN 0 AND 1
  ),
  CONSTRAINT ck_inventory_revision_positive CHECK (revision > 0)
);

CREATE INDEX idx_inventory_place_beverage
  ON venue_inventory_items (place_id, beverage_catalog_ref_id);
CREATE INDEX idx_inventory_availability_expires
  ON venue_inventory_items (availability_status, expires_at);
CREATE INDEX idx_inventory_menu_item ON venue_inventory_items (menu_item_id);
CREATE INDEX idx_inventory_expires_at ON venue_inventory_items (expires_at);

CREATE TABLE venue_price_offers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  place_id uuid NOT NULL REFERENCES places (id),
  menu_item_id uuid REFERENCES venue_menu_items (id),
  beverage_catalog_ref_id text,
  price_krw integer NOT NULL,
  currency text NOT NULL DEFAULT 'KRW',
  price_type price_type NOT NULL,
  min_order_quantity integer,
  note text,
  valid_from timestamptz,
  valid_until timestamptz,
  source_type source_type NOT NULL,
  confidence numeric(4,3) NOT NULL DEFAULT 0.500,
  revision bigint NOT NULL DEFAULT 1,
  created_by_user_id text,
  updated_by_user_id text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_price_offers_price_nonnegative CHECK (price_krw >= 0),
  CONSTRAINT ck_price_offers_min_order_nonnegative CHECK (
    min_order_quantity IS NULL OR min_order_quantity >= 0
  ),
  CONSTRAINT ck_price_offers_confidence_range CHECK (confidence BETWEEN 0 AND 1),
  CONSTRAINT ck_price_offers_revision_positive CHECK (revision > 0)
);

CREATE INDEX idx_price_place_beverage
  ON venue_price_offers (place_id, beverage_catalog_ref_id);
CREATE INDEX idx_price_menu_item ON venue_price_offers (menu_item_id);
CREATE INDEX idx_price_valid_until ON venue_price_offers (valid_until);
CREATE INDEX idx_price_krw ON venue_price_offers (price_krw);

COMMIT;
