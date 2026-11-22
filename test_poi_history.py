import unittest

from ict import closed_frame
from poi_history import analyze_poi_history, date_cutoff, zone_lifecycle


DAY = 86400
BASE = date_cutoff("2025-01-01")


def daily_rows(prices):
    return [(BASE + i * DAY, *price) for i, price in enumerate(prices)]


class PoiHistoryTest(unittest.TestCase):
    def test_contact_episodes_and_strict_bullish_invalidation(self):
        rows = daily_rows([
            (10, 11, 9, 10),
            (11, 12, 10, 11),        # Edge touch.
            (11, 12, 9, 10),         # Wick crosses, close exactly on edge.
            (14, 15, 13, 14),        # Separates contact episodes.
            (11, 13, 9, 9),          # Invalidation, counts contact.
            (10, 13, 9, 12),         # Ignored after first invalidation.
            (10, 13, 9, 12),
        ])
        result = zone_lifecycle(closed_frame(rows, "D1"), 0, 10, 12, 1, 0)
        self.assertEqual(result["state"], "invalidated_by_close")
        self.assertEqual((result["contact_bars"], result["contact_episodes"]), (3, 2))
        self.assertEqual(result["first_wick_breach"]["low"], 9)
        self.assertEqual(result["first_wick_breach"]["close"], 10)
        self.assertEqual(result["first_close_invalidation"]["close"], 9)

    def test_bearish_gap_invalidates_without_fabricating_a_contact(self):
        rows = daily_rows([(11, 12, 10, 11), (13, 15, 13, 14), (13, 15, 12, 14)])
        result = zone_lifecycle(closed_frame(rows, "D1"), 0, 10, 12, -1, 0)
        self.assertEqual(result["state"], "invalidated_by_close")
        self.assertEqual(result["contact_bars"], 0)
        self.assertIsNone(result["first_wick_breach"])
        self.assertEqual(result["first_close_invalidation"]["close"], 14)

    def test_fvg_is_only_available_after_confirmation_and_replay_is_stable(self):
        candles = [(10, 11, 9, 10)] * 30 + [
            (10, 15, 10, 14), (14, 16, 13, 15), (11, 12, 9, 9), (10, 12, 9, 11),
        ]
        rows = daily_rows(candles)
        at = BASE + 32 * DAY
        before = analyze_poi_history("TEST", rows, 0, at - DAY)
        self.assertFalse(any(z["kind"] == "FVG" for z in before["zones"]))
        replay = analyze_poi_history("TEST", rows, 0, at)
        self.assertEqual(replay, analyze_poi_history("TEST", rows[:33], 0, at))
        gap = next(z for z in replay["zones"] if z["kind"] == "FVG")
        self.assertEqual((gap["low"], gap["high"], gap["state"]), (11, 13, "untouched"))
        self.assertEqual(gap["origin"]["close"], 14)
        later = analyze_poi_history("TEST", rows, 0, at + DAY)
        gap = next(z for z in later["zones"] if (z["kind"], z["low"], z["high"]) == ("FVG", 11, 13))
        self.assertEqual(gap["state"], "invalidated_by_close")
