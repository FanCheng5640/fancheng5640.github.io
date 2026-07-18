"""Shared Google Scholar freshness checks for local and cloud automation."""

from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo


ISRAEL_TIMEZONE = "Asia/Jerusalem"


def parse_iso_date(value: str) -> date | None:
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError:
        return None


def current_date_in_timezone(
    now: datetime | None = None,
    timezone_name: str = ISRAEL_TIMEZONE,
) -> date:
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        raise ValueError("now must include timezone information")
    return instant.astimezone(ZoneInfo(timezone_name)).date()


def google_scholar_current_for_date(data: dict, target_date: date) -> bool:
    return (
        data.get("exists", True) is True
        and data.get("sync_status") == "ok"
        and parse_iso_date(data.get("updated", "")) == target_date
    )


def google_scholar_current_for_today(
    data: dict,
    now: datetime | None = None,
    timezone_name: str = ISRAEL_TIMEZONE,
) -> bool:
    return google_scholar_current_for_date(
        data,
        current_date_in_timezone(now=now, timezone_name=timezone_name),
    )
