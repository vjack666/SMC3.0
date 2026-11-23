"""INVARIANT 7: 08:15 Europe/London -> UTC with real GMT/BST offsets via zoneinfo."""

from datetime import date, datetime, time, timedelta, timezone

from helpers import (
    GUAYAQUIL_TZ,
    LONDON_TZ,
    iso_utc,
    london_0815_guayaquil,
    london_0815_utc,
    london_cutoff,
)


def test_winter_0815_london_is_0815_utc_and_0315_guayaquil():
    d = date(2026, 1, 15)
    cutoff = london_cutoff(d)
    assert london_0815_utc(d) == datetime(2026, 1, 15, 8, 15, tzinfo=timezone.utc)
    guayaquil = london_0815_guayaquil(d)
    assert guayaquil.hour == 3 and guayaquil.minute == 15
    assert guayaquil.date() == d
    assert iso_utc(cutoff) == "2026-01-15T08:15:00Z"


def test_summer_0815_london_is_0715_utc_and_0215_guayaquil():
    d = date(2026, 7, 15)
    cutoff = london_cutoff(d)
    assert london_0815_utc(d) == datetime(2026, 7, 15, 7, 15, tzinfo=timezone.utc)
    guayaquil = london_0815_guayaquil(d)
    assert guayaquil.hour == 2 and guayaquil.minute == 15
    assert guayaquil.date() == d
    assert iso_utc(cutoff) == "2026-07-15T07:15:00Z"


def test_offsets_are_read_from_zoneinfo_not_hardcoded():
    winter = london_cutoff(date(2026, 1, 15))
    summer = london_cutoff(date(2026, 7, 15))
    assert winter.utcoffset() == timedelta(0)
    assert summer.utcoffset() == timedelta(hours=1)
    assert winter.tzname() == "GMT"
    assert summer.tzname() == "BST"
    assert winter.astimezone(GUAYAQUIL_TZ).utcoffset() == timedelta(hours=-5)
    assert summer.astimezone(GUAYAQUIL_TZ).utcoffset() == timedelta(hours=-5)
    assert datetime.combine(date(2026, 7, 15), time(8, 15), tzinfo=LONDON_TZ
                            ).astimezone(LONDON_TZ).utcoffset() == timedelta(hours=1)


def test_dst_transition_boundaries_use_correct_offset():
    # 2026: BST starts 2026-03-29, ends 2026-10-25 (last Sundays).
    expectations = [
        (date(2026, 3, 28), 8, 3, timedelta(0)),
        (date(2026, 3, 30), 7, 2, timedelta(hours=1)),
        (date(2026, 10, 24), 7, 2, timedelta(hours=1)),
        (date(2026, 10, 26), 8, 3, timedelta(0)),
    ]
    for d, utc_hour, gq_hour, offset in expectations:
        cutoff = london_cutoff(d)
        assert cutoff.utcoffset() == offset
        converted = london_0815_utc(d)
        assert converted.hour == utc_hour and converted.minute == 15
        local = london_0815_guayaquil(d)
        assert local.hour == gq_hour and local.minute == 15
