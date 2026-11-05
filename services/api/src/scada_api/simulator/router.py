from datetime import datetime, timedelta

from fastapi import APIRouter

router = APIRouter(prefix="/simulator", tags=["Simulator"])


@router.get("/scada/simens/readings")
def get_scada_simens_readings(
    start_at: datetime,
    end_at: datetime,
):
    readings = [
        {
            "turbine_code": "WT-001",
            "timestamp": (end_at - timedelta(minutes=1)).isoformat(),
            "wind_speed": 8.2,
            "active_power": 1450.0,
            "rotor_speed": 12.5,
        },
        {
            "turbine_code": "WT-002",
            "timestamp": (end_at - timedelta(minutes=1)).isoformat(),
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
        "vendor": "simens",
        "readings": filtered_readings,
    }


@router.get("/scada/vestas/readings")
def get_scada_vestas_readings(
    start_at: datetime,
    end_at: datetime,
):
    readings = [
        {
            "asset_id": "V100-001",
            "recorded_at": (end_at - timedelta(minutes=1)).isoformat(),
            "wind_velocity": 8.2,
            "power_kw": 1350.0,
            "rotor_rpm": 11.5,
        },
        {
            "asset_id": "V100-002",
            "recorded_at": (end_at - timedelta(minutes=1)).isoformat(),
            "wind_velocity": 9.1,
            "power_kw": 1620.0,
            "rotor_rpm": 12.2,
        },
    ]

    filtered_readings = [
        reading
        for reading in readings
        if start_at <= datetime.fromisoformat(reading["recorded_at"]) < end_at
    ]

    return {
        "vendor": "vestas",
        "readings": filtered_readings,
    }
