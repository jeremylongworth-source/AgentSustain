import copy
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.data_tools import baseline, compare, convert, kpi, number, period, serialize
from scripts.contract_validation import ROOT


def metric(value, unit="kWh", name="Electricity", source="ev-1", interval="2025"):
    return {"value": value, "unit": unit, "name": name, "boundary_id": "b-1",
            "evidence_ids": [source], "period": period(interval)}


class DataToolTests(unittest.TestCase):
    def test_known_answer_conversions(self):
        for value, source, target, expected in [
            (2, "MWh", "kWh", "2000"), (1000, "L", "m3", "1"),
            (1, "kWh", "MJ", "3.6"), (2500, "kg", "t", "2.5"),
            (2, "t CO2e", "kg CO2e", "2000"),
        ]:
            with self.subTest(source=source, target=target):
                self.assertEqual(convert(value, source, target)["value"], Decimal(expected))

    def test_unsafe_conversions_rejected(self):
        for source, target in [("kg", "m3"), ("L", "kWh"), ("ton", "kg"), ("CAD", "USD"), ("kg", "kg CO2e")]:
            with self.subTest(source=source, target=target), self.assertRaises(ValueError):
                convert(1, source, target)

    def test_unknown_nonfinite_and_bool_rejected(self):
        for value in [None, True, "NaN", "Infinity", float("inf"), "missing"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                number(value)

    def test_explicit_calendar_periods(self):
        self.assertEqual(period("2024-02"), {"start": "2024-02-01", "end": "2024-02-29"})
        self.assertEqual(period("2025")["end"], "2025-12-31")
        self.assertEqual(period({"start": "2025-04-01", "end": "2026-03-31"})["end"], "2026-03-31")

    def test_ambiguous_invalid_and_reversed_periods_rejected(self):
        for value in ["FY2025", "01/02/2025", "2025-13", "2025-00", {"start": "2025-02-30", "end": "2025-03-01"}, {"start": "2025-04-01", "end": "2025-03-01"}]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                period(value)

    def test_baseline_known_answer(self):
        metrics = [metric(1, "MWh", source="a"), metric(500, source="b")]
        self.assertEqual(baseline(metrics, "kWh", True)["value"], Decimal(1500))

    def test_baseline_does_not_double_count_or_guess_coverage(self):
        metrics = [metric(100, source="a"), metric(100, source="a")]
        with self.assertRaises(ValueError):
            baseline(metrics, "kWh", True)
        with self.assertRaises(ValueError):
            baseline([metric(100)], "kWh")
        missing = metric(100, source="b")
        missing["evidence_ids"] = []
        with self.assertRaises(ValueError):
            baseline([metric(100, source="a"), missing], "kWh", True)

    def test_shared_document_with_reconciled_disjoint_lines(self):
        a, b = metric(200, "kg", source="document"), metric(300, "kg", source="document")
        a["id"], b["id"] = "paper", "cardboard"
        coverage = {
            "paper": [{"evidence_id": "document", "source_fragment": "line 1"}],
            "cardboard": [{"evidence_id": "document", "source_fragment": "line 2"}],
        }
        result = baseline([a, b], "kg", True, coverage)
        self.assertEqual(result["value"], Decimal(500))
        self.assertEqual(result["coverage_details"], coverage)
        coverage["cardboard"][0]["source_fragment"] = "line 1"
        with self.assertRaisesRegex(ValueError, "fragment reused"):
            baseline([a, b], "kg", True, coverage)

    def test_coverage_cannot_invent_sources_or_omit_metrics(self):
        a, b = metric(200, "kg", source="document"), metric(300, "kg", source="document")
        a["id"], b["id"] = "paper", "cardboard"
        coverage = {"paper": [{"evidence_id": "document", "source_fragment": "line 1"}]}
        with self.assertRaisesRegex(ValueError, "every selected metric"):
            baseline([a, b], "kg", True, coverage)
        coverage["cardboard"] = [{"evidence_id": "invented-source", "source_fragment": "line 2"}]
        with self.assertRaisesRegex(ValueError, "evidence references"):
            baseline([a, b], "kg", True, coverage)

    def test_mixed_periods_boundaries_and_missing_values_block_baseline(self):
        for change in [{"period": period("2024")}, {"boundary_id": "b-2"}, {"value": None}]:
            metrics = [metric(100, source="a"), metric(100, source="b")]
            metrics[1].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                baseline(metrics, "kWh", True)

    def test_kpi_ratio_and_percentage(self):
        self.assertEqual(kpi(metric(1000), metric(200, "count"), "ratio")["value"], Decimal(5))
        self.assertEqual(kpi(metric("0.5", "t"), metric(1000, "kg"), "percent")["value"], Decimal(50))

    def test_bad_kpi_denominators_and_percent_dimensions(self):
        for value in [0, -1, None]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                kpi(metric(100), metric(value, "count"), "ratio")
        with self.assertRaises(ValueError):
            kpi(metric(100), metric(10, "kg"), "percent")

    def test_comparison_known_answer_and_zero_prior(self):
        prior, current = metric(100, interval="2022"), metric(80, interval="2023")
        result = compare(prior, current, True)
        self.assertEqual(result["absolute_change"], Decimal(-20))
        self.assertEqual(result["percentage_change"], Decimal(-20))
        prior["value"] = 0
        result = compare(prior, current, True)
        self.assertEqual(result["absolute_change"], Decimal(80))
        self.assertIsNone(result["percentage_change"])
        self.assertIsNotNone(result["percentage_gap"])

    def test_comparison_rejects_unsupported_comparability(self):
        prior, current = metric(100, interval="2022"), metric(80, interval="2023")
        with self.assertRaises(ValueError):
            compare(prior, current)
        for change in [{"period": period("2022")}, {"period": period("2024")}, {"name": "Natural gas"}, {"boundary_id": "b-2"}]:
            changed = copy.deepcopy(current)
            changed.update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                compare(prior, changed, True)

    def test_decimal_precision_and_serialization(self):
        self.assertEqual(convert("0.1", "kWh", "Wh")["value"], Decimal(100))
        self.assertEqual(serialize(Decimal("0.125")), 0.125)
        for value in [Decimal("1e999"), Decimal("1e-999")]:
            with self.assertRaises(ValueError):
                serialize(value)

    def test_cli_success_and_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            request = Path(directory) / "request.json"
            request.write_text(json.dumps({"operation": "convert", "value": 2, "source_unit": "MWh", "target_unit": "kWh"}), encoding="utf-8")
            completed = subprocess.run([sys.executable, str(ROOT / "scripts/data_tools.py"), str(request)], capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(completed.stdout)["value"], 2000)
            request.write_text(json.dumps({"operation": "convert", "value": 2, "source_unit": "kg", "target_unit": "m3"}), encoding="utf-8")
            completed = subprocess.run([sys.executable, str(ROOT / "scripts/data_tools.py"), str(request)], capture_output=True, text=True)
            self.assertEqual(completed.returncode, 2)
            self.assertEqual(json.loads(completed.stdout)["error"], "INVALID_INPUT")


if __name__ == "__main__":
    unittest.main()
