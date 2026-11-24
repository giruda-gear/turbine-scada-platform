import logging
from datetime import UTC, datetime
from uuid import UUID

import httpx
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from scada_api.core.logging import setup_logging
from scada_api.data_sources.service import get_data_source
from scada_api.ingestion.client import fetch_readings
from scada_api.ingestion.enums import IngestionRunStatus
from scada_api.ingestion.locking import release_lock, try_acquire_lock
from scada_api.ingestion.producer import publish_raw_readings
from scada_api.ingestion.service import (
    calculate_polling_window,
    create_ingestion_run,
    get_checkpoint,
    record_polling_failure,
    update_checkpoint,
    update_ingestion_run,
)

setup_logging()
logger = logging.getLogger(__name__)

"""
Poller:   RUNNING → PUBLISHED   (Kafka publish after DB commit)
          RUNNING/PUBLISHED → FAILED (polling or publish failure)
Consumer: PUBLISHED → PROCESSING → SUCCESS
                                  ↘ FAILED

The checkpoint advances only after a successful publish.
"""


def run_polling(
    client: httpx.Client,
    data_source_id: UUID,
    session_factory: sessionmaker[Session],
    now: datetime | None = None,
) -> int:
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
        return 0

    start_at, end_at = window
    attempted_at = now

    with session_factory() as session, session.begin():
        ingestion_run = create_ingestion_run(
            session=session,
            data_source_id=data_source_id,
            window_start=start_at,
            window_end=end_at,
            started_at=attempted_at,
        )
        session.flush()
        ingestion_run_id = ingestion_run.id

    try:
        payload = fetch_readings(
            endpoint_url=endpoint_url,
            start_at=start_at,
            end_at=end_at,
            client=client,
        )
        received_count = len(payload["readings"])

        with session_factory() as session, session.begin():
            updated = update_ingestion_run(
                session=session,
                ingestion_run_id=ingestion_run_id,
                expected_status=IngestionRunStatus.RUNNING,
                status=IngestionRunStatus.PUBLISHED,
                completed_at=datetime.now(UTC),
                received_count=received_count,
            )
            if not updated:
                raise RuntimeError(
                    f"Ingestion run {ingestion_run_id} could not transition "
                    "from RUNNING to PUBLISHED"
                )
        logger.info("Ingestion run %s: PUBLISHED committed", ingestion_run_id)

        publish_raw_readings(
            ingestion_run_id=ingestion_run_id,
            data_source_id=data_source_id,
            provider=provider,
            window_start=start_at,
            window_end=end_at,
            payload=payload,
        )
        logger.info("Ingestion run %s: published to Kafka", ingestion_run_id)

        with session_factory() as session, session.begin():
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

        return received_count

    except Exception as exc:
        logger.exception("Polling failed for ingestion run %s", ingestion_run_id)
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
                expected_status=(
                    IngestionRunStatus.RUNNING,
                    IngestionRunStatus.PUBLISHED,
                ),
                status=IngestionRunStatus.FAILED,
                completed_at=datetime.now(UTC),
                error_message=str(exc),
            )

        raise


def run_polling_with_lock(
    client: httpx.Client,
    data_source_id: UUID,
    session_factory: sessionmaker[Session],
    engine: Engine,
    now: datetime | None = None,
) -> int | None:
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
