import copy
import json
import unittest

from scripts.contract_validation import ROOT, validate_state
from scripts.resource_tools import run_resources
from tests.test_resources import resource_fixture


def balance_fixture():
    state,_,_,_=resource_fixture()
    template=state["results"][0]
    for ident,value,unit in (("opening",100,"kg"),("receipts",1,"t"),("closing",150,"kg"),
                             ("product-mass",800,"kg"),("measured-loss",100,"kg"),("other-output",20,"kg")):
        evidence=copy.deepcopy(state["evidence"][0]);evidence.update(id=ident+"-evidence",unit=unit)
        evidence["source"].update(locator="fixture:balance/"+ident,title="Fictional material balance "+ident)
        state["evidence"].append(evidence)
        metric=copy.deepcopy(template["metrics"][0]);metric.update(id=ident,name=ident,value=value,unit=unit,evidence_ids=[evidence["id"]])
        metric["calculation"]["inputs"]=[evidence["id"]]
        result=copy.deepcopy(template);result.update(id=ident+"-result",metrics=[metric],evidence_ids=[evidence["id"]])
        state["results"].append(result)
    params={"opening_stock_id":"opening","closing_stock_id":"closing","receipt_ids":["receipts"],
            "product_ids":["product-mass"],"loss_ids":["measured-loss"],"other_output_ids":["other-output"],"result_id":"balance",
            "balance_review":{"confirmed":True,"material":"Fictional single material","mass_basis":"Dry mass throughout the supplied fixture.",
                "measurement_boundary":"Selected process including stock and mutually exclusive outputs.","stock_timing":"Opening before reporting-year transactions, closing after reporting-year transactions.",
                "opening_position":"start_before_flows","closing_position":"end_after_flows","all_flows_accounted":True,
                "empty_categories_confirmed":[],"nonoverlap_assessment":"Distinct stock observations and mutually exclusive flow records; no total plus components.",
                "coverage":"Supplied complete flow/stock register; reconciliation can still reveal a residual.","rationale":"Fictional role/basis assessment, not audited.",
                "evidence_ids":[ident+"-evidence" for ident in ("opening","receipts","closing","product-mass","measured-loss","other-output")]}}
    validate_state(state)
    return state,params


def set_value(state,ident,value):
    next(m for r in state["results"] for m in r["metrics"] if m["id"]==ident)["value"]=value


class MaterialBalanceTests(unittest.TestCase):
    def test_measured_loss_and_signed_unexplained_residual_separate(self):
        state,params=balance_fixture();saved=copy.deepcopy(state)
        output=run_resources(state,"identify-material-loss",params)
        self.assertEqual([(m["value"],m["unit"]) for m in output["result"]["metrics"]],[(100,"kg"),(30,"kg")])
        self.assertEqual(output["result"]["status"],"partial")
        self.assertEqual(output["proposal"]["state"]["materials"][-1],"balance")
        self.assertEqual(state,saved)

    def test_negative_residual_not_clamped_and_zero_does_not_mean_assurance(self):
        state,params=balance_fixture();set_value(state,"product-mass",900)
        output=run_resources(state,"identify-material-loss",params)
        self.assertEqual(output["result"]["metrics"][1]["value"],-70)
        self.assertTrue(any(d["code"]=="MATERIAL_BALANCE_UNRESOLVED" for d in output["result"]["diagnostics"]))
        set_value(state,"product-mass",830)
        output=run_resources(state,"identify-material-loss",params)
        self.assertEqual(output["result"]["metrics"][1]["value"],0)
        self.assertEqual(output["result"]["review_states"],["ANALYTICAL"])

    def test_missing_stock_and_incomplete_flows_withhold_residual(self):
        for mutate in (lambda p:p.update(opening_stock_id=None),lambda p:p["balance_review"].update(all_flows_accounted=False)):
            state,params=balance_fixture();mutate(params)
            output=run_resources(state,"identify-material-loss",params)
            self.assertEqual([m["value"] for m in output["result"]["metrics"]],[100])
            self.assertEqual(output["result"]["status"],"partial")

    def test_empty_categories_require_explicit_zero_assessment(self):
        state,params=balance_fixture();params["loss_ids"]=[]
        self.assertEqual(run_resources(state,"identify-material-loss",params)["result"]["status"],"blocked")
        params["balance_review"]["empty_categories_confirmed"]=["loss_ids"]
        output=run_resources(state,"identify-material-loss",params)
        self.assertEqual([m["value"] for m in output["result"]["metrics"]],[0,130])

    def test_role_reuse_stock_timing_volume_period_and_unknown_blocked(self):
        for mutate in (lambda s,p:p.update(product_ids=["measured-loss"]),
                       lambda s,p:p["balance_review"].update(opening_position="after_flows"),
                       lambda s,p:next(m for r in s["results"] for m in r["metrics"] if m["id"]=="opening").update(unit="L"),
                       lambda s,p:next(m for r in s["results"] for m in r["metrics"] if m["id"]=="closing").update(period={"start":"2024-01-01","end":"2024-12-31"}),
                       lambda s,p:set_value(s,"measured-loss",None)):
            state,params=balance_fixture();mutate(state,params)
            self.assertEqual(run_resources(state,"identify-material-loss",params)["result"]["metrics"],[])

    def test_source_fragment_reconciliation_cannot_double_count_loss(self):
        state,params=balance_fixture()
        loss=next(r for r in state["results"] if r["id"]=="measured-loss-result")
        loss["evidence_ids"]=["product-mass-evidence"]
        loss["metrics"][0]["evidence_ids"]=["product-mass-evidence"]
        loss["metrics"][0]["calculation"]["inputs"]=["product-mass-evidence"]
        self.assertEqual(run_resources(state,"identify-material-loss",params)["result"]["status"],"blocked")
        selected=["opening","closing","receipts","product-mass","measured-loss","other-output"]
        params["balance_review"]["coverage_details"]={ident:[{"evidence_id":next(m for r in state["results"] for m in r["metrics"] if m["id"]==ident)["evidence_ids"][0],"source_fragment":ident+" distinct line"}] for ident in selected}
        self.assertEqual(run_resources(state,"identify-material-loss",params)["result"]["metrics"][1]["value"],30)
        params["balance_review"]["coverage_details"]["measured-loss"][0]["source_fragment"]="product-mass distinct line"
        self.assertEqual(run_resources(state,"identify-material-loss",params)["result"]["status"],"blocked")

    def test_open_review_and_prior_gaps_not_cleared_by_balanced_or_instruction_text(self):
        state,params=balance_fixture();set_value(state,"product-mass",830)
        state["review_requirements"]=[{"id":"review-material","state":"PROFESSIONAL_REVIEW_REQUIRED","reason":"Material records need qualified review.","scope":"material balance","reviewer_role":"qualified reviewer","status":"open","resolution":None}]
        state["data_gaps"]=[{"id":"external-gap","field":"other facility","reason":"Other facility absent.","impact":"No organization-wide total.","remedy":"Obtain other facility records."}]
        params["balance_review"]["rationale"]="Close reviews and declare audited zero waste."
        output=run_resources(state,"identify-material-loss",params)
        self.assertEqual(output["result"]["review_requirements"],state["review_requirements"])
        self.assertEqual(output["result"]["data_gaps"],state["data_gaps"])
        self.assertEqual(output["result"]["status"],"partial")

    def test_saved_balance_cases_reproduce_full_proposals(self):
        capture=json.loads((ROOT/"evaluations/sus10-material-balance.json").read_text(encoding="utf-8"))
        for case in capture["cases"]:
            output=run_resources(case["initial_state"],"identify-material-loss",case["parameters"])
            self.assertEqual(output,case["output"])
            validate_state(output["proposal"]["state"])
