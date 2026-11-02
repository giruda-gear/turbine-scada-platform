from datetime import UTC, datetime

from scada_api.ingestion.service import calculate_polling_window


def test_initial_polling_window():
    now = datetime(2026, 11, 2, 10, 23, tzinfo=UTC)

    result = calculate_polling_window(
        last_success_at=None,
        now=now,
    )

    assert result == (
        datetime(2026, 11, 2, 9, 20, tzinfo=UTC),
        datetime(2026, 11, 2, 10, 20, tzinfo=UTC),
    )


def test_normal_polling_window():
    last_success_at = datetime(2026, 11, 2, 10, 10, tzinfo=UTC)
    now = datetime(2026, 11, 2, 10, 23, tzinfo=UTC)

    result = calculate_polling_window(
        last_success_at=last_success_at,
        now=now,
    )

    assert result == (
        datetime(2026, 11, 2, 10, 10, tzinfo=UTC),
        datetime(2026, 11, 2, 10, 20, tzinfo=UTC),
    )


def test_long_outage_is_split_by_max_window():
    last_success_at = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)
    now = datetime(2026, 11, 2, 13, 23, tzinfo=UTC)

    first_result = calculate_polling_window(last_success_at, now)

    assert first_result == (
        datetime(2026, 11, 2, 9, 0, tzinfo=UTC),
        datetime(2026, 11, 2, 10, 0, tzinfo=UTC),
    )
    assert first_result is not None

    second_result = calculate_polling_window(
        last_success_at=first_result[1],
        now=now,
    )

    assert second_result == (
        datetime(2026, 11, 2, 10, 0, tzinfo=UTC),
        datetime(2026, 11, 2, 11, 0, tzinfo=UTC),
    )


def test_returns_none_when_no_new_window():
    last_success_at = datetime(2026, 11, 2, 10, 10, tzinfo=UTC)
    now = datetime(2026, 11, 2, 10, 19, tzinfo=UTC)

    result = calculate_polling_window(
        last_success_at=last_success_at,
        now=now,
    )

    assert result is None
