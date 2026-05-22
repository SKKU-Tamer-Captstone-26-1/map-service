BEGIN;

CREATE TABLE outdoor_spot_profiles (
  place_id uuid PRIMARY KEY REFERENCES places (id),
  allowed_activity_notes text,
  nearby_store_notes text,
  seating_level outdoor_level,
  crowd_level outdoor_level,
  restroom_available boolean,
  parking_available boolean,
  weather_sensitive boolean NOT NULL DEFAULT true,
  policy_notes text,
  safety_notes text,
  last_verified_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE place_outbox_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  aggregate_type text NOT NULL,
  aggregate_id uuid NOT NULL,
  aggregate_revision bigint NOT NULL,
  event_type text NOT NULL,
  payload_json jsonb NOT NULL,
  status outbox_status NOT NULL DEFAULT 'PENDING',
  idempotency_key text,
  error_message text,
  created_at timestamptz NOT NULL DEFAULT now(),
  published_at timestamptz,
  CONSTRAINT ck_outbox_events_aggregate_revision_positive CHECK (
    aggregate_revision > 0
  )
);

CREATE INDEX idx_outbox_pending ON place_outbox_events (status, created_at);
CREATE INDEX idx_outbox_aggregate
  ON place_outbox_events (aggregate_type, aggregate_id, aggregate_revision);
CREATE INDEX idx_outbox_idempotency ON place_outbox_events (idempotency_key);

COMMIT;
