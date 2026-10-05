import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.contract_validation import ROOT, validate_state
from scripts.ghg_foundation import calculate_result
from scripts.ghg_inventory import build_inventory
from scripts.scope3_accounting import classify_scope3, calculate_category
from scripts.scope_classification import classify_sources
from scripts.state_proposal import propose


def category_fixture():
    request = json.loads((ROOT / "examples/ghg-foundation/synthetic-request.json").read_text(encoding="utf-8"))
    state = request["state"]
    # Fictional purchased material quantity and explicit synthetic intensity.
    state["results"][0]["metrics"][0].update(name="Purchased fixture material", value=100, unit="kg")
    state["evidence"][0]["unit"] = "kg"
    factor = state["emission_factors"][0]
    factor.update(value=2, unit="kg CO2e/kg")
    state["evidence"][1]["unit"] = factor["unit"]
    policy = request["parameters"]["policy"]
    policy["source_review"].update(confirmed_value=2, confirmed_unit=factor["unit"], coverage="Synthetic purchased material lifecycle intensity only")
    policy.update(scope3_category=1, lifecycle_boundary="Fictional cradle-to-gate intensity for this material", allocation_basis="Physical mass quantity attributable to this organization; no second allocation")
    state = calculate_result(state,"metric-001",factor["id"],policy,"material-co2e",True)["proposal"]["state"]
    source = {"id":"material","relationship":"purchase","capital_good":False,"not_other_categories":True,
              "in_value_chain":True,"emissions_in_scope_1_2":False,"activity_id":"metric-001","period":state["reporting_period"],
              "boundary_id":state["organizational_boundary"]["id"],"evidence_ids":["ev-001"],"rationale":"Fictional ordinary purchased material distinct from scope 1/2."}
    classified = classify_scope3(state,[source],"classification",True)
    source = json.loads(next(d["message"] for d in classified["result"]["diagnostics"] if d["code"]=="SCOPE3_CLASSIFICATION"))["sources"][0]
    state = classified["proposal"]["state"]
    component = {"source_id":"material","metric_id":"material-co2e-metric","factor_id":factor["id"],"policy":policy}
    review = {"category":1,"confirmed":True,"evidence_ids":["ev-001","factor-evidence"],"minimum_boundary_assessment":"Fictional aggregate cradle-to-gate coverage; not real source validation.",
              "exclusions_and_optional_coverage":"No exclusions within this single-source fictional category; other categories require screening.","gwp_basis":factor["gwp_basis"]}
    return state,[source],[component],review


class Scope3Tests(unittest.TestCase):
    def test_classification_all_categories_and_discriminators(self):
        state,sources,_,_ = category_fixture()
        facts = [({"relationship":"purchase","capital_good":False},1),({"relationship":"purchase","capital_good":True},2),
                 ({"relationship":"energy_lifecycle"},3),({"relationship":"transport","transport_purchased_by_org":True,"transport_stage":"org_to_customer"},4),
                 ({"relationship":"operational_waste"},5),({"relationship":"business_travel"},6),({"relationship":"employee_commuting"},7),
                 ({"relationship":"lease","lease_role":"lessee"},8),({"relationship":"transport","transport_purchased_by_org":False,"transport_stage":"org_to_customer"},9),
                 ({"relationship":"processing_sold_products"},10),({"relationship":"use_sold_products"},11),({"relationship":"end_of_life_sold_products"},12),
                 ({"relationship":"lease","lease_role":"lessor"},13),({"relationship":"franchise"},14),({"relationship":"investment"},15),
                 ({"relationship":"transport","transport_stage":"tier2_to_tier1","capital_good":False},1),
                 ({"relationship":"transport","transported_product":"fuel_energy"},3)]
        for changes,expected in facts:
            source = copy.deepcopy(sources[0]);source.update(changes)
            case_state = state
            if source["relationship"] == "lease":
                boundary = {"id":source["id"],"kind":"direct","relationship":"direct","facility_id":"facility-001",
                    "period":state["reporting_period"],"evidence_ids":["ev-001"],"rationale":"Fictional lease operation outside organizational control.",
                    "boundary_review":{"approach":state["organizational_boundary"]["approach"],"consolidation_method":"operational_control",
                        "operational_control":False,"period":state["reporting_period"],"evidence_ids":["ev-001"],"rationale":"Fictional evidence establishes no operational control."}}
                prior = classify_sources(state,"classify-scope-1-emissions",[boundary],"lease-exclusion",True)
                case_state = prior["proposal"]["state"]
                source["scope12_result_id"] = "lease-exclusion"
            output = classify_scope3(case_state,[source],"case",True)
            record = json.loads(next(d["message"] for d in output["result"]["diagnostics"] if d["code"] == "SCOPE3_CLASSIFICATION"))
            self.assertEqual(record["sources"][0]["category"],expected)

    def test_uncertain_scope_and_transport_do_not_default(self):
        state,sources,_,_ = category_fixture()
        for changes in ({"emissions_in_scope_1_2":None},{"relationship":"lease","lease_role":None},
                        {"relationship":"transport","transport_stage":"org_to_customer","transport_purchased_by_org":None},
                        {"capital_good":None}):
            source = copy.deepcopy(sources[0]);source.update(changes)
            output = classify_scope3(state,[source],"unknown",True)
            self.assertEqual(output["result"]["status"],"blocked")
            self.assertEqual(output["result"]["metrics"],[])

    def test_category_known_answer_and_domain_link(self):
        state,sources,components,review = category_fixture()
        saved = copy.deepcopy(state)
        output = calculate_category(state,1,sources,components,review,"category-1",True)
        self.assertEqual(output["result"]["metrics"][0]["value"],200)
        self.assertEqual(output["result"]["status"],"completed")
        self.assertEqual(output["proposal"]["state"]["ghg"]["scope_3"],["category-1"])
        self.assertEqual(state,saved)
        validate_state(output["proposal"]["state"])

    def test_category_factors_and_lifecycle_basis_are_required(self):
        state,sources,components,review = category_fixture()
        for mutate in (lambda c:c.update(factor_id="missing"),lambda c:c["policy"].update(scope3_category=2),
                       lambda c:c["policy"].update(lifecycle_boundary=""),lambda c:c["policy"].update(allocation_basis=""),
                       lambda c:c.update(metric_id="metric-001")):
            bad = copy.deepcopy(components);mutate(bad[0])
            self.assertEqual(calculate_category(state,1,sources,bad,review,"bad",True)["result"]["metrics"],[])
        ordinary = calculate_category(state,1,sources,components,review,"ordinary")
        self.assertIn("EMISSION_FACTOR_REQUIRED",{d["code"] for d in ordinary["result"]["diagnostics"]})

    def test_duplicate_material_source_and_component_overlap_blocked(self):
        state,sources,components,review = category_fixture()
        duplicate = copy.deepcopy(sources[0]);duplicate["id"]="renamed-material"
        self.assertEqual(calculate_category(state,1,sources+[duplicate],components,review,"duplicate",True)["result"]["metrics"],[])
        self.assertEqual(calculate_category(state,1,sources,components+components,review,"duplicate",True)["result"]["metrics"],[])

    def test_category_boundary_and_unknown_records_stay_partial(self):
        state,sources,components,review = category_fixture()
        review["minimum_boundary_assessment"]=""
        output = calculate_category(state,1,sources,components,review,"partial",True)
        self.assertEqual(output["result"]["metrics"][0]["value"],200)
        self.assertEqual(output["result"]["status"],"partial")
        sources[0]["period"]={"start":"2024-01-01","end":"2024-12-31"}
        self.assertEqual(calculate_category(state,1,sources,components,review,"wrong-period",True)["result"]["status"],"blocked")

    def test_inventory_selects_one_scope2_and_preserves_missing_categories(self):
        capture = json.loads((ROOT / "evaluations/sus07-composed-workflow.json").read_text())
        state = capture["final_state"]
        screening = [{"category":i,"status":"not_applicable","evidence_ids":["ev-001"],"rationale":"Fictional screening only; no actual business applicability determination."} for i in range(1,16)]
        review = {"confirmed":True,"evidence_ids":["ev-001"],"rationale":"Fictional source nonoverlap assessment only.","gwp_basis":state["emission_factors"][0]["gwp_basis"]}
        output = build_inventory(state,"workflow-scope1","workflow-scope2-location",[],screening,review,"inventory",True)
        self.assertEqual(output["result"]["metrics"][0]["value"],525)
        self.assertEqual(output["result"]["status"],"partial")
        self.assertEqual(output["result"]["review_requirements"],state["review_requirements"])
        screening[0]["status"]="applicable"
        output = build_inventory(state,"workflow-scope1","workflow-scope2-market",[],screening,review,"missing-category",True)
        self.assertIn("CATEGORY_RESULT_REQUIRED",{d["code"] for d in output["result"]["diagnostics"]})
        self.assertEqual(output["result"]["metrics"][0]["value"],525)
        self.assertEqual(build_inventory(state,None,None,[],[],review,"empty",True)["result"]["metrics"],[])
        ordinary = build_inventory(state,"workflow-scope1","workflow-scope2-location",[],screening,review,"ordinary")
        self.assertEqual(ordinary["result"]["metrics"],[])

    def test_cli_classification_and_invalid_skill(self):
        state,sources,_,_ = category_fixture()
        request = {"contract_version":"0.1.0","skill":"classify-scope-3-emissions","state":state,"parameters":{"sources":sources,"result_id":"cli","fixture_mode":True}}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"request.json"
            for skill,code in (("classify-scope-3-emissions",0),("calculate-co2e",2)):
                request["skill"]=skill;path.write_text(json.dumps(request),encoding="utf-8")
                run=subprocess.run([sys.executable,"-m","scripts.run_scope3",str(path)],cwd=ROOT,capture_output=True,text=True)
                self.assertEqual(run.returncode,code,run.stderr)

    def test_unknown_lease_cannot_be_reclassified_by_scope3_flag(self):
        state,sources,_,_ = category_fixture()
        source = copy.deepcopy(sources[0]);source.update(relationship="lease",lease_role="lessee",emissions_in_scope_1_2=False)
        output = classify_scope3(state,[source],"lease",True)
        self.assertEqual(output["result"]["status"],"blocked")
        self.assertIn("LEASE_BOUNDARY_REQUIRED",{d["code"] for d in output["result"]["diagnostics"]})

    def test_inventory_rechecks_subtotal_instead_of_trusting_label(self):
        state = json.loads((ROOT / "evaluations/sus07-composed-workflow.json").read_text())["final_state"]
        screening = [{"category":i,"status":"not_applicable","evidence_ids":["ev-001"],"rationale":"Fictional screening only."} for i in range(1,16)]
        review = {"confirmed":True,"evidence_ids":["ev-001"],"rationale":"Fictional reconciliation.","gwp_basis":state["emission_factors"][0]["gwp_basis"]}
        next(r for r in state["results"] if r["id"]=="workflow-scope1")["metrics"][0]["value"]=1
        output = build_inventory(state,"workflow-scope1","workflow-scope2-location",[],screening,review,"tampered",True)
        self.assertEqual(output["result"]["metrics"][0]["value"],500)
        self.assertEqual(output["result"]["status"],"partial")
        self.assertIn("INVENTORY_RECONCILIATION_REQUIRED",{d["code"] for d in output["result"]["diagnostics"]})

    def test_alternative_category_totals_are_not_both_counted(self):
        state,sources,components,review = category_fixture()
        state = calculate_category(state,1,sources,components,review,"category-first",True)["proposal"]["state"]
        state = calculate_category(state,1,sources,components,review,"category-alternative",True)["proposal"]["state"]
        screening = [{"category":i,"status":"applicable" if i==1 else "not_applicable","evidence_ids":["ev-001"],"rationale":"Fictional category screening."} for i in range(1,16)]
        coverage = {"confirmed":True,"evidence_ids":["ev-001"],"rationale":"Fictional nonoverlap review.","gwp_basis":review["gwp_basis"]}
        output = build_inventory(state,None,None,["category-first","category-alternative"],screening,coverage,"duplicate-inventory",True)
        self.assertEqual(output["result"]["metrics"],[])
        self.assertEqual(output["result"]["status"],"blocked")

    def test_inventory_factor_revalidation_failure_is_visible(self):
        state = json.loads((ROOT / "evaluations/sus07-composed-workflow.json").read_text())["final_state"]
        next(f for f in state["emission_factors"] if f["id"]=="gas-co2-factor")["status"]="candidate"
        screening = [{"category":i,"status":"not_applicable","evidence_ids":["ev-001"],"rationale":"Fictional category screening."} for i in range(1,16)]
        review = {"confirmed":True,"evidence_ids":["ev-001"],"rationale":"Fictional reconciliation.","gwp_basis":state["emission_factors"][0]["gwp_basis"]}
        output = build_inventory(state,"workflow-scope1","workflow-scope2-location",[],screening,review,"invalid-factor-inventory",True)
        self.assertEqual(output["result"]["status"],"partial")
        self.assertEqual(output["result"]["metrics"][0]["value"],500)
        self.assertIn("EMISSION_FACTOR_REQUIRED",{d["code"] for d in output["result"]["diagnostics"]})

    def test_rejected_zero_component_still_invalidates_category_completeness(self):
        state,sources,components,review = category_fixture()
        raw = copy.deepcopy(state["results"][0]);raw["id"]="zero-activity-normalization"
        raw["assumptions"] = list(state["assumptions"])
        raw["metrics"][0].update(id="zero-activity",value=1)
        state = propose(state,raw,"Add fictional distinct material activity for zero-factor regression")["state"]
        factor = copy.deepcopy(state["emission_factors"][0]);factor.update(id="zero-factor",value=0)
        state["emission_factors"].append(factor)
        policy = copy.deepcopy(components[0]["policy"])
        policy["source_review"].update(factor_id="zero-factor",activity_id="zero-activity",confirmed_value=0)
        state = calculate_result(state,"zero-activity","zero-factor",policy,"zero-co2e",True)["proposal"]["state"]
        source = copy.deepcopy(sources[0]);source.update(id="second-material",activity_id="zero-activity")
        sources.append(source)
        components.append({"source_id":"second-material","metric_id":"zero-co2e-metric","factor_id":"zero-factor","policy":policy})
        category = calculate_category(state,1,sources,components,review,"complete-category",True)
        self.assertEqual(category["result"]["status"],"completed")
        state = category["proposal"]["state"]
        next(f for f in state["emission_factors"] if f["id"]=="zero-factor")["status"]="candidate"
        screening = [{"category":i,"status":"applicable" if i==1 else "not_applicable","evidence_ids":["ev-001"],"rationale":"Fictional screening."} for i in range(1,16)]
        coverage = {"confirmed":True,"evidence_ids":["ev-001"],"rationale":"Fictional independent physical coverage.","gwp_basis":review["gwp_basis"]}
        inventory = build_inventory(state,None,None,["complete-category"],screening,coverage,"zero-revalidation",True)
        self.assertEqual(inventory["result"]["metrics"][0]["value"],200)
        self.assertIn("EMISSION_FACTOR_REQUIRED",{d["code"] for d in inventory["result"]["diagnostics"]})
