"""INVARIANT 8: failure modes -- stale feed, missing symbol, invalid manifest,
old latest.json never presented as new."""

from helpers import (
    CUTOFF_DATE,
    build_manifest,
    check_catalog,
    check_observe_only,
    classify_feed,
    latest_status,
    london_0815_utc,
    make_bundle,
    render_bundle,
    update_latest_if_valid,
    validate_manifest,
)

CUTOFF = london_0815_utc(CUTOFF_DATE)


def _latest(snapshot_date: str, validation: str = "PASSED", label: str = "new") -> dict:
    return {
        "snapshot_id": f"london-{snapshot_date}-0815",
        "snapshot_date": snapshot_date,
        "path": f"snapshots/{snapshot_date}/london_0815/manifest.json",
        "validation_status": validation,
        "label": label,  # self-declared label must be ignored by the checker
    }


def test_stale_feed_is_not_marked_fresh():
    bundle = make_bundle()
    inst = bundle["instruments"]["EURUSD"]
    assert classify_feed(inst, CUTOFF) == "FRESH"
    inst["last_bar_close_utc"] = inst["last_bar_open_utc"]  # closed 08:00, not 08:15
    assert classify_feed(inst, CUTOFF) == "STALE_FEED"
    assert inst["freshness_status"] == "FRESH"  # status flag is not blindly trusted
    inst["freshness_status"] = "STALE_FEED"
    assert classify_feed(inst, CUTOFF) == "STALE_FEED"


def test_missing_symbol_is_reported_not_silently_dropped():
    bundle = make_bundle()
    del bundle["instruments"]["GBPUSD"]
    bundle["exported"] = ["EURUSD"]
    errors = check_catalog(bundle, ["EURUSD", "GBPUSD"])
    assert errors
    assert any("missing-from-instruments:GBPUSD" in e for e in errors)
    assert any("missing-from-unavailable:GBPUSD" in e for e in errors)


def test_invalid_manifest_is_rejected():
    fixture = make_bundle()
    good = build_manifest(render_bundle(fixture), fixture)
    assert validate_manifest(good) == []
    bad = dict(good)
    bad.pop("snapshot_cutoff_utc")
    bad["mode"] = "LIVE_TRADING"
    bad["files"] = [{"path": "snapshot.json", "sha256": "xyz", "bytes": "large"}]
    errors = validate_manifest(bad)
    assert errors
    assert any("missing-key:snapshot_cutoff_utc" in e for e in errors)
    assert "invalid-mode" in errors
    assert "invalid-sha256" in errors
    assert "invalid-byte-count" in errors
    assert check_observe_only({"mode": "LIVE_TRADING", "instruments": {}})


def test_old_latest_json_is_never_labelled_new():
    old = _latest("2026-11-20")
    assert latest_status(old, CUTOFF_DATE) == "PENDIENTE DE SNAPSHOT NUEVO"
    assert old["label"] == "new"  # the self-label is explicitly not trusted
    assert latest_status(_latest("2026-11-23"), CUTOFF_DATE) == "NEW"
    assert latest_status(_latest("2026-11-23", "BLOCKED"), CUTOFF_DATE) == "BLOCKED"


def test_failed_run_does_not_replace_latest_pointer():
    old = _latest("2026-11-20")
    candidate = _latest("2026-11-23")
    for published, valid in ((False, True), (True, False), (False, False)):
        pointer = update_latest_if_valid(
            old, candidate, published=published, valid=valid, today=CUTOFF_DATE
        )
        assert pointer == old
        assert latest_status(pointer, CUTOFF_DATE) == "PENDIENTE DE SNAPSHOT NUEVO"
    good = update_latest_if_valid(
        old, candidate, published=True, valid=True, today=CUTOFF_DATE
    )
    assert good == candidate
    assert latest_status(good, CUTOFF_DATE) == "NEW"
