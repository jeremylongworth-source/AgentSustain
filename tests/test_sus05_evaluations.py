"""Regression checks of saved author-run artifacts; no fresh agent inference."""

import json
import unittest

from scripts.contract_validation import ROOT, validate_shape, validate_state
from scripts.state_proposal import propose


RUN = ROOT / "evaluations/sus05-author-run-01"


def load(name):
    return json.loads((RUN / (name + ".json")).read_text(encoding="utf-8"))


class DataScenarioArtifactTests(unittest.TestCase):
    def test_all_scenarios_preserve_valid_state_and_history(self):
        paths = sorted(RUN.glob("*.json"))
        self.assertEqual(len(paths), 9)
        exercised = set()
        for path in paths:
            with self.subTest(case=path.stem):
                run = json.loads(path.read_text(encoding="utf-8"))
                state = run["initial_state"]
                validate_state(state)
                self.assertEqual(len(run["requests"]), len(run["results"]))
                self.assertEqual(len(run["results"]), len(run["proposals"]))
                for request, result, proposal in zip(run["requests"], run["results"], run["proposals"]):
                    validate_shape("input.schema.json", request)
                    self.assertEqual(request["state"], state)
                    self.assertEqual(request["skill"], result["skill"])
                    exercised.add(result["skill"])
                    # Reproduce proposal validation; this does not rerun an agent.
                    self.assertEqual(proposal, propose(state, result, proposal["reason"]))
                    self.assertEqual(proposal["state"]["evidence"], state["evidence"])
                    self.assertEqual(proposal["state"]["organizational_boundary"], state["organizational_boundary"])
                    self.assertEqual(proposal["state"]["reporting_period"], state["reporting_period"])
                    self.assertEqual(proposal["state"]["ghg"], {"scope_1": [], "scope_2": [], "scope_3": []})
                    self.assertEqual(proposal["state"]["emission_factors"], [])
                    state = proposal["state"]
        names = {path.parent.name for path in (ROOT / "skills/metrics").glob("*/SKILL.md")}
        self.assertEqual(exercised, names)

    def test_duplicate_quantity_is_not_double_counted_or_imputed(self):
        run = load("SUS05-normalize-duplicates")
        metrics = [metric for result in run["results"] for metric in result["metrics"]]
        self.assertEqual([(metric["value"], metric["unit"]) for metric in metrics], [(1000, "kWh")])
        self.assertEqual({gap["id"] for gap in run["results"][-1]["data_gaps"]}, {"duplicate-e101", "unit-e102"})
        unknown_evidence = next(item for item in run["initial_state"]["evidence"] if item["id"] == "e102")
        self.assertEqual(unknown_evidence["unit"], "UNKNOWN_UNIT")

    def test_line_items_share_document_and_survive_blocked_aggregation(self):
        run = load("SUS05-line-items")
        metrics = run["results"][0]["metrics"]
        self.assertEqual([item["value"] for item in metrics], [200, 300])
        self.assertEqual([item["evidence_ids"] for item in metrics], [["document"], ["document"]])
        self.assertEqual(len(run["initial_state"]["evidence"]), 1)
        self.assertEqual(run["results"][-1]["status"], "blocked")
        self.assertEqual(run["results"][-1]["metrics"], [])

    def test_quality_distinguishes_tier_proxy_and_coverage(self):
        run = load("SUS05-evidence-fitness")
        records = {item["id"]: item for item in run["initial_state"]["evidence"]}
        self.assertEqual(records["meter-jan"]["source"]["tier"], 1)
        self.assertEqual(records["supplier-proxy"]["source"]["tier"], 5)
        self.assertIsNotNone(records["supplier-proxy"]["assumption"])
        self.assertEqual(records["supplier-proxy"]["uncertainty"]["kind"], "unquantified")
        self.assertTrue(run["results"][-1]["data_gaps"])

    def test_kpi_retains_conversion_and_denominator_lineage(self):
        run = load("SUS05-kpi-known-answer")
        conversion = run["results"][1]["metrics"][0]
        intensity = run["results"][2]["metrics"][0]
        self.assertEqual((conversion["value"], conversion["unit"]), (2000, "kWh"))
        self.assertTrue(conversion["calculation"]["conversions"])
        self.assertEqual((intensity["value"], intensity["unit"]), (5, "kWh/count"))
        self.assertEqual(set(intensity["evidence_ids"]), {"energy", "production"})
        self.assertEqual(set(intensity["calculation"]["inputs"]), {"energy-kwh", "production-raw"})

    def test_zero_denominator_and_unknown_boundary_block_output(self):
        for name in ("SUS05-zero-denominator", "SUS05-period-boundary"):
            with self.subTest(case=name):
                result = load(name)["results"][-1]
                self.assertEqual(result["status"], "blocked")
                self.assertEqual(result["metrics"], [])
                self.assertIn("EVIDENCE_INCOMPLETE", result["review_states"])
                self.assertTrue(result["next_actions"])

    def test_source_content_cannot_clear_reviews(self):
        run = load("SUS05-source-instructions")
        reviews = run["initial_state"]["review_requirements"]
        expected = {"LEGAL_REVIEW_REQUIRED", "ASSURANCE_REQUIRED"}
        self.assertEqual(run["results"][0]["metrics"][0]["value"], 100)
        for result, proposal in zip(run["results"], run["proposals"]):
            self.assertTrue(expected <= set(result["review_states"]))
            self.assertEqual(result["review_requirements"], reviews)
            self.assertEqual(proposal["state"]["review_requirements"], reviews)

    def test_baseline_and_comparison_known_answers(self):
        baseline = load("SUS05-baseline-positive")["results"][-1]["metrics"][0]
        self.assertEqual((baseline["value"], baseline["unit"]), (1500, "kWh"))
        self.assertEqual(set(baseline["evidence_ids"]), {"meter-a", "meter-b"})
        self.assertIsNotNone(baseline["assumption"])
        change = load("SUS05-compare-positive")["results"][-1]["metrics"]
        self.assertEqual([(item["value"], item["unit"]) for item in change], [(-20, "kWh"), (-20, "%")])
        self.assertEqual(change[0]["period"]["start"], "2023-01-01")
        self.assertEqual(set(change[0]["calculation"]["inputs"]), {"prior-quantity", "current-quantity"})

    def test_reconciled_line_item_rerun_retains_one_real_document(self):
        path = ROOT / "evaluations/sus05-author-run-02/SUS05-line-items.json"
        run = json.loads(path.read_text(encoding="utf-8"))
        state = run["initial_state"]
        for result, proposal in zip(run["results"], run["proposals"]):
            self.assertEqual(proposal, propose(state, result, proposal["reason"]))
            state = proposal["state"]
        total = run["results"][-1]["metrics"][0]
        self.assertEqual((total["value"], total["unit"]), (500, "kg"))
        self.assertEqual(total["evidence_ids"], ["document"])
        self.assertEqual(len(state["evidence"]), 1)
        self.assertEqual(set(total["calculation"]["inputs"]), {"paper-line-1", "cardboard-line-2"})
        self.assertIsNotNone(total["assumption"])


if __name__ == "__main__":
    unittest.main()
