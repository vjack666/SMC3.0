from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch

from sesiones import BAR, OpeningMonitor, assess_openings, mt5_offset, opening_schedule, utc_seconds


DAY = date(2026, 11, 19)
OFFSET = 7200


def fixture(day=DAY):
    _, _, asia, london = opening_schedule(day)[0]
    _, _, _, new_york = opening_schedule(day)[1]
    first = utc_seconds(asia) + OFFSET
    london_time = utc_seconds(london) + OFFSET
    ny_time = utc_seconds(new_york) + OFFSET
    d1 = london_time - (london_time % 86400)
    m15 = [(t, 1.1000, 1.1020, 1.0980, 1.1000)
           for t in range(first, ny_time + BAR + 1, BAR)]
    m15[(london_time - first) // BAR] = (london_time, 1.1000, 1.1051, 1.0990, 1.1010)
    m15[(ny_time - first) // BAR] = (ny_time, 1.1000, 1.1010, 1.0940, 1.0945)
    return {"D1": [(d1 - 86400, 1.1, 1.104, 1.095, 1.1),
                   (d1, 1.1, 9.0, .2, 1.1)], "M15": m15}


class SessionOpenTests(TestCase):
    def test_range_events_start_after_the_opening_and_exclude_position_zero(self):
        london = opening_schedule(DAY)[0][3]
        start = utc_seconds(london) + OFFSET
        frames = fixture()
        frames["M15"] = [
            (start, 1.100, 1.105, 1.095, 1.100),
            (start + BAR, 1.100, 1.106, 1.099, 1.101),
            (start + 2 * BAR, 1.101, 1.102, 1.093, 1.094),
            (start + 3 * BAR, 1.094, 1.100, 1.093, 1.099),
            (start + 4 * BAR, 1.099, 1.106, 1.094, 1.102),
            (start + 5 * BAR, 1.102, 1.107, 1.101, 1.106),
        ]
        results = assess_openings(DAY, london + timedelta(seconds=6 * BAR), OFFSET, frames)
        events = results[0]["events"]
        self.assertEqual([(r["open"], r["kind"], r["side"], r["level"]) for r in events],
                         [(start + BAR, "sweep", "high", 1.105), (start + 2 * BAR, "break", "low", 1.095)])
        self.assertEqual(events[0]["close_utc"], utc_seconds(london) + 2 * BAR)
        self.assertEqual(events[0]["wick"], 1.106)

    def test_range_notices_are_sent_once_per_symbol_after_close(self):
        london = opening_schedule(DAY)[0][3]
        start = utc_seconds(london) + OFFSET
        frames = fixture()
        frames["M15"] = [
            (start, 1.100, 1.105, 1.095, 1.100),
            (start + BAR, 1.100, 1.106, 1.099, 1.101),
            (start + 2 * BAR, 1.100, 1.104, 1.098, 1.101),
        ]
        now = london + timedelta(seconds=2 * BAR + 1)
        notifier = Mock()
        source = Mock(return_value=(frames, utc_seconds(now) + OFFSET))
        with TemporaryDirectory() as workspace, patch("sesiones.config", return_value={}):
            path = Path(workspace) / "alerts.json"
            monitor = OpeningMonitor(source, notifier, path)
            monitor.poll(now)
            monitor.poll(now + timedelta(seconds=10))
            OpeningMonitor(source, notifier, path).poll(now + timedelta(seconds=15))
        self.assertEqual(notifier.call_count, 3)
        self.assertEqual({call.args[0].split(" · ")[1] for call in notifier.call_args_list},
                         {"EURUSD", "GBPJPY", "US30"})
        self.assertTrue(all("Barrido del alto de Londres" in call.args[1] for call in notifier.call_args_list))

    def test_zoneinfo_handles_dst_mismatch_weeks(self):
        for day, expected in [(date(2026, 1, 19), (8, 13)),
                              (date(2026, 3, 16), (8, 12)),
                              (date(2026, 7, 20), (7, 12))]:
            self.assertEqual(tuple(spec[3].hour for spec in opening_schedule(day)), expected)

    def test_stale_or_inconsistent_time_does_not_guess_offset(self):
        now = opening_schedule(DAY)[0][3]
        self.assertEqual(mt5_offset(utc_seconds(now) + OFFSET - 3, now), OFFSET)
        self.assertIsNone(mt5_offset(utc_seconds(now) + OFFSET - 460, now))

    def test_opening_is_ignored_until_closed_even_if_its_wick_breaches(self):
        _, _, _, london = opening_schedule(DAY)[0]
        frames = fixture()
        before = assess_openings(DAY, london + timedelta(seconds=899), OFFSET, frames)
        self.assertEqual(before[0]["status"], "waiting_close")
        self.assertNotIn("high", before[0])
        frames["M15"] = [bar for bar in frames["M15"] if bar[0] <= utc_seconds(london) + OFFSET]
        no_successor = assess_openings(DAY, london + timedelta(seconds=901), OFFSET, frames)
        self.assertEqual(no_successor[0]["status"], "waiting_close")
        self.assertNotIn("low", no_successor[0])

    def test_closed_wicks_are_available_without_a_breach_or_context(self):
        frames = fixture()
        london = opening_schedule(DAY)[0][3]
        opened = utc_seconds(london) + OFFSET
        for prior_bar, expected in [(True, "closed"), (False, "missing_context")]:
            frames["M15"] = [row if row[0] != opened else (opened, 1.1, 1.1014, 1.0991, 1.1002)
                             for row in frames["M15"] if prior_bar or row[0] != opened - BAR]
            result = assess_openings(DAY, london + timedelta(seconds=BAR), OFFSET, frames)[0]
            self.assertEqual((result["status"], result["high"], result["low"]),
                             (expected, 1.1014, 1.0991))
            self.assertEqual(result["open"], opened)
            self.assertEqual(result["session_end"], (opened // 86400 + 1) * 86400)
            self.assertFalse(result.get("alerts"))

    def test_reads_and_caches_ranges_for_the_requested_symbol(self):
        now = opening_schedule(DAY)[1][3] + timedelta(seconds=BAR)
        highs = {"EURUSD": 1.1051, "GBPJPY": 208.795, "US30": 49125.13}

        def source(settings, symbol):
            frames = fixture()
            opened = utc_seconds(opening_schedule(DAY)[0][3]) + OFFSET
            frames["M15"] = [row if row[0] != opened else (opened, 1.1, highs[symbol], 1.099, 1.101)
                             for row in frames["M15"]]
            return frames, utc_seconds(now) + OFFSET

        reader = Mock(side_effect=source)
        with patch("sesiones.config", return_value={}):
            monitor = OpeningMonitor(data_reader=reader)
            for symbol in highs:
                snapshot = monitor.read(now, symbol)
                self.assertEqual(snapshot["symbol"], symbol)
                london = next(r for r in snapshot["checks"] if r["id"] == f"{DAY}/Londres")
                self.assertEqual(london["high"], highs[symbol])
            self.assertEqual(monitor.read(now)["symbol"], "EURUSD")
        self.assertEqual(reader.call_count, 3)

    def test_first_candle_compares_daily_and_the_correct_prior_session(self):
        _, _, _, new_york = opening_schedule(DAY)[1]
        results = assess_openings(DAY, new_york + timedelta(seconds=BAR), OFFSET, fixture())
        london, ny = results
        self.assertEqual(london["alerts"], ["Barrido de PDH", "Barrido de máximo de Asia"])
        self.assertEqual(ny["alerts"], ["Ruptura de PDL", "Ruptura de mínimo de Londres"])
        self.assertEqual(ny["references"][1]["high"], 1.1051)
        self.assertEqual(london["references"][0]["high"], 1.104)

    def test_native_alert_once_even_after_restart(self):
        _, _, _, london = opening_schedule(DAY)[0]
        now = london + timedelta(seconds=BAR + 1)
        notifier = Mock()
        source = Mock(return_value=(fixture(), utc_seconds(now) + OFFSET))
        with TemporaryDirectory() as workspace, patch("sesiones.config", return_value={}):
            path = Path(workspace) / "alerts.json"
            monitor = OpeningMonitor(source, notifier, path)
            monitor.poll(now)
            monitor.poll(now + timedelta(seconds=12))
            OpeningMonitor(source, notifier, path).poll(now + timedelta(seconds=14))
        notifier.assert_called_once()
        self.assertIn("Barrido de PDH", notifier.call_args.args[1])
