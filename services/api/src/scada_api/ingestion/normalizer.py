from uuid import UUID

from sqlalchemy.orm import Session

from scada_api.ingestion.adapter import (
    normalize_siemens_reading,
    normalize_vestas_reading,
)
from scada_api.ingestion.schema import CanonicalReading
from scada_api.ingestion.service import find_turbine_id, save_rejected_reading

ADAPTERS = {
    "siemens": normalize_siemens_reading,
    "vestas": normalize_vestas_reading,
}


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
