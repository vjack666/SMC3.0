from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock

from diario import read_json
from motor_smc.avisos import MarketNotices
from motor_smc.servicio import MarketPanel
from motor_smc.instrumentos import FOREX_SYMBOLS


NOW = datetime(2026, 11, 20, 15, tzinfo=timezone.utc)
OFFSET = 7200
AT = int(NOW.timestamp()) + OFFSET
ACCOUNT = ("terminal", "demo", 1)


def snapshot(when, status="qualified", *, evaluated=None):
    return {"symbol": "EURUSD", "asof": when, "book22": [
        {"id": "simulada", "model": "continuation", "direction": -1, "status": status,
         "evaluated": when if evaluated is None else evaluated, "rr": 3.52},
    ]}


class MarketNoticesTest(TestCase):
    def test_no_history_on_startup_and_only_new_qualification(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "notice.json"
            notify = Mock()
            monitor = MarketNotices(notify, path)
            monitor.observe_analysis(ACCOUNT, snapshot(AT - 1800), NOW, OFFSET, 2)
            monitor.observe_analysis(ACCOUNT, snapshot(AT - 900, "waiting"), NOW, OFFSET, 2)
            monitor.observe_analysis(ACCOUNT, snapshot(AT, "discarded"), NOW, OFFSET, 2)
            notify.assert_not_called()
            close = AT + 900
            now = NOW + timedelta(seconds=910)
            monitor.observe_analysis(ACCOUNT, snapshot(close), now, OFFSET, 2)
            monitor.observe_analysis(ACCOUNT, snapshot(close), now, OFFSET, 2)
            self.assertEqual(notify.call_count, 1)
            self.assertIn("Venta · Continuación · 3.52R", notify.call_args.args[1])
            self.assertEqual(len(read_json(path)), 1)
            restarted = MarketNotices(notify, path)
            restarted.observe_analysis(ACCOUNT, snapshot(AT), now, OFFSET, 2)
            restarted.observe_analysis(ACCOUNT, snapshot(close), now, OFFSET, 2)
            restarted.observe_analysis(ACCOUNT, snapshot(close + 900, evaluated=close + 600),
                                      now + timedelta(seconds=900), OFFSET, 2)
            self.assertEqual(notify.call_count, 1)

    def test_skip_result_without_recent_close_or_quote(self):
        notify = Mock()
        monitor = MarketNotices(notify)
        monitor.observe_analysis(ACCOUNT, snapshot(AT - 1800), NOW, OFFSET, 2)
        monitor.observe_analysis(ACCOUNT, snapshot(AT - 900), NOW, OFFSET, 2)
        monitor.observe_analysis(ACCOUNT, snapshot(AT), NOW, OFFSET, 181)
        monitor.observe_analysis(ACCOUNT, snapshot(AT + 900), NOW + timedelta(minutes=15), None, 2)
        notify.assert_not_called()

    def test_debounce_connection_and_ignore_startup_failure(self):
        notify = Mock()
        monitor = MarketNotices(notify)
        for seconds, connected in ((0, False), (50, False), (100, False), (120, True),
                                   (150, False), (180, True), (210, False), (250, False), (302, False),
                                   (310, False), (320, True), (330, True), (355, True), (400, True)):
            monitor.observe_connection(ACCOUNT, connected, NOW + timedelta(seconds=seconds))
        self.assertEqual(notify.call_count, 2)
        self.assertIn("sin conexión", notify.call_args_list[0].args[1])
        self.assertIn("recuperada", notify.call_args_list[1].args[1])

    def test_forex_and_us30_are_pinned_without_using_view_slots(self):
        panel = MarketPanel(notices=Mock())
        self.assertEqual(panel.watch_scopes, tuple((symbol, "M15") for symbol in (*FOREX_SYMBOLS, "US30")))
        for symbol in ("EURAUD", "EURCAD", "EURJPY", "AUDUSD", "USDJPY", "GER30", "SPX500"):
            panel.read(symbol, "H1")
        self.assertEqual(len(panel.scopes), 33)
        self.assertTrue(set(panel.watch_scopes) <= panel.scopes.keys())

    def test_batch_reuses_calculation_until_closed_signature_changes(self):
        from test_motor_smc import bars_at

        source = bars_at(10)
        full = Mock(return_value=(5, .00001, source, ()))
        probe = Mock(return_value={"EURUSD": ({"M15": source["M15"]}, AT, AT)})
        monitor = MarketPanel(lambda: {"terminal": "mock", "login": 1, "server": "demo"},
                              bars=full, analysis=Mock(return_value={"asof": 10}),
                              openings=Mock(), clock=lambda: NOW, notices=Mock(), watch_heads=probe)
        key = ("EURUSD", "M15")
        batch = [(key, monitor.scopes[key])]
        monitor.refresh_watch_batch(batch)
        monitor.refresh_watch_batch(batch)
        self.assertEqual(full.call_count, 1)
        self.assertEqual(monitor.notices.observe_analysis.call_count, 1)
        self.assertEqual(monitor.universe()["intraday"]["EURUSD"]["closed"], 10)
