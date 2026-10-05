import copy
import json
import re
import unittest

from jsonschema import Draft202012Validator, ValidationError

from contract_checks import ROOT, SCHEMAS, validate_shape, validate_state


def fixture(name):
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


class ArchitectureTests(unittest.TestCase):
    def setUp(self):
        self.state = fixture("architecture-state.json")
        self.blocked = fixture("factor-required-result.json")

    def test_schema_definitions(self):
        self.assertEqual(len(SCHEMAS), 6)
        for schema in SCHEMAS.values():
            Draft202012Validator.check_schema(schema)

    def test_fictional_state(self):
        validate_state(self.state)

    def test_input_envelope(self):
        value = {"contract_version": "0.1.0", "skill": "normalize-sustainability-data",
                 "state": self.state, "parameters": {}}
        validate_shape("input.schema.json", value)
        del value["state"]
        with self.assertRaises(ValidationError):
            validate_shape("input.schema.json", value)

    def test_factor_metadata(self):
        factor = {
            "id": "synthetic-factor", "value": 0.5, "unit": "kg CO2e/kWh",
            "source": {"locator": "fixture:factor", "publisher": "Fictional publisher",
                       "version": "fixture-1", "accessed": "2026-10-04"},
            "geography": "CA-ON", "vintage_year": 2025,
            "method": {"name": "Synthetic method", "version": "fixture-1", "source": "fixture:method"},
            "gwp_basis": "Synthetic CO2e fixture basis", "evidence_ids": ["ev-001"], "status": "synthetic",
        }
        validate_shape("emission-factor.schema.json", factor)
        for key in ("source", "geography", "vintage_year", "unit", "method", "gwp_basis", "evidence_ids"):
            with self.subTest(key=key):
                incomplete = copy.deepcopy(factor)
                del incomplete[key]
                with self.assertRaises(ValidationError):
                    validate_shape("emission-factor.schema.json", incomplete)
        self.state["emission_factors"].append(factor)
        validate_state(self.state)
        factor["evidence_ids"] = ["missing"]
        with self.assertRaisesRegex(ValueError, "Unresolved evidence"):
            validate_state(self.state)

    def test_factor_required_result(self):
        validate_shape("result.schema.json", self.blocked)
        self.state["results"].append(self.blocked)
        self.state["data_gaps"].extend(self.blocked["data_gaps"])
        validate_state(self.state)

    def test_result_gaps_and_assumptions_retained(self):
        self.state["results"].append(self.blocked)
        with self.assertRaisesRegex(ValueError, "Dropped data gap"):
            validate_state(self.state)
        self.state["data_gaps"].extend(self.blocked["data_gaps"])
        self.blocked["assumptions"] = ["Fictional assumption"]
        with self.assertRaisesRegex(ValueError, "Dropped assumption"):
            validate_state(self.state)
        self.state["assumptions"].extend(self.blocked["assumptions"])
        validate_state(self.state)

    def test_missing_provenance(self):
        for key in ("source", "method", "period", "unit", "quality", "assumption", "uncertainty", "calculation"):
            with self.subTest(key=key):
                evidence = copy.deepcopy(self.state["evidence"][0])
                del evidence[key]
                with self.assertRaises(ValidationError):
                    validate_shape("evidence.schema.json", evidence)

    def test_proxy_requires_assumption(self):
        evidence = self.state["evidence"][0]
        evidence["source"]["tier"] = 5
        with self.assertRaises(ValidationError):
            validate_shape("evidence.schema.json", evidence)
        evidence["assumption"] = "Synthetic proxy for architecture testing."
        validate_shape("evidence.schema.json", evidence)

    def test_factor_diagnostic_cannot_be_completed(self):
        self.blocked["status"] = "completed"
        with self.assertRaises(ValidationError):
            validate_shape("result.schema.json", self.blocked)

    def test_factor_diagnostic_requires_gap_and_state(self):
        for key in ("data_gaps", "review_states"):
            with self.subTest(key=key):
                result = copy.deepcopy(self.blocked)
                result[key] = [] if key == "data_gaps" else ["ANALYTICAL"]
                with self.assertRaises(ValidationError):
                    validate_shape("result.schema.json", result)

    def test_blocked_cannot_include_calculation(self):
        self.blocked["metrics"] = self.state["results"][0]["metrics"]
        with self.assertRaises(ValidationError):
            validate_shape("result.schema.json", self.blocked)

    def test_invalid_dates_and_extra_fields(self):
        for mutate in (
            lambda state: state["reporting_period"].update(start="2025-02-30"),
            lambda state: state.update(unapproved_field=True),
        ):
            state = copy.deepcopy(self.state)
            mutate(state)
            with self.assertRaises(ValidationError):
                validate_state(state)

    def test_reversed_period(self):
        self.state["reporting_period"]["start"] = "2026-01-01"
        with self.assertRaisesRegex(ValueError, "Reversed period"):
            validate_state(self.state)

    def test_duplicate_and_dangling_references(self):
        cases = [
            (lambda state: state["evidence"].append(copy.deepcopy(state["evidence"][0])), "Duplicate evidence"),
            (lambda state: state["results"][0]["evidence_ids"].append("missing"), "Unresolved evidence"),
            (lambda state: state["energy"].append("missing"), "Unresolved domain"),
            (lambda state: state["ghg"]["scope_1"].append("missing"), "Unresolved GHG"),
            (lambda state: state["organizational_boundary"]["facility_ids"].append("missing"), "Unknown boundary"),
            (lambda state: state["results"][0]["metrics"][0].update(boundary_id="missing"), "Unknown metric boundary"),
            (lambda state: state["results"][0]["metrics"][0]["calculation"]["inputs"].append("missing"), "Unresolved calculation"),
            (lambda state: state["results"][0].update(evidence_ids=[]), "Metric lineage"),
        ]
        for mutate, message in cases:
            with self.subTest(message=message):
                state = copy.deepcopy(self.state)
                mutate(state)
                with self.assertRaisesRegex(ValueError, message):
                    validate_state(state)

    def test_unknown_is_distinct_from_zero(self):
        metric = self.state["results"][0]["metrics"][0]
        for value in (None, 0):
            metric["value"] = value
            validate_state(self.state)
        metric["value"] = "unknown"
        with self.assertRaises(ValidationError):
            validate_state(self.state)

    def test_quantified_uncertainty_requires_value_and_unit(self):
        uncertainty = self.state["evidence"][0]["uncertainty"]
        uncertainty["kind"] = "quantified"
        with self.assertRaises(ValidationError):
            validate_state(self.state)
        uncertainty.update(value=2, unit="percent")
        validate_state(self.state)

    def test_review_resolution_scope(self):
        self.state["review_requirements"] = [{
            "id": "review-1", "state": "LEGAL_REVIEW_REQUIRED", "reason": "Fictional review",
            "scope": "res-001", "reviewer_role": "legal reviewer", "status": "resolved",
            "resolution": {"reviewer": "Fictional reviewer", "role": "legal reviewer",
                           "decision": "Reviewed", "scope": "different-result",
                           "date": "2026-10-04", "evidence_ids": ["ev-001"]},
        }]
        with self.assertRaisesRegex(ValueError, "scope mismatch"):
            validate_state(self.state)

    def test_multiple_review_requirements_and_resolution(self):
        requirements = []
        for index, review_state in enumerate(("LEGAL_REVIEW_REQUIRED", "ENGINEERING_REVIEW_REQUIRED")):
            requirements.append({
                "id": f"review-{index}", "state": review_state,
                "reason": "Fictional restricted decision", "scope": "res-001",
                "reviewer_role": "qualified professional", "status": "open", "resolution": None,
            })
        result = self.state["results"][0]
        result["review_states"].extend(item["state"] for item in requirements)
        result["review_requirements"] = requirements
        self.state["review_requirements"] = copy.deepcopy(requirements)
        validate_state(self.state)
        saved = copy.deepcopy(self.state)
        self.state["review_requirements"].pop()
        with self.assertRaisesRegex(ValueError, "Dropped review"):
            validate_state(self.state)
        self.state = saved
        self.state["review_requirements"][0]["status"] = "resolved"
        with self.assertRaises(ValidationError):
            validate_state(self.state)
        self.state["review_requirements"][0]["resolution"] = {
            "reviewer": "Fictional reviewer", "role": "qualified professional",
            "decision": "Accepted fixture scope", "scope": "res-001",
            "date": "2026-10-04", "evidence_ids": ["ev-001"],
        }
        validate_state(self.state)

    def test_required_state_without_obligation_rejected(self):
        self.state["results"][0]["review_states"].append("LEGAL_REVIEW_REQUIRED")
        with self.assertRaisesRegex(ValueError, "no requirement"):
            validate_state(self.state)

    def test_taxonomy_covers_roadmap_names_once(self):
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
        taxonomy = (ROOT / "docs/taxonomy.md").read_text(encoding="utf-8")
        parts = re.split(r"^## (\d+)\. ", roadmap, flags=re.M)
        expected = []
        for index in range(1, len(parts), 2):
            if int(parts[index]) not in range(7, 14):
                continue
            for block in re.findall(r"```text\n(.*?)```", parts[index + 1], re.S):
                expected.extend(line.strip() for line in block.splitlines()
                                if re.fullmatch(r"[a-z]+(?:-[a-z0-9]+)+", line.strip()))
        actual = re.findall(r"^- `([a-z]+(?:-[a-z0-9]+)+)`$", taxonomy, re.M)
        self.assertEqual(set(actual), set(expected))
        self.assertEqual(len(actual), len(set(actual)))
        self.assertEqual(len(re.findall(r"^## SUS-\d+: ", taxonomy, re.M)), 16)


if __name__ == "__main__":
    unittest.main()
