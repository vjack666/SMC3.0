"""Pruebas puras de ict3_confirm: sin MT5, sin servidor, sin data/."""
import copy
import unittest

from ict3_confirm import (
    CONFIRMED, MODE, NO_STOP, OBSERVABLE, RETESTING, SECONDS, WAIT,
    attach_confirmations,
)

T0 = 1_000_500          # divisible entre 300 y 60
RETEST = T0 + SECONDS["M5"]
DIGITS = 3
LEVEL = 1.200
POI = (1.195, 1.205)


def make_bars(tf, start, specs):
    """specs -> filas (time, open, high, low, close) con open neutro."""
    step = SECONDS[tf]
    return tuple((start + i * step, round((h + low) / 2, DIGITS), h, low, c)
                 for i, (h, low, c) in enumerate(specs))


def bullish_specs():
    """Serie M5 alcista con swings de 2 velas, defensa, CHOCH y liquidez."""
    return [
        (1.208, 1.202, 1.205),   # -10
        (1.206, 1.201, 1.203),   # -9
        (1.204, 1.200, 1.200),   # -8  swing low de origen 1.200
        (1.207, 1.201, 1.204),   # -7
        (1.210, 1.202, 1.208),   # -6
        (1.216, 1.206, 1.212),   # -5  swing high 1.216
        (1.212, 1.204, 1.206),   # -4
        (1.209, 1.202, 1.204),   # -3
        (1.214, 1.203, 1.211),   # -2  swing high 1.214 (lower high)
        (1.209, 1.202, 1.205),   # -1
        (1.203, 1.197, 1.201),   #  0  retest + defensa
        (1.212, 1.199, 1.208),   #  1
        (1.218, 1.206, 1.216),   #  2  CHOCH por cierre
        (1.222, 1.214, 1.220),   #  3
        (1.228, 1.220, 1.226),   #  4
        (1.232, 1.226, 1.230),   #  5
        (1.236, 1.230, 1.234),   #  6
        (1.240, 1.234, 1.238),   #  7
        (1.250, 1.240, 1.248),   #  8  swing high 1.250 (liquidez lejana)
        (1.248, 1.242, 1.244),   #  9
        (1.246, 1.240, 1.242),   # 10
    ]


def bullish_bars():
    return make_bars("M5", T0 - 10 * SECONDS["M5"], bullish_specs())


def m1_bullish_bars():
    specs = [
        (1.206, 1.200, 1.203), (1.210, 1.202, 1.206),
        (1.214, 1.204, 1.212),  # swing high 1.214 confirmado en i=4
        (1.208, 1.203, 1.206), (1.210, 1.204, 1.208),
        (1.216, 1.208, 1.215),  # ruptura por cierre
        (1.220, 1.214, 1.218), (1.224, 1.218, 1.222), (1.228, 1.222, 1.226),
    ]
    return make_bars("M1", T0, specs)


def make_event(state=RETESTING, *, direction=1, level=LEVEL, retest_at=RETEST,
               poi=POI, event_id="evt_test"):
    candidates = []
    if poi is not None:
        candidates = [{"zone_id": "z1", "kind": "FVG", "direction": direction,
                       "low": poi[0], "high": poi[1], "confirmed_at": T0 - 4 * SECONDS["M5"],
                       "first_touch_at": retest_at}]
    return {
        "event_id": event_id, "symbol": "EURUSD", "session_open": T0 - 86400,
        "observed_at": T0 - 9 * SECONDS["M5"], "state_time": RETEST - SECONDS["M5"],
        "accept_time": T0 - 5 * SECONDS["M5"], "level": level,
        "direction": direction, "poi_candidates": candidates,
        "primary_poi": "z1" if poi is not None else None,
        "retest_at": retest_at, "current_state": state,
        "transition_history": [{"from": "ACCEPTED_BREAK_WAIT_RETEST", "to": state,
                                "at": retest_at, "reason": "first_touch_after_confirmation"}],
        "window_results": {"4": {"state": state}},
        "pending_evidence": ["M5_M1_CONFIRMATION_NOT_LOADED", "STRUCTURAL_STOP_NOT_DEFINED"],
        "wait_reason": "M5_M1_CONFIRMATION_NOT_LOADED; STRUCTURAL_STOP_NOT_DEFINED",
        "entry_authorized": False,
    }


def make_result(events):
    return {"schema_version": "0.2-research", "mode": MODE,
            "ict3": {"schema_version": "0.2-research", "mode": MODE, "events": events}}


def source(m5=None, m1=None):
    return (DIGITS, 10 ** -DIGITS, {"M5": m5 or (), "M1": m1 or ()}, ())


def run(events, m5=None, m1=None, cutoff=None, **kwargs):
    result = make_result(events)
    if cutoff is None:
        cutoff = T0 + 10 * SECONDS["M5"] + SECONDS["M5"]
    returned = attach_confirmations(result, source(m5, m1), cutoff,
                                    digits=DIGITS, **kwargs)
    assert returned is result
    return result


class OnDemandLoadingTests(unittest.TestCase):
    def test_no_load_without_retest(self):
        event = make_event(state="ACCEPTED_BREAK_WAIT_RETEST")
        original = copy.deepcopy(event)
        result = run([event], bullish_bars(), m1_bullish_bars())
        self.assertNotIn("confirmation_state", event)
        self.assertEqual(result["ict3"]["load"]["m5_loaded"], False)
        self.assertEqual(result["ict3"]["load"]["m1_loaded"], False)
        self.assertEqual(result["ict3"]["load"]["load_reason"],
                         "NOT_REQUESTED_NO_M15_RETEST")
        self.assertEqual(result["ict3"]["load"]["coverage"]["events_requested"], 0)
        for key, value in original.items():
            self.assertEqual(event[key], value)
        self.assertIs(event["entry_authorized"], False)
        self.assertEqual(event["mode"], MODE)

    def test_load_with_retest_records_coverage_and_last_closed(self):
        cutoff = T0 + 10 * SECONDS["M5"] + SECONDS["M5"]
        m5 = bullish_bars()
        m1 = m1_bullish_bars()
        result = run([make_event()], m5, m1, cutoff)
        load = result["ict3"]["load"]
        self.assertTrue(load["m5_loaded"])
        self.assertTrue(load["m1_loaded"])
        self.assertEqual(load["load_reason"], "M5_M1_LOADED")
        self.assertEqual(load["last_closed_m5"], cutoff)
        self.assertEqual(load["coverage"]["m5_bars_closed"], 21)
        self.assertEqual(load["coverage"]["events_requested"], 1)
        self.assertLessEqual(load["last_closed_m1"], cutoff)
        self.assertEqual(load["coverage"]["m1_bars_closed"], 9)

    def test_missing_source_waits_without_inventing_data(self):
        result = make_result([make_event()])
        returned = attach_confirmations(result, None, RETEST + 10 * SECONDS["M5"],
                                        digits=DIGITS)
        self.assertIs(returned, result)
        event = result["ict3"]["events"][0]
        self.assertEqual(event["confirmation_state"], WAIT)
        self.assertEqual(result["ict3"]["load"]["load_reason"],
                         "LOWER_SOURCE_UNAVAILABLE")
        self.assertIn("M5_M1_CONFIRMATION_NOT_LOADED", event["pending_evidence"])
        self.assertIn("LOWER_SOURCE_UNAVAILABLE", event["reason"])
        self.assertIsNone(event["defense_at"])
        self.assertIsNone(event["m5_structure_kind"])
        self.assertIsNone(event["stop_price"])
        self.assertEqual(event["current_state"], RETESTING)
        self.assertIs(event["entry_authorized"], False)

    def test_loader_error_wins_over_present_bars(self):
        result = make_result([make_event()])
        attach_confirmations(result, source(bullish_bars(), m1_bullish_bars()),
                             T0 + 11 * SECONDS["M5"], digits=DIGITS,
                             loader_error="MT5 timeout M5/M1")
        event = result["ict3"]["events"][0]
        self.assertEqual(result["ict3"]["load"]["load_reason"],
                         "LOWER_SOURCE_ERROR: MT5 timeout M5/M1")
        self.assertEqual(event["confirmation_state"], WAIT)
        self.assertFalse(result["ict3"]["load"]["m5_loaded"])
        self.assertIn("MT5 timeout M5/M1", event["reason"])

    def test_terminal_states_are_not_rewritten(self):
        terminal = make_event(state="EXPANSION_NO_ENTRY")
        before = copy.deepcopy(terminal)
        result = run([terminal, make_event()], bullish_bars(), m1_bullish_bars())
        self.assertEqual(terminal["current_state"], "EXPANSION_NO_ENTRY")
        self.assertNotIn("confirmation_state", terminal)
        self.assertEqual(terminal["transition_history"], before["transition_history"])
        self.assertEqual(terminal["pending_evidence"], before["pending_evidence"])
        self.assertEqual(result["ict3"]["load"]["coverage"]["events_requested"], 1)
        self.assertIs(terminal["entry_authorized"], False)
        self.assertEqual(terminal["mode"], MODE)


class StructuralConfirmationTests(unittest.TestCase):
    def test_valid_defense_at_close(self):
        result = run([make_event()], bullish_bars(), cutoff=RETEST)
        event = result["ict3"]["events"][0]
        self.assertEqual(event["defense_at"], RETEST)
        self.assertNotIn("DEFENSE_NOT_CONFIRMED_M5", event["pending_evidence"])
        self.assertIn("M5_STRUCTURE_NOT_CONFIRMED", event["pending_evidence"])

    def test_invalid_defense_keeps_waiting(self):
        specs = bullish_specs()
        specs[10] = (1.203, 1.193, 1.198)   # toca la POI pero cierra dentro del nivel
        bars = make_bars("M5", T0 - 10 * SECONDS["M5"], specs)
        result = run([make_event()], bars, cutoff=RETEST)
        event = result["ict3"]["events"][0]
        self.assertIsNone(event["defense_at"])
        self.assertEqual(event["confirmation_state"], WAIT)
        self.assertIn("DEFENSE_NOT_CONFIRMED_M5", event["pending_evidence"])

    def test_m5_bos_choch_and_mss_are_deterministic(self):
        # CHOCH: lower high 1.214 tras el high 1.216, roto por cierre en i=2.
        event = run([make_event()], bullish_bars())["ict3"]["events"][0]
        self.assertEqual(event["m5_structure_kind"], "CHOCH")
        self.assertEqual(event["m5_structure_at"], T0 + 2 * SECONDS["M5"] + SECONDS["M5"])

        # BOS: high previo 1.210 más bajo que el swing roto 1.214.
        specs = bullish_specs()
        specs[5] = (1.210, 1.206, 1.208)
        specs[6] = (1.208, 1.204, 1.206)
        specs[7] = (1.206, 1.202, 1.204)
        bars = make_bars("M5", T0 - 10 * SECONDS["M5"], specs)
        event = run([make_event()], bars)["ict3"]["events"][0]
        self.assertEqual(event["m5_structure_kind"], "BOS")

        # MSS: un solo swing previo, sin contexto de tendencia previa.
        mss = [(1.200, 1.196, 1.198), (1.202, 1.198, 1.200),
               (1.204, 1.200, 1.202), (1.206, 1.202, 1.204),
               (1.208, 1.203, 1.206),
               (1.210, 1.197, 1.202),   # retest / defensa
               (1.216, 1.200, 1.206),   # swing high aislado
               (1.214, 1.204, 1.210),
               (1.212, 1.206, 1.208),
               (1.220, 1.208, 1.218)]   # ruptura por cierre -> MSS
        bars = make_bars("M5", T0 - 5 * SECONDS["M5"], mss)
        event = run([make_event()], bars,
                    cutoff=T0 + 5 * SECONDS["M5"] + SECONDS["M5"])["ict3"]["events"][0]
        self.assertEqual(event["m5_structure_kind"], "MSS")

    def test_m5_structure_not_confirmed_by_wick_or_missing_pivot(self):
        # La mecha rompe el swing, pero el cierre no.
        specs = bullish_specs()
        specs[12] = (1.220, 1.206, 1.213)   # high > 1.214, close < 1.214
        bars = make_bars("M5", T0 - 10 * SECONDS["M5"], specs)
        event = run([make_event()], bars,
                    cutoff=T0 + 3 * SECONDS["M5"])["ict3"]["events"][0]
        self.assertIsNone(event["m5_structure_kind"])
        self.assertEqual(event["confirmation_state"], WAIT)
        self.assertIn("M5_STRUCTURE_NOT_CONFIRMED", event["pending_evidence"])

        # Sin swing previo confirmado tampoco hay estructura.
        rising = [(1.200 + i * 0.002, 1.196 + i * 0.002, 1.198 + i * 0.002)
                  for i in range(12)]
        rising[5] = (1.216, 1.197, 1.202)   # retest / defensa dentro de serie monótona
        bars = make_bars("M5", T0 - 5 * SECONDS["M5"], rising)
        event = run([make_event()], bars,
                    cutoff=RETEST + SECONDS["M5"])["ict3"]["events"][0]
        self.assertIsNone(event["m5_structure_kind"])

    def test_m1_alone_never_replaces_m5(self):
        rising = [(1.200 + i * 0.002, 1.196 + i * 0.002, 1.198 + i * 0.002)
                  for i in range(8)]
        rising[0] = (1.204, 1.197, 1.201)   # retest M5 sin estructura M5
        m5 = make_bars("M5", T0, rising)
        result = run([make_event()], m5, m1_bullish_bars())
        event = result["ict3"]["events"][0]
        self.assertIsNone(event["m5_structure_kind"])
        self.assertEqual(event["m1_structure_kind"], "MSS")
        self.assertEqual(event["confirmation_state"], WAIT)
        self.assertEqual(event["current_state"], RETESTING)
        self.assertIn("M5_STRUCTURE_NOT_CONFIRMED", event["pending_evidence"])


class StructuralStopTests(unittest.TestCase):
    def test_origin_swing_has_authority(self):
        result = run([make_event()], bullish_bars(), m1_bullish_bars())
        event = result["ict3"]["events"][0]
        self.assertEqual(event["stop_basis"], "ORIGIN_SWING_INTACT")
        self.assertEqual(event["stop_price"], 1.200)
        self.assertEqual(event["stop_observed_at"], T0 - 8 * SECONDS["M5"] + SECONDS["M5"])

    def test_m5_reaction_extreme_when_origin_is_absent(self):
        specs = [(1.210, 1.190, 1.200), (1.212, 1.192, 1.202),
                 (1.214, 1.194, 1.204),
                 (1.216, 1.196, 1.206),   # retest / defensa
                 (1.214, 1.195, 1.204),
                 (1.212, 1.193, 1.202),   # swing low 1.193 confirmado en i=4
                 (1.218, 1.197, 1.210), (1.220, 1.199, 1.216)]
        bars = make_bars("M5", T0 - 3 * SECONDS["M5"], specs)
        event = run([make_event()], bars, cutoff=T0 + 5 * SECONDS["M5"])["ict3"]["events"][0]
        self.assertEqual(event["stop_basis"], "M5_REACTION_EXTREME")
        self.assertEqual(event["stop_price"], 1.193)

    def test_m1_confirmed_extreme_is_last_resort(self):
        m5 = [(1.210, 1.202, 1.206), (1.212, 1.204, 1.208),
              (1.214, 1.206, 1.210), (1.216, 1.208, 1.212),
              (1.218, 1.210, 1.214), (1.220, 1.212, 1.216)]
        m1 = [(1.220, 1.205, 1.210), (1.218, 1.204, 1.208),
              (1.216, 1.203, 1.206), (1.214, 1.202, 1.204),
              (1.212, 1.201, 1.202),
              (1.210, 1.200, 1.205),   # swing low 1.200 tras el retest
              (1.214, 1.202, 1.210), (1.218, 1.204, 1.214), (1.222, 1.208, 1.218)]
        result = run([make_event()], make_bars("M5", T0, m5),
                     make_bars("M1", T0, m1), cutoff=T0 + 9 * SECONDS["M1"])
        event = result["ict3"]["events"][0]
        self.assertEqual(event["stop_basis"], "M1_CONFIRMED_EXTREME")
        self.assertEqual(event["stop_price"], 1.200)

    def test_no_structural_stop_is_pending_not_invalidation(self):
        rising = [(1.200 + i * 0.002, 1.196 + i * 0.002, 1.198 + i * 0.002)
                  for i in range(8)]
        rising[0] = (1.204, 1.197, 1.201)
        event = run([make_event()], make_bars("M5", T0, rising))["ict3"]["events"][0]
        self.assertEqual(event["stop_basis"], NO_STOP)
        self.assertIsNone(event["stop_price"])
        self.assertIn("NO_STRUCTURAL_STOP", event["pending_evidence"])
        self.assertEqual(event["current_state"], RETESTING)   # no cambia a inválido


class TargetAndSetupTests(unittest.TestCase):
    def test_target_policy_status_observed_when_liquidity_is_too_close(self):
        specs = bullish_specs()
        specs[8] = (1.204, 1.150, 1.160)   # swing de origen lejano => R grande
        bars = make_bars("M5", T0 - 10 * SECONDS["M5"], specs)
        event = run([make_event()], bars)["ict3"]["events"][0]
        self.assertEqual(event["stop_basis"], "ORIGIN_SWING_INTACT")
        self.assertEqual(event["target_policy_status"], "TP1_BELOW_3R")
        self.assertEqual(event["current_state"], RETESTING)
        self.assertIs(event["entry_authorized"], False)

    def test_observable_setup_never_authorizes_an_order(self):
        result = run([make_event()], bullish_bars(), m1_bullish_bars())
        event = result["ict3"]["events"][0]
        self.assertEqual(event["current_state"], OBSERVABLE)
        self.assertEqual(event["confirmation_state"], CONFIRMED)
        self.assertEqual(event["target_policy_status"], "SATISFIED_TP1_3R_TP2_5R")
        self.assertIs(event["entry_authorized"], False)
        self.assertEqual(event["mode"], MODE)
        self.assertEqual(result["ict3"]["mode"], MODE)
        forbidden = {"entry", "order", "fill", "lots", "volume", "pnl"}
        self.assertFalse(forbidden.intersection(event))
        self.assertEqual(event["transition_history"][-1]["to"], OBSERVABLE)
        self.assertEqual(event["event_id"], "evt_test")
        self.assertEqual(event["observed_at"], T0 - 9 * SECONDS["M5"])

    def test_no_future_bars_are_used(self):
        bars = bullish_bars()
        cutoff = T0 + 2 * SECONDS["M5"] + SECONDS["M5"]
        event = run([make_event()], bars, cutoff=cutoff)["ict3"]["events"][0]
        self.assertEqual(event["m5_structure_at"], cutoff)
        far = {"kind": "M5_SWING", "price": 1.250}
        self.assertNotIn(far["price"], [row["price"] for row in event["target_liquidity"]])
        self.assertEqual(run([make_event()], bars)["ict3"]["events"][0]
                         ["target_policy_status"], "SATISFIED_TP1_3R_TP2_5R")
        self.assertIn(1.250, [row["price"] for row in
                              run([make_event()], bars)["ict3"]["events"][0]
                              ["target_liquidity"]])

    def test_prefix_replay_equals_full_series_at_same_cutoff(self):
        bars = bullish_bars()
        m1 = m1_bullish_bars()
        for i in (1, 2, 5, 10):
            cutoff = T0 + i * SECONDS["M5"] + SECONDS["M5"]
            prefix = tuple(row for row in bars if row[0] + SECONDS["M5"] <= cutoff)
            prefix_m1 = tuple(row for row in m1 if row[0] + SECONDS["M1"] <= cutoff)
            full = run([make_event()], bars, m1, cutoff)
            replay = run([make_event()], prefix, prefix_m1, cutoff)
            self.assertEqual(replay, full, "prefijo divergente en i=" + str(i))
        early = run([make_event()], bars, cutoff=RETEST)["ict3"]["events"][0]
        self.assertEqual(early["confirmation_state"], WAIT)
        self.assertEqual(early["current_state"], RETESTING)

    def test_bearish_rules_are_symmetric(self):
        # Reflejo de la serie alcista: swing high de origen 1.200, CHOCH bajista.
        specs = [(2.000 - low, 2.000 - h, 2.000 - c)
                 for h, low, c in bullish_specs()]
        specs[0] = (2.000 - 1.202, 2.000 - 1.208, 2.000 - 1.205)
        event = make_event(direction=-1, level=2.000 - LEVEL,
                           poi=(2.000 - POI[1], 2.000 - POI[0]))
        bars = make_bars("M5", T0 - 10 * SECONDS["M5"], specs)
        result = run([event], bars)["ict3"]["events"][0]
        self.assertEqual(result["m5_structure_kind"], "CHOCH")
        self.assertEqual(result["stop_basis"], "ORIGIN_SWING_INTACT")
        self.assertEqual(result["stop_price"], 0.800)
        self.assertEqual(result["current_state"], OBSERVABLE)
        self.assertIs(result["entry_authorized"], False)


if __name__ == "__main__":
    unittest.main()
