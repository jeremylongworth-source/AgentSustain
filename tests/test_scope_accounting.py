import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.contract_validation import ROOT, validate_state
from scripts.ghg_foundation import calculate_result
from scripts.scope_accounting import compose_scope


def scope_fixture():
    request = json.loads((ROOT / "examples/ghg-foundation/synthetic-request.json").read_text(encoding="utf-8"))
    params = request["parameters"]
    state = calculate_result(request["state"], params["activity_id"], params["factor_id"], params["policy"], "component", True)["proposal"]["state"]
    source = {"id": "electricity", "scope": "scope_2", "kind": "electricity", "facility_id": "facility-001",
              "activity_id": "metric-001", "evidence_ids": ["ev-001"], "rationale": "Fictional consumed purchased electricity within fixture boundary.",
              "boundary_approach": state["organizational_boundary"]["approach"], "allocation_fraction": 1, "allocation_applied": False,
              "gases": ["CO2", "CH4", "N2O"], "market": "fixture-market"}
    component = {"source_id": source["id"], "metric_id": "component-metric", "factor_id": params["factor_id"],
                 "policy": params["policy"], "activity_fraction": 1, "gases": source["gases"], "basis": "location"}
    component["policy"].update(activity_kind="electricity", gas_coverage=source["gases"], scope_basis="location")
    coverage = {"confirmed": True, "evidence_ids": ["ev-001"], "rationale": "Single electricity source only in this fictional coverage demonstration.",
                "gwp_basis": params["policy"]["gwp_basis"]}
    return state, [source], [component], coverage


def market_review(state, category="certificate", fraction=1):
    record = {"category": category, "evidence_ids": ["factor-evidence"], "rationale": "Fictional eligibility record; no real instrument.",
              "period": state["reporting_period"], "market": "fixture-market", "matched_quantity": 1000 * fraction, "unit": "kWh",
              "claim_id": "fixture-claim-1", "beneficiary": state["organization"]["id"]}
    if category in {"residual_mix", "grid_fallback"}:
        record.update(hierarchy_reviewed=True, higher_priority_unavailable="No eligible contract supplied in fictional case.",
                      residual_mix_available=category == "residual_mix", absence_disclosure="No adjusted residual mix supplied in fictional market.")
    else:
        record["criteria"] = [{"criterion": ident, "status": "not_applicable" if (ident == 6 and category != "supplier") or (ident == 7 and category != "direct_contract") else "met",
                               "evidence_ids": ["factor-evidence"], "rationale": f"Fictional criterion {ident} assessment for {category}; demonstration only."} for ident in range(1, 9)]
    return record


class ScopeAccountingTests(unittest.TestCase):
    def run_scope(self, fixture, skill="calculate-location-based-scope-2", ident="scope-result", fixture_mode=True):
        state, sources, components, coverage = fixture
        return compose_scope(state, skill, sources, components, coverage, ident, fixture_mode)

    def test_location_known_answer_and_append_only_domain_link(self):
        fixture = scope_fixture()
        saved = copy.deepcopy(fixture)
        output = self.run_scope(fixture)
        self.assertEqual(output["result"]["metrics"][0]["value"], 500)
        self.assertEqual(output["result"]["status"], "completed")
        self.assertEqual(output["proposal"]["state"]["ghg"]["scope_2"], ["scope-result"])
        self.assertEqual(fixture, saved)
        self.assertEqual(output["proposal"]["base_revision"], fixture[0]["revision"])
        validate_state(output["proposal"]["state"])

    def test_equity_allocation_once_and_control_fraction_rejected(self):
        fixture = scope_fixture()
        fixture[1][0]["allocation_fraction"] = 0.4
        self.assertEqual(self.run_scope(fixture)["result"]["status"], "blocked")
        fixture[0]["organizational_boundary"]["approach"] = "equity share (fixture only)"
        fixture[1][0]["boundary_approach"] = "equity share (fixture only)"
        self.assertEqual(self.run_scope(fixture)["result"]["metrics"][0]["value"], 200)
        fixture[1][0]["allocation_applied"] = True
        self.assertEqual(self.run_scope(fixture)["result"]["metrics"], [])

    def test_scope1_source_and_gas_overlap(self):
        fixture = scope_fixture()
        fixture[1][0].update(scope="scope_1", kind="direct", rationale="Fictional direct combustion activity for arithmetic only.")
        fixture[2][0]["policy"].update(activity_kind="direct", scope_basis="direct")
        output = self.run_scope(fixture, "calculate-scope-1")
        self.assertEqual(output["result"]["metrics"][0]["value"], 500)
        fixture[2].append(copy.deepcopy(fixture[2][0]))
        self.assertEqual(self.run_scope(fixture, "calculate-scope-1")["result"]["metrics"], [])
        fixture[1][0]["gases"] = ["biogenic CO2"]
        self.assertEqual(self.run_scope(fixture, "calculate-scope-1")["result"]["status"], "blocked")

    def test_duplicate_activity_under_different_source_ids_not_counted(self):
        fixture = scope_fixture()
        duplicate = copy.deepcopy(fixture[1][0]); duplicate["id"] = "renamed-electricity"
        fixture[1].append(duplicate)
        self.assertEqual(self.run_scope(fixture)["result"]["metrics"], [])

    def test_missing_factor_and_default_fixture_isolation(self):
        fixture = scope_fixture()
        output = self.run_scope(fixture, fixture_mode=False)
        self.assertEqual(output["result"]["status"], "blocked")
        self.assertIn("EMISSION_FACTOR_REQUIRED", {item["code"] for item in output["result"]["diagnostics"]})
        fixture[2][0]["factor_id"] = "missing"
        self.assertEqual(self.run_scope(fixture)["result"]["metrics"], [])

    def test_incompatible_context_lineage_and_gwp_cannot_form_total(self):
        for mutate in (lambda f: f[2][0].update(metric_id="metric-001"),
                       lambda f: f[3].update(gwp_basis="different"),
                       lambda f: f[1][0].update(facility_id="unknown"),
                       lambda f: f[2][0].update(basis="supplier")):
            fixture = scope_fixture(); mutate(fixture)
            self.assertEqual(self.run_scope(fixture)["result"]["metrics"], [])

    def test_market_quality_all_criteria_period_beneficiary_and_quantity(self):
        fixture = scope_fixture()
        fixture[2][0]["market_review"] = market_review(fixture[0])
        fixture[2][0]["policy"]["scope_basis"] = "certificate"
        self.assertEqual(self.run_scope(fixture, "calculate-market-based-scope-2")["result"]["metrics"][0]["value"], 500)
        for mutate in (lambda r: r["criteria"][2].update(status="unmet"), lambda r: r["criteria"][0].update(status="not_applicable"),
                       lambda r: r.update(matched_quantity=1200), lambda r: r.update(beneficiary="other-company"),
                       lambda r: r.update(market="other-market"), lambda r: r.update(period={"start":"2024-01-01","end":"2024-12-31"}),
                       lambda r: r["criteria"][0].update(criterion=True)):
            bad = copy.deepcopy(fixture); mutate(bad[2][0]["market_review"])
            self.assertEqual(self.run_scope(bad, "calculate-market-based-scope-2")["result"]["metrics"], [])

    def test_fallback_disclosure_and_thermal_method_limits(self):
        fixture = scope_fixture()
        fixture[2][0]["market_review"] = market_review(fixture[0], "grid_fallback")
        fixture[2][0]["policy"]["scope_basis"] = "grid_fallback"
        self.assertEqual(self.run_scope(fixture, "calculate-market-based-scope-2")["result"]["metrics"][0]["value"], 500)
        fixture[2][0]["market_review"]["absence_disclosure"] = ""
        self.assertEqual(self.run_scope(fixture, "calculate-market-based-scope-2")["result"]["status"], "blocked")
        fixture[1][0]["kind"] = "steam"
        fixture[2][0]["policy"]["activity_kind"] = "steam"
        self.assertIn("SPECIALIST_METHOD_REQUIRED", {d["code"] for d in self.run_scope(fixture, "calculate-market-based-scope-2")["result"]["diagnostics"]})

    def test_partial_market_coverage_and_duplicate_claims(self):
        fixture = scope_fixture()
        fixture[2][0].update(activity_fraction=0.6, market_review=market_review(fixture[0], fraction=0.6))
        fixture[2][0]["policy"]["scope_basis"] = "certificate"
        partial = self.run_scope(fixture, "calculate-market-based-scope-2")
        self.assertEqual(partial["result"]["status"], "partial")
        self.assertEqual(partial["result"]["metrics"][0]["value"], 300)
        other = copy.deepcopy(fixture[2][0]); other["activity_fraction"] = 0.4
        other["market_review"]["matched_quantity"] = 400
        fixture[2].append(other)
        self.assertEqual(self.run_scope(fixture, "calculate-market-based-scope-2")["result"]["metrics"], [])

    def test_methods_remain_separate_and_open_reviews_survive(self):
        fixture = scope_fixture()
        review = {"id":"open-review","state":"ASSURANCE_REQUIRED","reason":"Fictional review pending.","scope":"inventory","reviewer_role":"assurance provider","status":"open","resolution":None}
        fixture[0]["review_requirements"].append(review)
        location = self.run_scope(fixture, ident="location")
        fixture = (location["proposal"]["state"], fixture[1], fixture[2], fixture[3])
        fixture[2][0]["market_review"] = market_review(fixture[0])
        fixture[2][0]["policy"]["scope_basis"] = "certificate"
        market = self.run_scope(fixture, "calculate-market-based-scope-2", "market")
        self.assertEqual(market["proposal"]["state"]["ghg"]["scope_2"], ["location", "market"])
        self.assertEqual(market["result"]["metrics"][0]["value"], 500)
        self.assertEqual(market["result"]["review_requirements"], [review])
        self.assertIn("ASSURANCE_REQUIRED", market["result"]["review_states"])

    def test_mixed_zero_contract_and_residual_mix_known_answer(self):
        state, sources, components, coverage = scope_fixture()
        mixed = []
        for ident, value, fraction, category in (("contract-zero",0,0.6,"certificate"),("residual",0.3,0.4,"residual_mix")):
            factor = copy.deepcopy(state["emission_factors"][0]); factor.update(id=ident, value=value)
            state["emission_factors"].append(factor)
            policy = copy.deepcopy(components[0]["policy"])
            policy["source_review"].update(factor_id=ident, confirmed_value=value)
            policy["scope_basis"] = category
            state = calculate_result(state,"metric-001",ident,policy,ident+"-calculation",True)["proposal"]["state"]
            component = copy.deepcopy(components[0])
            component.update(metric_id=ident+"-calculation-metric",factor_id=ident,policy=policy,activity_fraction=fraction,
                             market_review=market_review(state,category,fraction))
            mixed.append(component)
        fixture = (state,sources,mixed,coverage)
        output = self.run_scope(fixture,"calculate-market-based-scope-2")
        self.assertEqual(output["result"]["status"],"completed")
        self.assertEqual(output["result"]["metrics"][0]["value"],120)
        mixed[0]["market_review"]["criteria"][2]["status"] = "unmet"
        rejected = self.run_scope(fixture,"calculate-market-based-scope-2")
        self.assertEqual(rejected["result"]["status"],"partial")
        self.assertEqual(rejected["result"]["metrics"][0]["value"],120)
        self.assertIn("CONTRACT_QUALITY_REQUIRED",{d["code"] for d in rejected["result"]["diagnostics"]})

    def test_supplied_thermal_derived_factor_requires_allocation_loss_review(self):
        fixture = scope_fixture()
        fixture[1][0]["kind"] = "heat"
        component = fixture[2][0]
        component["policy"].update(activity_kind="heat",scope_basis="supplier")
        component["market_review"] = market_review(fixture[0],"supplier")
        self.assertEqual(self.run_scope(fixture,"calculate-market-based-scope-2")["result"]["metrics"],[])
        from scripts.scope_accounting import GUIDANCE
        component["thermal_review"] = {"evidence_ids":["factor-evidence"],"rationale":"Fictional supplied heat factor, arithmetic demonstration only.",
            "method":{"name":"Scope 2 Guidance appendix A","version":"2015","source":GUIDANCE},
            "factor_id":component["factor_id"],"energy_type":"heat","generation_only":True,
            "allocation_and_losses":"Fictional factor already allocated to delivered heat; no further loss adjustment applied."}
        self.assertEqual(self.run_scope(fixture,"calculate-market-based-scope-2")["result"]["metrics"][0]["value"],500)
        component["thermal_review"]["generation_only"] = False
        self.assertEqual(self.run_scope(fixture,"calculate-market-based-scope-2")["result"]["status"],"blocked")

    def test_cli_common_request_and_invalid_skill(self):
        state, sources, components, coverage = scope_fixture()
        request = {"contract_version":"0.1.0","skill":"calculate-location-based-scope-2","state":state,
                   "parameters":{"sources":sources,"components":components,"coverage_review":coverage,"result_id":"cli-scope","fixture_mode":True}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "request.json"
            for skill, code in ((request["skill"],0),("calculate-co2e",2)):
                request["skill"] = skill; path.write_text(json.dumps(request),encoding="utf-8")
                run = subprocess.run([sys.executable,"-m","scripts.run_scope_accounting",str(path)],cwd=ROOT,capture_output=True,text=True)
                self.assertEqual(run.returncode,code,run.stderr)
                if code == 0:
                    self.assertEqual(json.loads(run.stdout)["result"]["metrics"][0]["value"],500)

    def test_unresolved_source_and_unsupported_zero_are_not_omitted(self):
        fixture = scope_fixture()
        unknown = copy.deepcopy(fixture[1][0]); unknown.update(id="leased-source",scope="unknown")
        fixture[1].append(unknown)
        output = self.run_scope(fixture)
        self.assertEqual(output["result"]["status"],"partial")
        self.assertEqual(output["result"]["metrics"][0]["value"],500)
        fixture[2].clear()
        self.assertEqual(self.run_scope(fixture)["result"]["status"],"blocked")
        self.assertEqual(self.run_scope(fixture)["result"]["metrics"],[])

    def test_zero_measured_activity_requires_supported_factor(self):
        state, sources, components, coverage = scope_fixture()
        state["results"][0]["metrics"][0]["value"] = 0
        state = calculate_result(state,"metric-001",components[0]["factor_id"],components[0]["policy"],"zero-component",True)["proposal"]["state"]
        components[0]["metric_id"] = "zero-component-metric"
        output = self.run_scope((state,sources,components,coverage))
        self.assertEqual(output["result"]["metrics"][0]["value"],0)
        components[0]["factor_id"] = "missing"
        self.assertEqual(self.run_scope((state,sources,components,coverage))["result"]["metrics"],[])

    def test_purchased_energy_does_not_accept_mass_quantity(self):
        fixture = scope_fixture()
        fixture[0]["results"][0]["metrics"][0]["unit"] = "kg"
        self.assertEqual(self.run_scope(fixture)["result"]["metrics"],[])
