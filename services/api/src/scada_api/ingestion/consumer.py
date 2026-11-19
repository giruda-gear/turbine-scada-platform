import json
import logging
from datetime import UTC, datetime
from uuid import UUID

from confluent_kafka import Consumer, KafkaException
from sqlalchemy.orm import Session, sessionmaker

from scada_api.core.config import settings
from scada_api.core.logging import setup_logging
from scada_api.ingestion.constants import RAW_READINGS_TOPIC
from scada_api.ingestion.enums import IngestionRunStatus
from scada_api.ingestion.normalizer import normalize_payload
from scada_api.ingestion.service import (
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


def process_message(
    message: dict,
    session_factory: sessionmaker[Session],
) -> None:
    ingestion_run_id = message["ingestion_run_id"]
    data_source_id = UUID(message["data_source_id"])
    provider = message["provider"]
    payload = message["payload"]

    now = datetime.now(UTC)

    with session_factory() as session, session.begin():
        update_ingestion_run(
            session=session,
            ingestion_run_id=ingestion_run_id,
            status=IngestionRunStatus.PROCESSING,
        )

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

            update_ingestion_run(
                session=session,
                ingestion_run_id=ingestion_run_id,
                status=IngestionRunStatus.SUCCESS,
                completed_at=now,
                received_count=len(payload["readings"]),
                inserted_count=result.inserted,
                updated_count=result.updated,
                unchanged_count=result.unchanged,
                rejected_count=len(payload["readings"]) - len(readings),
                error_message=None,
            )

    except Exception as exc:
        # Mark failure in a separate transaction.
        with session_factory() as session, session.begin():
            update_ingestion_run(
                session=session,
                ingestion_run_id=ingestion_run_id,
                status=IngestionRunStatus.FAILED,
                completed_at=datetime.now(UTC),
                error_message=str(exc),
            )

        raise

    logger.info(
        "Ingestion run processed: id=%s inserted=%s updated=%s unchanged=%s rejected=%s",
        ingestion_run_id,
        result.inserted,
        result.updated,
        result.unchanged,
        len(payload["readings"]) - len(readings),
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
                logger.error("Received Kafka message with null value")
                continue

            message = json.loads(raw_value.decode("utf-8"))

            process_message(
                message=message,
                session_factory=session_factory,
            )

            # commit only after the database transaction succeeds.
            consumer.commit(
                message=msg,
                asynchronous=False,
            )

    except KeyboardInterrupt:
        logger.info("Consumer stopped")

    finally:
        consumer.close()


if __name__ == "__main__":
    from scada_api.core.database import SessionLocal

    consume_messages(session_factory=SessionLocal)
