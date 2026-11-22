"""Replay causal parametrizado: prefijo truncationado == serie completa en ``t``.

Cada caso se evalúa con ``cutoff`` fijo usando (a) todas las velas y (b) solo
el prefijo cerrado a ese corte. No hay MT5, servidor, credenciales ni escrituras.
"""
import unittest

from ict3_confirm import MODE, NO_STOP, SECONDS, WAIT
from test_ict3_confirm import (
    DIGITS, RETEST, T0, bullish_bars, bullish_specs, make_bars,
    make_event, m1_bullish_bars, run,
)
from test_ict3_causality import forbidden_keys, late_confirmation_bars

FULL = T0 + 10 * SECONDS["M5"] + SECONDS["M5"]
CUTOFFS = (T0 + SECONDS["M5"] + SECONDS["M5"],
           T0 + 2 * SECONDS["M5"] + SECONDS["M5"],
           T0 + 5 * SECONDS["M5"] + SECONDS["M5"],
           FULL)


def bos_bars():
    specs = bullish_specs()
    specs[5] = (1.210, 1.206, 1.208)
    specs[6] = (1.208, 1.204, 1.206)
    specs[7] = (1.206, 1.202, 1.204)
    return make_bars("M5", T0 - 10 * SECONDS["M5"], specs)


def mss_bars():
    specs = [(1.200, 1.196, 1.198), (1.202, 1.198, 1.200),
             (1.204, 1.200, 1.202), (1.206, 1.202, 1.204),
             (1.208, 1.203, 1.206), (1.210, 1.197, 1.202),
             (1.216, 1.200, 1.206), (1.214, 1.204, 1.210),
             (1.212, 1.206, 1.208), (1.220, 1.208, 1.218)]
    return make_bars("M5", T0 - 5 * SECONDS["M5"], specs)


def near_liquidity_bars():
    specs = bullish_specs()
    specs[8] = (1.204, 1.150, 1.160)
    return make_bars("M5", T0 - 10 * SECONDS["M5"], specs)


def m5_reaction_bars():
    specs = [(1.210, 1.190, 1.200), (1.212, 1.192, 1.202),
             (1.214, 1.194, 1.204), (1.216, 1.196, 1.206),
             (1.214, 1.195, 1.204), (1.212, 1.193, 1.202),
             (1.218, 1.197, 1.210), (1.220, 1.199, 1.216)]
    return make_bars("M5", T0 - 3 * SECONDS["M5"], specs)


def m1_last_resort():
    m5 = [(1.210, 1.202, 1.206), (1.212, 1.204, 1.208),
          (1.214, 1.206, 1.210), (1.216, 1.208, 1.212),
          (1.218, 1.210, 1.214), (1.220, 1.212, 1.216)]
    m1 = [(1.220, 1.205, 1.210), (1.218, 1.204, 1.208),
          (1.216, 1.203, 1.206), (1.214, 1.202, 1.204),
          (1.212, 1.201, 1.202), (1.210, 1.200, 1.205),
          (1.214, 1.202, 1.210), (1.218, 1.204, 1.214), (1.222, 1.208, 1.218)]
    return make_bars("M5", T0, m5), make_bars("M1", T0, m1)


def no_stop_bars():
    rising = [(1.200 + i * 0.002, 1.196 + i * 0.002, 1.198 + i * 0.002)
              for i in range(8)]
    rising[0] = (1.204, 1.197, 1.201)
    return make_bars("M5", T0, rising)


CASES = {
    "complete": (bullish_bars(), m1_bullish_bars(), {}),
    "no_m1": (bullish_bars(), None, {}),
    "late_confirmation": (late_confirmation_bars(), m1_bullish_bars(), {}),
    "bos": (bos_bars(), m1_bullish_bars(), {}),
    "mss": (mss_bars(), None, {}),
    "near_liquidity": (near_liquidity_bars(), m1_bullish_bars(), {}),
    "no_stop": (no_stop_bars(), None, {}),
    "mt5_error": (bullish_bars(), m1_bullish_bars(),
                  {"loader_error": "MT5 M5/M1 timeout"}),
}


def paired(name, cutoff, **kwargs):
    """Devuelve (resultado_serie_completa, resultado_prefijo) en el mismo corte."""
    m5, m1, case_kwargs = CASES[name]
    extra = dict(case_kwargs)
    extra.update(kwargs)
    full = run([make_event()], m5, m1, cutoff, **extra)
    pf_m5 = tuple(row for row in (m5 or ()) if row[0] + SECONDS["M5"] <= cutoff)
    pf_m1 = tuple(row for row in (m1 or ()) if row[0] + SECONDS["M1"] <= cutoff)
    prefix = run([make_event()], pf_m5, pf_m1, cutoff, **extra)
    return full, prefix


class PrefixReplayTests(unittest.TestCase):
    def test_prefix_equals_full_for_every_confirmation_field(self):
        for name in CASES:
            for cutoff in CUTOFFS:
                with self.subTest(case=name, cutoff=cutoff):
                    full, prefix = paired(name, cutoff)
                    self.assertEqual(prefix, full)
                    event = full["ict3"]["events"][0]
                    self.assertIs(event["entry_authorized"], False)
                    self.assertEqual(event["mode"], MODE)

    def test_structure_kind_stable_under_prefix(self):
        scenarios = (("complete", FULL, "CHOCH"),
                     ("bos", FULL, "BOS"),
                     ("mss", T0 + 5 * SECONDS["M5"] + SECONDS["M5"], "MSS"))
        for name, cutoff, expected in scenarios:
            with self.subTest(case=name, expected=expected):
                full, prefix = paired(name, cutoff)
                event = full["ict3"]["events"][0]
                self.assertEqual(event["m5_structure_kind"], expected)
                self.assertEqual(prefix["ict3"]["events"][0]["m5_structure_kind"],
                                 expected)
                self.assertLessEqual(event["m5_structure_at"], cutoff)

    def test_stop_authority_stable_under_prefix(self):
        m5r, m1r = m1_last_resort()
        scenarios = (
            ("complete", FULL, "ORIGIN_SWING_INTACT", 1.200),
            ("late_confirmation", T0 + 11 * SECONDS["M5"], "ORIGIN_SWING_INTACT", 1.198),
            ("no_stop", T0 + SECONDS["M5"], NO_STOP, None),
        )
        for name, cutoff, basis, price in scenarios:
            with self.subTest(case=name, basis=basis):
                full, prefix = paired(name, cutoff)
                event = full["ict3"]["events"][0]
                self.assertEqual(event["stop_basis"], basis)
                self.assertEqual(event["stop_price"], price)
                self.assertEqual(prefix["ict3"]["events"][0]["stop_basis"], basis)
                self.assertEqual(prefix["ict3"]["events"][0]["stop_price"], price)
        for label, m5, m1, cutoff, basis, price in (
            ("m5_reaction", m5_reaction_bars(), None, T0 + 5 * SECONDS["M5"],
             "M5_REACTION_EXTREME", 1.193),
            ("m1_reaction", m5r, m1r, T0 + 9 * SECONDS["M1"],
             "M1_CONFIRMED_EXTREME", 1.200),
        ):
            with self.subTest(case=label, basis=basis):
                full = run([make_event()], m5, m1, cutoff)["ict3"]["events"][0]
                pf_m5 = tuple(row for row in m5 if row[0] + SECONDS["M5"] <= cutoff)
                pf_m1 = tuple(row for row in (m1 or ()) if row[0] + SECONDS["M1"] <= cutoff)
                replay = run([make_event()], pf_m5, pf_m1,
                             cutoff)["ict3"]["events"][0]
                self.assertEqual(full["stop_basis"], basis)
                self.assertEqual(full["stop_price"], price)
                self.assertEqual((replay["stop_basis"], replay["stop_price"]),
                                 (basis, price))

    def test_liquidity_and_target_policy_stable_under_prefix(self):
        scenarios = (
            ("complete", FULL, "SATISFIED_TP1_3R_TP2_5R"),
            ("near_liquidity", FULL, "TP1_BELOW_3R"),
            ("late_confirmation", T0 + 11 * SECONDS["M5"], "TP2_BELOW_5R"),
        )
        for name, cutoff, expected in scenarios:
            with self.subTest(case=name, status=expected):
                full, prefix = paired(name, cutoff)
                event = full["ict3"]["events"][0]
                self.assertEqual(event["target_policy_status"], expected)
                self.assertEqual(prefix["ict3"]["events"][0]["target_policy_status"],
                                 expected)
                self.assertEqual(prefix["ict3"]["events"][0]["target_liquidity"],
                                 event["target_liquidity"])
                for row in event["target_liquidity"]:
                    self.assertLessEqual(row["observed_at"], cutoff)

    def test_without_m1_is_explicit_and_prefix_stable(self):
        for cutoff in CUTOFFS:
            with self.subTest(cutoff=cutoff):
                full, prefix = paired("no_m1", cutoff)
                load = full["ict3"]["load"]
                self.assertTrue(load["m5_loaded"])
                self.assertIsInstance(load["m1_loaded"], bool)
                event = full["ict3"]["events"][0]
                self.assertIsNone(event["m1_structure_kind"])
                self.assertIsNone(event["m1_structure_at"])
                self.assertEqual(prefix, full)
                if cutoff >= FULL:
                    self.assertFalse(load["m1_loaded"])
                    self.assertEqual(load["load_reason"],
                                     "M1_BARS_UNAVAILABLE_M5_USED")

    def test_mt5_loader_error_waits_without_inventing_data(self):
        for cutoff in CUTOFFS:
            with self.subTest(cutoff=cutoff):
                full, prefix = paired("mt5_error", cutoff)
                event = full["ict3"]["events"][0]
                load = full["ict3"]["load"]
                self.assertEqual(event["confirmation_state"], WAIT)
                self.assertEqual(load["load_reason"],
                                 "LOWER_SOURCE_ERROR: MT5 M5/M1 timeout")
                self.assertFalse(load["m5_loaded"])
                self.assertIsNone(event["defense_at"])
                self.assertIsNone(event["m5_structure_kind"])
                self.assertIsNone(event["stop_price"])
                self.assertEqual(event["current_state"], "RETESTING_POI")
                self.assertIs(event["entry_authorized"], False)
                self.assertEqual(prefix, full)
                self.assertFalse(forbidden_keys(full))


if __name__ == "__main__":
    unittest.main()
