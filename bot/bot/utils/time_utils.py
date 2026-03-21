from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ms_to_datetime(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


def datetime_to_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def interval_to_seconds(interval: int) -> int:
    """Convert interval in minutes to seconds."""
    return interval * 60


def interval_label(interval: int) -> str:
    """Convert interval minutes to Bybit kline category string."""
    return str(interval)
