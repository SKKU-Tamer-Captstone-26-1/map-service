from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


SOURCE_TYPES = {
    "OPERATOR",
    "OWNER",
    "FIELD_RESEARCH",
    "PUBLIC_DATA",
    "KAKAO",
    "USER_REPORT",
    "SYSTEM",
}

SOURCE_TYPE_ALIASES = {
    "PUBLIC_PAGE": "PUBLIC_DATA",
    "OFFICIAL_PAGE": "PUBLIC_DATA",
}

SOURCE_POLICIES = {"STORABLE", "REALTIME_ONLY", "RESTRICTED"}

SOURCE_POLICY_ALIASES = {
    "STORABLE_WITH_ATTRIBUTION": "STORABLE",
    "REFERENCE_FOR_OPERATOR_REVIEW": "RESTRICTED",
    "REVIEW_REQUIRED": "RESTRICTED",
}

PLACE_TYPES = {
    "BAR",
    "PUB",
    "LIQUOR_SHOP",
    "BOTTLE_SHOP",
    "RESTAURANT",
    "OUTDOOR_SPOT",
    "CONVENIENCE_STORE",
    "OTHER",
}

MENU_TYPES = {
    "BOTTLE",
    "GLASS",
    "COCKTAIL",
    "BEER",
    "WINE",
    "WHISKEY",
    "FOOD",
    "FOOD_PAIRING",
    "CORKAGE",
    "EVENT",
}

ITEM_STATUSES = {"ACTIVE", "HIDDEN", "DISCONTINUED", "PENDING_REVIEW"}

AVAILABILITY_STATUSES = {"IN_STOCK", "LOW_STOCK", "OUT_OF_STOCK", "UNKNOWN", "DISCONTINUED"}

PRICE_TYPES = {"BOTTLE", "GLASS", "COCKTAIL", "CORKAGE", "SET", "EVENT", "HAPPY_HOUR", "DELIVERY", "PICKUP"}

ACTOR_ROLES = {"OPERATOR", "OWNER", "MANAGER", "STAFF", "USER", "SYSTEM", "INGESTION_WORKER", "ANONYMOUS"}

REVIEW_STATUS_ALIASES = {
    "NEEDS_REVIEW": "PENDING",
    "PENDING": "PENDING",
    "APPROVED": "APPROVED",
    "REJECTED": "REJECTED",
    "MERGED": "MERGED",
    "SKIPPED": "SKIPPED",
}


@dataclass(frozen=True)
class CoordinateParseResult:
    latitude: Decimal | None
    longitude: Decimal | None
    valid: bool
    error: str | None = None


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value)).replace("\ufeff", "")
    return re.sub(r"\s+", " ", text).strip()


def normalize_place_name(value: Any) -> str:
    text = clean_text(value)
    text = text.lower()
    text = re.sub(r"[\"'`]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_address(value: Any) -> str:
    text = clean_text(value)
    text = text.replace("대한민국 ", "")
    return re.sub(r"\s+", " ", text).strip()


def normalize_phone_optional(value: Any) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    text = text.replace(" ", "")
    text = re.sub(r"[.]", "-", text)
    text = re.sub(r"-+", "-", text)
    return text


def normalize_source_type(value: Any) -> str:
    source_type = clean_text(value).upper()
    source_type = SOURCE_TYPE_ALIASES.get(source_type, source_type)
    if source_type not in SOURCE_TYPES:
        raise ValueError(f"unsupported source_type: {value}")
    return source_type


def normalize_source_policy(value: Any) -> str:
    policy = clean_text(value).upper()
    policy = SOURCE_POLICY_ALIASES.get(policy, policy)
    if policy not in SOURCE_POLICIES:
        raise ValueError(f"unsupported source_policy: {value}")
    return policy


def validate_source_policy(source_type: Any, source_policy: Any) -> str:
    normalized_type = normalize_source_type(source_type)
    normalized_policy = normalize_source_policy(source_policy)
    if normalized_type == "KAKAO" and normalized_policy == "STORABLE":
        raise ValueError("Kakao sources must be REALTIME_ONLY or RESTRICTED, not STORABLE")
    return normalized_policy


def normalize_place_type(value: Any) -> str:
    place_type = clean_text(value).upper()
    place_type = place_type.replace("-", "_").replace(" ", "_")
    if place_type not in PLACE_TYPES:
        raise ValueError(f"unsupported candidate_place_type: {value}")
    return place_type


def normalize_menu_type(value: Any) -> str:
    return _normalize_enum(value, MENU_TYPES, "menu_type")


def normalize_item_status(value: Any, default: str = "ACTIVE") -> str:
    text = clean_text(value)
    if not text:
        return default
    return _normalize_enum(text, ITEM_STATUSES, "item_status")


def normalize_availability_status(value: Any) -> str:
    return _normalize_enum(value, AVAILABILITY_STATUSES, "availability_status")


def normalize_price_type(value: Any) -> str:
    return _normalize_enum(value, PRICE_TYPES, "price_type")


def normalize_actor_role(value: Any, default: str | None = None) -> str | None:
    text = clean_text(value)
    if not text and default is not None:
        return default
    if not text:
        return None
    return _normalize_enum(text, ACTOR_ROLES, "actor_role")


def normalize_review_status(value: Any, default: str = "PENDING") -> str:
    text = clean_text(value).upper()
    if not text:
        return default
    status = REVIEW_STATUS_ALIASES.get(text)
    if not status:
        raise ValueError(f"unsupported review_status: {value}")
    return status


def _normalize_enum(value: Any, allowed: set[str], field_name: str) -> str:
    normalized = clean_text(value).upper().replace("-", "_").replace(" ", "_")
    if normalized not in allowed:
        raise ValueError(f"unsupported {field_name}: {value}")
    return normalized


def parse_bool(value: Any, default: bool = False) -> bool:
    text = clean_text(value).upper()
    if not text:
        return default
    if text in {"Y", "YES", "TRUE", "1", "ON"}:
        return True
    if text in {"N", "NO", "FALSE", "0", "OFF"}:
        return False
    if text in {"YES_AFTER_REVIEW", "YES_AFTER_PERMISSION_CHECK"}:
        return False
    return default


def parse_decimal_optional(value: Any) -> Decimal | None:
    text = clean_text(value)
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        raise ValueError(f"invalid decimal: {value}") from None


def validate_coordinates(latitude: Decimal | float | str | None, longitude: Decimal | float | str | None) -> tuple[bool, str | None]:
    if latitude is None and longitude is None:
        return True, None
    if latitude is None or longitude is None:
        return False, "latitude and longitude must be provided together"
    try:
        lat = Decimal(str(latitude))
        lng = Decimal(str(longitude))
    except InvalidOperation:
        return False, "latitude or longitude is not numeric"
    if not (Decimal("-90") <= lat <= Decimal("90")):
        return False, "latitude out of range"
    if not (Decimal("-180") <= lng <= Decimal("180")):
        return False, "longitude out of range"
    return True, None


def parse_lat_lng(latitude_value: Any, longitude_value: Any) -> CoordinateParseResult:
    try:
        latitude = parse_decimal_optional(latitude_value)
        longitude = parse_decimal_optional(longitude_value)
    except ValueError as exc:
        return CoordinateParseResult(None, None, False, str(exc))
    valid, error = validate_coordinates(latitude, longitude)
    return CoordinateParseResult(latitude, longitude, valid, error)
