BEGIN;

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS map_view;

DO $$
BEGIN
  CREATE TYPE map_view.marker_visibility_state AS ENUM (
    'visible',
    'hidden'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE map_view.marker_publication_event_type AS ENUM (
    'marker_published',
    'marker_hidden',
    'marker_moved',
    'marker_layer_changed',
    'marker_deleted'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

CREATE TABLE IF NOT EXISTS map_view.marker_layers (
  code varchar PRIMARY KEY,
  label_ko varchar NOT NULL,
  label_en varchar,
  icon_key varchar NOT NULL,
  display_order integer NOT NULL DEFAULT 0,
  default_visible boolean NOT NULL DEFAULT true,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_marker_layers_display_order
  ON map_view.marker_layers (display_order);
CREATE INDEX IF NOT EXISTS idx_marker_layers_active
  ON map_view.marker_layers (is_active);

CREATE TABLE IF NOT EXISTS map_view.markers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  place_ref uuid NOT NULL,
  layer_code varchar NOT NULL,
  label varchar NOT NULL,
  location geography(Point, 4326) NOT NULL,
  geohash varchar,
  icon_key varchar,
  visibility map_view.marker_visibility_state NOT NULL DEFAULT 'visible',
  filter_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  published_revision bigint NOT NULL,
  published_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_markers_place_ref UNIQUE (place_ref),
  CONSTRAINT fk_markers_layer_code
    FOREIGN KEY (layer_code)
    REFERENCES map_view.marker_layers (code),
  CONSTRAINT ck_markers_published_revision_positive
    CHECK (published_revision > 0),
  CONSTRAINT ck_markers_filter_json_object
    CHECK (jsonb_typeof(filter_json) = 'object')
);

CREATE INDEX IF NOT EXISTS idx_markers_location_gist
  ON map_view.markers USING GIST (location);
CREATE INDEX IF NOT EXISTS idx_markers_layer_code
  ON map_view.markers (layer_code);
CREATE INDEX IF NOT EXISTS idx_markers_visibility
  ON map_view.markers (visibility);
CREATE INDEX IF NOT EXISTS idx_markers_layer_visibility
  ON map_view.markers (layer_code, visibility);
CREATE INDEX IF NOT EXISTS idx_markers_geohash
  ON map_view.markers (geohash);
CREATE INDEX IF NOT EXISTS idx_markers_published_revision
  ON map_view.markers (published_revision);

CREATE TABLE IF NOT EXISTS map_view.marker_publication_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type map_view.marker_publication_event_type NOT NULL,
  marker_id uuid,
  place_ref uuid NOT NULL,
  published_revision bigint NOT NULL,
  payload_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  consumed_at timestamptz,
  CONSTRAINT fk_marker_events_marker_id
    FOREIGN KEY (marker_id)
    REFERENCES map_view.markers (id)
    ON DELETE SET NULL,
  CONSTRAINT ck_marker_events_published_revision_positive
    CHECK (published_revision > 0),
  CONSTRAINT ck_marker_events_payload_json_object
    CHECK (jsonb_typeof(payload_json) = 'object')
);

CREATE INDEX IF NOT EXISTS idx_marker_events_place_ref
  ON map_view.marker_publication_events (place_ref);
CREATE INDEX IF NOT EXISTS idx_marker_events_created_at
  ON map_view.marker_publication_events (created_at);
CREATE INDEX IF NOT EXISTS idx_marker_events_consumed_at
  ON map_view.marker_publication_events (consumed_at);
CREATE INDEX IF NOT EXISTS idx_marker_events_place_revision
  ON map_view.marker_publication_events (place_ref, published_revision);
CREATE INDEX IF NOT EXISTS idx_marker_events_marker_id
  ON map_view.marker_publication_events (marker_id);

COMMIT;
