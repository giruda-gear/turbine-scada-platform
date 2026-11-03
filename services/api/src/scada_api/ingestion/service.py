from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from scada_api.ingestion.schema import CanonicalReading
from scada_api.models import IngestionCheckpoints, SensorReading, TurbineSourceMapping

INITIAL_LOOKBACK = timedelta(hours=1)
MAX_WINDOW = timedelta(hours=1)


def get_checkpoint(
    session: Session,
    data_source_id: UUID,
) -> IngestionCheckpoints | None:
    return session.get(IngestionCheckpoints, data_source_id)


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
        {
            "turbine_id": reading.turbine_id,
            "measured_at": reading.measured_at,
            "wind_speed_ms": reading.wind_speed_ms,
            "power_output_kw": reading.power_output_kw,
            "rotor_speed_rpm": reading.rotor_speed_rpm,
        }
        for reading in readings
    ]

    statement = pg_insert(SensorReading).values(records)

    statement = statement.on_conflict_do_update(
        index_elements=[
            SensorReading.turbine_id,
            SensorReading.measured_at,
        ],
        set_={
            "wind_speed_ms": statement.excluded.wind_speed_ms,
            "power_output_kw": statement.excluded.power_output_kw,
            "rotor_speed_rpm": statement.excluded.rotor_speed_rpm,
            "received_at": func.now(),
        },
    )

    session.execute(statement)

    return len(records)


def update_checkpoint(
    checkpoint: IngestionCheckpoints,
    attempted_at: datetime,
    end_at: datetime,
) -> None:
    checkpoint.last_attempt_at = attempted_at
    checkpoint.last_success_at = end_at
    checkpoint.last_error = None


def record_polling_failure(
    checkpoint: IngestionCheckpoints,
    attempted_at: datetime,
    error: str,
) -> None:
    checkpoint.last_attempt_at = attempted_at
    checkpoint.last_error = error[:1000]


def calculate_polling_window(
    last_success_at: datetime | None,
    now: datetime,
) -> tuple[datetime, datetime] | None:
    end_at = floor_interval(now)

    if last_success_at is None:
        start_at = floor_interval(end_at - INITIAL_LOOKBACK)
    else:
        start_at = last_success_at

    if start_at >= end_at:
        return None

    end_at = min(end_at, start_at + MAX_WINDOW)

    return start_at, end_at


def floor_interval(
    value: datetime,
    interval_miutes: int = 10,
) -> datetime:
    return value.replace(
        minute=(value.minute // interval_miutes) * interval_miutes,
        second=0,
        microsecond=0,
    )
