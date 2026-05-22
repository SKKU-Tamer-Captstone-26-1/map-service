from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from scripts.map_place_ingestion.cli_common import read_csv_rows
from scripts.map_place_ingestion.normalize import clean_text, normalize_place_type


@dataclass(frozen=True)
class CategoryMappingRule:
    raw_keyword: str
    target_place_type: str
    confidence: Decimal
    default_action: str
    notes: str = ""


@dataclass(frozen=True)
class CategoryMappingResult:
    place_type: str
    confidence: Decimal
    action: str
    matched_keyword: str | None
    needs_review: bool
    notes: str = ""


def load_category_mapping(path: Path) -> list[CategoryMappingRule]:
    rows = read_csv_rows(path)
    rules: list[CategoryMappingRule] = []
    for row in rows:
        keyword = clean_text(row.get("raw_keyword"))
        if not keyword:
            continue
        rules.append(
            CategoryMappingRule(
                raw_keyword=keyword,
                target_place_type=normalize_place_type(row.get("target_place_type")),
                confidence=Decimal(clean_text(row.get("confidence")) or "0"),
                default_action=clean_text(row.get("default_action")).lower() or "needs_review",
                notes=clean_text(row.get("notes")),
            )
        )
    return sorted(rules, key=lambda rule: (rule.confidence, len(rule.raw_keyword)), reverse=True)


def map_category_to_place_type(values: list[Any], rules: list[CategoryMappingRule]) -> CategoryMappingResult:
    text = " ".join(clean_text(value).lower() for value in values if clean_text(value))
    for rule in rules:
        if rule.raw_keyword.lower() in text:
            action = rule.default_action
            return CategoryMappingResult(
                place_type=rule.target_place_type,
                confidence=rule.confidence,
                action=action,
                matched_keyword=rule.raw_keyword,
                needs_review=action != "accept_candidate" or rule.confidence < Decimal("0.80"),
                notes=rule.notes,
            )
    return CategoryMappingResult(
        place_type="OTHER",
        confidence=Decimal("0"),
        action="needs_review",
        matched_keyword=None,
        needs_review=True,
        notes="no mapping rule matched",
    )

