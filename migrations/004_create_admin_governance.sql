BEGIN;

CREATE TABLE business_claims (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  place_id uuid NOT NULL REFERENCES places (id),
  requester_user_id text NOT NULL,
  requester_name text,
  requester_phone text,
  claim_status claim_status NOT NULL DEFAULT 'PENDING',
  business_registration_no_hash text,
  evidence_document_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  requested_at timestamptz NOT NULL DEFAULT now(),
  reviewed_by_user_id text,
  reviewed_at timestamptz,
  rejection_reason text,
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_business_claims_place ON business_claims (place_id);
CREATE INDEX idx_business_claims_requester ON business_claims (requester_user_id);
CREATE INDEX idx_business_claims_status ON business_claims (claim_status);

CREATE TABLE place_managers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  place_id uuid NOT NULL REFERENCES places (id),
  user_id text NOT NULL,
  manager_role manager_role NOT NULL,
  status manager_status NOT NULL DEFAULT 'ACTIVE',
  granted_by_user_id text,
  granted_reason text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  revoked_at timestamptz,
  CONSTRAINT uq_place_managers_place_user UNIQUE (place_id, user_id)
);

CREATE INDEX idx_place_managers_user_status ON place_managers (user_id, status);
CREATE INDEX idx_place_managers_place_status ON place_managers (place_id, status);

CREATE TABLE place_change_requests (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  place_id uuid NOT NULL REFERENCES places (id),
  requested_by_user_id text NOT NULL,
  requester_role requester_role NOT NULL,
  change_type change_type NOT NULL,
  current_value_json jsonb,
  requested_value_json jsonb NOT NULL,
  status request_status NOT NULL DEFAULT 'PENDING',
  reviewed_by_user_id text,
  reviewed_at timestamptz,
  review_note text,
  idempotency_key text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_change_requests_place ON place_change_requests (place_id);
CREATE INDEX idx_change_requests_queue
  ON place_change_requests (status, change_type, created_at);
CREATE INDEX idx_change_requests_idempotency
  ON place_change_requests (idempotency_key);

CREATE TABLE place_overrides (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  place_id uuid NOT NULL REFERENCES places (id),
  field_name text NOT NULL,
  override_value_json jsonb NOT NULL,
  reason text NOT NULL,
  priority integer NOT NULL DEFAULT 100,
  active boolean NOT NULL DEFAULT true,
  created_by_user_id text NOT NULL,
  expires_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_place_overrides_priority_nonnegative CHECK (priority >= 0)
);

CREATE INDEX idx_place_overrides_active_field
  ON place_overrides (place_id, field_name, active);

CREATE TABLE place_audit_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_user_id text,
  actor_role actor_role,
  action audit_action NOT NULL,
  target_type audit_target_type NOT NULL,
  target_id uuid NOT NULL,
  before_json jsonb,
  after_json jsonb,
  request_id text,
  ip_address inet,
  user_agent text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_logs_target
  ON place_audit_logs (target_type, target_id, created_at);
CREATE INDEX idx_audit_logs_actor
  ON place_audit_logs (actor_user_id, created_at);
CREATE INDEX idx_audit_logs_action ON place_audit_logs (action);

COMMIT;
