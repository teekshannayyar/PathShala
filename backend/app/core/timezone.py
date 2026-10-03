"""The client's local calendar day, for study streaks.

The browser sends its IANA timezone in the X-Timezone header (for example
"Asia/Kolkata"). A missing or invalid value falls back to UTC."""
import datetime
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Header

UTC = ZoneInfo("UTC")
MAX_TZ_LENGTH = 64


def parse_timezone(name: Optional[str]) -> ZoneInfo:
    name = (name or "").strip()
    if not name or len(name) > MAX_TZ_LENGTH:
        return UTC
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        # ValueError covers keys like "../etc/passwd" or absolute paths.
        return UTC


def get_user_tz(x_timezone: Optional[str] = Header(None)) -> ZoneInfo:
    return parse_timezone(x_timezone)


def now_utc() -> datetime.datetime:
    """The current instant. Tests monkeypatch this to fix the clock."""
    return datetime.datetime.now(datetime.timezone.utc)


def local_date(tz: ZoneInfo) -> datetime.date:
    return now_utc().astimezone(tz).date()


def local_today(tz: ZoneInfo) -> str:
    """Today's date in tz, as YYYY-MM-DD."""
    return local_date(tz).isoformat()


def to_local_date(value: datetime.datetime, tz: ZoneInfo) -> datetime.date:
    """The calendar day of a stored timestamp in tz. Naive values are UTC."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=datetime.timezone.utc)
    return value.astimezone(tz).date()
