from uuid import uuid4

from scada_api.ingestion.producer import publish_raw_readings

publish_raw_readings(
    data_source_id=uuid4(),
    provider="vestas",
    payload={
        "turbine_id": "V-001",
        "power_kw": 2500.0,
        "wind_speed_ms": 12.4,
    },
)
