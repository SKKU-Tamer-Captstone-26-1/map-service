BEGIN;

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$
BEGIN
  CREATE TYPE source_type AS ENUM (
    'OPERATOR',
    'OWNER',
    'FIELD_RESEARCH',
    'PUBLIC_DATA',
    'KAKAO',
    'USER_REPORT',
    'SYSTEM'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE source_policy AS ENUM (
    'STORABLE',
    'REALTIME_ONLY',
    'RESTRICTED'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE import_type AS ENUM (
    'PUBLIC_DATA_FILE',
    'PUBLIC_DATA_API',
    'FIELD_RESEARCH_FILE',
    'OWNER_SUBMISSION',
    'OPERATOR_MANUAL',
    'USER_REPORT',
    'KAKAO_REALTIME_REFERENCE'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE import_status AS ENUM (
    'PENDING',
    'RUNNING',
    'COMPLETED',
    'FAILED',
    'CANCELLED'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE candidate_match_status AS ENUM (
    'NEW_CANDIDATE',
    'POSSIBLE_DUPLICATE',
    'MATCHED_EXISTING',
    'REJECTED',
    'NEEDS_REVIEW'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE candidate_review_status AS ENUM (
    'PENDING',
    'REVIEWING',
    'APPROVED',
    'REJECTED',
    'MERGED',
    'SKIPPED'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE dedupe_match_status AS ENUM (
    'PENDING',
    'ACCEPTED',
    'REJECTED',
    'SUPERSEDED'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE review_task_type AS ENUM (
    'VERIFY_NEW_PLACE',
    'VERIFY_DUPLICATE',
    'VERIFY_CLOSED',
    'VERIFY_LOCATION',
    'VERIFY_SOURCE_CONFLICT',
    'REVIEW_OWNER_CHANGE',
    'REVIEW_USER_REPORT'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE review_task_status AS ENUM (
    'PENDING',
    'ASSIGNED',
    'RESOLVED',
    'CANCELLED'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE place_type AS ENUM (
    'BAR',
    'PUB',
    'LIQUOR_SHOP',
    'BOTTLE_SHOP',
    'RESTAURANT',
    'OUTDOOR_SPOT',
    'CONVENIENCE_STORE',
    'OTHER'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE place_status AS ENUM (
    'DRAFT',
    'ACTIVE',
    'HIDDEN',
    'TEMPORARILY_CLOSED',
    'CLOSED',
    'DUPLICATE_MERGED',
    'REJECTED',
    'ARCHIVED'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE publication_status AS ENUM (
    'DRAFT',
    'PUBLISHED',
    'UNPUBLISHED'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE verified_level AS ENUM (
    'UNVERIFIED',
    'OWNER_VERIFIED',
    'OPERATOR_VERIFIED'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE media_type AS ENUM (
    'REPRESENTATIVE',
    'INTERIOR',
    'EXTERIOR',
    'MENU',
    'EVENT',
    'OWNER_PROOF'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE media_status AS ENUM (
    'ACTIVE',
    'HIDDEN',
    'REJECTED',
    'DELETED'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE claim_status AS ENUM (
    'PENDING',
    'APPROVED',
    'REJECTED',
    'CANCELLED',
    'REVOKED'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE manager_role AS ENUM (
    'OWNER',
    'MANAGER',
    'STAFF'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE manager_status AS ENUM (
    'ACTIVE',
    'SUSPENDED',
    'REVOKED'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE requester_role AS ENUM (
    'OWNER',
    'MANAGER',
    'STAFF',
    'OPERATOR',
    'SYSTEM'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE change_type AS ENUM (
    'NAME',
    'ADDRESS',
    'LOCATION',
    'PLACE_TYPE',
    'CLOSE',
    'REOPEN',
    'OWNERSHIP_TRANSFER',
    'MERGE_REQUEST',
    'PUBLICATION_STATUS',
    'RECOMMENDATION_ELIGIBILITY'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE request_status AS ENUM (
    'PENDING',
    'APPROVED',
    'REJECTED',
    'CANCELLED'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE actor_role AS ENUM (
    'OPERATOR',
    'OWNER',
    'MANAGER',
    'STAFF',
    'USER',
    'SYSTEM',
    'INGESTION_WORKER',
    'ANONYMOUS'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE audit_action AS ENUM (
    'PLACE_CREATED',
    'PLACE_UPDATED',
    'PLACE_PUBLISHED',
    'PLACE_UNPUBLISHED',
    'PLACE_CLOSED',
    'PLACE_HIDDEN',
    'PLACE_MERGED',
    'SOURCE_LINKED',
    'MENU_CREATED',
    'MENU_UPDATED',
    'INVENTORY_UPDATED',
    'PRICE_UPDATED',
    'CLAIM_APPROVED',
    'CLAIM_REJECTED',
    'CHANGE_REQUEST_CREATED',
    'CHANGE_REQUEST_APPROVED',
    'OVERRIDE_CREATED',
    'OVERRIDE_DISABLED',
    'IMPORT_BATCH_CREATED',
    'IMPORT_CANDIDATE_REVIEWED'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE audit_target_type AS ENUM (
    'PLACE',
    'SOURCE_REF',
    'MENU_ITEM',
    'INVENTORY_ITEM',
    'PRICE_OFFER',
    'CLAIM',
    'CHANGE_REQUEST',
    'OVERRIDE',
    'IMPORT_BATCH',
    'IMPORT_CANDIDATE',
    'REVIEW_TASK'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE report_type AS ENUM (
    'CLOSED',
    'WRONG_ADDRESS',
    'WRONG_LOCATION',
    'WRONG_PRICE',
    'OUT_OF_STOCK',
    'DUPLICATE',
    'INAPPROPRIATE',
    'OTHER'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE report_status AS ENUM (
    'PENDING',
    'REVIEWING',
    'RESOLVED',
    'REJECTED'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE tag_type AS ENUM (
    'ATMOSPHERE',
    'AMENITY',
    'CATEGORY',
    'LOCAL',
    'RECOMMENDATION'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE menu_type AS ENUM (
    'BOTTLE',
    'GLASS',
    'COCKTAIL',
    'BEER',
    'WINE',
    'WHISKEY',
    'FOOD',
    'FOOD_PAIRING',
    'CORKAGE',
    'EVENT'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE item_status AS ENUM (
    'ACTIVE',
    'HIDDEN',
    'DISCONTINUED',
    'PENDING_REVIEW'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE availability_status AS ENUM (
    'IN_STOCK',
    'LOW_STOCK',
    'OUT_OF_STOCK',
    'UNKNOWN',
    'DISCONTINUED'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE price_type AS ENUM (
    'BOTTLE',
    'GLASS',
    'COCKTAIL',
    'CORKAGE',
    'SET',
    'EVENT',
    'HAPPY_HOUR',
    'DELIVERY',
    'PICKUP'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE outdoor_level AS ENUM (
    'NONE',
    'LOW',
    'MEDIUM',
    'HIGH',
    'VARIES'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE outbox_status AS ENUM (
    'PENDING',
    'PUBLISHED',
    'FAILED',
    'SKIPPED'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

DO $$
BEGIN
  CREATE TYPE travel_mode AS ENUM (
    'WALK',
    'CAR',
    'TRANSIT',
    'MIXED'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;
$$;

COMMIT;
