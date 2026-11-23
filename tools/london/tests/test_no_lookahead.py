"""INVARIANT 1: no look-ahead. Event and POI timestamps <= snapshot cutoff."""

from datetime import timedelta

from helpers import (
    CUTOFF_DATE,
    check_no_lookahead,
    iso_utc,
    london_cutoff,
    make_bundle,
    to_utc,
)

CUTOFF = to_utc(london_cutoff(CUTOFF_DATE))


def test_good_bundle_has_no_post_cutoff_events_or_pois():
    assert check_no_lookahead(make_bundle(), CUTOFF) == []


def test_timestamps_equal_to_cutoff_are_allowed():
    bundle = make_bundle()
    for inst in bundle["instruments"].values():
        inst["events"][0]["observed_at"] = iso_utc(CUTOFF)
        inst["pois"][0]["created_at"] = iso_utc(CUTOFF)
    assert check_no_lookahead(bundle, CUTOFF) == []


def test_event_after_cutoff_is_rejected():
    bundle = make_bundle()
    late = iso_utc(CUTOFF + timedelta(minutes=1))
    bundle["instruments"]["EURUSD"]["events"][0]["observed_at"] = late
    errors = check_no_lookahead(bundle, CUTOFF)
    assert errors, "a post-cutoff event must be detected"
    assert all("EURUSD.events[0].observed_at after cutoff" in e for e in errors)


def test_poi_created_after_cutoff_is_rejected():
    bundle = make_bundle()
    late = iso_utc(CUTOFF + timedelta(seconds=1))
    bundle["instruments"]["GBPUSD"]["pois"][0]["created_at"] = late
    errors = check_no_lookahead(bundle, CUTOFF)
    assert errors, "a POI born after the cut must be detected"
    assert any("GBPUSD.pois[0].created_at after cutoff" in e for e in errors)
