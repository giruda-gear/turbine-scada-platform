import logging
from datetime import UTC, datetime
from uuid import UUID

import httpx
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from scada_api.data_sources.service import get_data_source
from scada_api.ingestion.client import fetch_readings
from scada_api.ingestion.enums import IngestionRunStatus
from scada_api.ingestion.locking import release_lock, try_acquire_lock
from scada_api.ingestion.normalizer import normalize_payload
from scada_api.ingestion.service import (
    SaveResult,
    calculate_polling_window,
    create_ingestion_run,
    get_checkpoint,
    record_polling_failure,
    save_readings,
    update_checkpoint,
    update_ingestion_run,
)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

"""
* Initial transaction
Create and commit IngestionRun with status running.

* HTTP request
Fetch vendor payload outside the database transaction.

* Success transaction
Normalize → save rejected readings → save canonical readings → update checkpoint → update ingestion run → commit together.

* Failure transaction
Update checkpoint failure information and mark ingestion run failed → commit.
"""


def run_polling(
    client: httpx.Client,
    data_source_id: UUID,
    session_factory: sessionmaker[Session],
    now: datetime | None = None,
) -> SaveResult:
    now = now or datetime.now(UTC)

    with session_factory() as session:
        data_source = get_data_source(
            session=session,
            data_source_id=data_source_id,
        )
        checkpoint = get_checkpoint(
            session=session,
            data_source_id=data_source_id,
        )

        if data_source is None:
            raise ValueError(f"Data source not found: {data_source_id}")

        if data_source.protocol != "http":
            raise ValueError(f"Unsupported polling protocol: {data_source.protocol}")

        if not data_source.endpoint_url:
            raise ValueError("HTTP data source requires an endpoint_url")

        if checkpoint is None:
            raise ValueError(f"Checkpoint not found: {data_source_id}")

        endpoint_url = data_source.endpoint_url
        provider = data_source.provider

        window = calculate_polling_window(
            last_success_at=checkpoint.last_success_at,
            now=now,
        )

    if window is None:
        return SaveResult(
            inserted=0,
            updated=0,
            unchanged=0,
        )

    start_at, end_at = window
    attempted_at = now

    with session_factory() as session:
        ingestion_run = create_ingestion_run(
            session=session,
            data_source_id=data_source_id,
            window_start=start_at,
            window_end=end_at,
            started_at=attempted_at,
        )

        ingestion_run_id = ingestion_run.id

    try:
        payload = fetch_readings(
            endpoint_url=endpoint_url,
            start_at=start_at,
            end_at=end_at,
            client=client,
        )

        with session_factory() as session, session.begin():
            readings = normalize_payload(
                session=session,
                data_source_id=data_source_id,
                provider=provider,
                payload=payload,
                ingestion_run_id=ingestion_run_id,
            )

            saved_count = save_readings(
                session=session,
                readings=readings,
            )

            checkpoint = get_checkpoint(
                session=session,
                data_source_id=data_source_id,
            )

            if checkpoint is None:
                raise ValueError(f"Checkpoint not found: {data_source_id}")

            update_checkpoint(
                checkpoint=checkpoint,
                attempted_at=attempted_at,
                end_at=end_at,
            )

            update_ingestion_run(
                session=session,
                ingestion_run_id=ingestion_run_id,
                status=IngestionRunStatus.SUCCESS,
                completed_at=now,
                received_count=len(payload["readings"]),
                inserted_count=saved_count.inserted,
                updated_count=saved_count.updated,
                unchanged_count=saved_count.unchanged,
                rejected_count=len(payload["readings"]) - len(readings),
            )

        return saved_count

    except Exception as exc:
        with session_factory() as session, session.begin():
            checkpoint = get_checkpoint(
                session=session,
                data_source_id=data_source_id,
            )

            if checkpoint is not None:
                record_polling_failure(
                    checkpoint=checkpoint,
                    error=str(exc),
                    attempted_at=attempted_at,
                )

            update_ingestion_run(
                session=session,
                ingestion_run_id=ingestion_run_id,
                status=IngestionRunStatus.FAILED,
                completed_at=now,
                error_message=str(exc),
            )

        raise


def run_polling_with_lock(
    client: httpx.Client,
    data_source_id: UUID,
    session_factory: sessionmaker[Session],
    engine: Engine,
    now: datetime | None = None,
) -> SaveResult | None:
    with engine.connect() as connection:
        acquired = try_acquire_lock(connection, data_source_id)

        if not acquired:
            logger.info(
                "Skipping data source %s: already being polled",
                data_source_id,
            )
            return None

        try:
            logger.info("Worker acquired lock for %s", data_source_id)

            return run_polling(
                client=client,
                data_source_id=data_source_id,
                session_factory=session_factory,
                now=now,
            )
        finally:
            release_lock(connection, data_source_id)
            logger.info("Worker released lock for %s", data_source_id)


# if __name__ == "__main__":
#     poll_all_data_sources()
