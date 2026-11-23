"""INVARIANT 5: privacy -- no login, balance, account, local path or token."""

from helpers import check_privacy, make_bundle


def test_good_bundle_has_no_private_fields_or_paths():
    assert check_privacy(make_bundle()) == []


def test_private_key_injection_is_detected():
    bundle = make_bundle()
    bundle["instruments"]["EURUSD"]["events"][0]["account_number"] = "synthetic"
    errors = check_privacy(bundle)
    assert errors
    assert any("private key:" in e for e in errors)


def test_local_path_in_value_is_detected():
    bundle = make_bundle()
    bundle["instruments"]["GBPUSD"]["events"][0]["note"] = (
        r"C:\Users\example\AppData\Local\MT5\terminal.exe"
    )
    errors = check_privacy(bundle)
    assert errors
    assert any("local path:" in e for e in errors)


def test_token_and_balance_fields_are_detected():
    bundle = make_bundle()
    bundle["token"] = "synthetic-value"
    bundle["balance"] = 0
    errors = check_privacy(bundle)
    assert errors
    assert any("token" in e for e in errors)
    assert any("balance" in e for e in errors)
