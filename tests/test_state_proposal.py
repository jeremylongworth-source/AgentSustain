import copy
import json
import unittest

from scripts.contract_validation import ROOT, validate_state
from scripts.state_proposal import propose


class StateProposalTests(unittest.TestCase):
    def setUp(self):
        self.state = json.loads((ROOT / "examples/architecture-state.json").read_text(encoding="utf-8"))
        self.result = copy.deepcopy(self.state["results"][0])
        self.result["id"] = "res-new"
        self.result["metrics"] = []

    def test_append_preserves_inputs_and_revision(self):
        saved = copy.deepcopy(self.state)
        proposal = propose(self.state, self.result, "Validate new result")
        self.assertEqual(self.state, saved)
        self.assertEqual(proposal["base_revision"], saved["revision"])
        self.assertEqual(proposal["state"]["revision"], saved["revision"] + 1)
        self.assertEqual(proposal["state"]["results"][:-1], saved["results"])

    def test_reused_ids_cannot_replace_history(self):
        with self.assertRaisesRegex(ValueError, "Result ID already"):
            propose(self.state, self.state["results"][0], "Attempt replacement")
        with self.assertRaisesRegex(ValueError, "Evidence ID already"):
            propose(self.state, self.result, "Attempt replacement", self.state["evidence"])

    def test_review_obligations_cannot_disappear(self):
        review = {"id": "review-1", "state": "LEGAL_REVIEW_REQUIRED", "reason": "Legal decision pending",
                  "scope": "organization", "reviewer_role": "legal professional", "status": "open", "resolution": None}
        self.state["review_requirements"] = [review]
        with self.assertRaisesRegex(ValueError, "review requirement omitted"):
            propose(self.state, self.result, "Attempt omission")
        self.result["review_requirements"] = [copy.deepcopy(review)]
        with self.assertRaisesRegex(ValueError, "review state omitted"):
            propose(self.state, self.result, "Attempt state omission")
        self.result["review_states"].append("LEGAL_REVIEW_REQUIRED")
        proposal = propose(self.state, self.result, "Retain legal review")
        self.assertEqual(proposal["state"]["review_requirements"], [review])

    def test_gaps_and_assumptions_cannot_disappear(self):
        gap = {"id": "gap-1", "field": "fuel", "reason": "Units missing", "impact": "No conversion", "remedy": "Obtain units"}
        self.state["data_gaps"] = [gap]
        with self.assertRaisesRegex(ValueError, "Existing gap omitted"):
            propose(self.state, self.result, "Attempt omission")
        self.result["data_gaps"] = [copy.deepcopy(gap)]
        self.state["assumptions"] = ["Synthetic assumption"]
        with self.assertRaisesRegex(ValueError, "Existing assumption omitted"):
            propose(self.state, self.result, "Attempt assumption omission")
        self.result["assumptions"] = ["Synthetic assumption"]
        propose(self.state, self.result, "Preserve gaps and assumptions")

    def test_nonfinite_values_rejected(self):
        for value in (float("nan"), float("inf")):
            self.state["results"][0]["metrics"][0]["value"] = value
            with self.assertRaisesRegex(ValueError, "Nonfinite metric"):
                validate_state(self.state)

    def test_self_and_indirect_lineage_cycles_rejected(self):
        metric = self.state["results"][0]["metrics"][0]
        metric["calculation"]["inputs"] = [metric["id"]]
        with self.assertRaisesRegex(ValueError, "lineage cycle"):
            validate_state(self.state)
        metric["calculation"]["inputs"] = ["ev-001"]
        self.state["evidence"][0]["calculation"] = {
            "formula": "Derived from output", "inputs": [metric["id"]], "conversions": [], "rounding": "none"}
        with self.assertRaisesRegex(ValueError, "lineage cycle"):
            validate_state(self.state)


if __name__ == "__main__":
    unittest.main()
