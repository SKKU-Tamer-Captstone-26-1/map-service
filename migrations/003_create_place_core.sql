BEGIN;

CREATE TABLE places (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  place_type place_type NOT NULL,
  canonical_name text NOT NULL,
  normalized_name text NOT NULL,
  status place_status NOT NULL DEFAULT 'DRAFT',
  publication_status publication_status NOT NULL DEFAULT 'DRAFT',
  address text,
  road_address text,
  address_detail text,
  location geography(Point, 4326),
  latitude numeric(10,7),
  longitude numeric(10,7),
  geohash text,
  phone text,
  website_url text,
  instagram_url text,
  price_level smallint,
  verified_level verified_level NOT NULL DEFAULT 'UNVERIFIED',
  recommendation_eligible boolean NOT NULL DEFAULT true,
  created_by_source_id uuid REFERENCES data_sources (id),
  created_by_actor_user_id text,
  merged_into_place_id uuid,
  revision bigint NOT NULL DEFAULT 1,
  published_at timestamptz,
  closed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_places_latitude_range CHECK (
    latitude IS NULL OR latitude BETWEEN -90 AND 90
  ),
  CONSTRAINT ck_places_longitude_range CHECK (
    longitude IS NULL OR longitude BETWEEN -180 AND 180
  ),
  CONSTRAINT ck_places_price_level_range CHECK (
    price_level IS NULL OR price_level BETWEEN 1 AND 5
  ),
  CONSTRAINT ck_places_revision_positive CHECK (revision > 0),
  CONSTRAINT fk_places_merged_into
    FOREIGN KEY (merged_into_place_id)
    REFERENCES places (id)
    DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX idx_places_normalized_name ON places (normalized_name);
CREATE INDEX idx_places_geohash ON places (geohash);
CREATE INDEX idx_places_public_query
  ON places (status, publication_status, place_type);
CREATE INDEX idx_places_recommendation_query
  ON places (place_type, recommendation_eligible);
CREATE INDEX idx_places_created_by_source ON places (created_by_source_id);
CREATE INDEX idx_places_merged_into ON places (merged_into_place_id);
CREATE INDEX idx_places_location_gist ON places USING GIST (location);
CREATE INDEX idx_places_public_active_published
  ON places (place_type, updated_at)
  WHERE status = 'ACTIVE'
    AND publication_status = 'PUBLISHED';
CREATE INDEX idx_places_recommendation_eligible
  ON places (place_type, updated_at)
  WHERE status = 'ACTIVE'
    AND publication_status = 'PUBLISHED'
    AND recommendation_eligible = true;

CREATE TABLE place_source_refs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  place_id uuid NOT NULL REFERENCES places (id),
  source_id uuid NOT NULL REFERENCES data_sources (id),
  external_source_id text,
  external_url text,
  source_policy source_policy NOT NULL,
  match_confidence numeric(4,3),
  is_primary boolean NOT NULL DEFAULT false,
  last_checked_at timestamptz,
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_place_source_refs_match_confidence_range CHECK (
    match_confidence IS NULL OR match_confidence BETWEEN 0 AND 1
  )
);

CREATE INDEX idx_place_source_refs_place ON place_source_refs (place_id);
CREATE UNIQUE INDEX uq_place_source_refs_source_external
  ON place_source_refs (source_id, external_source_id)
  WHERE external_source_id IS NOT NULL;
CREATE INDEX idx_place_source_refs_primary ON place_source_refs (is_primary);

ALTER TABLE place_import_candidates
  ADD CONSTRAINT fk_import_candidates_matched_place
  FOREIGN KEY (matched_place_id)
  REFERENCES places (id)
  DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE place_dedupe_matches
  ADD CONSTRAINT fk_dedupe_matches_existing_place
  FOREIGN KEY (existing_place_id)
  REFERENCES places (id)
  DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE place_review_tasks
  ADD CONSTRAINT fk_review_tasks_place
  FOREIGN KEY (place_id)
  REFERENCES places (id)
  DEFERRABLE INITIALLY DEFERRED;

COMMIT;
