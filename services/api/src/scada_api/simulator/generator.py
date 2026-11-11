import hashlib
import random
from datetime import datetime

from scada_api.simulator.time import normalize_utc


def make_rng(
    turbine_code: str,
    measured_at: datetime,
) -> random.Random:
    measured_at = normalize_utc(measured_at)

    seed_source = f"{turbine_code}|{measured_at.isoformat()}"
    # ensure the same innput always produces the same seed
    seed = hashlib.sha256(seed_source.encode("utf-8")).digest()

    return random.Random(int.from_bytes(seed, byteorder="big"))


def generate_values(
    rng: random.Random,
) -> tuple[float, float, float]:
    wind_speed = rng.uniform(3.0, 15.0)

    power_output = max(
        0.0,
        (wind_speed - 3.0) * 150 + rng.uniform(-50, 50),
    )

    rotor_speed = wind_speed * 1.5 + rng.uniform(-0.5, 0.5)

    return wind_speed, power_output, rotor_speed
