from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException

from scada_api.simulator.siemens import generate_siemens_reading
from scada_api.simulator.time import normalize_utc
from scada_api.simulator.vestas import generate_vestas_reading

router = APIRouter()


TURBINES = {
    "siemens": ["WT-001", "WT-002"],
    "vestas": ["V100-001", "V100-002"],
}


def generate_readings(
    provider: str,
    start_at: datetime,
    end_at: datetime,
) -> list[dict]:
    start_at = normalize_utc(start_at)
    end_at = normalize_utc(end_at)

    if start_at >= end_at:
        raise HTTPException(
            status_code=400,
            detail="start_at must be earlier than end_at",
        )
    # TODO: generate multiple readings
    measured_at = end_at - timedelta(minutes=10)
    
    if not start_at <= measured_at < end_at:
        return []

    generators = {
        "siemens": generate_siemens_reading,
        "vestas": generate_vestas_reading,
    }

    generator = generators[provider]

    return [generator(turbine_code, measured_at) for turbine_code in TURBINES[provider]]


@router.get("/scada/siemens/readings")
def get_scada_siemens_readings(
    start_at: datetime,
    end_at: datetime,
):
    return {
        "vendor": "siemens",
        "interval_seconds": 600,
        "aggregation": "mean",
        "readings": generate_readings(
            "siemens",
            start_at,
            end_at,
        ),
    }


@router.get("/scada/vestas/readings")
def get_scada_vestas_readings(
    start_at: datetime,
    end_at: datetime,
):
    return {
        "vendor": "vestas",
        "interval_seconds": 600,
        "aggregation": "mean",
        "readings": generate_readings(
            "vestas",
            start_at,
            end_at,
        ),
    }
