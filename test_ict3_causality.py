"""Validación causal de las correcciones del Lote Hermes 03.

Pruebas puras: sin MT5, sin servidor, sin escrituras en ``data/``.
Un pivote formado antes del retest pero confirmado después no es conocible
en el retest y, por tanto, no puede alterar retrospectivamente el stop.
"""
import unittest

from ict3_confirm import (
    CONFIRMED, MODE, NO_STOP, OBSERVABLE, RETESTING, SECONDS, WAIT,
    _closed_bars, _origin_swing, _pivots, _reaction_pivot, attach_confirmations,
)
from test_ict3_confirm import (
    DIGITS, POI, RETEST, T0, bullish_bars, bullish_specs, make_bars,
    make_event, make_result, m1_bullish_bars, run,
)

LATE_CUTOFF = T0 + 11 * SECONDS["M5"]
FULL_CUTOFF = T0 + 10 * SECONDS["M5"] + SECONDS["M5"]
FORBIDDEN = frozenset({"entry", "order", "fill", "lots", "volume", "pnl",
                       "position", "cash_value"})
OBSERVED_FIELDS = (
    "confirmation_state", "defense_at", "m5_structure_kind", "m5_structure_at",
    "m1_structure_kind", "m1_structure_at", "stop_basis", "stop_price",
    "stop_observed_at", "target_policy_status", "target_price", "target_liquidity",
    "pending_evidence", "wait_reason", "reason", "current_state", "state_time",
    "transition_history", "entry_authorized", "mode",
)


def late_confirmation_bars():
    """Dos swings bajos: 1.198 conocible y 1.190 confirmado tras el retest."""
    specs = bullish_specs()
    specs[6] = (1.204, 1.198, 1.202)   # confirmado en i=8 (T0-600) -> válido
    specs[9] = (1.205, 1.190, 1.200)   # confirmado en i=11 (T0+600) -> futuro
    return make_bars("M5", T0 - 10 * SECONDS["M5"], specs)


def forbidden_keys(node):
    if isinstance(node, dict):
        return {key for key, value in node.items()
                if key in FORBIDDEN} | set().union(*(forbidden_keys(v) for v in node.values())) if node else set()
    if isinstance(node, (list, tuple)):
        return set().union(*(forbidden_keys(v) for v in node)) if node else set()
    return set()


class OriginSwingCausalityTests(unittest.TestCase):
    def test_origin_swing_requires_confirmation_not_after_retest(self):
        bars = late_confirmation_bars()
        closed = _closed_bars(bars, "M5", LATE_CUTOFF)
        lows = [p for p in _pivots(closed, DIGITS) if p["kind"] == "L"]
        late = [p for p in lows if p["price"] == 1.190]
        self.assertTrue(late, "el pivote tardío debe existir en la serie completa")
        self.assertLess(late[0]["at"], RETEST)
        self.assertGreater(late[0]["confirmed_at"], RETEST)

        origin = _origin_swing(closed, (), lows, 1, RETEST, DIGITS)
        self.assertIsNotNone(origin)
        self.assertEqual(origin["price"], 1.198)
        self.assertLessEqual(origin["confirmed_at"], RETEST)

    def test_late_confirmed_pivot_does_not_rewrite_stop_in_prefix_replay(self):
        bars = late_confirmation_bars()
        m1 = m1_bullish_bars()
        full = run([make_event()], bars, m1, LATE_CUTOFF)["ict3"]["events"][0]
        prefix_bars = tuple(row for row in bars
                            if row[0] + SECONDS["M5"] <= RETEST)
        prefix_m1 = tuple(row for row in m1
                          if row[0] + SECONDS["M1"] <= RETEST)
        replay = run([make_event()], prefix_bars, prefix_m1, RETEST)["ict3"]["events"][0]

        for field in ("stop_basis", "stop_price", "stop_observed_at"):
            with self.subTest(field=field):
                self.assertEqual(full[field], replay[field])
        # El pivote 1.190 se confirma en T0+600: no puede aparecer como stop
        # aunque la serie completa ya contenga esa vela.
        self.assertEqual(full["stop_basis"], "ORIGIN_SWING_INTACT")
        self.assertEqual(full["stop_price"], 1.198)
        self.assertEqual(replay["stop_price"], 1.198)
        self.assertNotIn(1.190, (full["stop_price"], replay["stop_price"]))
        self.assertFalse(forbidden_keys(full))
        self.assertIs(full["entry_authorized"], False)


class ReactionPivotCausalityTests(unittest.TestCase):
    def test_reaction_pivot_requires_confirmation_inside_interval(self):
        specs = bullish_specs()
        specs[8] = (1.214, 1.150, 1.211)   # swing bajo 1.150 confirmado en T0+300
        for tf, start, end in (("M5", T0 - 600, T0), ("M1", T0 - 600, T0)):
            with self.subTest(tf=tf):
                raw = make_bars(tf, T0 - 10 * SECONDS[tf], specs[:12])
                closed = _closed_bars(raw, tf, T0 + 11 * SECONDS[tf])
                pivots = _pivots(closed, DIGITS)
                candidates = [p for p in pivots if p["price"] == 1.150
                              and p["kind"] == "L"]
                self.assertTrue(candidates, "el pivote tardío debe existir")
                self.assertGreater(candidates[0]["confirmed_at"], end)
                found = _reaction_pivot(closed, 1, start, end, DIGITS)
                self.assertNotEqual(found and found["price"], 1.150)
                if found is not None:
                    self.assertLessEqual(found["confirmed_at"], end)

    def test_reaction_pivot_accepts_confirmation_within_interval(self):
        specs = bullish_specs()
        specs[8] = (1.214, 1.150, 1.211)
        raw = make_bars("M5", T0 - 10 * SECONDS["M5"], specs[:12])
        closed = _closed_bars(raw, "M5", T0 + 11 * SECONDS["M5"])
        found = _reaction_pivot(closed, 1, T0 - 600, T0 + 300, DIGITS)
        self.assertIsNotNone(found)
        self.assertEqual(found["price"], 1.150)
        self.assertLessEqual(found["confirmed_at"], T0 + 300)


class LoadContractTests(unittest.TestCase):
    def test_load_fields_have_declared_types(self):
        result = run([make_event()], bullish_bars(), m1_bullish_bars(), FULL_CUTOFF)
        load = result["ict3"]["load"]
        self.assertIsInstance(load["m5_loaded"], bool)
        self.assertIsInstance(load["m1_loaded"], bool)
        self.assertIsInstance(load["last_closed_m5"], int)
        self.assertIsInstance(load["last_closed_m1"], int)
        self.assertIsInstance(load["load_reason"], str)
        coverage = load["coverage"]
        for key in ("m5_bars_closed", "m1_bars_closed", "m5_first_closed",
                    "m1_first_closed", "events_requested"):
            self.assertIsInstance(coverage[key], int, key)
        event = result["ict3"]["events"][0]
        self.assertIsInstance(event["confirmation_state"], str)
        self.assertIsInstance(event["defense_at"], int)
        self.assertIsInstance(event["m5_structure_kind"], str)
        self.assertIsInstance(event["m5_structure_at"], int)
        self.assertIsInstance(event["m1_structure_kind"], str)
        self.assertIsInstance(event["m1_structure_at"], int)
        self.assertIsInstance(event["stop_basis"], str)
        self.assertIsInstance(event["stop_price"], (int, float))
        self.assertIsInstance(event["stop_observed_at"], int)
        self.assertIsInstance(event["target_policy_status"], str)
        self.assertIsInstance(event["target_price"], (int, float))
        self.assertIsInstance(event["target_liquidity"], list)
        for row in event["target_liquidity"]:
            self.assertIsInstance(row["kind"], str)
            self.assertIsInstance(row["price"], (int, float))
            self.assertIsInstance(row["observed_at"], int)
        self.assertIsInstance(event["pending_evidence"], list)
        self.assertIsInstance(event["wait_reason"], str)
        self.assertIs(event["entry_authorized"], False)
        self.assertEqual(event["mode"], MODE)

    def test_no_future_candle_is_exposed_at_cutoff(self):
        cutoff = T0 + 2 * SECONDS["M5"] + SECONDS["M5"]
        result = run([make_event()], bullish_bars(), m1_bullish_bars(), cutoff)
        load = result["ict3"]["load"]
        self.assertLessEqual(load["last_closed_m5"], cutoff)
        self.assertLessEqual(load["last_closed_m1"], cutoff)
        event = result["ict3"]["events"][0]
        for key in ("defense_at", "m5_structure_at", "m1_structure_at",
                    "stop_observed_at", "target_price", "state_time"):
            value = event[key]
            if value is not None:
                self.assertLessEqual(value, cutoff, key)
        for row in event["target_liquidity"]:
            self.assertLessEqual(row["observed_at"], cutoff)
        self.assertNotIn(1.250, [row["price"] for row in event["target_liquidity"]])

    def test_wait_reason_is_explicit_without_inventing_data(self):
        result = make_result([make_event()])
        attach_confirmations(result, None, RETEST, digits=DIGITS)
        event = result["ict3"]["events"][0]
        self.assertEqual(event["confirmation_state"], WAIT)
        self.assertEqual(result["ict3"]["load"]["load_reason"],
                         "LOWER_SOURCE_UNAVAILABLE")
        self.assertIn("M5_M1_CONFIRMATION_NOT_LOADED", event["pending_evidence"])
        self.assertIn("LOWER_SOURCE_UNAVAILABLE", event["reason"])
        self.assertIsNone(event["defense_at"])
        self.assertIsNone(event["stop_price"])
        self.assertEqual(event["current_state"], RETESTING)

    def test_observe_only_for_eurusd_gbpjpy_and_us30(self):
        for symbol in ("EURUSD", "GBPJPY", "US30"):
            with self.subTest(symbol=symbol):
                event = make_event(event_id="evt_" + symbol)
                event["symbol"] = symbol
                result = run([event], bullish_bars(), m1_bullish_bars(), FULL_CUTOFF)
                body = result["ict3"]
                self.assertEqual(body["mode"], MODE)
                self.assertEqual(result["mode"], MODE)
                self.assertFalse(forbidden_keys(result))
                for item in body["events"]:
                    self.assertIs(item["entry_authorized"], False)
                    self.assertEqual(item["mode"], MODE)
                    self.assertEqual(item["symbol"], symbol)
                    self.assertTrue(set(OBSERVED_FIELDS).issubset(item))


if __name__ == "__main__":
    unittest.main()
