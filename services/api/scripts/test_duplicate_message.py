from datetime import UTC, datetime
from uuid import UUID

from scada_api.ingestion.producer import publish_raw_readings

publish_raw_readings(
    ingestion_run_id=29,  # already SUCCESS
    data_source_id=UUID("01a1ac47-1032-7a75-b984-819c68f29df0"),
    provider="siemens",
    window_start=datetime.now(UTC),
    window_end=datetime.now(UTC),
    payload={"readings": []},
)

print("Duplicate message published")
