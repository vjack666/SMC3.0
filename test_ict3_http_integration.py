"""Integración HTTP de ``GET /api/ict`` sin MT5, credenciales ni escrituras.

Se levanta un ``LocalServer`` propio en un puerto efímero; el servidor de
producción nunca se contacta. Las lecturas de MT5 se sustituyen por fixtures.
"""
import http.client
import json
import threading
import unittest
from unittest.mock import patch

import ict
import smc
from ict3_confirm import MODE, SECONDS
from motor_smc.instrumentos import ALERT_SYMBOLS
from smc import LOCAL, Handler, LocalServer
from test_ict3_confirm import DIGITS, bullish_bars, make_event, make_result, m1_bullish_bars, run
from test_ict3_causality import forbidden_keys

CUTOFF = 1_700_000_000


class Ict3HttpIntegrationTests(unittest.TestCase):
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

    def get(self, path):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
        try:
            conn.request("GET", path, headers={"Host": LOCAL})
            response = conn.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            conn.close()

    @staticmethod
    def assert_observe_only(payload):
        forbidden = forbidden_keys(payload)
        assert not forbidden, "claves prohibidas: " + repr(forbidden)
        assert payload["ict3"]["mode"] == MODE
        assert payload.get("mode", MODE) == MODE
        for event in payload["ict3"]["events"]:
            assert event["entry_authorized"] is False
            assert event["mode"] == MODE

    def test_get_api_ict_for_eurusd_gbpjpy_and_us30(self):
        calls = []

        def fake_chart(settings, symbol, frame, cutoff=None):
            calls.append((symbol, frame, cutoff))
            event = make_event(event_id="evt_" + symbol)
            event["symbol"] = symbol
            return run([event], bullish_bars(), m1_bullish_bars(), CUTOFF)

        with patch.object(smc, "ict_chart", side_effect=fake_chart):
            for symbol in ALERT_SYMBOLS:
                with self.subTest(symbol=symbol):
                    status, headers, body = self.get(
                        f"/api/ict?symbol={symbol}&tf=M15&at={CUTOFF}")
                    self.assertEqual(status, 200)
                    self.assertEqual(headers.get("Cache-Control"), "no-store")
                    self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
                    payload = json.loads(body)
                    self.assert_observe_only(payload)
                    event = payload["ict3"]["events"][0]
                    self.assertEqual(event["symbol"], symbol)
                    load = payload["ict3"]["load"]
                    self.assertTrue(load["m5_loaded"])
                    self.assertTrue(load["m1_loaded"])
                    self.assertEqual(load["load_reason"], "M5_M1_LOADED")
                    self.assertLessEqual(load["last_closed_m5"], CUTOFF)
                    self.assertLessEqual(load["last_closed_m1"], CUTOFF)
        self.assertEqual(calls, [(symbol, "M15", CUTOFF) for symbol in ALERT_SYMBOLS])

    def test_http_on_demand_skips_lower_reads_without_retest(self):
        calls = []

        def fake_read(settings, symbol, frames):
            calls.append(tuple(frames))
            return (2, 0.01, {tf: () for tf in ict.PROFILE}, ())

        analyzed = {
            "enabled": True,
            "ict3": {"mode": MODE, "events": [
                {"current_state": "ACCEPTED_BREAK_WAIT_RETEST", "event_id": "e",
                 "entry_authorized": False}]},
        }
        with patch.object(smc, "ict_chart", side_effect=ict.ict_chart), \
             patch.object(ict, "read_bars", side_effect=fake_read), \
             patch.object(ict, "analyze_bars", return_value=analyzed):
            status, _, body = self.get(f"/api/ict?symbol=EURUSD&tf=M15&at={CUTOFF}")
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assert_observe_only(payload)
        self.assertEqual(len(calls), 1)
        self.assertNotIn("M5", calls[0])
        self.assertNotIn("M1", calls[0])
        self.assertEqual(payload["ict3"]["load"]["load_reason"],
                         "NOT_REQUESTED_NO_M15_RETEST")
        self.assertFalse(payload["ict3"]["load"]["m5_loaded"])

    def test_http_on_demand_reads_lower_only_with_retest(self):
        calls = []

        def fake_read(settings, symbol, frames):
            calls.append(tuple(frames))
            if "M5" in frames:
                return (DIGITS, 10 ** -DIGITS,
                        {"M5": bullish_bars(), "M1": ()}, ())
            return (2, 0.01, {tf: () for tf in ict.PROFILE}, ())

        analyzed = {
            "enabled": True,
            "ict3": {"mode": MODE, "events": [
                {"current_state": "RETESTING_POI", "event_id": "e",
                 "entry_authorized": False}]},
        }
        with patch.object(smc, "ict_chart", side_effect=ict.ict_chart), \
             patch.object(ict, "read_bars", side_effect=fake_read), \
             patch.object(ict, "analyze_bars", return_value=analyzed):
            status, _, body = self.get(f"/api/ict?symbol=GBPJPY&tf=M15&at={CUTOFF}")
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assert_observe_only(payload)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1], ("M5", "M1"))
        self.assertEqual(payload["ict3"]["load"]["load_reason"],
                         "M1_BARS_UNAVAILABLE_M5_USED")

    def test_http_mt5_error_keeps_wait_state_and_no_fabricated_data(self):
        def fake_read(settings, symbol, frames):
            if "M5" in frames:
                raise RuntimeError("MT5 sin historial M5/M1")
            return (2, 0.01, {tf: () for tf in ict.PROFILE}, ())

        analyzed = {
            "enabled": True,
            "ict3": {"mode": MODE, "events": [
                {"current_state": "RETESTING_POI", "event_id": "e",
                 "entry_authorized": False}]},
        }
        with patch.object(smc, "ict_chart", side_effect=ict.ict_chart), \
             patch.object(ict, "read_bars", side_effect=fake_read), \
             patch.object(ict, "analyze_bars", return_value=analyzed):
            status, _, body = self.get(f"/api/ict?symbol=US30&tf=M15&at={CUTOFF}")
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assert_observe_only(payload)
        self.assertIn("MT5 sin historial M5/M1",
                      payload["ict3"]["load"]["load_reason"])
        event = payload["ict3"]["events"][0]
        self.assertEqual(event["confirmation_state"], "WAIT_M5_M1_CONFIRMATION")
        self.assertIsNone(event["defense_at"])
        self.assertIsNone(event["m5_structure_kind"])
        self.assertIsNone(event["stop_price"])


if __name__ == "__main__":
    unittest.main()
