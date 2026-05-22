from __future__ import annotations

import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from scripts.map_place_ingestion.category_mapping import load_category_mapping, map_category_to_place_type
from scripts.map_place_ingestion.cli_common import load_source_registry
from scripts.map_place_ingestion.dedupe import calculate_dedupe_score
from scripts.map_place_ingestion.import_outdoor_spot_candidates import build_candidates as build_outdoor_candidates
from scripts.map_place_ingestion.import_source_registry import build_source_records
from scripts.map_place_ingestion.normalize import parse_lat_lng, validate_source_policy
from scripts.map_place_ingestion.quality_rules import evaluate_inventory_freshness, evaluate_price_validity


BOOTSTRAP_ROOT = Path(__file__).resolve().parents[1] / "map_place_data_bootstrap_v0_3"


class MapPlaceIngestionTests(unittest.TestCase):
    def test_kakao_storable_source_policy_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_source_policy("KAKAO", "STORABLE")

    def test_source_registry_builder_rejects_kakao_storable(self) -> None:
        rows = [
            {
                "source_code": "KAKAO_BAD",
                "source_name_ko": "Kakao Bad",
                "source_type": "KAKAO",
                "source_policy": "STORABLE",
            }
        ]
        records, errors = build_source_records(rows, Path("source_registry.csv"))
        self.assertEqual(records, [])
        self.assertTrue(any("Kakao" in error for error in errors))

    def test_category_mapping_maps_clear_liquor_and_outdoor_categories(self) -> None:
        rules = load_category_mapping(BOOTSTRAP_ROOT / "data/category_mapping_seed.csv")
        liquor = map_category_to_place_type(["와인샵"], rules)
        outdoor = map_category_to_place_type(["한강공원"], rules)
        self.assertEqual(liquor.place_type, "BOTTLE_SHOP")
        self.assertEqual(outdoor.place_type, "OUTDOOR_SPOT")

    def test_ambiguous_category_needs_review(self) -> None:
        rules = load_category_mapping(BOOTSTRAP_ROOT / "data/category_mapping_seed.csv")
        result = map_category_to_place_type(["일반음식점"], rules)
        self.assertTrue(result.needs_review)
        self.assertEqual(result.action, "needs_review")

    def test_invalid_coordinates_are_rejected(self) -> None:
        parsed = parse_lat_lng("91", "127")
        self.assertFalse(parsed.valid)
        self.assertIn("latitude", parsed.error or "")

    def test_missing_outdoor_coordinates_require_geocode_review(self) -> None:
        rows = [
            {
                "external_source_id": "HANGANG_TEST",
                "source_code": "HANGANG_OFFICIAL_PARK_PAGE",
                "candidate_place_type": "outdoor_spot",
                "canonical_name": "테스트한강공원",
                "normalized_name": "",
                "address": "서울시 테스트구",
                "road_address": "",
                "lat": "",
                "lng": "",
                "geocode_required": "",
                "review_status": "needs_review",
            }
        ]
        registry = load_source_registry(BOOTSTRAP_ROOT / "data/source_registry.csv")
        candidates, errors, warnings = build_outdoor_candidates(rows, registry, BOOTSTRAP_ROOT / "data/seoul_hangang_outdoor_spot_seed_candidates.csv")
        self.assertEqual(errors, [])
        self.assertTrue(candidates[0].metadata["geocode_required"])
        self.assertTrue(any("geocode_required" in warning for warning in warnings))

    def test_dedupe_score_is_deterministic(self) -> None:
        candidate = {
            "canonical_name": "Example Bar",
            "road_address": "Seoul Gangnam",
            "latitude": Decimal("37.5000"),
            "longitude": Decimal("127.0000"),
            "phone": "02-123-4567",
        }
        existing = dict(candidate)
        self.assertEqual(calculate_dedupe_score(candidate, existing), calculate_dedupe_score(candidate, existing))
        self.assertEqual(calculate_dedupe_score(candidate, existing), 1.0)

    def test_stale_inventory_rule(self) -> None:
        findings = evaluate_inventory_freshness(
            {"last_seen_at": "2026-01-01T00:00:00+00:00"},
            now=datetime(2026, 5, 22, tzinfo=timezone.utc),
        )
        self.assertTrue(any(finding.rule_code == "OUTDATED_INVENTORY" for finding in findings))

    def test_expired_price_offer_rule(self) -> None:
        findings = evaluate_price_validity(
            {"valid_until": "2026-01-01T00:00:00+00:00"},
            now=datetime(2026, 5, 22, tzinfo=timezone.utc),
        )
        self.assertTrue(any(finding.rule_code == "EXPIRED_PRICE_OFFER" for finding in findings))


if __name__ == "__main__":
    unittest.main()
