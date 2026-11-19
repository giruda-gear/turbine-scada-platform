from datetime import UTC, datetime, timedelta
from uuid import uuid4

from scada_api.ingestion.producer import publish_raw_readings

now = datetime.now(UTC)


publish_raw_readings(
    data_source_id=uuid4(),
    provider="vestas",
    window_start=now - timedelta(minutes=10),
    window_end=now,
    payload={
        "turbine_id": "V-001",
        "power_kw": 2500.0,
        "wind_speed_ms": 12.4,
    },
)
