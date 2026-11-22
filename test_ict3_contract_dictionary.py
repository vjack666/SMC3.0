"""Contrato formal de Fase 5: diccionario, tipos, compatibilidad y HTTP.

Sin MT5, sin credenciales y sin escrituras en ``data/``. Los servidores que se
levantan aqui son efimeros (puerto 0) y las lecturas se sustituyen por fixtures.
"""
import copy
import http.client
import json
import threading
import unittest
from unittest.mock import patch

import ict
import smc
from ict3_contract import (
    CONFIRMATION_FIELDS, CONTRACT_VERSION, EVENT, FORBIDDEN_KEYS, LOAD, MODE,
    SCHEMA_VERSION, TOP_LEVEL, assert_valid, classify_wait, describe, validate,
)
from smc import LOCAL, Handler, LocalServer
from test_ict3_causality import forbidden_keys
from test_ict3_confirm import bullish_bars, make_event, m1_bullish_bars, run
from test_ict3_contract import Ict3ContractTests

CUTOFF = 1_000_500 + 10 * 300 + 300


def complete_event(**kwargs):
    """Evento del contrato real, no un fixture incompleto."""
    event = make_event(**kwargs)
    event.update({
        "level_name": "PDH",
        "force": {"body_ratio": 0.9, "body_multiple": 2.1,
                  "close_extension": 0.8, "close_location": 0.9, "strong": True},
        "link_state": "LINKED_ACCEPTED_BREAK",
        "observation_windows": [],
    })
    return event


class ContractDictionaryTests(unittest.TestCase):
    def test_catalog_is_complete_and_serializable(self):
        catalog = describe()
        self.assertEqual(catalog["contract_version"], CONTRACT_VERSION)
        self.assertEqual(catalog["schema_version"], SCHEMA_VERSION)
        self.assertEqual(catalog["mode"], MODE)
        self.assertEqual(set(catalog["sections"]),
                         {"ict3", "event", "load", "coverage", "transition", "liquidity"})
        for section in catalog["sections"].values():
            for field in section.values():
                self.assertEqual(set(field), {"type", "nullable", "unit",
                                              "source", "meaning"})
        self.assertTrue(json.loads(json.dumps(catalog)))
        self.assertTrue(CONFIRMATION_FIELDS.issubset(EVENT))
        self.assertTrue(FORBIDDEN_KEYS)

    def test_observable_payload_satisfies_the_contract(self):
        block = run([complete_event()], bullish_bars(), m1_bullish_bars(),
                    CUTOFF)["ict3"]
        assert_valid(block, cutoff=CUTOFF)
        event = block["events"][0]
        self.assertEqual(event["current_state"], "OBSERVABLE_SETUP")
        self.assertIs(event["entry_authorized"], False)
        self.assertEqual(event["mode"], MODE)
        self.assertEqual(classify_wait(block), "SIN_ESPERA")
        self.assertEqual(forbidden_keys(block), set())

    def test_no_confirmation_subobject_for_event_without_retest(self):
        block = run([complete_event(state="ACCEPTED_BREAK_WAIT_RETEST")],
                    bullish_bars(), m1_bullish_bars(), CUTOFF)["ict3"]
        assert_valid(block, cutoff=CUTOFF)
        event = block["events"][0]
        self.assertFalse(CONFIRMATION_FIELDS.intersection(event))
        self.assertEqual(classify_wait(block), "SIN_RETEST")
        self.assertEqual(event["current_state"], "ACCEPTED_BREAK_WAIT_RETEST")
        self.assertTrue(event["pending_evidence"])

    def test_wait_cases_are_distinguishable_without_guessing(self):
        # Datos ausentes: no hay velas M5 cerradas al corte.
        missing = run([complete_event()], (), (), CUTOFF)["ict3"]
        assert_valid(missing, cutoff=CUTOFF)
        self.assertEqual(classify_wait(missing), "DATOS_AUSENTES")
        self.assertEqual(missing["load"]["load_reason"],
                         "NO_CLOSED_M5_BARS_AT_CUTOFF")

        # Datos presentes pero retest incompleto.
        events = [complete_event()]
        events[0]["direction"] = 0
        weak = run(events, bullish_bars(), m1_bullish_bars(), CUTOFF)["ict3"]
        assert_valid(weak, cutoff=CUTOFF)
        self.assertEqual(classify_wait(weak), "DATOS_AUSENTES")
        self.assertIn("RETEST_EVIDENCE_INCOMPLETE", weak["events"][0]["reason"])

        # Evidencia insuficiente: M5/M1 cargados sin estructura completa.
        thin = run([complete_event()], bullish_bars(), m1_bullish_bars(),
                   cutoff=1_000_800)["ict3"]
        self.assertEqual(classify_wait(thin), "EVIDENCIA_INSUFICIENTE")
        assert_valid(thin, cutoff=1_000_800)
        self.assertIn("M5_STRUCTURE_NOT_CONFIRMED",
                      thin["events"][0]["pending_evidence"])

    def test_validator_rejects_contract_violations(self):
        block = run([complete_event()], bullish_bars(), m1_bullish_bars(),
                    CUTOFF)["ict3"]
        broken = copy.deepcopy(block)
        broken["events"][0]["entry_authorized"] = True
        broken["events"][0]["stop_price"] = "1.2000"
        broken["events"][0]["order"] = {"side": "buy"}
        issues = validate(broken, cutoff=CUTOFF)
        self.assertTrue(any("entry_authorized" in item for item in issues))
        self.assertTrue(any("stop_price" in item for item in issues))
        self.assertTrue(any("order" in item for item in issues))
        with self.assertRaises(AssertionError):
            assert_valid(broken, cutoff=CUTOFF)

    def test_validator_rejects_future_instants(self):
        block = run([complete_event()], bullish_bars(), m1_bullish_bars(),
                    CUTOFF)["ict3"]
        broken = copy.deepcopy(block)
        broken["events"][0]["stop_observed_at"] = CUTOFF + 1
        issues = validate(broken, cutoff=CUTOFF)
        self.assertTrue(any("posterior al corte" in item for item in issues))

    def test_legacy_breaks_keep_their_previous_fields(self):
        studies, frame, cutoff = Ict3ContractTests.accepted_break()
        payload = ict.ict3_payload(studies, [], frame, cutoff,
                                   symbol="EURUSD")
        core = {"event_id", "level_name", "level", "direction", "state",
                "observed_at", "state_time", "strong"}
        self.assertTrue(core.issubset(studies[0]))
        cutoff = 1795111200
        history = tuple(
            (tf, tuple((cutoff + i * ict.SECONDS[tf], 1.1, 1.101, 1.099, 1.1)
                       for i in range(-55, 1)))
            for tf in ict.PROFILE
        )
        result = ict.analyze_cached(history, "M15", cutoff)
        self.assertIn("ict3_breaks", result)
        self.assertIn("ict3", result)
        self.assertTrue({"schema_version", "mode", "events"}.issubset(result["ict3"]))
        full = run([complete_event()], bullish_bars(), m1_bullish_bars(),
                   CUTOFF)["ict3"]
        self.assertTrue(set(LOAD).issubset(full["load"]))


class WireContractTests(unittest.TestCase):
    """GET /api/ict devuelve exactamente el bloque validado por el contrato."""

    @classmethod
    def setUpClass(cls):
        cls.server = LocalServer(("127.0.0.1", 0), Handler, market=None, notify=False)
        cls.host = str(cls.server.server_address[0])
        cls.port = int(cls.server.server_address[1])
        cls.thread = threading.Thread(target=cls.server.serve_forever,
                                      kwargs={"poll_interval": 0.01}, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def get(self, path, host=LOCAL):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
        try:
            conn.request("GET", path, headers={"Host": host})
            response = conn.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            conn.close()

    def test_wire_payload_validates_and_keeps_legacy_block(self):
        full = run([complete_event()], bullish_bars(), m1_bullish_bars(), CUTOFF)
        full["ict3_breaks"] = [complete_event()]
        with patch.object(smc, "ict_chart", return_value=full):
            status, headers, body = self.get(
                f"/api/ict?symbol=EURUSD&tf=M15&at={CUTOFF}")
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Cache-Control"), "no-store")
        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
        payload = json.loads(body)
        assert_valid(payload["ict3"], cutoff=CUTOFF)
        self.assertIn("ict3_breaks", payload)
        self.assertEqual(payload["ict3"]["schema_version"], SCHEMA_VERSION)
        self.assertEqual(forbidden_keys(payload), set())

    def test_invalid_cutoff_and_trading_routes_stay_closed(self):
        status, _, body = self.get("/api/ict?at=9999999999")
        self.assertEqual(status, 400)
        self.assertIn("Corte", body.decode("utf-8"))
        for path in ("/api/trade", "/api/order", "/api/position", "/api/fill"):
            with self.subTest(path=path):
                status, _, body = self.get(path)
                self.assertEqual(status, 404)

    def test_forbidden_host_is_rejected(self):
        status, _, _ = self.get("/api/ict?at=%d" % CUTOFF,
                                host="malicious.example")
        self.assertEqual(status, 403)


if __name__ == "__main__":
    unittest.main()
