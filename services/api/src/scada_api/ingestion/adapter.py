from scada_api.ingestion.schema import NormalizedSourceReading
from scada_api.models.organization import UUID


def normalize_siemens_reading(
    raw: dict,
) -> NormalizedSourceReading:
    return NormalizedSourceReading(
        external_turbine_id=raw["turbine_code"],
        measured_at=raw["timestamp"],
        wind_speed_ms=raw.get("wind_speed"),
        power_output_kw=raw.get("active_power"),
        rotor_speed_rpm=raw.get("rotor_speed"),
    )
