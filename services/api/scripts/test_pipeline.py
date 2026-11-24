from uuid import UUID

import httpx

from scada_api.core.database import SessionLocal, engine
from scada_api.ingestion.poller import run_polling_with_lock

data_source_id = UUID(
    "01a1ac47-1032-7a75-b984-819c68f29df0"
)

with httpx.Client(timeout=30.0) as client:
    result = run_polling_with_lock(
        client=client,
        data_source_id=data_source_id,
        session_factory=SessionLocal,
        engine=engine,
    )

print(f"Published readings: {result}")
