from datetime import UTC, datetime, timedelta, timezone

from scada_api.simulator.generator import generate_values, make_rng


def generate_reading(turbine_code: str, measured_at: datetime) -> tuple:
    rng = make_rng(turbine_code, measured_at)

    return generate_values(rng)


def test_same_turbine_and_timestamp_produce_same_reading():
    timestamp = datetime(2026, 11, 11, 10, 0, tzinfo=UTC)

    first = generate_reading("WT-001", timestamp)
    second = generate_reading("WT-001", timestamp)

    assert first == second


def test_different_turbines_produce_different_readings():
    timestamp = datetime(2026, 11, 11, 10, 0, tzinfo=UTC)

    first = generate_reading("WT-001", timestamp)
    second = generate_reading("WT-002", timestamp)

    assert first != second


def test_different_timestamps_produce_different_readings():
    timestamp = datetime(2026, 11, 11, 10, 0, tzinfo=UTC)

    first = generate_reading("WT-001", timestamp)
    second = generate_reading(
        "WT-001",
        timestamp + timedelta(minutes=10),
    )

    assert first != second


def test_equivalent_timezones_produce_same_reading():
    utc_timestamp = datetime(2026, 11, 11, 10, 0, tzinfo=UTC)
    cet_timestamp = datetime(2026, 11, 11, 11, 0, tzinfo=timezone(timedelta(hours=1)))

    first = generate_reading("WT-001", utc_timestamp)
    second = generate_reading("WT-001", cet_timestamp)

    assert first == second


def test_naive_datetime_is_rejected():
    timestamp = datetime(2026, 11, 11, 10, 0)

    try:
        generate_reading("WT-001", timestamp)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for naive datetime")
