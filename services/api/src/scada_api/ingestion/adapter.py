from scada_api.ingestion.schema import NormalizedSourceReading


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


def normalize_vestas_reading(
    raw: dict,
) -> NormalizedSourceReading:
    return NormalizedSourceReading(
        external_turbine_id=raw["asset_id"],
        measured_at=raw["recorded_at"],
        wind_speed_ms=raw.get("wind_velocity"),
        power_output_kw=raw.get("power_kw"),
        rotor_speed_rpm=raw.get("rotor_rpm"),
    )
