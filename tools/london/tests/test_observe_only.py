"""INVARIANT 2: OBSERVE_ONLY_NO_ORDER, entry_authorized false, no trading keys."""

from helpers import check_observe_only, make_bundle


def test_mode_is_observe_only_and_all_entries_unauthorized():
    bundle = make_bundle()
    assert bundle["mode"] == "OBSERVE_ONLY_NO_ORDER"
    for inst in bundle["instruments"].values():
        assert inst["candidates"]
        assert all(c["entry_authorized"] is False for c in inst["candidates"])
    assert check_observe_only(bundle) == []


def test_entry_authorized_true_is_rejected():
    bundle = make_bundle()
    bundle["instruments"]["EURUSD"]["candidates"][0]["entry_authorized"] = True
    errors = check_observe_only(bundle)
    assert errors
    assert any("EURUSD.candidates[0].entry_authorized" in e for e in errors)


def test_trading_keys_are_absent_from_synthetic_bundle():
    bundle = make_bundle()
    assert check_observe_only(bundle) == []


def test_injected_order_key_is_rejected():
    bundle = make_bundle()
    bundle["instruments"]["GBPUSD"]["candidates"][0]["order"] = {
        "side": "BUY", "lots": 1
    }
    errors = check_observe_only(bundle)
    assert errors
    assert any("trading key:" in e for e in errors)
