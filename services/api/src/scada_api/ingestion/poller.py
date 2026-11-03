from datetime import UTC, datetime
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from scada_api.core.database import SessionLocal
from scada_api.ingestion.adapter import normalize_siemens_reading
from scada_api.ingestion.schema import CanonicalReading
from scada_api.ingestion.service import (
    calculate_polling_window,
    find_turbine_id,
    get_checkpoint,
    record_polling_failure,
    save_readings,
    update_checkpoint,
)

SCADA_API_URL = "http://127.0.0.1:8009/api/simulator/scada/readings"


def fetch_readings(
    start_at: datetime,
    end_at: datetime,
) -> dict:
    response = httpx.get(
        SCADA_API_URL,
        params={
            "start_at": start_at.isoformat(),
            "end_at": end_at.isoformat(),
        },
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


def run_polling(data_source_id: UUID) -> int:
    with SessionLocal() as session:
        checkpoint = get_checkpoint(
            session=session,
            data_source_id=data_source_id,
        )

        if checkpoint is None:
            raise ValueError(f"Checkpoint not found: {data_source_id}")

        window = calculate_polling_window(
            last_success_at=checkpoint.last_success_at,
            now=datetime.now(UTC),
        )

    if window is None:
        return 0

    start_at, end_at = window
    attempted_at = datetime.now(UTC)

    try:
        payload = fetch_readings(
            start_at=start_at,
            end_at=end_at,
        )
        # release DB connection before the API call (avoids pool exhaustion)

        with SessionLocal() as session, session.begin():
            readings = normalize_payload(
                session=session,
                data_source_id=data_source_id,
                payload=payload,
            )

            saved_count = save_readings(
                session=session,
                readings=readings,
            )

            checkpoint = get_checkpoint(
                session=session,
                data_source_id=data_source_id,
            )
            assert checkpoint is not None

            if checkpoint is None:
                raise ValueError(f"Checkpoint not found: {data_source_id}")
            # later, think about the race condition

            update_checkpoint(
                checkpoint=checkpoint,
                attempted_at=attempted_at,
                end_at=end_at,
            )

        return saved_count

    except Exception as exc:
        with SessionLocal() as session, session.begin():
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
        raise


if __name__ == "__main__":
    data_source_id = UUID("01a1a0df-e7a0-7091-8c3c-6957a404b3de")

    saved_count = run_polling(data_source_id)

    print(f"Readings saved: {saved_count}")
