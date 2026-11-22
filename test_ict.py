import unittest
from types import SimpleNamespace

import pandas as pd

from ict import (PROFILE, SECONDS, analyze_cached, closed_frame, daily_liquidity, engine,
                 daily_break_studies, last_friday_reference)
from ict22 import Observer, Session


class ClosedBarTests(unittest.TestCase):
    def test_position_zero_and_incomplete_bar_are_excluded(self):
        rows = [(0, 1, 2, 1, 2), (900, 2, 3, 2, 3), (1800, 3, 900, 1, 890)]
        before = closed_frame(rows, "M15", 899)
        at_close = closed_frame(rows, "M15", 900)
        latest = closed_frame(rows, "M15")
        self.assertTrue(before.empty)
        self.assertEqual(at_close["closed"].tolist(), [900])
        self.assertEqual(latest["high"].tolist(), [2, 3])

    def test_weekend_gap_does_not_extend_previous_bar(self):
        rows = [(0, 1, 2, 1, 2), (259200, 2, 3, 2, 3)]
        self.assertEqual(closed_frame(rows, "D1", 86400)["closed"].tolist(), [86400])

    def test_future_bars_do_not_change_an_old_snapshot(self):
        cutoff = 1795111200
        history, extended = [], []
        for tf in PROFILE:
            duration = SECONDS[tf]
            rows = tuple(
                (cutoff + i * duration, 1.1, 1.101, 1.099, 1.1)
                for i in range(-55, 1)
            )
            history.append((tf, rows))
            # Alter the bar in formation and add an extreme bar in the future.
            extended.append((tf, (*rows[:-1], (cutoff, 1.0, 8.0, .01, .02),
                                  (cutoff + duration, 1.0, 1.2, .1, .2))))
        engine()
        self.assertEqual(analyze_cached(tuple(history), "M15", cutoff),
                         analyze_cached(tuple(extended), "M15", cutoff))


class DailyLiquidityTests(unittest.TestCase):
    def test_uses_symbol_precision_for_wicks_and_touches(self):
        daily = [(0, 42000.1, 42010.10, 42000.00, 42005.00),
                 (86400, 42005.0, 50000.0, 30000.0, 42005.0)]
        bars = [(0, 42000.1, 42010.100001, 42000.000001, 42005.0),
                (86400, 42005.0, 42010.100002, 42004.0, 42005.0),
                (87300, 42005.0, 50000.0, 30000.0, 42005.0)]
        result = daily_liquidity(daily, closed_frame(bars, "M15"), 87300, digits=2)
        self.assertEqual((result["pdh"], result["pdl"]), (42010.10, 42000.00))
        self.assertEqual((result["pdh_m15_open"], result["pdl_m15_open"]), (0, 0))
        self.assertEqual([(event["kind"], event["level"]) for event in result["events"]],
                         [("touch", "PDH")])

    def test_uses_previous_d1_and_only_closed_m15_in_current_session(self):
        start = 259200
        daily = [(0, 1.1, 1.3, 1, 1.1),
                 (86400, 1.1, 1.2, 1.05, 1.1),
                 (start, 1.1, 9, .1, 2)]
        bars = [
            (86400, 1.1, 1.2, 1.09, 1.11),
            (87300, 1.11, 1.2, 1.07, 1.1),
            (88200, 1.1, 1.12, 1.05, 1.1),
            (start - 900, 1.1, 1.4, 1.03, 1.1),
            (start, 1.1, 1.21, 1.1, 1.19),
            (start + 900, 1.19, 1.22, 1.19, 1.21),
            (start + 1800, 1.21, 1.22, 1.18, 1.19),
            (start + 2700, 1.19, 1.23, 1.02, 1.1),
            (start + 3600, 1.1, 1.11, 1.05, 1.1),
            (start + 4500, 1.1, 1.19, 1.04, 1.05),
            (start + 5400, 1.05, 1.15, 1.03, 1.08),
            (start + 6300, 1.08, 1.3, 1.01, 1.12),
        ]
        cutoff = start + 6300
        result = daily_liquidity(daily, closed_frame(bars, "M15"), cutoff)
        self.assertEqual((result["pdh"], result["pdl"]), (1.2, 1.05))
        self.assertEqual(result["source_open"], 86400)
        self.assertEqual(result["pdh_m15_open"], 86400)
        self.assertEqual(result["pdl_m15_open"], 88200)
        self.assertEqual(result["m15_count"], 7)
        self.assertEqual([(x["kind"], x["level"]) for x in result["events"]],
                         [("sweep", "PDH"), ("break", "PDH"), ("late_return", "PDH"),
                          ("both", None), ("touch", "PDL"), ("boundary_close", "PDL"),
                          ("sweep", "PDL")])


class FridayReferenceTests(unittest.TestCase):
    def test_uses_only_the_latest_fully_closed_friday(self):
        prior = 1794528000  # Friday 2026-11-13 00:00 in the MT5 clock.
        latest = 1795132800  # Friday 2026-11-20 00:00.
        daily = [
            (prior, 1.0, 1.2, .9, 1.1),
            (prior + 3 * 86400, 1.1, 1.3, 1.0, 1.2),
            (latest, 1.2, 1.4, 1.05, 1.3),
        ]
        before_close = last_friday_reference(daily, latest + 86399)
        after_close = last_friday_reference(daily, latest + 86400)
        self.assertEqual(before_close["source_open"], prior)
        self.assertEqual((after_close["source_open"], after_close["high"], after_close["low"]),
                         (latest, 1.4, 1.05))


class DailyBreakStudyTests(unittest.TestCase):
    def test_preserves_accepted_strong_break_without_calling_it_an_entry(self):
        daily = [(0, 1.0, 1.20, .90, 1.1), (86400, 1.1, 1.4, 1.0, 1.3)]
        rows = [(86400 + i * 900,
                 1.10 if i == 0 else 1.25,
                 (1.11 if i < 14 else 1.36 + (i - 14) * .01),
                 (1.09 if i < 14 else 1.25 + (i - 14) * .01),
                 (1.105 if i < 14 else 1.35 + (i - 14) * .01)) for i in range(16)]
        frame = closed_frame([*rows, (86400 + 16 * 900, 0, 0, 0, 0)], "M15")
        studies = daily_break_studies(daily, frame, 86400 + 16 * 900, digits=2)
        accepted = [item for item in studies if item["state"] == "ACCEPTED_BREAK_WAIT_RETEST"]
        self.assertTrue(accepted)
        self.assertTrue(accepted[0]["strong"])
        self.assertNotIn("entry", accepted[0])
        self.assertTrue(accepted[0]["event_id"].startswith("evt_"))
        self.assertLessEqual(accepted[0]["observed_at"], 86400 + 16 * 900)
        self.assertLessEqual(accepted[0]["state_time"], 86400 + 16 * 900)

    @staticmethod
    def _break_rows(count):
        return [(86400 + i * 900,
                 1.10 if i == 0 else 1.25,
                 (1.11 if i < 14 else 1.36 + (i - 14) * .01),
                 (1.09 if i < 14 else 1.25 + (i - 14) * .01),
                 (1.105 if i < 14 else 1.35 + (i - 14) * .01))
                for i in range(count)]

    def test_event_id_is_deterministic_and_symbol_scoped(self):
        daily = [(0, 1.0, 1.20, .90, 1.1), (86400, 1.1, 1.4, 1.0, 1.3)]
        rows = self._break_rows(16)
        frame = closed_frame([*rows, (86400 + 16 * 900, 0, 0, 0, 0)], "M15")
        first = daily_break_studies(daily, frame, 86400 + 16 * 900, symbol="EURUSD", digits=2)
        again = daily_break_studies(daily, frame, 86400 + 16 * 900, symbol="EURUSD", digits=2)
        other = daily_break_studies(daily, frame, 86400 + 16 * 900, symbol="GBPUSD", digits=2)
        self.assertEqual([x["event_id"] for x in first], [x["event_id"] for x in again])
        self.assertNotEqual([x["event_id"] for x in first], [x["event_id"] for x in other])
        self.assertEqual(len({x["event_id"] for x in first}), len(first))

    def test_pdh_and_pdl_events_have_distinct_identities(self):
        daily = [(0, 1.0, 1.20, .90, 1.1), (86400, 1.1, 1.5, .6, 1.3)]
        rows = [(86400 + i * 900, 1.10, 1.11, 1.09, 1.10) for i in range(14)]
        rows += [(86400 + 14 * 900, 1.10, 1.30, 1.09, 1.25),
                 (86400 + 15 * 900, 1.25, 1.31, 1.24, 1.26),
                 (86400 + 16 * 900, 1.10, 1.11, 0.80, 0.85),
                 (86400 + 17 * 900, 0.85, 0.86, 0.70, 0.80)]
        frame = closed_frame([*rows, (86400 + 18 * 900, 0, 0, 0, 0)], "M15")
        studies = daily_break_studies(daily, frame, 86400 + 18 * 900, symbol="EURUSD", digits=2)
        self.assertEqual(sorted(x["level_name"] for x in studies), ["PDH", "PDL"])
        self.assertEqual(len({x["event_id"] for x in studies}), 2)

    def test_prefix_replay_preserves_event_identity_and_times(self):
        daily = [(0, 1.0, 1.20, .90, 1.1), (86400, 1.1, 1.4, 1.0, 1.3)]
        short_rows = self._break_rows(16)
        long_rows = self._break_rows(20)
        short = daily_break_studies(
            daily, closed_frame([*short_rows, (86400 + 16 * 900, 0, 0, 0, 0)], "M15"),
            86400 + 16 * 900, symbol="EURUSD", digits=2)
        long = daily_break_studies(
            daily, closed_frame([*long_rows, (86400 + 20 * 900, 0, 0, 0, 0)], "M15"),
            86400 + 20 * 900, symbol="EURUSD", digits=2)
        accepted_short = next(x for x in short if x["state"] == "ACCEPTED_BREAK_WAIT_RETEST")
        accepted_long = next(x for x in long if x["state"] == "ACCEPTED_BREAK_WAIT_RETEST")
        self.assertEqual(accepted_short, accepted_long)

    @staticmethod
    def _frame(rows, cutoff):
        return closed_frame([*rows, (rows[-1][0] + 900, 0, 0, 0, 0)], "M15", cutoff)

    @staticmethod
    def _failure_rows(count):
        rows = DailyBreakStudyTests._break_rows(count)
        rows[15] = (86400 + 15 * 900, 1.35, 1.36, 1.09, 1.10)
        return rows

    def test_prefix_matrix_candidate_then_accepted(self):
        daily = [(0, 1.0, 1.20, .90, 1.1), (86400, 1.1, 1.4, 1.0, 1.3)]
        rows = self._break_rows(16)
        signal_close, accept_close = rows[14][0] + 900, rows[15][0] + 900
        open_study = daily_break_studies(
            daily, self._frame(rows[:15], signal_close), signal_close,
            symbol="EURUSD", digits=2)
        accepted_study = daily_break_studies(
            daily, self._frame(rows, accept_close), accept_close,
            symbol="EURUSD", digits=2)
        candidate = next(x for x in open_study if x["state"] == "BREAK_CANDIDATE")
        accepted = next(x for x in accepted_study if x["state"] == "ACCEPTED_BREAK_WAIT_RETEST")
        self.assertEqual(candidate["event_id"], accepted["event_id"])
        self.assertEqual(candidate["observed_at"], accepted["observed_at"])
        self.assertEqual(candidate["state_time"], signal_close)
        self.assertEqual(accepted["state_time"], accept_close)
        self.assertNotIn("failure_time", accepted)

    def test_prefix_matrix_candidate_then_failed(self):
        daily = [(0, 1.0, 1.20, .90, 1.1), (86400, 1.1, 1.4, 1.0, 1.3)]
        rows = self._failure_rows(16)
        signal_close, failure_close = rows[14][0] + 900, rows[15][0] + 900
        open_study = daily_break_studies(
            daily, self._frame(rows[:15], signal_close), signal_close,
            symbol="EURUSD", digits=2)
        failed_study = daily_break_studies(
            daily, self._frame(rows, failure_close), failure_close,
            symbol="EURUSD", digits=2)
        candidate = next(x for x in open_study if x["state"] == "BREAK_CANDIDATE")
        failed = next(x for x in failed_study if x["state"] == "FAILED_BREAK")
        self.assertEqual(candidate["event_id"], failed["event_id"])
        self.assertEqual(candidate["observed_at"], failed["observed_at"])
        self.assertEqual(failed["failure_time"], failure_close)
        self.assertEqual(failed["state_time"], failure_close)
        self.assertNotIn("accept_time", failed)

    def test_open_candidate_identity_and_times_survive_later_prefixes(self):
        daily = [(0, 1.0, 1.20, .90, 1.1), (86400, 1.1, 1.4, 1.0, 1.3)]
        rows = self._break_rows(20)
        signal_close = rows[14][0] + 900
        short = daily_break_studies(
            daily, self._frame(rows[:15], signal_close), signal_close,
            symbol="EURUSD", digits=2)
        long = daily_break_studies(
            daily, self._frame(rows, signal_close), signal_close,
            symbol="EURUSD", digits=2)
        short_event = next(x for x in short if x["state"] == "BREAK_CANDIDATE")
        long_event = next(x for x in long if x["state"] == "BREAK_CANDIDATE")
        self.assertEqual(short_event, long_event)
        self.assertEqual((short_event["observed_at"], short_event["state_time"]),
                         (signal_close, signal_close))
        self.assertNotIn("failure_time", short_event)
        self.assertNotIn("accept_time", short_event)

    def test_no_failed_break_without_real_failure_time(self):
        daily = [(0, 1.0, 1.20, .90, 1.1), (86400, 1.1, 1.4, 1.0, 1.3)]
        scenarios = {
            "open": (self._break_rows(15), 15),
            "accepted": (self._break_rows(16), 16),
            "failed": (self._failure_rows(16), 16),
        }
        for name, (rows, count) in scenarios.items():
            with self.subTest(scenario=name):
                cutoff = 86400 + count * 900
                studies = daily_break_studies(
                    daily, self._frame(rows, cutoff), cutoff,
                    symbol="EURUSD", digits=2)
                failed = [x for x in studies if x["state"] == "FAILED_BREAK"]
                self.assertTrue(all("failure_time" in x for x in failed))
                self.assertTrue(all(x["failure_time"] <= cutoff for x in failed))
                self.assertTrue(all(x["state_time"] == x["failure_time"] for x in failed))


class Book22Tests(unittest.TestCase):
    @staticmethod
    def continuation(target, *, limit=24):
        prices = [(99, 99.9, 98.7, 99)] * 24
        prices[10] = (99, target, 98.7, 99)
        prices[17] = (99, 99.9, 98, 99)
        prices[20:] = [(99, 101.4, 98.9, 101.2), (101.2, 103, 101, 102.8),
                       (102.8, 103, 100.9, 101.7), (101.5, 103, 101, 102)]
        rates = [(i * 900, *row) for i, row in enumerate(prices[:limit])]
        frame = closed_frame([*rates, (limit * 900, 0, 0, 0, 0)], "M15")
        zone = SimpleNamespace(direction=1, confirmation_bar=21, meta={}, zone_low=100,
                               zone_high=102, type=SimpleNamespace(value="OB"))

        def displacement(bars):
            return pd.DataFrame({"displacement_bullish": bars.index == 21})

        observer = Observer(frame, [zone], displacement, 2, .01, {22 * 900: .02})
        session = Session((0, 99, 100, 90, 99), 20 * 900, 20, limit, False)
        return observer.monitor(session, 21, 20, "continuation", 1, "BEARISH")

    def test_structural_target_controls_ratio_without_moving_stop_or_target(self):
        for target, status, reason in [(108, "discarded", "below_rr"),
                                        (115, "qualified", "in_range"),
                                        (130, "discarded", "above_rr")]:
            with self.subTest(target=target):
                setup = self.continuation(target)
                self.assertEqual((setup["status"], setup["reason"]), (status, reason))
                self.assertEqual(setup["tp"], target)
                self.assertLess(setup["sl"], 98)
                self.assertEqual(setup["entry"], 101.52)
                self.assertEqual(setup["alignment"], "counter")
                self.assertEqual(setup["h4_bias"], "BEARISH")
                self.assertEqual(setup["stop_basis"], "m15_swing")
                self.assertEqual(setup["reference_spread"], .02)
                self.assertLessEqual(setup["displacement_close"], setup["confirmation"])
                self.assertLess(setup["retest"], setup["evaluated"])

    def test_waits_for_reference_candle_to_close(self):
        setup = self.continuation(115, limit=23)
        self.assertEqual((setup["status"], setup["reason"]), ("waiting", "await_reference"))
        self.assertNotIn("entry", setup)
        self.assertNotIn("tp", setup)
        self.assertNotIn("reference_open", setup)
        self.assertEqual(setup["evaluated"], 23 * 900)


if __name__ == "__main__":
    unittest.main()
