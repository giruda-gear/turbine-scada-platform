from datetime import datetime

from scada_api.simulator.generator import (
    generate_values,
    make_rng,
)
from scada_api.simulator.time import normalize_utc


def generate_vestas_reading(
    turbine_code: str,
    measured_at: datetime,
) -> dict:
    measured_at = normalize_utc(measured_at)

    rng = make_rng(turbine_code, measured_at)

    wind_speed, power_output, rotor_speed = generate_values(rng)

    return {
        "asset_id": turbine_code,
        "recorded_at": measured_at.isoformat(),
        "wind_velocity": round(wind_speed, 2),
        "power_kw": round(power_output, 1),
        "rotor_rpm": round(rotor_speed, 2),
    }
