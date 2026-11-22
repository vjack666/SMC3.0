import unittest
from unittest.mock import patch

import ict


class OnDemandLowerLoadTests(unittest.TestCase):
    @staticmethod
    def result_with_state(state):
        return {
            "enabled": True,
            "source": ict.REVISION,
            "ict3": {
                "schema_version": "0.2-research",
                "mode": "OBSERVE_ONLY_NO_ORDER",
                "events": [{"current_state": state, "event_id": "evt_test",
                            "entry_authorized": False}],
            },
        }

    def base_source(self):
        return (2, 0.01, {tf: () for tf in ict.PROFILE}, ())

    def lower_source(self):
        return (2, 0.01, {"M5": (), "M1": ()}, ())

    def test_no_load_when_no_m15_retest(self):
        calls = []

        def fake_read(settings, symbol, frames):
            calls.append(tuple(frames))
            return self.lower_source() if "M5" in frames else self.base_source()

        with patch.object(ict, "read_bars", side_effect=fake_read), \
             patch.object(ict, "analyze_bars", return_value=self.result_with_state("ACCEPTED_BREAK_WAIT_RETEST")):
            result = ict.ict_chart({}, "EURUSD", "M15", 1_700_000_000)
        self.assertEqual(len(calls), 1)
        self.assertNotIn("M5", calls[0])
        self.assertNotIn("M1", calls[0])
        self.assertEqual(result["ict3"]["load"]["load_reason"], "NOT_REQUESTED_NO_M15_RETEST")

    def test_load_m5_m1_only_when_m15_retest(self):
        calls = []

        def fake_read(settings, symbol, frames):
            calls.append(tuple(frames))
            return self.lower_source() if "M5" in frames else self.base_source()

        with patch.object(ict, "read_bars", side_effect=fake_read), \
             patch.object(ict, "analyze_bars", return_value=self.result_with_state("RETESTING_POI")):
            ict.ict_chart({}, "EURUSD", "M15", 1_700_000_000)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1], ("M5", "M1"))

    def test_loader_error_is_explicit_and_never_fabricates(self):
        def fake_read(settings, symbol, frames):
            if "M5" in frames:
                raise RuntimeError("MT5 sin historio")
            return self.base_source()

        with patch.object(ict, "read_bars", side_effect=fake_read), \
             patch.object(ict, "analyze_bars", return_value=self.result_with_state("RETESTING_POI")):
            result = ict.ict_chart({}, "EURUSD", "M15", 1_700_000_000)
        event = result["ict3"]["events"][0]
        self.assertEqual(event["confirmation_state"], "WAIT_M5_M1_CONFIRMATION")
        self.assertIsNone(event["m5_structure_kind"])
        self.assertIsNone(event["stop_price"])
        self.assertIn("MT5 sin historio", result["ict3"]["load"]["load_reason"])


if __name__ == "__main__":
    unittest.main()
