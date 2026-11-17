from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Connection


def try_acquire_lock(
    connection: Connection,
    data_source_id: UUID,
) -> bool:
    result = connection.execute(
        text("""
            SELECT pg_try_advisory_lock(
                hashtextextended(CAST(:data_source_id AS text), 0)
            )
        """),
        {"data_source_id": str(data_source_id)},
    )
    return result.scalar_one()


def release_lock(
    connection: Connection,
    data_source_id: UUID,
) -> None:
    connection.execute(
        text("""
            SELECT pg_advisory_unlock(
                hashtextextended(CAST(:data_source_id AS text), 0)
            )
        """),
        {"data_source_id": str(data_source_id)},
    )
