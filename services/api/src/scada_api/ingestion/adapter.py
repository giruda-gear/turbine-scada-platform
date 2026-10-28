from scada_api.ingestion.schema import CanonicalReading
from scada_api.models.organization import UUID


def normalize_nordwind_reading(
    raw: dict,
    turbine_id: UUID,
) -> CanonicalReading:
    return CanonicalReading(
        turbine_id=turbine_id,
        measured_at=raw["timestamp"],
        wind_speed_ms=raw.get("wind_speed"),
        power_output_kw=raw.get("active_power"),
        rotor_speed_rpm=raw.get("rotor_speed"),
    )
