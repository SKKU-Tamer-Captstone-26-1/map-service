BEGIN;

CREATE TABLE data_sources (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_type source_type NOT NULL,
  source_name text NOT NULL,
  source_policy source_policy NOT NULL,
  license_name text,
  license_url text,
  trust_level smallint NOT NULL DEFAULT 0,
  active boolean NOT NULL DEFAULT true,
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_data_sources_trust_level_nonnegative CHECK (trust_level >= 0),
  CONSTRAINT uq_data_sources_type_name UNIQUE (source_type, source_name)
);

CREATE INDEX idx_data_sources_type ON data_sources (source_type);
CREATE INDEX idx_data_sources_policy ON data_sources (source_policy);

CREATE TABLE place_import_batches (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id uuid NOT NULL REFERENCES data_sources (id),
  import_type import_type NOT NULL,
  file_name text,
  original_uri text,
  status import_status NOT NULL DEFAULT 'PENDING',
  started_at timestamptz,
  completed_at timestamptz,
  row_count integer NOT NULL DEFAULT 0,
  success_count integer NOT NULL DEFAULT 0,
  error_count integer NOT NULL DEFAULT 0,
  checksum_sha256 text,
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_by_user_id text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_import_batches_row_count_nonnegative CHECK (row_count >= 0),
  CONSTRAINT ck_import_batches_success_count_nonnegative CHECK (success_count >= 0),
  CONSTRAINT ck_import_batches_error_count_nonnegative CHECK (error_count >= 0)
);

CREATE INDEX idx_import_batches_source ON place_import_batches (source_id);
CREATE INDEX idx_import_batches_status ON place_import_batches (status);
CREATE INDEX idx_import_batches_created_at ON place_import_batches (created_at);

CREATE TABLE place_import_candidates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_id uuid NOT NULL REFERENCES place_import_batches (id),
  source_id uuid NOT NULL REFERENCES data_sources (id),
  external_source_id text,
  source_policy source_policy NOT NULL,
  raw_payload_json jsonb NOT NULL,
  normalized_name text,
  normalized_address text,
  source_category_name text,
  candidate_place_type place_type,
  location geography(Point, 4326),
  latitude numeric(10,7),
  longitude numeric(10,7),
  match_status candidate_match_status NOT NULL DEFAULT 'NEW_CANDIDATE',
  matched_place_id uuid,
  dedupe_confidence numeric(4,3),
  review_status candidate_review_status NOT NULL DEFAULT 'PENDING',
  rejection_reason text,
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_import_candidates_latitude_range CHECK (
    latitude IS NULL OR latitude BETWEEN -90 AND 90
  ),
  CONSTRAINT ck_import_candidates_longitude_range CHECK (
    longitude IS NULL OR longitude BETWEEN -180 AND 180
  ),
  CONSTRAINT ck_import_candidates_dedupe_confidence_range CHECK (
    dedupe_confidence IS NULL OR dedupe_confidence BETWEEN 0 AND 1
  )
);

CREATE INDEX idx_import_candidates_batch ON place_import_candidates (batch_id);
CREATE INDEX idx_import_candidates_source_external
  ON place_import_candidates (source_id, external_source_id);
CREATE INDEX idx_import_candidates_normalized_name
  ON place_import_candidates (normalized_name);
CREATE INDEX idx_import_candidates_normalized_address
  ON place_import_candidates (normalized_address);
CREATE INDEX idx_import_candidates_match_status
  ON place_import_candidates (match_status);
CREATE INDEX idx_import_candidates_review_status
  ON place_import_candidates (review_status);
CREATE INDEX idx_import_candidates_matched_place
  ON place_import_candidates (matched_place_id);
CREATE INDEX idx_import_candidates_location_gist
  ON place_import_candidates USING GIST (location);

CREATE TABLE place_dedupe_matches (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id uuid NOT NULL REFERENCES place_import_candidates (id),
  existing_place_id uuid NOT NULL,
  match_strategy text NOT NULL,
  confidence numeric(4,3) NOT NULL,
  status dedupe_match_status NOT NULL DEFAULT 'PENDING',
  decided_by_user_id text,
  decided_at timestamptz,
  decision_note text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_dedupe_matches_confidence_range CHECK (confidence BETWEEN 0 AND 1)
);

CREATE INDEX idx_dedupe_matches_candidate ON place_dedupe_matches (candidate_id);
CREATE INDEX idx_dedupe_matches_place ON place_dedupe_matches (existing_place_id);
CREATE INDEX idx_dedupe_matches_status ON place_dedupe_matches (status);
CREATE INDEX idx_dedupe_matches_confidence ON place_dedupe_matches (confidence);

CREATE TABLE place_review_tasks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id uuid REFERENCES place_import_candidates (id),
  place_id uuid,
  task_type review_task_type NOT NULL,
  priority integer NOT NULL DEFAULT 100,
  status review_task_status NOT NULL DEFAULT 'PENDING',
  assigned_to_user_id text,
  resolution_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  resolution_note text,
  created_at timestamptz NOT NULL DEFAULT now(),
  resolved_at timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_review_tasks_priority_nonnegative CHECK (priority >= 0)
);

CREATE INDEX idx_review_tasks_status ON place_review_tasks (status);
CREATE INDEX idx_review_tasks_queue
  ON place_review_tasks (status, priority, created_at);
CREATE INDEX idx_review_tasks_candidate ON place_review_tasks (candidate_id);
CREATE INDEX idx_review_tasks_place ON place_review_tasks (place_id);

COMMIT;
