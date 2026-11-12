from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, literal_column, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from scada_api.ingestion.schema import CanonicalReading
from scada_api.models import IngestionCheckpoints, SensorReading, TurbineSourceMapping

INITIAL_LOOKBACK = timedelta(hours=1)
MAX_WINDOW = timedelta(hours=1)


@dataclass
class SaveResult:
    inserted: int
    updated: int
    unchanged: int


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


def save_readings(session: Session, readings: list[CanonicalReading]) -> SaveResult:
    if not readings:
        return SaveResult(0, 0, 0)

    by_key = {
        (r.turbine_id, r.measured_at): {
            "turbine_id": r.turbine_id,
            "measured_at": r.measured_at,
            "wind_speed_ms": r.wind_speed_ms,
            "power_output_kw": r.power_output_kw,
            "rotor_speed_rpm": r.rotor_speed_rpm,
        }
        for r in readings
    }
    records = list(by_key.values())
    batch_duplicates = len(readings) - len(records)

    stmt = pg_insert(SensorReading).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=[SensorReading.turbine_id, SensorReading.measured_at],
        set_={
            "wind_speed_ms": stmt.excluded.wind_speed_ms,
            "power_output_kw": stmt.excluded.power_output_kw,
            "rotor_speed_rpm": stmt.excluded.rotor_speed_rpm,
            "updated_at": func.now(),
        },
        where=or_(
            SensorReading.wind_speed_ms.is_distinct_from(stmt.excluded.wind_speed_ms),
            SensorReading.power_output_kw.is_distinct_from(
                stmt.excluded.power_output_kw
            ),
            SensorReading.rotor_speed_rpm.is_distinct_from(
                stmt.excluded.rotor_speed_rpm
            ),
        ),
    ).returning(literal_column("(xmax = 0)"))

    rows = session.execute(stmt).all()
    inserted = sum(1 for (is_new,) in rows if is_new)
    updated = len(rows) - inserted
    unchanged = len(records) - len(rows) + batch_duplicates

    return SaveResult(inserted, updated, unchanged)


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
