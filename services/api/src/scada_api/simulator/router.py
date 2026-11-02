from datetime import UTC, datetime

from fastapi import APIRouter

router = APIRouter(prefix="/simulator", tags=["Simulator"])


@router.get("/scada/readings")
def get_scada_readings(
    start_at: datetime,
    end_at: datetime,
):
    readings = [
        {
            "turbine_code": "WT-001",
            "timestamp": datetime.now(UTC).isoformat(),
            "wind_speed": 8.2,
            "active_power": 1450.0,
            "rotor_speed": 12.5,
        },
        {
            "turbine_code": "WT-002",
            "timestamp": datetime.now(UTC).isoformat(),
            "wind_speed": 9.1,
            "active_power": 1820.0,
            "rotor_speed": 13.2,
        },
    ]

    filtered_readings = [
        reading
        for reading in readings
        if start_at <= datetime.fromisoformat(reading["timestamp"]) < end_at
    ]

    return {
        "vendor": "vendor_a",
        "readings": filtered_readings,
    }
