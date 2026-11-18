import json
import logging
from uuid import UUID

from confluent_kafka import Producer

from scada_api.core.config import settings

logger = logging.getLogger(__name__)

RAW_READINGS_TOPIC = "raw-readings"


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


def publish_raw_readings(
    data_source_id: UUID,
    provider: str,
    payload: dict,
) -> None:
    producer = Producer(
        {
            "bootstrap.servers": settings.kafka_bootstrap_servers,
        }
    )

    message = {
        "data_source_id": str(data_source_id),
        "provider": provider,
        "payload": payload,
    }

    producer.produce(
        topic=RAW_READINGS_TOPIC,
        key=str(
            data_source_id
        ),  # the same key are normally routed to the same partition
        value=json.dumps(message),
        callback=delivery_report,
    )

    remaining = producer.flush(timeout=10)

    if remaining > 0:
        raise TimeoutError(
            f"{remaining} Kafka message(s) were not delivered within 10 seconds"
        )
