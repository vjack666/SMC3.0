from datetime import datetime, timedelta, timezone
from unittest import TestCase
from unittest.mock import Mock, patch

from motor_smc.instrumentos import ALERT_SYMBOLS, MT5_SYMBOLS
from motor_smc.servicio import MarketPanel, PanelScope


SETTINGS = {"terminal": "example", "server": "demo", "login": 1}
NOW = datetime(2026, 11, 20, 15, tzinfo=timezone.utc)
TICK = int(NOW.timestamp()) + 7200
PROFILES = ("D1", "H4", "H1", "M15")


def bars_at(current, forming=1.1):
    return {tf: ((current - 100, 1.1, 1.2, 1.0, 1.1), (current, 1.1, 1.2, 1.0, forming))
            for tf in PROFILES}


class MarketPanelTest(TestCase):
    def setUp(self):
        self.head = Mock(return_value=(bars_at(10), TICK, TICK))
        self.history = Mock(return_value=(5, 0.00001, bars_at(10), ()))
        self.analysis = Mock(return_value={"enabled": True})
        self.openings = Mock(return_value={"checks": []})
        self.now = NOW
        self.panel = MarketPanel(lambda: SETTINGS, self.head, self.history, self.analysis,
                                 self.openings, clock=lambda: self.now, daily=Mock(return_value=10))
        self.scope = PanelScope(0)

    def refresh(self):
        self.scope.payload = self.panel.refresh("EURUSD", "M15", self.scope)
        return self.scope.payload

    def test_forming_candle_changes_chart_without_recalculating_analysis(self):
        self.assertEqual(self.refresh()["state"], "current")
        self.head.return_value = (bars_at(10, forming=1.16), TICK, TICK)
        active = self.refresh()
        self.assertEqual(active["chart"]["rows"][-1][-1], 1.16)
        self.assertEqual((self.history.call_count, self.analysis.call_count, self.openings.call_count), (1, 1, 1))
        self.head.return_value = (bars_at(20), TICK, TICK)
        self.history.return_value = (5, 0.00001, bars_at(20), ())
        self.refresh()
        self.assertEqual((self.history.call_count, self.analysis.call_count, self.openings.call_count), (2, 2, 2))

    def test_disconnect_keeps_last_success_and_recovers_without_duplicate_calculation(self):
        self.head.side_effect = RuntimeError("Terminal desconectado")
        self.assertEqual(self.refresh()["state"], "unavailable")
        self.head.side_effect = None
        good = self.refresh()
        self.now += timedelta(seconds=8)
        self.head.side_effect = RuntimeError("Terminal desconectado")
        failed = self.refresh()
        self.assertEqual(failed["state"], "stale")
        self.assertEqual(failed["last_success"], good["last_success"])
        self.assertEqual(failed["chart"], good["chart"])
        self.head.side_effect = None
        self.assertEqual(self.refresh()["state"], "current")
        self.assertEqual(self.analysis.call_count, 1)

    def test_daily_pass_reports_only_observed_assets_and_leaves_alerts_unchanged(self):
        self.assertEqual(self.panel.universe(), {"total": 33, "assets": {}})
        for symbol in MT5_SYMBOLS:
            self.panel.refresh_universe()
            self.panel.daily.assert_called_with(SETTINGS, symbol)
        self.assertEqual(set(self.panel.universe()["assets"]), set(MT5_SYMBOLS))
        self.assertEqual(ALERT_SYMBOLS, ("EURUSD", "GBPJPY", "US30"))
        with self.assertRaises(ValueError):
            self.panel.read("TVC:DXY", "D1")

    def test_read_ages_cached_result_during_a_slow_worker(self):
        self.refresh()
        self.panel.scopes["EURUSD", "M15"] = self.scope
        self.now += timedelta(seconds=30)
        with patch("motor_smc.servicio.monotonic", return_value=30):
            self.assertEqual(self.panel.read("EURUSD", "M15")["state"], "stale")
