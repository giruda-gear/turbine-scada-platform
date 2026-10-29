from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from scada_api.core.database import SessionLocal
from scada_api.ingestion.adapter import normalize_siemens_reading
from scada_api.ingestion.schema import CanonicalReading
from scada_api.ingestion.service import find_turbine_id, save_readings

SCADA_API_URL = "http://127.0.0.1:8000/api/simulator/scada/readings"


def fetch_readings() -> dict:
    response = httpx.get(
        SCADA_API_URL,
        timeout=10.0,
    )
    response.raise_for_status()
    return response.json()


def normalize_payload(
    session: Session,
    data_source_id: UUID,
    payload: dict,
) -> list[CanonicalReading]:
    readings: list[CanonicalReading] = []

    for raw in payload["readings"]:
        source_reading = normalize_siemens_reading(raw)

        turbine_id = find_turbine_id(
            session=session,
            data_source_id=data_source_id,
            external_turbine_id=source_reading.external_turbine_id,
        )

        if turbine_id is None:
            # TODO: logging
            print(f"Skipping unmapped turbine: {source_reading.external_turbine_id}")
            continue

        reading = CanonicalReading(
            turbine_id=turbine_id,
            measured_at=source_reading.measured_at,
            wind_speed_ms=source_reading.wind_speed_ms,
            power_output_kw=source_reading.power_output_kw,
            rotor_speed_rpm=source_reading.rotor_speed_rpm,
        )
        readings.append(reading)

    return readings


if __name__ == "__main__":
    data_source_id = UUID("01a18812-610c-77f3-96f5-bd5e15f2b7fe")
    payload = fetch_readings()

    print(f"Vendor: {payload['vendor']}")
    print(f"Readings received: {len(payload['readings'])}")

    with SessionLocal() as session:
        readings = normalize_payload(
            session=session,
            data_source_id=data_source_id,
            payload=payload,
        )

        saved_count = save_readings(
            session=session,
            readings=readings,
        )

    print(f"Readings normalized: {len(readings)}")
    print(f"Readings saved: {saved_count}")
