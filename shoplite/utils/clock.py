"""The current time in one place, so tests can move the clock."""

from datetime import UTC, datetime, timedelta

# Naive UTC datetimes everywhere: SQLite has no time-zone type.
_offset = timedelta(0)


def utcnow() -> datetime:
    """Return the current UTC time (naive)."""
    return datetime.now(UTC).replace(tzinfo=None) + _offset


def advance(delta: timedelta) -> None:
    """Move the clock forward (tests only)."""
    global _offset
    _offset += delta


def reset() -> None:
    """Put the clock back to real time."""
    global _offset
    _offset = timedelta(0)
