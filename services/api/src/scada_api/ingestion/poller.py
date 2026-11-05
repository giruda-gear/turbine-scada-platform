from datetime import UTC, datetime
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from scada_api.core.database import SessionLocal
from scada_api.data_sources.service import get_data_source
from scada_api.ingestion.adapter import (
    normalize_siemens_reading,
    normalize_vestas_reading,
)
from scada_api.ingestion.schema import CanonicalReading
from scada_api.ingestion.service import (
    calculate_polling_window,
    find_turbine_id,
    get_checkpoint,
    record_polling_failure,
    save_readings,
    update_checkpoint,
)

ADAPTERS = {
    "siemens": normalize_siemens_reading,
    "vestas": normalize_vestas_reading,
}


def fetch_readings(
    endpoint_url: str,
    start_at: datetime,
    end_at: datetime,
) -> dict:
    response = httpx.get(
        endpoint_url,
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
    provider: str,
    payload: dict,
) -> list[CanonicalReading]:
    readings: list[CanonicalReading] = []
    adapter = ADAPTERS.get(provider)

    if adapter is None:
        raise ValueError(f"Unsupported SCADA provider: {provider}")

    for raw in payload["readings"]:
        source_reading = adapter(raw)

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
        data_source = get_data_source(
            session=session,
            data_source_id=data_source_id,
        )
        checkpoint = get_checkpoint(
            session=session,
            data_source_id=data_source_id,
        )

        if data_source is None:
            raise ValueError(f"Data source not found: {data_source_id}")
        if data_source.protocol != "http":
            raise ValueError(f"Unsupported polling protocol: {data_source.protocol}")

        if not data_source.endpoint_url:
            raise ValueError("HTTP data source requires an endpoint_url")

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
            endpoint_url=data_source.endpoint_url,
            start_at=start_at,
            end_at=end_at,
        )
        # release DB connection before the API call (avoids pool exhaustion)

        with SessionLocal() as session, session.begin():
            readings = normalize_payload(
                session=session,
                data_source_id=data_source_id,
                provider=data_source.provider,
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
    data_source_id = UUID("01a1ac47-1032-7a75-b984-819c68f29df0")

    saved_count = run_polling(data_source_id)

    print(f"Readings saved: {saved_count}")
