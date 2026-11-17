from datetime import datetime

import httpx


def fetch_readings(
    client: httpx.Client,
    endpoint_url: str,
    start_at: datetime,
    end_at: datetime,
) -> dict:
    response = client.get(
        endpoint_url,
        params={
            "start_at": start_at.isoformat(),
            "end_at": end_at.isoformat(),
        },
        timeout=10.0,
    )
    response.raise_for_status()

    return response.json()
