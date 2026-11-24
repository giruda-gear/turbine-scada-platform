import json
import logging
from datetime import datetime
from uuid import UUID

from confluent_kafka import Producer

from scada_api.core.config import settings
from scada_api.ingestion.constants import RAW_READINGS_TOPIC
from scada_api.main import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def publish_raw_readings(
    ingestion_run_id: int,
    data_source_id: UUID,
    provider: str,
    window_start: datetime,
    window_end: datetime,
    payload: dict,
) -> None:
    producer = Producer(
        {
            "bootstrap.servers": settings.kafka_bootstrap_servers,
        }
    )

    message = {
        "ingestion_run_id": ingestion_run_id,
        "data_source_id": str(data_source_id),
        "provider": provider,
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "payload": payload,
    }
    # the same key are normally routed to the same partition
    producer.produce(
        topic=RAW_READINGS_TOPIC,
        key=str(data_source_id),
        value=json.dumps(message),
        callback=delivery_report,
    )

    remaining = producer.flush(timeout=10)

    if remaining > 0:
        raise TimeoutError(
            f"{remaining} Kafka message(s) were not delivered within 10 seconds"
        )


def delivery_report(err, msg) -> None:
    if err is not None:
        logger.error("Kafka message delivery failed: %s", err)
    else:
        logger.info(
            "Kafka message delivered: topic=%s partition=%s offset=%s",
            msg.topic(),
            msg.partition(),
            msg.offset(),
        )
