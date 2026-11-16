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
from scada_api.ingestion.enums import IngestionRunStatus
from scada_api.ingestion.schema import CanonicalReading
from scada_api.ingestion.service import (
    SaveResult,
    calculate_polling_window,
    create_ingestion_run,
    find_turbine_id,
    get_checkpoint,
    record_polling_failure,
    save_readings,
    save_rejected_reading,
    update_checkpoint,
    update_ingestion_run,
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
    ingestion_run_id: int,
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
            save_rejected_reading(
                session=session,
                ingestion_run_id=ingestion_run_id,
                external_turbine_id=source_reading.external_turbine_id,
                raw_payload=raw,
                reason="unmapped_turbine",
                error_message=f"No mapping found for {source_reading.external_turbine_id}",
            )
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

'''
* Initial transaction
Create and commit IngestionRun with status running.

* HTTP request
Fetch vendor payload outside the database transaction.

* Success transaction
Normalize → save rejected readings → save canonical readings → update checkpoint → update ingestion run → commit together.

* Failure transaction
Update checkpoint failure information and mark ingestion run failed → commit.
'''
def run_polling(
    client: httpx.Client,
    data_source_id: UUID,
    session_factory: sessionmaker[Session],
    now: datetime | None = None,
) -> SaveResult:
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
        return SaveResult(
            inserted=0,
            updated=0,
            unchanged=0,
        )

    start_at, end_at = window
    attempted_at = now

    with session_factory() as session:
        ingestion_run = create_ingestion_run(
            session=session,
            data_source_id=data_source_id,
            window_start=start_at,
            window_end=end_at,
            started_at=attempted_at,
        )

        ingestion_run_id = ingestion_run.id

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
                ingestion_run_id=ingestion_run_id,
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

            update_ingestion_run(
                session=session,
                ingestion_run_id=ingestion_run_id,
                status=IngestionRunStatus.SUCCESS,
                completed_at=now,
                received_count=len(payload["readings"]),
                inserted_count=saved_count.inserted,
                updated_count=saved_count.updated,
                unchanged_count=saved_count.unchanged,
                rejected_count=len(payload["readings"]) - len(readings),
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
                    attempted_at=attempted_at,
                )

            update_ingestion_run(
                session=session,
                ingestion_run_id=ingestion_run_id,
                status=IngestionRunStatus.FAILED,
                completed_at=now,
                error_message=str(exc),
            )

        raise


if __name__ == "__main__":
    data_source_id = UUID("01a1ac47-1032-7a75-b984-819c68f29df0")

    with httpx.Client() as client:
        result = run_polling(
            client=client,
            data_source_id=data_source_id,
            session_factory=SessionLocal,
        )

    print(f"Inserted: {result.inserted}")
    print(f"Updated: {result.updated}")
    print(f"Unchanged: {result.unchanged}")
