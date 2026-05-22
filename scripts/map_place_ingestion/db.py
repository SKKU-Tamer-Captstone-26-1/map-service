from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator


class DatabaseUnavailable(RuntimeError):
    pass


def resolve_database_url(explicit_url: str | None) -> str:
    database_url = explicit_url or os.environ.get("DATABASE_URL") or os.environ.get("MAP_SERVICE_DATABASE_URL")
    if not database_url:
        raise DatabaseUnavailable("--database-url, DATABASE_URL, or MAP_SERVICE_DATABASE_URL is required with --apply")
    return database_url


@contextmanager
def connect(explicit_url: str | None) -> Iterator[Any]:
    database_url = resolve_database_url(explicit_url)
    try:
        import psycopg
    except ImportError:
        psycopg = None
    if psycopg is not None:
        with psycopg.connect(database_url) as connection:
            yield connection
        return

    try:
        import psycopg2
    except ImportError as exc:
        raise DatabaseUnavailable("Install psycopg or psycopg2 to use --apply DB writes") from exc
    connection = psycopg2.connect(database_url)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def fetch_source_by_code(cursor: Any, source_code: str) -> tuple[str, str, str]:
    cursor.execute(
        """
        SELECT id::text, source_type::text, source_policy::text
        FROM data_sources
        WHERE metadata_json->>'source_code' = %s
        LIMIT 1
        """,
        (source_code,),
    )
    row = cursor.fetchone()
    if not row:
        raise DatabaseUnavailable(f"data_sources row not found for source_code={source_code}; run import_source_registry.py first")
    return row[0], row[1], row[2]

