from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from scada_api.ingestion.schema import CanonicalReading
from scada_api.models import SensorReading, TurbineSourceMapping


def find_turbine_id(
    session: Session,
    data_source_id: UUID,
    external_turbine_id: str,
) -> UUID | None:
    statement = select(TurbineSourceMapping.turbine_id).where(
        TurbineSourceMapping.data_source_id == data_source_id,
        TurbineSourceMapping.external_turbine_id == external_turbine_id,
    )

    return session.scalar(statement)


def save_readings(
    session: Session,
    readings: list[CanonicalReading],
) -> int:
    if not readings:
        return 0

    records = [
        SensorReading(
            turbine_id=reading.turbine_id,
            measured_at=reading.measured_at,
            wind_speed_ms=reading.wind_speed_ms,
            power_kw=reading.power_output_kw,
            rotor_speed_rpm=reading.rotor_speed_rpm,
        )
        for reading in readings
    ]

    session.add_all(records)
    session.commit()

    return len(records)
