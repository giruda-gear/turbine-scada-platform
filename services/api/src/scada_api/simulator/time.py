from datetime import UTC, datetime


def normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timezone-aware datetime is required")

    return value.astimezone(UTC)
