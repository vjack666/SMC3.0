import http.client
import threading
import unittest

from ict import (PROFILE, SECONDS, analyze_cached, closed_frame, daily_break_studies,
                 ict3_payload)
from smc import LOCAL, Handler, LocalServer


class Ict3ContractTests(unittest.TestCase):
    @staticmethod
    def accepted_break():
        daily = [(0, 1.0, 1.20, .90, 1.1), (86400, 1.1, 1.4, 1.0, 1.3)]
        rows = [(86400 + i * 900,
                 1.10 if i == 0 else 1.25,
                 (1.11 if i < 14 else 1.36 + (i - 14) * .01),
                 (1.09 if i < 14 else 1.25 + (i - 14) * .01),
                 (1.105 if i < 14 else 1.35 + (i - 14) * .01))
                for i in range(16)]
        frame = closed_frame([*rows, (86400 + 16 * 900, 0, 0, 0, 0)], "M15")
        studies = daily_break_studies(daily, frame, 86400 + 16 * 900,
                                      symbol="EURUSD", digits=2)
        return studies, frame, 86400 + 16 * 900

    def test_payload_has_minimum_fields_and_never_authorizes_entry(self):
        studies, frame, cutoff = self.accepted_break()
        payload = ict3_payload(studies, [], frame, cutoff)
        self.assertEqual(payload["schema_version"], "0.2-research")
        self.assertEqual(payload["mode"], "OBSERVE_ONLY_NO_ORDER")
        self.assertTrue(payload["events"])
        event = payload["events"][0]
        required = {"event_id", "observed_at", "state_time", "force", "poi_candidates",
                    "current_state", "retest_at", "transition_history", "pending_evidence",
                    "wait_reason", "entry_authorized"}
        self.assertTrue(required.issubset(event))
        self.assertIs(event["entry_authorized"], False)
        forbidden = {"entry", "stop", "target", "lots", "order", "fill", "pnl"}
        self.assertFalse(forbidden.intersection(event))
        self.assertEqual(event["force"]["strong"], True)

    def test_ict3_block_keeps_legacy_ict3_breaks(self):
        cutoff = 1795111200
        history = tuple(
            (tf, tuple((cutoff + i * SECONDS[tf], 1.1, 1.101, 1.099, 1.1)
                       for i in range(-55, 1)))
            for tf in PROFILE
        )
        result = analyze_cached(history, "M15", cutoff)
        self.assertIn("ict3_breaks", result)
        self.assertIn("ict3", result)
        self.assertIsInstance(result["ict3_breaks"], list)
        self.assertEqual(result["ict3"]["schema_version"], "0.2-research")
        self.assertEqual(result["ict3"]["mode"], "OBSERVE_ONLY_NO_ORDER")

    def test_invalid_cutoff_produces_no_ict3_block(self):
        cutoff = 1795111200
        history = tuple(
            (tf, tuple((cutoff + i * SECONDS[tf], 1.1, 1.101, 1.099, 1.1)
                       for i in range(-55, 1)))
            for tf in PROFILE
        )
        with self.assertRaises(RuntimeError):
            analyze_cached(history, "M15", cutoff - 1_000_000)


class Ict3HttpContractTests(unittest.TestCase):
    """Real HTTP checks against smc.Handler on an ephemeral port.

    The production server on 127.0.0.1:8766 is never contacted: we bind our
    own LocalServer to port 0 and drive it with http.client.  The exercised
    routes need no MT5 terminal and perform no writes to data/.
    """

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
            # Override Host so the real handler accepts it even though the
            # socket is bound to an ephemeral port, not the usual 8766.
            conn.request("GET", path, headers={"Host": host})
            response = conn.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            conn.close()

    def test_http_contract_headers_remain_read_only(self):
        """A permitted GET really returns the two hardening headers."""
        status, headers, body = self.get("/api/poi-universe")
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Cache-Control"), "no-store")
        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
        # Body is a real catalog payload, not merely matching source text.
        self.assertIn("forex", body.decode("utf-8"))

    def test_invalid_host_is_forbidden(self):
        status, _, body = self.get("/api/poi-universe", host="malicious.example")
        self.assertEqual(status, 403)
        self.assertIn("error", body.decode("utf-8"))

    def test_invalid_cutoff_is_bad_request(self):
        status, _, body = self.get("/api/ict?at=9999999999")
        self.assertEqual(status, 400)
        self.assertIn("Corte", body.decode("utf-8"))

    def test_unknown_trading_route_is_not_found(self):
        for path in ("/api/trade", "/api/order"):
            with self.subTest(path=path):
                status, _, body = self.get(path)
                self.assertEqual(status, 404)
                self.assertIn("error", body.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
