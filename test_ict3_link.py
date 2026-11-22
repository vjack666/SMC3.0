"""Pruebas de enlace causal e ICT 3.0 M15 (Tareas 2 y 3 del Lote Hermes 02).

No importa ``ict.py`` ni ``test_ict.py``: el otro agente las está corrigiendo
en paralelo. Las zonas se obtienen del motor ICT 2.0 fijado (f453bf2) mediante
``build_ltf_canonical_feed`` o construyendo sus propios ``MarketObject``.
"""
import re
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str((Path(__file__).resolve().parent / "motor_smc" / "fuentes" / "ict2")))
from engine.ltf_canonical_feed import build_ltf_canonical_feed  # noqa: E402
from engine.market_object import MarketObject, ObjectState, ObjectType, Role  # noqa: E402

from ict3_link import (  # noqa: E402
    ACCEPTED, ACCEPTANCE_LOST, EXPANSION, POI_INVALID, RETESTING,
    CAUSAL_IMPULSE_RULE, DEFAULT_OBSERVATION_WINDOWS,
    advance_state, associate_pois, build_ict3_link,
)

T0 = 1_700_000_000
M15 = 900
BAR = lambda index: T0 + index * M15  # noqa: E731
CLOSE = lambda index: BAR(index) + M15  # noqa: E731
TS = lambda epoch: pd.Timestamp(epoch, unit="s", tz="UTC")  # noqa: E731

# Secuencia: cierre fuera en j=2, aceptación en j=3, FVG bull confirmado en j=4
# con vela impulsora (middle_bar) en j=3. Zona canónica [1.206, 1.210].
BREAK = {
    2: (1.100, 1.206, 1.100, 1.205),
    3: (1.206, 1.212, 1.204, 1.208),
    4: (1.208, 1.215, 1.210, 1.212),
    5: (1.212, 1.216, 1.211, 1.214),
    6: (1.214, 1.220, 1.207, 1.218),
    7: (1.218, 1.219, 1.195, 1.197),
}
DEFAULT_BAR = (1.10, 1.101, 1.099, 1.100)


def m15_frame(count, overrides=None):
    """Marco M15 totalmente cerrado, con `opened`, `closed` y `time`."""
    overrides = overrides or {}
    rows = []
    for index in range(count):
        open_, high, low, close = overrides.get(index, DEFAULT_BAR)
        opened = BAR(index)
        rows.append({
            "opened": opened, "closed": CLOSE(index), "time": TS(CLOSE(index)),
            "open": open_, "high": high, "low": low, "close": close,
        })
    return pd.DataFrame(rows)


def canonical_zones(frame, cutoff):
    """Zonas FVG/OB M15 reales del motor fijado, con prefijo hasta cutoff."""
    feed = build_ltf_canonical_feed(
        {"M15": frame}, TS(cutoff), exec_tf="M15", include_sequence=False, symbol="TEST")
    return feed["zones"]["M15"]


def accepted_break(**changes):
    event = {
        "event_id": "evt_link_test",
        "state": ACCEPTED,
        "direction": 1,
        "level_name": "PDH",
        "level": 1.20,
        "signal_open": BAR(2),
        "signal_close": CLOSE(2),
        "accept_open": BAR(3),
        "accept_time": CLOSE(3),
        "observed_at": CLOSE(3),
        "state_time": CLOSE(3),
    }
    event.update(changes)
    return event


def engine_object(zone_id, kind, direction, low, high, confirmation_index, impulse_index,
                  *, role=Role.REFINEMENT):
    """MarketObject canónico con contrato temporal candidate<=confirm<=tradable."""
    meta = {"middle_bar": impulse_index} if kind == "FVG" else {"followthrough": impulse_index}
    return MarketObject(
        id=zone_id, symbol="TEST",
        type=ObjectType.FVG if kind == "FVG" else ObjectType.ORDER_BLOCK,
        origin_tf="M15", role=role, direction=direction,
        zone_low=low, zone_high=high,
        creation_time=TS(CLOSE(confirmation_index)), state=ObjectState.ACTIVE,
        bar_index=confirmation_index, bar_time=TS(CLOSE(confirmation_index)),
        candidate_bar=max(0, impulse_index - 1), candidate_time=TS(CLOSE(max(0, impulse_index - 1))),
        confirmation_bar=confirmation_index, confirmation_time=TS(CLOSE(confirmation_index)),
        tradable_bar=confirmation_index, tradable_time=TS(CLOSE(confirmation_index)),
        meta=meta,
    )


class CausalAssociationTests(unittest.TestCase):
    def setUp(self):
        self.frame = m15_frame(12, BREAK)
        self.cutoff = CLOSE(11)
        self.zones = canonical_zones(self.frame, self.cutoff)
        self.event = accepted_break()

    def test_valid_fvg_same_direction_is_associated(self):
        link = associate_pois(self.event, self.zones, self.frame, self.cutoff)
        primary = next(row for row in link["poi_candidates"] if row["zone_id"] == link["primary_poi"])
        self.assertEqual(primary["zone_id"], "FVG_M15_4_BULL")
        self.assertEqual((primary["kind"], primary["direction"]), ("FVG", 1))
        self.assertIn("in_break_sequence=[2,3]", primary["association_reason"])
        self.assertIsNone(primary["rejected_reason"])
        self.assertTrue(link["accepted_with_poi"])
        self.assertEqual(link["link_state"], "accepted_with_poi")
        self.assertEqual(link["state"], ACCEPTED)  # estado principal intacto
        self.assertEqual(link["causal_window"]["rule"], CAUSAL_IMPULSE_RULE)
        self.assertEqual((link["causal_window"]["from_bar"], link["causal_window"]["to_bar"]), (2, 3))

    def test_valid_ob_same_direction_is_associated(self):
        ob = engine_object("OB_M15_3_BULL", "OB", 1, 1.200, 1.210, 3, 3)
        link = associate_pois(self.event, [ob], self.frame, self.cutoff)
        only = link["poi_candidates"][0]
        self.assertEqual(link["primary_poi"], "OB_M15_3_BULL")
        self.assertEqual(only["kind"], "OB")
        self.assertIn("in_break_sequence=[2,3]", only["association_reason"])
        self.assertIsNone(only["rejected_reason"])

    def test_opposite_direction_zone_is_rejected(self):
        bear = engine_object("FVG_M15_3_BEAR", "FVG", -1, 1.200, 1.210, 3, 3)
        link = associate_pois(self.event, [bear], self.frame, self.cutoff)
        row = link["poi_candidates"][0]
        self.assertEqual(row["rejected_reason"], "opposite_direction")
        self.assertIsNone(row["association_reason"])
        self.assertFalse(link["accepted_with_poi"])

    def test_zone_confirmed_before_signal_not_in_impulse_is_rejected(self):
        early = engine_object("FVG_M15_1_BULL", "FVG", 1, 1.100, 1.105, 1, 0)
        link = associate_pois(self.event, [early], self.frame, self.cutoff)
        self.assertEqual(link["poi_candidates"][0]["rejected_reason"],
                         "impulse_before_break_sequence")
        self.assertIsNone(link["primary_poi"])

    def test_zone_confirmed_after_cutoff_is_invisible(self):
        future = engine_object("FVG_M15_20_BULL", "FVG", 1, 1.200, 1.210, 20, 20)
        link = associate_pois(self.event, [future], self.frame, self.cutoff)
        row = link["poi_candidates"][0]
        self.assertEqual(row["rejected_reason"], "confirmed_after_cutoff")
        self.assertIsNone(row["first_touch_at"])
        self.assertIsNone(link["primary_poi"])

    def test_touch_before_confirmation_is_not_counted_as_retest(self):
        # La vela impulsora j=3 toca la zona [1.206, 1.210] antes de la
        # confirmación en j=4; solo j=6 la toca después, y este marco termina
        # en j=5. El objeto además miente con un first_touch_time anterior.
        frame = m15_frame(6, BREAK)
        zones = canonical_zones(frame, CLOSE(5))
        target = next(z for z in zones if z.id == "FVG_M15_4_BULL")
        target.first_touch_time = TS(CLOSE(3))
        link = associate_pois(self.event, zones, frame, CLOSE(5))
        primary = next(row for row in link["poi_candidates"] if row["zone_id"] == target.id)
        self.assertIsNone(primary["first_touch_at"])

    def test_prefix_replay_preserves_the_link_when_evidence_does_not_change(self):
        zones = self.zones  # construidas con el corte completo, con toques futuros
        short = associate_pois(self.event, zones, self.frame.iloc[:6], CLOSE(5))
        long = associate_pois(self.event, zones, self.frame, CLOSE(5))
        self.assertEqual(short, long)


class StateMachineTests(unittest.TestCase):
    def setUp(self):
        self.event = accepted_break()
        self.full_overrides = dict(BREAK)
        for index in range(8, 48):
            self.full_overrides[index] = (1.214, 1.217, 1.213, 1.215)

    def frame_and_zones(self, count, overrides):
        frame = m15_frame(count, overrides)
        return frame, canonical_zones(frame, CLOSE(count - 1))

    def test_acceptance_without_zone_keeps_principal_state(self):
        frame, _ = self.frame_and_zones(6, BREAK)
        link = build_ict3_link(self.event, [], frame, CLOSE(5))
        self.assertTrue(link["accepted_without_poi"])
        self.assertEqual(link["state"], ACCEPTED)
        self.assertEqual(link["current_state"], ACCEPTED)
        self.assertEqual(link["transition_history"], [])
        for window in link["window_results"].values():
            self.assertFalse(window["retest_within"])

    def test_acceptance_with_zone_but_no_touch_is_pending(self):
        frame, zones = self.frame_and_zones(6, BREAK)
        link = build_ict3_link(self.event, zones, frame, CLOSE(5))
        self.assertTrue(link["accepted_with_poi"])
        self.assertEqual(link["current_state"], ACCEPTED)
        self.assertEqual(link["transition_history"], [])
        self.assertFalse(link["window_results"]["4"]["window_complete"])

    def test_touch_exactly_at_zone_edge_enters_retesting(self):
        overrides = dict(BREAK)
        overrides[6] = (1.214, 1.220, 1.210, 1.218)  # low == zone_high
        overrides[7] = (1.218, 1.219, 1.213, 1.217)
        frame, zones = self.frame_and_zones(8, overrides)
        link = build_ict3_link(self.event, zones, frame, CLOSE(7))
        self.assertEqual(link["current_state"], RETESTING)
        self.assertEqual(len(link["transition_history"]), 1)
        self.assertEqual(link["transition_history"][0],
                         {"from": ACCEPTED, "to": RETESTING, "at": CLOSE(6),
                          "reason": "first_touch_after_confirmation"})
        self.assertEqual(link["retest_at"], CLOSE(6))

    def test_gap_through_zone_invalidates_after_touch(self):
        frame, zones = self.frame_and_zones(10, self.full_overrides)
        link = build_ict3_link(self.event, zones, frame, CLOSE(9))
        self.assertEqual([t["to"] for t in link["transition_history"]],
                         [RETESTING, POI_INVALID])
        self.assertEqual(link["transition_history"][1]["at"], CLOSE(7))
        self.assertEqual(link["transition_history"][1]["reason"],
                         "close_through_structural_boundary_against_direction")

    def test_acceptance_lost_before_retest(self):
        overrides = dict(BREAK)
        overrides[4] = (1.208, 1.215, 1.194, 1.195)  # cierra dentro de PDH
        frame = m15_frame(8, overrides)
        ob = engine_object("OB_M15_3_BULL", "OB", 1, 1.200, 1.210, 3, 3)
        link = build_ict3_link(self.event, [ob], frame, CLOSE(7))
        self.assertEqual(link["current_state"], ACCEPTANCE_LOST)
        self.assertEqual(link["transition_history"],
                         [{"from": ACCEPTED, "to": ACCEPTANCE_LOST, "at": CLOSE(4),
                           "reason": "m15_close_back_inside_level_before_retest"}])

    def test_poi_invalid_after_touch_without_gap(self):
        overrides = dict(BREAK)
        overrides[7] = (1.215, 1.217, 1.202, 1.199)  # cierra por debajo del límite
        frame, zones = self.frame_and_zones(9, overrides)
        link = build_ict3_link(self.event, zones, frame, CLOSE(8))
        self.assertEqual(link["current_state"], POI_INVALID)
        self.assertEqual([t["to"] for t in link["transition_history"]],
                         [RETESTING, POI_INVALID])

    def test_expansion_without_retest_for_all_four_windows(self):
        overrides = dict(self.full_overrides)
        overrides[6] = (1.214, 1.217, 1.212, 1.215)  # sin toque y sin volver dentro
        overrides[7] = (1.214, 1.217, 1.212, 1.215)
        frame, zones = self.frame_and_zones(48, overrides)
        link = build_ict3_link(self.event, zones, frame, CLOSE(47))
        self.assertEqual(link["current_state"], EXPANSION)
        self.assertEqual(sorted(int(w) for w in link["window_results"]),
                         list(DEFAULT_OBSERVATION_WINDOWS))
        for width in DEFAULT_OBSERVATION_WINDOWS:
            window = link["window_results"][str(width)]
            self.assertTrue(window["retest_within"] is False)
            self.assertTrue(window["window_complete"])
            self.assertEqual(window["state"], EXPANSION)
        self.assertEqual(link["transition_history"][-1],
                         {"from": ACCEPTED, "to": EXPANSION, "at": CLOSE(35),
                          "reason": "no_retest_within_max_observation_window_comparable_results"})

    def test_no_duplicate_transitions_while_price_stays_outside(self):
        overrides = dict(BREAK)
        for index in range(7, 24):
            overrides[index] = (1.214, 1.217, 1.212, 1.215)
        frame, zones = self.frame_and_zones(24, overrides)
        link = build_ict3_link(self.event, zones, frame, CLOSE(23))
        self.assertEqual(link["current_state"], RETESTING)
        self.assertEqual(len(link["transition_history"]), 1)

    def test_prefix_to_t_equals_full_series_at_t_for_each_transition(self):
        scenarios = {
            RETESTING: dict(self.full_overrides),
            POI_INVALID: dict(self.full_overrides),
            ACCEPTANCE_LOST: dict(self.full_overrides),
            EXPANSION: dict(self.full_overrides),
        }
        for state, overrides in scenarios.items():
            with self.subTest(state=state):
                if state == EXPANSION:
                    overrides = dict(self.full_overrides)
                    overrides[6] = (1.214, 1.217, 1.212, 1.215)
                    overrides[7] = (1.214, 1.217, 1.212, 1.215)
                    cutoff_bar = 35
                elif state == ACCEPTANCE_LOST:
                    overrides = dict(self.full_overrides)
                    overrides[4] = (1.208, 1.215, 1.194, 1.195)
                    cutoff_bar = 4
                elif state == POI_INVALID:
                    cutoff_bar = 7
                else:
                    cutoff_bar = 6
                frame, zones = self.frame_and_zones(48, overrides)
                cutoff = CLOSE(cutoff_bar)
                prefix = build_ict3_link(self.event, zones, frame.iloc[:cutoff_bar + 1], cutoff)
                full = build_ict3_link(self.event, zones, frame, cutoff)
                self.assertEqual(prefix, full)
                self.assertEqual(prefix["current_state"], state)
                self.assertEqual(prefix["transition_history"][-1]["at"], cutoff)

    def test_no_order_entry_stop_target_or_m5_fields(self):
        frame, zones = self.frame_and_zones(10, self.full_overrides)
        link = build_ict3_link(self.event, zones, frame, CLOSE(9))
        blob = repr(link)
        for forbidden in ("OBSERVABLE_SETUP",):
            self.assertNotIn(forbidden, blob)
        self.assertIsNone(re.search(r"\bM5\b|\bM1\b", blob))
        for row in link["poi_candidates"]:
            self.assertEqual(set(row), {
                "zone_id", "kind", "direction", "low", "high", "confirmed_at",
                "first_touch_at", "association_reason", "rejected_reason"})
        for item in link["transition_history"]:
            self.assertEqual(set(item), {"from", "to", "at", "reason"})
        self.assertFalse(any(key in link for key in
                             ("entry", "stop", "target", "sl", "tp", "price", "volume", "lots")))


def assert_window_states_are_causal(testcase, link, cutoff):
    """Aserción general: ninguna ventana usa evidencia posterior a su horizon.

    Para cada ventana se recalcula el estado con las transiciones con
    ``at <= horizon`` (o ``<= cutoff`` si la ventana está incompleta) y se
    exige que coincida con el publicado. ``retest_within`` respeta el mismo
    límite. Así cualquier fuga temporal desde el futuro queda detectada.
    """
    for width, window in link["window_results"].items():
        bound = window["horizon"] if window["horizon"] is not None else cutoff
        prior = [item for item in link["transition_history"] if item["at"] <= bound]
        if prior:
            expected = prior[-1]["to"]
        elif window["window_complete"] and not window["retest_within"]:
            expected = EXPANSION
        else:
            expected = ACCEPTED
        testcase.assertEqual(window["state"], expected,
                             f"window {width}: estado filtrado por horizon {bound}")
        retests = [item["at"] for item in link["transition_history"]
                   if item["to"] == RETESTING and item["at"] <= bound]
        testcase.assertEqual(window["retest_within"], bool(retests),
                             f"window {width}: retest_within filtrado por horizon {bound}")


class CausalRegressionTests(unittest.TestCase):
    """Pruebas diagnósticas exigidas por C4, C5 y C6 (Lote Hermes 02)."""

    def setUp(self):
        self.event = accepted_break()
        self.full_overrides = dict(BREAK)
        for index in range(8, 48):
            self.full_overrides[index] = (1.214, 1.217, 1.213, 1.215)

    def frame_and_zones(self, count, overrides):
        frame = m15_frame(count, overrides)
        return frame, canonical_zones(frame, CLOSE(count - 1))

    def expansion_overrides(self, *, touch_bar=None):
        overrides = dict(self.full_overrides)
        overrides[6] = (1.214, 1.217, 1.212, 1.215)  # sin toque
        overrides[7] = (1.214, 1.217, 1.212, 1.215)  # sin tránsito
        if touch_bar is not None:
            overrides[touch_bar] = (1.214, 1.220, 1.207, 1.216)  # toque tardío
        return overrides

    # ------------------------------------------------------------------ C4 --
    def test_c4_late_touch_at_bar_40_cannot_rewrite_expansion(self):
        """Corte de 32 M15 y replay con toque en la vela 40: mismo estado terminal."""
        overrides = self.expansion_overrides(touch_bar=40)
        frame = m15_frame(41, overrides)
        zones = canonical_zones(frame, CLOSE(40))
        short = build_ict3_link(self.event, zones, frame.iloc[:36], CLOSE(35))
        at_horizon = build_ict3_link(self.event, zones, frame, CLOSE(35))
        long = build_ict3_link(self.event, zones, frame, CLOSE(40))

        expected_transition = {
            "from": ACCEPTED, "to": EXPANSION, "at": CLOSE(35),
            "reason": "no_retest_within_max_observation_window_comparable_results",
        }
        for name, link in (("32 M15", short), ("at horizon", at_horizon), ("bar 40", long)):
            with self.subTest(replay=name):
                self.assertEqual(link["current_state"], EXPANSION)
                self.assertEqual(link["transition_history"], [expected_transition])
                self.assertIsNone(link["retest_at"])
                assert_window_states_are_causal(self, link, CLOSE(35) if name != "bar 40" else CLOSE(40))
        # El prefijo hasta el horizonte y el replay completo son idénticos.
        self.assertEqual(short, at_horizon)
        self.assertEqual(short["transition_history"], long["transition_history"])
        self.assertEqual(short["window_results"], long["window_results"])

    # ------------------------------------------------------------------ C5 --
    def test_c5_retest_within_4_and_later_invalidation(self):
        """Retest en la ventana 4; POI_INVALID en la 8 no debe filtrarse a la 4."""
        overrides = dict(self.full_overrides)
        overrides[7] = (1.214, 1.217, 1.212, 1.215)  # neutralizar el through de BREAK
        overrides[8] = (1.210, 1.211, 1.200, 1.204)  # cierre < zlo=1.206 tras el retest
        frame, zones = self.frame_and_zones(12, overrides)
        link = build_ict3_link(self.event, zones, frame, CLOSE(11))

        self.assertEqual([item["to"] for item in link["transition_history"]],
                         [RETESTING, POI_INVALID])
        self.assertEqual(link["transition_history"][0]["at"], CLOSE(6))
        self.assertEqual(link["transition_history"][1]["at"], CLOSE(8))
        four = link["window_results"]["4"]
        eight = link["window_results"]["8"]
        self.assertTrue(four["retest_within"])
        self.assertEqual(four["state"], RETESTING)
        self.assertEqual(eight["state"], POI_INVALID)
        assert_window_states_are_causal(self, link, CLOSE(11))

    def test_c5_no_window_state_depends_on_a_later_transition(self):
        """Aserción general sobre todos los escenarios y las 4 ventanas 4/8/16/32."""
        scenarios = {}

        gap = self.expansion_overrides(touch_bar=40)
        scenarios["expansion"] = (m15_frame(41, gap), CLOSE(40))

        late = dict(self.full_overrides)
        late[7] = (1.214, 1.217, 1.212, 1.215)
        late[8] = (1.210, 1.211, 1.200, 1.204)
        scenarios["late_invalidation"] = (m15_frame(12, late), CLOSE(11))

        for name, (frame, cutoff) in scenarios.items():
            with self.subTest(scenario=name):
                zones = canonical_zones(frame, cutoff)
                link = build_ict3_link(self.event, zones, frame, cutoff)
                self.assertEqual(sorted(int(w) for w in link["window_results"]),
                                 list(DEFAULT_OBSERVATION_WINDOWS))
                assert_window_states_are_causal(self, link, cutoff)

    # ------------------------------------------------------------------ C6 --
    def test_c6_bull_gap_skipping_zone_invalidates_without_contact(self):
        """Gap alcista: cierra 1.205 < low 1.210 sin tocar la zona ni perder PDH."""
        overrides = dict(BREAK)
        for index in range(4, 10):
            overrides[index] = (1.204, 1.206, 1.202, 1.205)
        frame = m15_frame(10, overrides)
        ob = engine_object("OB_M15_3_BULL", "OB", 1, 1.210, 1.220, 3, 3)
        link = build_ict3_link(self.event, [ob], frame, CLOSE(9))

        row = frame.iloc[4]
        self.assertLess(row["high"], 1.210)  # sin contacto geométrico
        self.assertGreater(row["close"], self.event["level"])  # conserva el PDH roto
        self.assertEqual(link["current_state"], POI_INVALID)
        self.assertEqual([item["to"] for item in link["transition_history"]], [POI_INVALID])
        self.assertEqual(link["transition_history"][0], {
            "from": ACCEPTED, "to": POI_INVALID, "at": CLOSE(4),
            "reason": "close_through_structural_boundary_against_direction",
        })
        self.assertIsNone(link["retest_at"])

    def test_c6_bear_gap_skipping_zone_invalidates_without_contact(self):
        """Gap bajista: cierra 1.225 > high 1.220 sin tocar la zona ni perder PDL."""
        overrides = {}
        for index in range(10):
            overrides[index] = (1.230, 1.231, 1.228, 1.229)
        overrides[2] = (1.240, 1.240, 1.224, 1.226)  # primer cierre fuera a la baja
        overrides[3] = (1.226, 1.228, 1.220, 1.222)  # aceptación
        for index in range(4, 10):
            overrides[index] = (1.224, 1.228, 1.223, 1.225)
        frame = m15_frame(10, overrides)
        ob = engine_object("OB_M15_3_BEAR", "OB", -1, 1.210, 1.220, 3, 3)
        event = accepted_break(direction=-1, level_name="PDL", level=1.230)
        link = build_ict3_link(event, [ob], frame, CLOSE(9))

        row = frame.iloc[4]
        self.assertGreater(row["low"], 1.220)  # sin contacto geométrico
        self.assertLess(row["close"], event["level"])  # conserva el PDL roto
        self.assertEqual(link["current_state"], POI_INVALID)
        self.assertEqual([item["to"] for item in link["transition_history"]], [POI_INVALID])
        self.assertEqual(link["transition_history"][0], {
            "from": ACCEPTED, "to": POI_INVALID, "at": CLOSE(4),
            "reason": "close_through_structural_boundary_against_direction",
        })
        self.assertIsNone(link["retest_at"])

    def test_c6_daily_level_loss_precedes_zone_invalidation_in_both_directions(self):
        """Precedencia documentada: perder PDH/PDL gana sobre atravesar la POI."""
        # Alcista: cierre 1.198 < PDH 1.200 y < low 1.210 -> ACCEPTANCE_LOST.
        bull_overrides = dict(BREAK)
        for index in range(4, 8):
            bull_overrides[index] = (1.200, 1.201, 1.197, 1.198)
        bull_frame = m15_frame(8, bull_overrides)
        bull_ob = engine_object("OB_M15_3_BULL", "OB", 1, 1.210, 1.220, 3, 3)
        bull_link = build_ict3_link(self.event, [bull_ob], bull_frame, CLOSE(7))
        self.assertEqual([item["to"] for item in bull_link["transition_history"]],
                         [ACCEPTANCE_LOST])
        self.assertEqual(bull_link["transition_history"][0]["reason"],
                         "m15_close_back_inside_level_before_retest")

        # Bajista: cierre 1.232 > PDL 1.230 y > high 1.220 -> ACCEPTANCE_LOST.
        bear_overrides = {}
        for index in range(8):
            bear_overrides[index] = (1.230, 1.231, 1.228, 1.229)
        bear_overrides[2] = (1.240, 1.240, 1.224, 1.226)
        bear_overrides[3] = (1.226, 1.228, 1.220, 1.222)
        for index in range(4, 8):
            bear_overrides[index] = (1.231, 1.233, 1.230, 1.232)
        bear_frame = m15_frame(8, bear_overrides)
        bear_ob = engine_object("OB_M15_3_BEAR", "OB", -1, 1.210, 1.220, 3, 3)
        bear_event = accepted_break(direction=-1, level_name="PDL", level=1.230)
        bear_link = build_ict3_link(bear_event, [bear_ob], bear_frame, CLOSE(7))
        self.assertEqual([item["to"] for item in bear_link["transition_history"]],
                         [ACCEPTANCE_LOST])
        self.assertEqual(bear_link["transition_history"][0]["reason"],
                         "m15_close_back_inside_level_before_retest")


if __name__ == "__main__":
    unittest.main()
