from __future__ import annotations

import math
from decimal import Decimal
from difflib import SequenceMatcher
from typing import Any

from scripts.map_place_ingestion.normalize import normalize_address, normalize_phone_optional, normalize_place_name


def _similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    return SequenceMatcher(None, left, right).ratio()


def haversine_meters(lat1: Any, lng1: Any, lat2: Any, lng2: Any) -> float | None:
    if None in {lat1, lng1, lat2, lng2}:
        return None
    try:
        lat1_f = float(Decimal(str(lat1)))
        lng1_f = float(Decimal(str(lng1)))
        lat2_f = float(Decimal(str(lat2)))
        lng2_f = float(Decimal(str(lng2)))
    except Exception:
        return None
    earth_radius_m = 6371000.0
    phi1 = math.radians(lat1_f)
    phi2 = math.radians(lat2_f)
    delta_phi = math.radians(lat2_f - lat1_f)
    delta_lambda = math.radians(lng2_f - lng1_f)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return earth_radius_m * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def calculate_dedupe_score(candidate: dict[str, Any], existing: dict[str, Any]) -> float:
    candidate_external = candidate.get("external_source_id") or candidate.get("source_external_id")
    existing_external = existing.get("external_source_id") or existing.get("source_external_id")
    if candidate_external and existing_external and str(candidate_external) == str(existing_external):
        return 1.0

    name_score = _similarity(
        normalize_place_name(candidate.get("normalized_name") or candidate.get("name") or candidate.get("canonical_name")),
        normalize_place_name(existing.get("normalized_name") or existing.get("name") or existing.get("canonical_name")),
    )
    address_score = _similarity(
        normalize_address(candidate.get("normalized_address") or candidate.get("address") or candidate.get("road_address")),
        normalize_address(existing.get("normalized_address") or existing.get("address") or existing.get("road_address")),
    )
    phone_score = 0.0
    candidate_phone = normalize_phone_optional(candidate.get("phone"))
    existing_phone = normalize_phone_optional(existing.get("phone"))
    if candidate_phone and existing_phone:
        phone_score = 1.0 if candidate_phone == existing_phone else 0.0

    distance = haversine_meters(candidate.get("latitude"), candidate.get("longitude"), existing.get("latitude"), existing.get("longitude"))
    if distance is None:
        coordinate_score = 0.0
    elif distance <= 30:
        coordinate_score = 1.0
    elif distance <= 100:
        coordinate_score = 0.85
    elif distance <= 250:
        coordinate_score = 0.55
    else:
        coordinate_score = 0.0

    score = (name_score * 0.35) + (address_score * 0.25) + (coordinate_score * 0.25) + (phone_score * 0.15)
    return round(min(1.0, max(0.0, score)), 3)

