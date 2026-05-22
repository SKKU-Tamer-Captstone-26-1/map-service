from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from scripts.map_place_ingestion.cli_common import json_dumps
from scripts.map_place_ingestion.db import connect, fetch_source_by_code


@dataclass(frozen=True)
class CandidateInsert:
    source_code: str
    external_source_id: str
    raw_payload: dict[str, Any]
    normalized_name: str
    normalized_address: str
    source_category_name: str | None
    candidate_place_type: str
    latitude: Decimal | None
    longitude: Decimal | None
    review_status: str
    metadata: dict[str, Any]
    review_task_type: str = "VERIFY_NEW_PLACE"
    review_priority: int = 100


def apply_candidate_import(
    *,
    database_url: str | None,
    input_path: Path,
    source_code: str,
    import_type: str,
    candidates: list[CandidateInsert],
    batch_metadata: dict[str, Any],
) -> dict[str, Any]:
    if not candidates:
        return {"applied": False, "inserted_candidates": 0, "inserted_review_tasks": 0}

    with connect(database_url) as connection:
        with connection.cursor() as cursor:
            source_id, _source_type, source_policy = fetch_source_by_code(cursor, source_code)
            cursor.execute(
                """
                INSERT INTO place_import_batches (
                  source_id,
                  import_type,
                  file_name,
                  original_uri,
                  status,
                  completed_at,
                  row_count,
                  success_count,
                  error_count,
                  metadata_json
                )
                VALUES (%s, %s, %s, %s, 'COMPLETED', now(), %s, %s, 0, %s::jsonb)
                RETURNING id::text
                """,
                (
                    source_id,
                    import_type,
                    input_path.name,
                    str(input_path),
                    len(candidates),
                    len(candidates),
                    json_dumps(batch_metadata),
                ),
            )
            batch_id = cursor.fetchone()[0]

            inserted_candidates = 0
            inserted_review_tasks = 0
            for candidate in candidates:
                cursor.execute(
                    """
                    INSERT INTO place_import_candidates (
                      batch_id,
                      source_id,
                      external_source_id,
                      source_policy,
                      raw_payload_json,
                      normalized_name,
                      normalized_address,
                      source_category_name,
                      candidate_place_type,
                      location,
                      latitude,
                      longitude,
                      review_status,
                      metadata_json
                    )
                    VALUES (
                      %s,
                      %s,
                      %s,
                      %s,
                      %s::jsonb,
                      %s,
                      %s,
                      %s,
                      %s,
                      CASE
                        WHEN %s::numeric IS NULL OR %s::numeric IS NULL THEN NULL
                        ELSE ST_SetSRID(ST_MakePoint(%s::numeric, %s::numeric), 4326)::geography
                      END,
                      %s,
                      %s,
                      %s,
                      %s::jsonb
                    )
                    RETURNING id::text
                    """,
                    (
                        batch_id,
                        source_id,
                        candidate.external_source_id or None,
                        source_policy,
                        json_dumps(candidate.raw_payload),
                        candidate.normalized_name or None,
                        candidate.normalized_address or None,
                        candidate.source_category_name,
                        candidate.candidate_place_type,
                        candidate.latitude,
                        candidate.longitude,
                        candidate.longitude,
                        candidate.latitude,
                        candidate.latitude,
                        candidate.longitude,
                        candidate.review_status,
                        json_dumps(candidate.metadata),
                    ),
                )
                candidate_id = cursor.fetchone()[0]
                inserted_candidates += 1

                cursor.execute(
                    """
                    INSERT INTO place_review_tasks (
                      candidate_id,
                      task_type,
                      priority,
                      status,
                      resolution_json
                    )
                    VALUES (%s, %s, %s, 'PENDING', '{}'::jsonb)
                    """,
                    (candidate_id, candidate.review_task_type, candidate.review_priority),
                )
                inserted_review_tasks += 1

    return {
        "applied": True,
        "batch_source_code": source_code,
        "inserted_candidates": inserted_candidates,
        "inserted_review_tasks": inserted_review_tasks,
    }
