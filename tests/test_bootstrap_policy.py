from __future__ import annotations

import unittest

from scripts.bootstrap.normalize_public_data_sample import (
    SMBA_SOURCE,
    load_category_mappings,
    load_source_registry,
    map_category,
)
from scripts.bootstrap.validate_research_package import DEFAULT_BOOTSTRAP_DIR, validate


MOIS_GENERAL_FOOD_SOURCE = "행정안전부_식품_일반음식점 조회서비스"
MOIS_DANRAN_SOURCE = "행정안전부_식품_단란주점영업 조회서비스"
MOIS_ADULT_NIGHTLIFE_SOURCE = "행정안전부_식품_유흥주점영업 조회서비스"
PUBLIC_PARK_SOURCE = "전국도시공원정보표준데이터"
KAKAO_SOURCE = "Kakao Local API"


class BootstrapPolicyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source_registry = load_source_registry(DEFAULT_BOOTSTRAP_DIR)

    def test_research_package_is_valid(self) -> None:
        report = validate(DEFAULT_BOOTSTRAP_DIR)
        self.assertTrue(report["ok"], report["errors"])

    def test_kakao_stays_realtime_only_and_out_of_category_mapping(self) -> None:
        kakao = self.source_registry[KAKAO_SOURCE]
        self.assertEqual(kakao["storage_policy"], "realtime_only")
        self.assertEqual(kakao["default_target"], "realtime_lookup")
        self.assertEqual(kakao["canonical_use_allowed"], "false")
        self.assertEqual(load_category_mappings(DEFAULT_BOOTSTRAP_DIR, KAKAO_SOURCE), [])

    def test_unknown_park_source_stays_needs_review(self) -> None:
        park = self.source_registry[PUBLIC_PARK_SOURCE]
        self.assertEqual(park["storage_policy"], "unknown_needs_review")
        self.assertEqual(park["default_target"], "needs_review")

        mapping = map_category(
            "근린공원",
            load_category_mappings(DEFAULT_BOOTSTRAP_DIR, PUBLIC_PARK_SOURCE),
        )
        self.assertEqual(mapping["candidate_place_type"], "needs_review")
        self.assertEqual(mapping["mapping_confidence"], "none")
        self.assertTrue(mapping["mapping_review_required"])

    def test_restricted_adult_sources_stay_excluded(self) -> None:
        for source_name in (MOIS_DANRAN_SOURCE, MOIS_ADULT_NIGHTLIFE_SOURCE):
            source = self.source_registry[source_name]
            self.assertEqual(source["storage_policy"], "restricted")
            self.assertEqual(source["default_target"], "excluded")
            self.assertEqual(source["canonical_use_allowed"], "false")

            mapping = map_category(
                "any",
                load_category_mappings(DEFAULT_BOOTSTRAP_DIR, source_name),
            )
            self.assertEqual(mapping["candidate_place_type"], "excluded")
            self.assertEqual(mapping["mapping_confidence"], "high")
            self.assertTrue(mapping["mapping_review_required"])

    def test_ambiguous_alcohol_categories_do_not_auto_map_to_pub_or_bar(self) -> None:
        cases = [
            (SMBA_SOURCE, "맥주/호프"),
            (SMBA_SOURCE, "요리 주점"),
            (SMBA_SOURCE, "생맥주 전문"),
            (MOIS_GENERAL_FOOD_SOURCE, "호프/통닭"),
            (MOIS_GENERAL_FOOD_SOURCE, "바"),
        ]

        for source_name, category in cases:
            with self.subTest(source_name=source_name, category=category):
                mapping = map_category(
                    category,
                    load_category_mappings(DEFAULT_BOOTSTRAP_DIR, source_name),
                )
                self.assertEqual(mapping["candidate_place_type"], "needs_review")
                self.assertNotIn(mapping["candidate_place_type"], {"pub", "bar"})
                self.assertTrue(mapping["mapping_review_required"])

    def test_observed_smba_i2_food_categories_are_candidate_only(self) -> None:
        mappings = load_category_mappings(DEFAULT_BOOTSTRAP_DIR, SMBA_SOURCE)

        restaurant = map_category("백반/한정식", mappings)
        self.assertEqual(restaurant["candidate_place_type"], "restaurant")
        self.assertEqual(restaurant["mapping_confidence"], "medium")
        self.assertTrue(restaurant["mapping_review_required"])

        cafe = map_category("카페", mappings)
        self.assertEqual(cafe["candidate_place_type"], "other")
        self.assertEqual(cafe["mapping_confidence"], "low")
        self.assertTrue(cafe["mapping_review_required"])

        adult_nightlife = map_category("일반 유흥 주점", mappings)
        self.assertEqual(adult_nightlife["candidate_place_type"], "excluded")
        self.assertTrue(adult_nightlife["mapping_review_required"])


if __name__ == "__main__":
    unittest.main()
