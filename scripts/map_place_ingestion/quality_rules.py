from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.map_place_ingestion.cli_common import read_csv_rows
from scripts.map_place_ingestion.normalize import clean_text, normalize_source_policy, normalize_source_type, parse_lat_lng


DECISION_ORDER = {
    "accept_candidate": 0,
    "needs_review": 1,
    "defer": 2,
    "reject_candidate": 3,
}


@dataclass(frozen=True)
class QualityRule:
    rule_code: str
    description: str
    severity: str
    result: str
    target: str


@dataclass(frozen=True)
class QualityFinding:
    rule_code: str
    decision: str
    message: str
    severity: str = "MEDIUM"


def load_quality_rules(path: Path) -> dict[str, QualityRule]:
    rows = read_csv_rows(path)
    rules: dict[str, QualityRule] = {}
    for row in rows:
        rule_code = clean_text(row.get("rule_code"))
        if not rule_code:
            continue
        rules[rule_code] = QualityRule(
            rule_code=rule_code,
            description=clean_text(row.get("description")),
            severity=clean_text(row.get("severity")).upper() or "MEDIUM",
            result=clean_text(row.get("result")),
            target=clean_text(row.get("target")),
        )
    return rules


def _finding(rule_code: str, decision: str, message: str, rules: dict[str, QualityRule] | None = None) -> QualityFinding:
    severity = rules.get(rule_code).severity if rules and rule_code in rules else "MEDIUM"
    return QualityFinding(rule_code, decision, message, severity)


def final_decision(findings: list[QualityFinding]) -> str:
    if not findings:
        return "accept_candidate"
    return max((finding.decision for finding in findings), key=lambda value: DECISION_ORDER[value])


def evaluate_place_candidate(
    row: dict[str, Any],
    *,
    source_type: str,
    source_policy: str,
    rules: dict[str, QualityRule] | None = None,
    seen_external_ids: set[str] | None = None,
    persist_canonical: bool = False,
) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    name = clean_text(row.get("canonical_name") or row.get("상호명") or row.get("BPLCNM"))
    address = clean_text(row.get("road_address") or row.get("address") or row.get("도로명주소") or row.get("지번주소") or row.get("RDNWHLADDR") or row.get("SITEWHLADDR"))
    lat_value = row.get("lat") or row.get("위도")
    lng_value = row.get("lng") or row.get("경도")
    coords = parse_lat_lng(lat_value, lng_value)

    if not name:
        findings.append(_finding("MISSING_NAME", "reject_candidate", "name is required", rules))
    if not address and coords.latitude is None and coords.longitude is None:
        findings.append(_finding("MISSING_ADDRESS_AND_COORDS", "reject_candidate", "address or coordinates are required", rules))
    elif address and coords.latitude is None and coords.longitude is None:
        findings.append(_finding("MISSING_COORDS", "needs_review", "coordinates are missing; geocode review required", rules))
    if not coords.valid:
        findings.append(_finding("INVALID_LAT_LNG", "reject_candidate", coords.error or "invalid coordinates", rules))

    normalized_source_type = normalize_source_type(source_type)
    normalized_policy = normalize_source_policy(source_policy)
    if normalized_policy in {"REALTIME_ONLY", "RESTRICTED"} and persist_canonical:
        findings.append(_finding("RESTRICTED_SOURCE_POLICY", "reject_candidate", "restricted/realtime source cannot be persisted canonically", rules))
    if normalized_source_type == "KAKAO":
        if normalized_policy == "STORABLE" or persist_canonical:
            findings.append(_finding("KAKAO_PERSISTENCE_ATTEMPT", "reject_candidate", "Kakao data cannot be canonical bulk-ingested", rules))

    external_id = clean_text(row.get("external_source_id") or row.get("상가업소번호") or row.get("MGTNO"))
    if seen_external_ids is not None and external_id:
        if external_id in seen_external_ids:
            findings.append(_finding("DUP_SOURCE_EXTERNAL_ID", "needs_review", "duplicate source external id in this import", rules))
        seen_external_ids.add(external_id)

    place_type = clean_text(row.get("candidate_place_type"))
    if not place_type or place_type.lower() == "other":
        findings.append(_finding("AMBIGUOUS_BUSINESS_TYPE", "needs_review", "place type is missing or ambiguous", rules))

    status_text = clean_text(row.get("TRDSTATENM") or row.get("DTLSTATENM") or row.get("business_status"))
    if any(token in status_text for token in ("폐업", "말소", "취소", "폐쇄")):
        findings.append(_finding("CLOSED_LICENSE_STATUS", "needs_review", "closed status must create review, not direct closure", rules))

    return findings


def evaluate_inventory_freshness(row: dict[str, Any], *, now: datetime | None = None, max_age_days: int = 30) -> list[QualityFinding]:
    now = now or datetime.now(timezone.utc)
    findings: list[QualityFinding] = []
    expires_at = _parse_datetime(row.get("expires_at"))
    last_seen_at = _parse_datetime(row.get("last_seen_at"))
    if expires_at and expires_at < now:
        findings.append(QualityFinding("OUTDATED_INVENTORY", "needs_review", "inventory expires_at is in the past"))
    elif last_seen_at and (now - last_seen_at).days > max_age_days:
        findings.append(QualityFinding("OUTDATED_INVENTORY", "needs_review", "inventory last_seen_at is stale"))
    elif not expires_at and not last_seen_at:
        findings.append(QualityFinding("OUTDATED_INVENTORY", "needs_review", "inventory needs last_seen_at or expires_at"))
    return findings


def evaluate_price_validity(row: dict[str, Any], *, now: datetime | None = None) -> list[QualityFinding]:
    now = now or datetime.now(timezone.utc)
    valid_until = _parse_datetime(row.get("valid_until"))
    if valid_until and valid_until < now:
        return [QualityFinding("EXPIRED_PRICE_OFFER", "reject_candidate", "price offer valid_until is in the past")]
    return []


def _parse_datetime(value: Any) -> datetime | None:
    text = clean_text(value)
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        try:
            parsed = datetime.fromisoformat(normalized + "T00:00:00+00:00")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)

