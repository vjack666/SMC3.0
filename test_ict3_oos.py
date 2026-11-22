"""Fase 7 — pruebas del protocolo OOS (sin MT5, sin servidor, sin escrituras).

Ejecutar: ``.venv/Scripts/python.exe -m unittest test_ict3_oos -v``
"""
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
import unittest

import ict3_oos as oos

START = int(datetime(2026, 11, 1, tzinfo=timezone.utc).timestamp())


class InventoryTests(unittest.TestCase):
    def test_inventory_fields_and_declared_gaps(self):
        candles = oos.synthetic_candles(
            "EURUSD", "M15", 21, start_epoch=START, seed=1, gap_every=5)
        row = oos.inventory_entry("EURUSD", "M15", candles)
        self.assertEqual(row["alias"], "EUR/USD")
        self.assertEqual(row["source"], oos.SYNTHETIC_SOURCE)
        self.assertTrue(row["declared_synthetic"])
        self.assertEqual(row["candles"], 21)
        # Huecos declarados en los indices 5, 10, 15 y 20.
        self.assertEqual(row["gaps"], 4)
        self.assertEqual(row["first_close_epoch"], candles[0][0] + oos.SECONDS["M15"])
        self.assertEqual(row["last_close_epoch"], candles[-1][0] + oos.SECONDS["M15"])
        self.assertEqual(row["first_close"], oos._iso(candles[0][0] + 900))
        self.assertEqual(row["real_coverage"], oos.REAL_PENDING)

    def test_coherent_ohlc_and_determinism(self):
        a = oos.synthetic_candles("GBPJPY", "D1", 30, start_epoch=START, seed=9)
        b = oos.synthetic_candles("GBPJPY", "D1", 30, start_epoch=START, seed=9)
        self.assertEqual(a, b)
        for opened, o, h, low, c in a:
            self.assertGreaterEqual(h, max(o, c))
            self.assertLessEqual(low, min(o, c))
        self.assertNotEqual(a, oos.synthetic_candles(
            "GBPJPY", "D1", 30, start_epoch=START, seed=10))

    def test_pending_inventory_never_invents_coverage(self):
        rows = oos.pending_inventory(symbols=("EURUSD",), frames=("D1", "M15"))
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertEqual(row["source"], oos.REAL_PENDING)
            self.assertEqual(row["candles"], 0)
            self.assertIsNone(row["first_close"])
            self.assertIsNone(row["last_close"])
            self.assertEqual(row["gaps"], 0)
            self.assertFalse(row["declared_synthetic"])

    def test_common_coverage_records_exclusions(self):
        dataset = {
            "EURUSD": {"M15": [(START, 1, 1.1, 0.9, 1.05)], "D1": []},
            "GBPJPY": {"D1": [(START, 1, 1.1, 0.9, 1.05)]},
        }
        inventory = oos.build_inventory(dataset)
        coverage = oos.common_coverage(inventory, frames=("M15",))
        self.assertEqual(coverage["included"], ["EURUSD"])
        self.assertEqual([row["symbol"] for row in coverage["excluded"]], ["GBPJPY"])
        self.assertEqual(coverage["excluded"][0]["reason"], "MISSING_FRAMES")

    def test_alias_fallback(self):
        self.assertEqual(oos.alias_for("EURUSD"), "EUR/USD")
        self.assertEqual(oos.alias_for("XYZ"), "XYZ")


class PartitionTests(unittest.TestCase):
    def test_separation_is_disjoint_and_complete(self):
        observations = oos.synthetic_observations(
            oos.FROZEN_PARAMETERS, symbols=("EURUSD", "GBPJPY"), days=20)
        partition = oos.separate_calibration_evaluation(
            oos.FROZEN_PARAMETERS, observations)
        self.assertEqual(partition["separation_date"], "2026-11-15")
        integrity = oos.calibration_evaluation_integrity(partition)
        self.assertTrue(integrity["disjoint"])
        self.assertTrue(integrity["complete"])
        self.assertTrue(integrity["separated"])
        self.assertEqual(integrity["counts"]["total"], len(observations))
        self.assertEqual(integrity["counts"]["calibration"]
                         + integrity["counts"]["evaluation"], len(observations))
        self.assertTrue(all(o["observed_date"] < "2026-11-15"
                            for o in partition["calibration"]))
        self.assertTrue(all(o["observed_date"] >= "2026-11-15"
                            for o in partition["evaluation"]))

    def test_frozen_parameters_are_immutable(self):
        self.assertEqual(oos.FROZEN_PARAMETERS.mode, oos.MODE)
        self.assertEqual(oos.FROZEN_PARAMETERS.windows, (4, 8, 16, 32))
        with self.assertRaises(FrozenInstanceError):
            setattr(oos.FROZEN_PARAMETERS, "separation_date", "2020-01-01")
        custom = oos.FrozenParameters(separation_date="2026-10-01")
        self.assertEqual(custom.separation_date, "2026-10-01")
        partition = oos.separate_calibration_evaluation(custom, [])
        self.assertEqual(partition["frozen_parameters"]["separation_date"], "2026-10-01")


class GroupingTests(unittest.TestCase):
    def test_grouping_uses_all_six_dimensions(self):
        observations = oos.synthetic_observations(
            oos.FROZEN_PARAMETERS, symbols=("EURUSD", "GBPJPY"), days=12)
        grouped = oos.group_observed_states(observations)
        self.assertEqual(grouped["dimensions"], oos.DIMENSIONS)
        self.assertEqual(sum(row["count"] for row in grouped["rows"]), len(observations))
        for row in grouped["rows"]:
            self.assertTrue(set(oos.DIMENSIONS).issubset(row))
            self.assertIn(row["level"], oos.LEVELS)
            self.assertIn(row["state"], oos.STATES)
            self.assertIn(row["window"], oos.DEFAULT_WINDOWS)
            self.assertIn(row["session"], oos.SESSIONS)
        self.assertEqual(sum(grouped["denominators"]["by_symbol"].values()),
                         len(observations))
        self.assertEqual(sum(grouped["denominators"]["by_symbol_level"].values()),
                         len(observations))

    def test_effective_coverage_denominators(self):
        observations = oos.synthetic_observations(
            oos.FROZEN_PARAMETERS, symbols=("US30",), days=15)
        coverage = oos.group_observed_states(observations)["effective_coverage"]
        self.assertEqual(coverage["total"], len(observations))
        self.assertLessEqual(coverage["with_poi_and_complete_window"],
                             coverage["with_poi"])
        self.assertLessEqual(coverage["with_poi_and_complete_window"],
                             coverage["complete_window"])
        self.assertGreaterEqual(coverage["ratio"], 0.0)
        self.assertLessEqual(coverage["ratio"], 1.0)

    def test_session_assignments_are_declared(self):
        self.assertEqual(oos.session_for_time(START + 3 * 3600), "ASIA")
        self.assertEqual(oos.session_for_time(START + 8 * 3600), "LONDON")
        self.assertEqual(oos.session_for_time(START + 14 * 3600), "NEW_YORK")
        self.assertEqual(oos.session_for_time(START + 23 * 3600), "OTHER")


class PrefixInvarianceTests(unittest.TestCase):
    def setUp(self):
        self.candles = oos.synthetic_candles(
            "EURUSD", "M15", 64, start_epoch=START, seed=3)
        self.cutoffs = [row[0] + 900 for row in self.candles[::7]]

    def test_prefix_equals_full_at_every_cutoff(self):
        report = oos.verify_prefix_invariance(
            self.candles, "M15", self.cutoffs, level=1.0)
        self.assertTrue(report["invariant"], report["mismatches"])
        self.assertEqual(report["cutoffs_checked"], len(self.cutoffs))
        self.assertTrue(all(check["equal"] for check in report["checks"]))
        self.assertEqual(report["mismatches"], [])

    def test_prefix_of_excludes_future_candles(self):
        cutoff = self.cutoffs[5]
        prefix = oos.prefix_of(self.candles, "M15", cutoff)
        self.assertTrue(all(row[0] + 900 <= cutoff for row in prefix))
        self.assertLess(len(prefix), len(self.candles))

    def test_leaking_reducer_is_detected(self):
        def leaking(candles, frame, cutoff, level):
            # Reductor deliberadamente NO casual: mira la ultima vela disponible
            # en la serie completa, sin respetar el corte.
            return (("LEAK", round(candles[-1][4], 5)),) if candles else ()

        report = oos.verify_prefix_invariance(
            self.candles, "M15", self.cutoffs, reducer=leaking, level=1.0)
        self.assertFalse(report["invariant"])
        self.assertTrue(report["mismatches"])


class ExecutionForbiddenTests(unittest.TestCase):
    def test_refuse_execution_metrics_is_explicit(self):
        for metric in ("fills", "lotaje", "pnl", "equity_curve"):
            with self.subTest(metric=metric):
                with self.assertRaises(oos.ExecutionMetricsForbidden):
                    oos.refuse_execution_metrics(metric)

    def test_forbidden_keys_are_rejected_recursively(self):
        with self.assertRaises(oos.ExecutionMetricsForbidden):
            oos.assert_no_execution_metrics({"ict3": {"events": [{"lots": 1}]}})
        with self.assertRaises(oos.ExecutionMetricsForbidden):
            oos.assert_no_execution_metrics([{"pnl": 10.0}])
        self.assertTrue(oos.assert_no_execution_metrics(
            {"states": [{"state": "RETESTING_POI", "count": 3}]}))


class ReportTests(unittest.TestCase):
    def test_report_without_source_marks_real_coverage_pending(self):
        report = oos.build_report(dataset=None)
        self.assertEqual(report["source"], oos.REAL_PENDING)
        self.assertTrue(report["declared_synthetic"])
        self.assertEqual(report["real_coverage"], oos.REAL_PENDING)
        self.assertTrue(all(row["candles"] == 0 for row in report["inventory"]))
        self.assertTrue(report["prefix_invariance"]["invariant"])
        self.assertTrue(report["integrity"]["separated"])
        self.assertEqual(report["mode"], oos.MODE)

    def test_report_with_dataset_is_reproducible(self):
        dataset = {"EURUSD": {"M15": oos.synthetic_candles(
            "EURUSD", "M15", 48, start_epoch=START, seed=2, gap_every=9)}}
        first = oos.build_report(dataset=dataset, seed=2)
        second = oos.build_report(dataset=dataset, seed=2)
        self.assertEqual(first, second)
        self.assertEqual(first["source"], oos.SYNTHETIC_SOURCE)
        self.assertTrue(first["prefix_invariance"]["invariant"])
        self.assertTrue(oos.assert_no_execution_metrics(first))
        markdown = oos.render_report(first)
        self.assertIn("Solo estados observados", markdown)
        self.assertIn("EURUSD", markdown)
        self.assertIn("Invariancia prefijo==completa: OK", markdown)

    def test_module_does_not_import_mt5_or_read_data(self):
        with open(oos.__file__, encoding="utf-8") as handle:
            source = handle.read()
        self.assertNotIn("import MetaTrader5", source)
        self.assertNotIn("import mt5", source)
        self.assertNotIn("mt5.", source)
        self.assertIn("SYNTHETIC_DECLARED", source)


if __name__ == "__main__":
    unittest.main()
