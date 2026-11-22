"""Contrato de esquema del bloque ``ict3`` verificado sobre payloads reales.

Fase 5, agente de contrato y esquema.  Los payloads NO se escriben a mano: se
producen con las funciones reales del pipeline -- ``ict.analyze_cached`` (que
internamente usa ``ict.ict3_payload`` + ``ict3_link.link_breaks``) y
``ict3_confirm.attach_confirmations`` -- a partir de velas cerradas sintéticas
estructuralmente válidas.  No se contacta MT5, no se escribe en ``data/`` y no
se crean rutas de orden, cuenta ni posición.

Se comprueba que:
  * los campos obligatorios están presentes y con el tipo declarado;
  * ``entry_authorized`` es ``False`` en TODOS los eventos;
  * no aparecen ``entry/order/fill/lots/volume/pnl`` en ningún nivel;
  * los casos de espera legítima (sin retest, sin M5, sin stop, sin liquidez)
    se explican con un motivo explícito y sin inventar evidencia.

Este archivo es autónomo: no importa ``ict3_contract`` (que puede cambiar en
paralelo) para que la verificación del esquema no dependa de otro agente.
"""
from __future__ import annotations

import copy
import unittest

from ict import analyze_cached, closed_frame, ict3_payload
from ict3_confirm import MODE, attach_confirmations

SCHEMA_VERSION = "0.2-research"
NUMBER = (int, float)

# Especificaciones (tipo, nullable).  Espejo del diccionario
# docs/ict3/FASE_05_DICCIONARIO_CAMPOS.md.
TOP_LEVEL = {
    "schema_version": (str, False),
    "mode": (str, False),
    "events": (list, False),
    "load": (dict, False),
}
EVENT_BASE = {
    "event_id": (str, False),
    "symbol": (str, False),
    "session_open": (int, False),
    "observed_at": (int, False),
    "state_time": (int, False),
    "accept_time": (int, True),
    "level_name": (str, False),
    "level": (NUMBER, False),
    "direction": (int, False),
    "force": (dict, False),
    "link_state": (str, False),
    "current_state": (str, False),
    "retest_at": (int, True),
    "poi_candidates": (list, False),
    "primary_poi": ((dict, str), True),
    "transition_history": (list, False),
    "window_results": (dict, False),
    "observation_windows": (list, False),
    "pending_evidence": (list, False),
    "wait_reason": (str, False),
    "entry_authorized": (bool, False),
    "mode": (str, False),
}
# Bloque todo-o-nada: aparece completo solo en eventos que pasaron por RETESTING_POI.
EVENT_CONFIRMATION = {
    "confirmation_state": (str, False),
    "defense_at": (int, True),
    "m5_structure_kind": (str, True),
    "m5_structure_at": (int, True),
    "m1_structure_kind": (str, True),
    "m1_structure_at": (int, True),
    "stop_basis": (str, False),
    "stop_price": (NUMBER, True),
    "stop_observed_at": (int, True),
    "target_policy_status": (str, False),
    "target_price": (NUMBER, True),
    "target_liquidity": (list, False),
}
# ``reason`` solo existe en eventos que attach_confirmations ya finish-ó.
EVENT_OPTIONAL = {"reason": (str, False)}
LOAD = {
    "m5_loaded": (bool, False),
    "m1_loaded": (bool, False),
    "last_closed_m5": (int, True),
    "last_closed_m1": (int, True),
    "coverage": (dict, False),
    "load_reason": (str, False),
}
COVERAGE = {
    "m5_bars_closed": (int, False),
    "m1_bars_closed": (int, False),
    "m5_first_closed": (int, True),
    "m1_first_closed": (int, True),
    "events_requested": (int, False),
}
TRANSITION = {
    "from": (str, False), "to": (str, False),
    "at": (int, False), "reason": (str, False),
}
LIQUIDITY = {
    "kind": (str, False), "price": (NUMBER, False), "observed_at": (int, False),
}
FORCE = {
    "body_ratio": (NUMBER, False), "body_multiple": (NUMBER, True),
    "close_extension": (NUMBER, True), "close_location": (NUMBER, False),
    "strong": (bool, False),
}
POI_CANDIDATE = {
    "zone_id": (str, False), "kind": (str, False), "direction": (int, False),
    "low": (NUMBER, False), "high": (NUMBER, False),
    "confirmed_at": (int, True), "first_touch_at": (int, True),
    "association_reason": (str, True), "rejected_reason": (str, True),
}
WINDOW_RESULT = {
    "window_bars": (int, False), "state": (str, False),
    "retest_within": (bool, False), "bars_observed": (int, False),
    "window_complete": (bool, False), "horizon": (int, True),
}
FORBIDDEN = frozenset({
    "entry", "order", "fill", "lots", "volume", "pnl",
    "position", "cash_value", "balance", "equity", "margin", "ticket", "deal",
})


# --------------------------------------------------------------------------- #
# generación de payloads reales                                                #
# --------------------------------------------------------------------------- #
BASE = 1_000_800  # múltiplo de 900, 300 y 60


def _causal_zone():
    """Zona FVG M15 causal: su impulso cae en la secuencia de ruptura."""
    class _FVG:
        value = "FVG"

    class Zone:
        origin_tf = "M15"
        id = "z-causal-1"
        type = _FVG
        direction = 1
        zone_low = 1.34
        zone_high = 1.36
        confirmation_time = BASE + 15 * 900  # cierre de la vela de aceptación
        confirmation_bar = 60                # índice M15 de esa vela
        meta = {"middle_bar": 59}            # índice de la vela de señal

    return Zone()


def _histories():
    """Historial sintético con un PDH roto y un retest causal de la POI."""
    d1 = [(BASE - k * 86400, 1.10, 1.20, 0.90, 1.10) for k in range(45, 0, -1)]
    d1.append((BASE, 1.10, 1.40, 1.00, 1.30))

    m15 = [(BASE - k * 900, 1.15, 1.151, 1.149, 1.15) for k in range(45, 0, -1)]
    for i in range(16):  # ruptura: señal en i=14, aceptación en i=15
        close = 1.105 if i < 14 else 1.35 + (i - 14) * .01
        high = 1.11 if i < 14 else 1.36 + (i - 14) * .01
        low = 1.09 if i < 14 else 1.25 + (i - 14) * .01
        m15.append((BASE + i * 900, close, high, low, close))
    for j in range(4):  # velas que retestean la POI [1.34, 1.36]
        m15.append((BASE + (16 + j) * 900, 1.35, 1.36, 1.34, 1.35))

    h4 = [(BASE - k * 14400, 1.15, 1.151, 1.149, 1.15) for k in range(45, 0, -1)]
    h4.append((BASE, 1.15, 1.151, 1.149, 1.15))
    h1 = [(BASE - k * 3600, 1.15, 1.151, 1.149, 1.15) for k in range(45, 0, -1)]
    h1.append((BASE, 1.15, 1.151, 1.149, 1.15))

    flat = tuple(
        (tf, tuple((BASE + i * sec - 55 * sec, 1.10, 1.101, 1.099, 1.10)
                   for i in range(56)))
        for tf, sec in (("D1", 86400), ("H4", 14400), ("H1", 3600), ("M15", 900))
    )
    break_hist = tuple((tf, tuple(v)) for tf, v in
                       (("D1", d1), ("H4", h4), ("H1", h1), ("M15", m15)))
    return flat, break_hist


def _lower_source():
    """Velas M5/M1 cerradas, todas con cierre <= cutoff."""
    m5 = tuple((BASE + i * 300, 1.20, 1.201, 1.199, 1.20) for i in range(-10, 21))
    m1 = tuple((BASE + i * 60, 1.20, 1.201, 1.199, 1.20) for i in range(-10, 21))
    return (5, 0.00001, {"M5": m5, "M1": m1}, ())


def _flat_payload():
    flat, _ = _histories()
    cutoff = BASE - 55 * 86400 + 55 * 86400  # BASE, suficiente para 56 velas D1
    result = copy.deepcopy(analyze_cached(flat, "M15", cutoff, symbol="EURUSD", digits=5))
    attach_confirmations(result, None, cutoff, digits=5)
    return result, cutoff


def _break_payload():
    """Ruptura aceptada real: campos base del evento, sin confirmación M5/M1."""
    _, break_hist = _histories()
    cutoff = BASE + 20 * 900
    result = copy.deepcopy(analyze_cached(break_hist, "M15", cutoff,
                                          symbol="EURUSD", digits=5))
    attach_confirmations(result, None, cutoff, digits=5)
    return result, cutoff


def _confirmed_payload(lower=True):
    """Retest causal real, con o sin datos M5/M1.  Todo vía funciones reales."""
    _, break_hist = _histories()
    cutoff = BASE + 20 * 900
    result = copy.deepcopy(analyze_cached(break_hist, "M15", cutoff,
                                          symbol="EURUSD", digits=5))
    frame = closed_frame(dict(break_hist)["M15"], "M15", cutoff)
    # ict3_payload es exactamente la función que analyze_cached usa para el bloque.
    result["ict3"] = ict3_payload(result["ict3_breaks"], [_causal_zone()], frame,
                                  cutoff, symbol="EURUSD")
    attach_confirmations(result, _lower_source() if lower else None, cutoff, digits=5)
    return result, cutoff


# --------------------------------------------------------------------------- #
# helpers de verificación                                                      #
# --------------------------------------------------------------------------- #
def _type_ok(value, spec):
    kinds, nullable = spec
    if value is None:
        return nullable
    if kinds is bool:
        return isinstance(value, bool)
    if kinds is NUMBER:
        return isinstance(value, NUMBER) and not isinstance(value, bool)
    return isinstance(value, kinds) and not isinstance(value, bool)


def _forbidden(node):
    found = set()
    if isinstance(node, dict):
        for key, value in node.items():
            if key in FORBIDDEN:
                found.add(key)
            found |= _forbidden(value)
    elif isinstance(node, (list, tuple)):
        for item in node:
            found |= _forbidden(item)
    return found


class Ict3SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payloads = {
            "flat": _flat_payload(),
            "no_retest": _break_payload(),
            "confirmed_nodata": _confirmed_payload(lower=False),
            "confirmed_m5": _confirmed_payload(lower=True),
        }

    def check_section(self, node, fields, label):
        self.assertIsInstance(node, dict, label)
        for key, (kinds, nullable) in fields.items():
            self.assertIn(key, node, f"{label}.{key} ausente")
            self.assertTrue(_type_ok(node[key], (kinds, nullable)),
                            f"{label}.{key}: tipo/nulabilidad inválido "
                            f"({type(node[key]).__name__})")
        return node

    def check_top(self, block, label):
        self.check_section(block, TOP_LEVEL, label)
        self.assertEqual(block["schema_version"], SCHEMA_VERSION)
        self.assertEqual(block["mode"], MODE)
        self.assertIsInstance(block["events"], list)
        self.assertIsInstance(block["load"], dict)

    def check_load(self, load, label):
        self.check_section(load, LOAD, label)
        self.check_section(load["coverage"], COVERAGE, label + ".coverage")

    def check_event(self, event, label, *, confirm=False):
        fields = dict(EVENT_BASE)
        if confirm:
            fields.update(EVENT_CONFIRMATION)
        self.check_section(event, fields, label)
        for key, spec in EVENT_OPTIONAL.items():
            if key in event:
                self.assertTrue(_type_ok(event[key], spec), label + "." + key)
        self.assertIs(event["entry_authorized"], False, label)
        self.assertEqual(event["mode"], MODE, label)
        self.check_section(event["force"], FORCE, label + ".force")
        for i, cand in enumerate(event["poi_candidates"]):
            self.check_section(cand, POI_CANDIDATE, f"{label}.poi_candidates[{i}]")
        for i, step in enumerate(event["transition_history"]):
            self.check_section(step, TRANSITION, f"{label}.transition_history[{i}]")
        for name, window in event["window_results"].items():
            self.check_section(window, WINDOW_RESULT, f"{label}.window_results[{name}]")
        for i, level in enumerate(event.get("target_liquidity", [])):
            self.check_section(level, LIQUIDITY, f"{label}.target_liquidity[{i}]")
        self.assertIsInstance(event["pending_evidence"], list)
        self.assertIsInstance(event["wait_reason"], str)
        self.assertTrue(event["wait_reason"])

    def check_no_forbidden(self, block, label):
        self.assertFalse(_forbidden(block), f"{label}: claves prohibidas {_forbidden(block)}")

    # ---------------------------------------------------------------- tests --
    def test_01_top_level_and_load_from_analyze_cached(self):
        """Payload real sin eventos: esquema superior y ``load`` completos."""
        result, _ = self.payloads["flat"]
        self.assertIn("ict3", result)
        self.assertIn("ict3_breaks", result)
        block = result["ict3"]
        self.check_top(block, "ict3(flat)")
        self.check_load(block["load"], "ict3.load(flat)")

    def test_02_base_event_fields_from_analyze_cached_break(self):
        """Ruptura aceptada real: campos base del evento, sin confirmación M5/M1."""
        result, _ = self.payloads["no_retest"]
        block = result["ict3"]
        self.check_top(block, "ict3(no_retest)")
        self.check_load(block["load"], "ict3.load(no_retest)")
        self.assertTrue(block["events"])
        for i, event in enumerate(block["events"]):
            self.check_event(event, f"ict3.event[{i}](no_retest)", confirm=False)
            self.assertFalse(EVENT_CONFIRMATION.keys() & event.keys())

    def test_03_full_event_schema_with_confirmations(self):
        """RETESTING real + M5/M1: todos los campos base y de confirmación."""
        result, _ = self.payloads["confirmed_m5"]
        block = result["ict3"]
        self.check_top(block, "ict3(confirmed)")
        self.check_load(block["load"], "ict3.load(confirmed)")
        self.assertTrue(block["events"])
        for i, event in enumerate(block["events"]):
            self.check_event(event, f"ict3.event[{i}](confirmed)", confirm=True)
            self.assertEqual(event["current_state"], "RETESTING_POI")

    def test_04_entry_authorized_is_always_false(self):
        """Invariante de observación en los cuatro payloads reales."""
        for name, (result, _) in self.payloads.items():
            with self.subTest(payload=name):
                block = result["ict3"]
                self.assertEqual(block["mode"], MODE)
                for event in block["events"]:
                    self.assertIs(event["entry_authorized"], False)
                    self.assertEqual(event["mode"], MODE)

    def test_05_no_trading_keys_anywhere(self):
        """No aparecen entry/order/fill/lots/volume/pnl en ningún nivel."""
        for name, (result, _) in self.payloads.items():
            with self.subTest(payload=name):
                self.check_no_forbidden(result["ict3"], f"ict3({name})")
                self.assertFalse(_forbidden(result), f"result({name})")

    def test_06_legacy_ict3_breaks_preserved(self):
        """El bloque versionado convive con ``ict3_breaks`` sin alteration."""
        for name, (result, _) in self.payloads.items():
            with self.subTest(payload=name):
                self.assertIn("ict3", result)
                self.assertIn("ict3_breaks", result)
                self.assertIsInstance(result["ict3_breaks"], list)

    def test_07_wait_without_retest_is_explicit(self):
        """Sin retest: no se piden M5/M1 y ``wait_reason`` explica por qué."""
        result, _ = self.payloads["no_retest"]
        load = result["ict3"]["load"]
        self.assertFalse(load["m5_loaded"])
        self.assertFalse(load["m1_loaded"])
        self.assertEqual(load["load_reason"], "NOT_REQUESTED_NO_M15_RETEST")
        self.assertEqual(load["coverage"]["events_requested"], 0)
        for event in result["ict3"]["events"]:
            self.assertTrue(event["wait_reason"])
            self.assertIs(event["entry_authorized"], False)
            self.assertFalse(EVENT_CONFIRMATION.keys() & event.keys())

    def test_08_wait_without_m5_data_never_invents(self):
        """Sin M5: estado WAIT, motivos explícitos, campos nulos y sin entrada."""
        result, _ = self.payloads["confirmed_nodata"]
        load = result["ict3"]["load"]
        self.assertEqual(load["load_reason"], "LOWER_SOURCE_UNAVAILABLE")
        self.assertFalse(load["m5_loaded"])
        for event in result["ict3"]["events"]:
            self.check_event(event, "ict3.event(confirmed_nodata)", confirm=True)
            self.assertEqual(event["confirmation_state"], "WAIT_M5_M1_CONFIRMATION")
            self.assertIn("M5_M1_CONFIRMATION_NOT_LOADED", event["pending_evidence"])
            self.assertIsNone(event["defense_at"])
            self.assertIsNone(event["stop_price"])
            self.assertIs(event["entry_authorized"], False)

    def test_09_wait_without_stop_and_liquidity(self):
        """Sin stop ni liquidez: pendiente observable, nunca invalidación/entrada."""
        result, _ = self.payloads["confirmed_m5"]
        for event in result["ict3"]["events"]:
            pending = event["pending_evidence"]
            if "NO_STRUCTURAL_STOP" in pending:
                self.assertEqual(event["stop_basis"], "NO_STRUCTURAL_STOP")
                self.assertIsNone(event["stop_price"])
            if event["target_policy_status"] == "NO_STRUCTURAL_REFERENCE":
                self.assertIsNone(event["target_price"])
                self.assertEqual(event["target_liquidity"], [])
            self.assertIs(event["entry_authorized"], False)
            self.assertTrue(event["wait_reason"])

    def test_10_all_timestamps_respect_cutoff(self):
        """Ningún instante publicado supera el corte (sin look-ahead)."""
        for name, (result, cutoff) in self.payloads.items():
            time_keys = ("observed_at", "state_time", "retest_at", "defense_at",
                         "m5_structure_at", "m1_structure_at", "stop_observed_at")
            with self.subTest(payload=name):
                load = result["ict3"]["load"]
                for key in ("last_closed_m5", "last_closed_m1"):
                    value = load[key]
                    if value is not None:
                        self.assertLessEqual(value, cutoff)
                for event in result["ict3"]["events"]:
                    for key in time_keys:
                        value = event.get(key)
                        if value is not None:
                            self.assertLessEqual(value, cutoff, f"{name}:{key}")
                    for step in event["transition_history"]:
                        self.assertLessEqual(step["at"], cutoff)
                    for level in event.get("target_liquidity", []):
                        self.assertLessEqual(level["observed_at"], cutoff)


if __name__ == "__main__":
    unittest.main()
