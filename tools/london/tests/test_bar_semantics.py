"""INVARIANT 3: M15 semantics -- open 08:00 closes 08:15; position zero unused."""

from datetime import timedelta

from helpers import (
    CUTOFF_DATE,
    closed_frame,
    latest_closed,
    london_cutoff,
    make_raw_feed,
    parse_iso_utc,
    to_utc,
    validate_bar,
)

CUTOFF = to_utc(london_cutoff(CUTOFF_DATE))


def test_m15_open_0800_closes_0815_and_is_last_closed():
    raw = make_raw_feed()
    last = latest_closed(raw, CUTOFF)
    assert last is not None
    assert parse_iso_utc(last["open_utc"]) == CUTOFF - timedelta(minutes=15)
    assert parse_iso_utc(last["close_utc"]) == CUTOFF
    assert last["open_london"].endswith("08:00:00+00:00") or "08:00:00" in last["open_london"]
    assert "08:15:00" in last["close_london"]
    assert validate_bar(last) == []


def test_position_zero_is_never_used_as_closed_bar():
    raw = make_raw_feed(poison_index0=True)
    anchor = raw[0]
    last = latest_closed(raw, CUTOFF)
    assert last is not raw[0]
    assert last is closed_frame(raw)[-2]  # 08:00-08:15, never the anchor at index 0
    assert anchor["close_utc"] not in {b["close_utc"] for b in closed_frame(raw)}
    assert parse_iso_utc(last["close_utc"]) == CUTOFF
    assert all(b is not anchor for b in closed_frame(raw))


def test_malformed_bar_duration_is_rejected():
    raw = make_raw_feed()
    bad = dict(raw[1])
    opened = parse_iso_utc(bad["open_utc"])
    from helpers import iso_utc
    bad["close_utc"] = iso_utc(opened + timedelta(minutes=30))
    errors = validate_bar(bad)
    assert errors
    assert any("wrong bar duration" in e for e in errors)


def test_bar_after_cutoff_is_not_eligible():
    raw = make_raw_feed()
    future = raw[-1]  # 08:15-08:30, closes after the cut
    last = latest_closed(raw, CUTOFF)
    assert last is not future
    assert parse_iso_utc(future["close_utc"]) > CUTOFF
