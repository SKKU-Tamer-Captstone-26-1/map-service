# Codex Task: Build Safe Import Scripts for Map/Place Data

Build scripts that can import the provided templates into staging.

## Hard Rules

- Default mode is dry-run.
- Staging only.
- No Kakao calls.
- No direct publish.
- No destructive DB commands.

## Required scripts

Create or update scripts for:

```text
operator_place_seed_template.csv
seoul_hangang_outdoor_spot_seed_candidates.csv
owner_menu_items_template.csv
owner_inventory_items_template.csv
owner_price_offers_template.csv
```

## Validation

Use `data/data_quality_rules.csv`.

## Category mapping

Use `data/category_mapping_seed.csv`.

## Final response

Korean. Include verification and exact commands to run.
