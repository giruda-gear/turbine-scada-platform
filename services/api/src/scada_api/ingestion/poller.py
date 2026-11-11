import logging
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

logger = logging.getLogger(__name__)

ADAPTERS = {
    "siemens": normalize_siemens_reading,
    "vestas": normalize_vestas_reading,
}


def fetch_readings(
    client: httpx.Client,
    endpoint_url: str,
    start_at: datetime,
    end_at: datetime,
) -> dict:
    response = client.get(
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
            logger.warning("Unmapped turbine: %s", source_reading.external_turbine_id)
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


from sqlalchemy.orm import sessionmaker


def run_polling(
    client: httpx.Client,
    data_source_id: UUID,
    session_factory: sessionmaker[Session],
    now: datetime | None = None,
) -> int:
    now = now or datetime.now(UTC)

    with session_factory() as session:
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

        endpoint_url = data_source.endpoint_url
        provider = data_source.provider

        window = calculate_polling_window(
            last_success_at=checkpoint.last_success_at,
            now=now,
        )

    if window is None:
        return 0

    start_at, end_at = window
    attempted_at = datetime.now(UTC)

    try:
        payload = fetch_readings(
            endpoint_url=endpoint_url,
            start_at=start_at,
            end_at=end_at,
            client=client,
        )
        print(endpoint_url)
        print(payload)

        with session_factory() as session, session.begin():
            readings = normalize_payload(
                session=session,
                data_source_id=data_source_id,
                provider=provider,
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

            update_checkpoint(
                checkpoint=checkpoint,
                attempted_at=attempted_at,
                end_at=end_at,
            )

        return saved_count

    except Exception as exc:
        with session_factory() as session, session.begin():
            checkpoint = get_checkpoint(
                session=session,
                data_source_id=data_source_id,
            )

            if checkpoint is not None:
                record_polling_failure(
                    checkpoint=checkpoint,
                    error=str(exc),
                    attempted_at=now,
                )

        raise


if __name__ == "__main__":
    data_source_id = UUID("01a1ac47-1032-7a75-b984-819c68f29df0")

    with httpx.Client() as client:
        saved_count = run_polling(
            data_source_id=data_source_id,
            session_factory=SessionLocal,
            client=client,
        )

    print(f"Readings saved: {saved_count}")
