import httpx

SCADA_API_URL = "http://127.0.0.1:8000/api/simulator/scada/readings"


def fetch_readings() -> dict:
    response = httpx.get(
        SCADA_API_URL,
        timeout=10.0,
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    payload = fetch_readings()

    print(f"Vendor: {payload['vendor']}")
    print(f"Readings received: {len(payload['readings'])}")

    for reading in payload["readings"]:
        print(reading)
