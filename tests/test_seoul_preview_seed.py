from __future__ import annotations

import unittest

from scripts.db.seed_seoul_preview_markers_from_smba import (
    CATEGORY_RULES_BY_CODE,
    PREVIEW_SOURCE,
    build_marker,
    skip_reason,
)


class SeoulPreviewSeedTest(unittest.TestCase):
    def test_build_marker_marks_smba_pub_as_non_canonical_preview(self) -> None:
        row = {
            "bizesId": "MA010120220805430528",
            "bizesNm": "테스트 생맥주",
            "lon": "126.9229",
            "lat": "37.5563",
            "indsLclsCd": "I2",
            "indsLclsNm": "음식",
            "indsMclsCd": "I211",
            "indsMclsNm": "주점",
            "indsSclsCd": "I21103",
            "indsSclsNm": "생맥주 전문",
            "rdnmAdr": "서울특별시 마포구 테스트로 1",
            "signguNm": "마포구",
        }

        marker = build_marker(row, CATEGORY_RULES_BY_CODE["I21103"], fetched_at="2026-05-23T00:00:00+00:00")

        self.assertIsNotNone(marker)
        assert marker is not None
        self.assertEqual(marker["layer_code"], "pub")
        self.assertEqual(marker["label"], "테스트 생맥주")
        self.assertEqual(marker["filter_json"]["source"], PREVIEW_SOURCE)
        self.assertFalse(marker["filter_json"]["canonical"])
        self.assertTrue(marker["filter_json"]["preview_only"])
        self.assertTrue(marker["filter_json"]["review_required"])

    def test_excludes_adult_nightlife_tokens(self) -> None:
        row = {
            "bizesId": "adult-1",
            "bizesNm": "제외 샘플",
            "lon": "126.9229",
            "lat": "37.5563",
            "indsSclsCd": "I21103",
            "indsSclsNm": "일반 유흥 주점",
        }

        self.assertEqual(skip_reason(row, CATEGORY_RULES_BY_CODE["I21103"]), "excluded_adult_nightlife")
        self.assertIsNone(build_marker(row, CATEGORY_RULES_BY_CODE["I21103"], fetched_at="2026-05-23T00:00:00+00:00"))

    def test_skips_rows_outside_seoul_bbox(self) -> None:
        row = {
            "bizesId": "outside-1",
            "bizesNm": "부산 샘플",
            "lon": "129.0756",
            "lat": "35.1796",
            "indsSclsCd": "G20602",
            "indsSclsNm": "주류 소매업",
        }

        self.assertEqual(skip_reason(row, CATEGORY_RULES_BY_CODE["G20602"]), "outside_seoul_bbox")


if __name__ == "__main__":
    unittest.main()
