"""DST-safe London 08:15 cutoff utilities.

Standard library only (``datetime`` + ``zoneinfo``).  No third-party
packages and no hardcoded UTC offsets: every conversion is derived from
the IANA tz database via ``zoneinfo.ZoneInfo``.

Verified timezone truth (2026, computed with ``zoneinfo``):

* ``Europe/London`` is GMT (UTC+00:00) in winter and BST (UTC+01:00) in
  summer.  In 2026 BST starts on 2026-03-29 and ends on 2026-10-25.
* ``America/Guayaquil`` (Ecuador) is UTC-05:00 year round; it observes no
  DST, so its offset never changes.

Therefore 08:15 London == 03:15 Guayaquil during GMT and == 02:15
Guayaquil during BST.  The plan's claim is correct: there is no
discrepancy.  See README.md for the full verification table.
"""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

__all__ = [
    "LONDON_TZ",
    "GUAYAQUIL_TZ",
    "resolve_cutoff",
    "previous_london_session",
    "bar_window",
    "is_london_open_day",
]

LONDON_TZ = "Europe/London"
GUAYAQUIL_TZ = "America/Guayaquil"

_STRICT_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _zone(name: str) -> ZoneInfo:
    """Return a ZoneInfo, raising ValueError for unknown/invalid zones."""
    if not isinstance(name, str) or not name:
        raise ValueError("time zone must be a non-empty string")
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"unknown time zone: {name!r}") from exc


def _parse_date(date_str: str) -> date:
    """Parse a strict ``YYYY-MM-DD`` date string, raising ValueError."""
    if not isinstance(date_str, str) or not _STRICT_ISO_DATE.match(date_str):
        raise ValueError(f"date_str must be YYYY-MM-DD, got {date_str!r}")
    try:
        return date.fromisoformat(date_str)
    except ValueError as exc:
        raise ValueError(f"invalid calendar date: {date_str!r}") from exc


def _validate_hm(hour: int, minute: int) -> None:
    if isinstance(hour, bool) or not isinstance(hour, int) or not 0 <= hour <= 23:
        raise ValueError(f"hour must be an int in 0..23, got {hour!r}")
    if isinstance(minute, bool) or not isinstance(minute, int) or not 0 <= minute <= 59:
        raise ValueError(f"minute must be an int in 0..59, got {minute!r}")


def _london_label(dt: datetime) -> str:
    """ISO 8601 with the human-readable zone abbreviation appended."""
    return f"{dt.isoformat()} {dt.tzname()}"


def is_london_open_day(date_str: str, tz: str = LONDON_TZ) -> bool:
    """True when the given date is a London weekday (Monday-Friday)."""
    parsed = _parse_date(date_str)
    _zone(tz)  # validate even though the weekday does not depend on the zone
    return parsed.weekday() < 5


def resolve_cutoff(
    date_str: str,
    tz: str = LONDON_TZ,
    hour: int = 8,
    minute: int = 15,
) -> dict:
    """Resolve a local wall-clock cutoff to UTC / London / Guayaquil.

    Args:
        date_str: Calendar date in strict ``YYYY-MM-DD`` form, interpreted
            in ``tz`` (default ``Europe/London``).
        tz: IANA time zone for the wall-clock cutoff (default London).
        hour: Local hour, 0-23 (default 8).
        minute: Local minute, 0-59 (default 15).

    Returns:
        Dict with keys:

        ``cutoff_utc_epoch`` -- integer Unix epoch seconds.
        ``cutoff_utc_iso`` -- UTC ISO 8601 with ``+00:00``.
        ``cutoff_london_iso`` -- London ISO 8601 with ``GMT``/``BST``
            appended, e.g. ``2026-07-15T08:15:00+01:00 BST``.
        ``cutoff_london_tzname`` -- ``GMT`` or ``BST``.
        ``cutoff_london_utc_offset_seconds`` -- 0 (GMT) or 3600 (BST).
        ``cutoff_guayaquil_iso`` -- ISO 8601 in ``America/Guayaquil``.
        ``cutoff_guayaquil_tzname`` -- normally ``-05``.
        ``weekday_london`` -- full weekday name of the London local date.
        ``is_london_open_day`` -- True for Monday-Friday.

        Plus echo fields ``date``, ``tz``, ``hour`` and ``minute``.

    Raises:
        ValueError: for a malformed date, out-of-range hour/minute, or an
            unknown time zone.

    Note:
        On DST transition days the 08:15 wall time is never inside the
        spring-forward gap or the autumn fold (those occur near 01:00-02:00
        London time), so the offset is unambiguous.  ``fold=0`` is the
        default and is left implicit.
    """
    parsed = _parse_date(date_str)
    _validate_hm(hour, minute)
    zone = _zone(tz)
    guayaquil = _zone(GUAYAQUIL_TZ)

    wall = datetime(parsed.year, parsed.month, parsed.day, hour, minute)
    local = wall.replace(tzinfo=zone)
    utc = local.astimezone(timezone.utc)
    gye = local.astimezone(guayaquil)

    return {
        "date": parsed.isoformat(),
        "tz": tz,
        "hour": hour,
        "minute": minute,
        "cutoff_utc_epoch": int(utc.timestamp()),
        "cutoff_utc_iso": utc.isoformat(),
        "cutoff_london_iso": _london_label(local),
        "cutoff_london_tzname": local.tzname(),
        "cutoff_london_utc_offset_seconds": int(local.utcoffset().total_seconds()),
        "cutoff_guayaquil_iso": gye.isoformat(),
        "cutoff_guayaquil_tzname": gye.tzname(),
        "weekday_london": local.strftime("%A"),
        "is_london_open_day": local.weekday() < 5,
    }


def previous_london_session(date_str: str, tz: str = LONDON_TZ) -> str:
    """Return the most recent London trading session date, ``YYYY-MM-DD``.

    Documented behavior:

    * If ``date_str`` is a weekday (Monday-Friday) it is returned unchanged
      (the session is inclusive of the requested day).
    * If ``date_str`` is a Saturday or Sunday, the preceding Friday is
      returned (the last session before the weekend).
    * No market-holiday calendar is applied; "open day" means weekday only.
    * The result is a date string, not a datetime, and is independent of
      DST because it is a pure calendar calculation.

    Raises ``ValueError`` for a malformed ``date_str`` or unknown ``tz``.
    """
    parsed = _parse_date(date_str)
    _zone(tz)
    if parsed.weekday() < 5:
        return parsed.isoformat()
    days_back = parsed.weekday() - 4  # Sat(5)->1, Sun(6)->2
    return (parsed - timedelta(days=days_back)).isoformat()


def bar_window(cutoff_epoch: int | float, minutes: int = 15, tz: str = LONDON_TZ) -> dict:
    """Describe the M-bar (default M15) containing ``cutoff_epoch``.

    The bar open is the wall-clock minute boundary at or before the cutoff;
    the close is exactly ``minutes`` of real time later.  Both labels are
    rendered in London time with the GMT/BST abbreviation appended.

    Args:
        cutoff_epoch: Unix epoch seconds (int or float).
        minutes: Bar length in minutes (default 15 for M15).
        tz: IANA time zone used for the wall-clock labels (default London).

    Returns:
        Dict with ``bar_open_epoch``, ``bar_close_epoch``,
        ``bar_open_london_iso``, ``bar_close_london_iso``,
        ``bar_open_london_time``, ``bar_close_london_time``,
        ``cutoff_london_iso``, ``cutoff_inside_bar``, plus echo fields.

    Raises ``ValueError`` for invalid input.
    """
    if isinstance(cutoff_epoch, bool) or not isinstance(cutoff_epoch, (int, float)):
        raise ValueError(f"cutoff_epoch must be a number, got {cutoff_epoch!r}")
    if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes <= 0:
        raise ValueError(f"minutes must be a positive int, got {minutes!r}")
    zone = _zone(tz)

    cutoff_utc = datetime.fromtimestamp(cutoff_epoch, tz=timezone.utc)
    cutoff_local = cutoff_utc.astimezone(zone)

    floored = cutoff_local.replace(second=0, microsecond=0)
    minute_of_day = floored.hour * 60 + floored.minute
    floored_minute = (minute_of_day // minutes) * minutes
    open_wall = datetime.combine(
        floored.date(), time(hour=0)
    ) + timedelta(minutes=floored_minute)
    bar_open = open_wall.replace(tzinfo=zone)
    bar_close = (bar_open.astimezone(timezone.utc) + timedelta(minutes=minutes)).astimezone(zone)

    open_epoch = int(bar_open.timestamp())
    close_epoch = int(bar_close.timestamp())

    return {
        "cutoff_epoch": cutoff_epoch,
        "cutoff_london_iso": _london_label(cutoff_local),
        "bar_minutes": minutes,
        "tz": tz,
        "bar_open_epoch": open_epoch,
        "bar_close_epoch": close_epoch,
        "bar_open_london_iso": _london_label(bar_open),
        "bar_close_london_iso": _london_label(bar_close),
        "bar_open_london_time": bar_open.strftime("%H:%M"),
        "bar_close_london_time": bar_close.strftime("%H:%M"),
        "cutoff_inside_bar": open_epoch <= cutoff_epoch < close_epoch,
    }
