import json
import logging
import time
from datetime import UTC, datetime
from uuid import UUID

from confluent_kafka import Consumer, KafkaException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, InterfaceError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from scada_api.core.config import settings
from scada_api.core.logging import setup_logging
from scada_api.ingestion.constants import (
    MAX_RETRIES,
    RAW_READINGS_TOPIC,
    RETRY_DELAY_SECONDS,
)
from scada_api.ingestion.enums import IngestionRunStatus
from scada_api.ingestion.exceptions import (
    PermanentProcessingError,
    TransientProcessingError,
)
from scada_api.ingestion.normalizer import normalize_payload
from scada_api.ingestion.service import (
    get_ingestion_run_status,
    save_readings,
    update_ingestion_run,
)

setup_logging()
logger = logging.getLogger(__name__)


def create_consumer() -> Consumer:
    return Consumer(
        {
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "group.id": "scada-normalizer",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )


def _claim_ingestion_run(
    ingestion_run_id: int,
    session_factory: sessionmaker[Session],
) -> bool:
    """
    Attempt the PUBLISHED -> PROCESSING transition.
    Returns:
        True  : proceed with processing
        False : the run is already finished (duplicate message), so skip
    Raises:
        TransientProcessingError: the run is not PUBLISHED yet; retry later
    """
    with session_factory() as session, session.begin():
        updated = update_ingestion_run(
            session=session,
            ingestion_run_id=ingestion_run_id,
            expected_status=IngestionRunStatus.PUBLISHED,
            status=IngestionRunStatus.PROCESSING,
        )
        if updated:
            logger.info("Ingestion run %s: PROCESSING", ingestion_run_id)
            return True

        current = get_ingestion_run_status(session, ingestion_run_id)

    if current in (IngestionRunStatus.SUCCESS, IngestionRunStatus.FAILED):
        logger.info(
            "Ingestion run %s already %s, skipping duplicate message",
            ingestion_run_id,
            current,
        )
        return False

    if current == IngestionRunStatus.PROCESSING:
        # Redelivery after the consumer crashed mid-processing.
        # Safe to reprocess because saves are upserts.
        logger.warning(
            "Ingestion run %s already PROCESSING, reprocessing",
            ingestion_run_id,
        )
        return True

    raise TransientProcessingError(
        f"Ingestion run {ingestion_run_id} is not ready for processing "
        f"(status={current})"
    )


def process_message(
    message: dict,
    session_factory: sessionmaker[Session],
) -> None:
    ingestion_run_id = int(message["ingestion_run_id"])
    data_source_id = UUID(message["data_source_id"])
    provider = message["provider"]
    payload = message["payload"]

    logger.info("Consumer received ingestion run %s", ingestion_run_id)

    if not _claim_ingestion_run(ingestion_run_id, session_factory):
        return

    try:
        with session_factory() as session, session.begin():
            readings = normalize_payload(
                session=session,
                data_source_id=data_source_id,
                provider=provider,
                payload=payload,
                ingestion_run_id=ingestion_run_id,
            )

            result = save_readings(
                session=session,
                readings=readings,
            )

            received = len(payload["readings"])
            rejected = received - len(readings)

            updated = update_ingestion_run(
                session=session,
                ingestion_run_id=ingestion_run_id,
                expected_status=IngestionRunStatus.PROCESSING,
                status=IngestionRunStatus.SUCCESS,
                completed_at=datetime.now(UTC),
                received_count=received,
                inserted_count=result.inserted,
                updated_count=result.updated,
                unchanged_count=result.unchanged,
                rejected_count=rejected,
            )
            if not updated:
                raise PermanentProcessingError(
                    f"Ingestion run {ingestion_run_id} "
                    "could not transition from PROCESSING to SUCCESS"
                )

    except (OperationalError, InterfaceError) as exc:
        raise TransientProcessingError(f"Database connection error: {exc}") from exc

    except (
        IntegrityError,
        ValidationError,
        KeyError,
        ValueError,
    ) as exc:
        error = PermanentProcessingError(f"Invalid ingestion data: {exc}")

        with session_factory() as session, session.begin():
            update_ingestion_run(
                session=session,
                ingestion_run_id=ingestion_run_id,
                expected_status=IngestionRunStatus.PROCESSING,
                status=IngestionRunStatus.FAILED,
                completed_at=datetime.now(UTC),
                error_message=str(error),
            )

        raise error from exc

    logger.info(
        "Ingestion run processed: id=%s inserted=%s updated=%s unchanged=%s rejected=%s",
        ingestion_run_id,
        result.inserted,
        result.updated,
        result.unchanged,
        rejected,
    )


def consume_messages(
    session_factory: sessionmaker[Session],
) -> None:
    consumer = create_consumer()

    consumer.subscribe([RAW_READINGS_TOPIC])

    logger.info("Subscribed to topic: %s", RAW_READINGS_TOPIC)

    try:
        while True:
            msg = consumer.poll(timeout=1.0)

            if msg is None:
                continue

            if msg.error():
                raise KafkaException(msg.error())

            raw_value = msg.value()
            if raw_value is None:
                logger.error(
                    "Received Kafka message with null value: partition=%s offset=%s",
                    msg.partition(),
                    msg.offset(),
                )
                consumer.commit(message=msg, asynchronous=False)
                continue

            message = json.loads(raw_value.decode("utf-8"))

            try:
                for attempt in range(MAX_RETRIES + 1):
                    try:
                        process_message(
                            message=message, session_factory=session_factory
                        )
                        break
                    except PermanentProcessingError:
                        raise
                    except TransientProcessingError as exc:
                        if attempt == MAX_RETRIES:
                            raise

                        logger.warning(
                            "Transient error processing message. Retry %s/%s: %s",
                            attempt + 1,
                            MAX_RETRIES,
                            exc,
                        )
                        time.sleep(RETRY_DELAY_SECONDS)

                # commit only after the database transaction succeeds.
                consumer.commit(message=msg, asynchronous=False)

            except PermanentProcessingError:
                logger.exception("Permanent processing failure")
                # Message is handled as failed; commit to avoid endless redelivery.
                consumer.commit(message=msg, asynchronous=False)

            except Exception:
                logger.exception(
                    "Failed to process Kafka message: topic=%s partition=%s offset=%s",
                    msg.topic(),
                    msg.partition(),
                    msg.offset(),
                )
                raise

    except KeyboardInterrupt:
        logger.info("Consumer stopped")

    finally:
        consumer.close()


if __name__ == "__main__":
    from scada_api.core.database import SessionLocal

    consume_messages(session_factory=SessionLocal)
