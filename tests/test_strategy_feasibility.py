import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.contract_validation import ROOT, validate_state
from scripts.strategy_tools import run_strategy
from tests.test_strategy import chain, record


def feasibility_fixture(kind="intensity"):
    state, target, _ = chain(kind)
    state = run_strategy(state, "develop-target", target)["proposal"]["state"]
    template = copy.deepcopy(state["results"][0]["metrics"][0])
    def source(ident, value, unit, projected=False):
        evidence = copy.deepcopy(state["evidence"][0]); evidence["id"] = ident + "-evidence"; evidence["unit"] = unit
        evidence["source"].update(locator="fixture:" + ident, title="Fictional " + ident + " source", tier=5 if projected else 1)
        evidence["method"].update(name="Fictional modeled joint outcome" if projected else "Fictional quote/budget record", source="fixture:" + ident)
        if projected:
            evidence["period"] = copy.deepcopy(target["target"]["period"])
            evidence["assumption"] = "Supplied fictional joint future model; no realized outcome."
        state["evidence"].append(evidence)
        metric = copy.deepcopy(template); metric.update(id=ident, name="Fictional " + ident, value=value, unit=unit, evidence_ids=[evidence["id"]],
            period=evidence["period"], method=evidence["method"], assumption="Supplied fictional joint future model; no realized outcome." if projected else None)
        metric["calculation"]["inputs"] = [evidence["id"]]
        state["results"][0]["metrics"].append(metric); state["results"][0]["evidence_ids"].append(evidence["id"])
        if metric["assumption"]:
            for assumptions in (state["results"][0]["assumptions"], state["assumptions"]):
                if metric["assumption"] not in assumptions:
                    assumptions.append(metric["assumption"])
        return metric
    gross = source("joint-outcome", 1500 if kind == "intensity" else 750, "kWh", True)
    low = source("joint-low", 1400 if kind == "intensity" else 700, "kWh", True)
    high = source("joint-high", 1700 if kind == "intensity" else 850, "kWh", True)
    activity = source("future-service", 200, "count", True)
    cost = source("joint-cost", 400, "CAD"); budget = source("available-budget", 300, "CAD")
    scope = target["target_review"]["scope"]
    accounting = next(r for r in state["results"] if r["skill"] == "establish-baseline")
    accounting = record({"result": accounting}, "STRATEGY_BASELINE")["baseline_review"]["accounting_basis"]
    fit = lambda m: {"confirmed": True, "evidence_ids": m["evidence_ids"], "scope": scope, "accounting_basis": accounting,
        "rationale": "Fictional joint source inspected for this selected scope and gross basis."}
    review = {"confirmed": True, "reviewer_role": "Fictional strategy analyst", "rationale": "Fictional model and delivery source screening, not independent approval.",
        "boundary_id": state["organizational_boundary"]["id"], "evidence_ids": [gross["evidence_ids"][0]], "scope": scope, "accounting_basis": accounting}
    selected = [gross, low, high] + ([activity] if kind == "intensity" else [])
    basis = dict(review, model_assumption="Fictional same-product 2030 annual joint model; savings interactions already modeled.",
        service_definition="Equivalent accepted widgets and same purchased-electricity meter", interaction_assessment="One joint scenario outcome, no sum of isolated savings.",
        uncertainty_basis="Supplied low/central/high modeled outcomes; no probabilities.", aggregation_basis="joint_modelled_outcome", timing_basis="full_period_from_start",
        metric_contexts={m["id"]: fit(m) for m in selected})
    state["projects"] = [{"id": "meter-upgrade", "evidence_ids": gross["evidence_ids"], "attributes": {"name": "Fictional selected upgrade"}}]
    investment = {"cost_metric_id": cost["id"], "budget_metric_id": budget["id"], "review": dict(review, currency="CAD", valuation_date="2025-09-01",
        dollar_basis="nominal", tax_basis="pre_tax", cost_scope="Fictional joint installed cost; no lifecycle total", funding_basis="Supplied fictional capital envelope, funding unapproved.",
        project_ids=["meter-upgrade"], metric_contexts={m["id"]: fit(m) for m in (cost, budget)})}
    scenario = {"id": "joint-upgrade", "outcome_metric_id": gross["id"], "range_metric_ids": [low["id"], high["id"]],
        "activity_metric_id": activity["id"] if kind == "intensity" else None, "scenario_review": basis,
        "initiatives": [{"id": "install-upgrade", "project_id": "meter-upgrade", "owner": "Fictional operations lead", "commission_date": "2029-12-01", "depends_on": [],
            "evidence_ids": gross["evidence_ids"], "description": "Modeled upgrade requires qualified engineering and owner funding review."}],
        "constraints": [{"id": domain + "-condition", "domain": domain, "status": "unresolved" if domain == "organizational" else "supported",
            "owner": "Fictional " + domain + " reviewer", "description": "Fictional " + domain + " modeled assumption remains subject to owner/specialist review.",
            "evidence_ids": [] if domain == "organizational" else gross["evidence_ids"]} for domain in ("technical", "financial", "organizational", "service", "evidence")], "investment": investment}
    params = {"target_result_id": target["result_id"], "scenarios": [scenario], "feasibility_review": dict(review,
        decision_basis="Conditional objective coverage versus delivery constraints; no scenario selection.", uncertainty_basis="Joint supplied scenario range; no probability or engineering validation.",
        review_date="2026-10-05", coverage_complete=False), "result_id": "target-feasibility"}
    validate_state(state)
    return state, params


def metric(state, ident):
    return next(m for r in state["results"] for m in r["metrics"] if m["id"] == ident)


class FeasibilityTests(unittest.TestCase):
    def test_intensity_growth_range_budget_and_gates_remain_distinct(self):
        state, params = feasibility_fixture(); original = copy.deepcopy(state)
        out = run_strategy(state, "evaluate-target-feasibility", params); r = record(out, "TARGET_FEASIBILITY"); row = r["scenarios"][0]
        values = {m["id"]: m["value"] for m in out["result"]["metrics"]}
        self.assertEqual(values[row["point_metric_id"]], 7.5); self.assertEqual(values[row["endpoint_gap_metric_id"]], -.5)
        self.assertEqual(values[row["allowed_gross_metric_id"]], 1600); self.assertEqual(values[row["absolute_change_metric_id"]], 500)
        self.assertEqual(values[row["budget_gap_metric_id"]], -100)
        self.assertTrue(row["point_meets_proposed_objective"]); self.assertEqual(row["range_screen"], "range_straddles_objective")
        self.assertEqual(row["indicator_range"]["low"], 7); self.assertEqual(row["indicator_range"]["high"], 8.5)
        self.assertEqual(row["delivery_screen"], "known_conditions_not_met")
        for flag in ("target_adopted", "public_claim_authorized", "implementation_authorized", "funding_authorized"):
            self.assertFalse(r[flag])
        self.assertIsNone(r["feasibility"]); self.assertIsNone(r["portfolio_total"]); self.assertIsNone(r["selected_scenario_id"])
        self.assertEqual(state, original); self.assertEqual(out["proposal"]["state"]["ghg"], state["ghg"])
        self.assertEqual(out["proposal"]["state"]["projects"], state["projects"])
        for item in state["review_requirements"]:
            self.assertIn(item, out["result"]["review_requirements"])
        for item in state["data_gaps"]:
            self.assertIn(item, out["result"]["data_gaps"])
        validate_state(out["proposal"]["state"])

    def test_absolute_scenarios_do_not_use_service_or_sum_alternatives(self):
        state, params = feasibility_fixture("absolute")
        second = copy.deepcopy(params["scenarios"][0]); second["id"] = "alternative"
        params["scenarios"].append(second)
        r = record(run_strategy(state, "evaluate-target-feasibility", params), "TARGET_FEASIBILITY")
        self.assertEqual(len(r["scenarios"]), 2); self.assertIsNone(r["portfolio_total"])
        self.assertEqual(r["scenarios"][0]["range_screen"], "range_straddles_objective")

    def test_range_all_none_and_signed_gap(self):
        for point, low, high, expected in ((1500, 1400, 1600, "all_supplied_levels_meet"), (1800, 1700, 1900, "none_supplied_levels_meet")):
            state, params = feasibility_fixture()
            for ident, value in (("joint-outcome", point), ("joint-low", low), ("joint-high", high)):
                metric(state, ident)["value"] = value
            out = run_strategy(state, "evaluate-target-feasibility", params); row = record(out, "TARGET_FEASIBILITY")["scenarios"][0]
            self.assertEqual(row["range_screen"], expected)
            self.assertEqual(row["point_meets_proposed_objective"], point <= 1600)

    def test_missing_range_and_investment_remain_unknown_not_zero(self):
        state, params = feasibility_fixture(); scenario = params["scenarios"][0]
        scenario.update(range_metric_ids=None, investment=None)
        for ident in ("joint-low", "joint-high"):
            scenario["scenario_review"]["metric_contexts"].pop(ident)
        out = run_strategy(state, "evaluate-target-feasibility", params); row = record(out, "TARGET_FEASIBILITY")["scenarios"][0]
        self.assertIsNone(row["indicator_range"]); self.assertIsNone(row["investment"]); self.assertIsNone(row["budget_gap_metric_id"])
        self.assertEqual(out["result"]["status"], "partial"); self.assertIsNone(row["feasibility"])

    def test_late_delivery_and_full_period_timing_are_known_unmet(self):
        for when in ("2031-01-01", "2030-07-01", "2026-01-01"):
            state, params = feasibility_fixture(); params["scenarios"][0]["initiatives"][0]["commission_date"] = when
            out = run_strategy(state, "evaluate-target-feasibility", params); row = record(out, "TARGET_FEASIBILITY")["scenarios"][0]
            self.assertTrue(row["point_meets_proposed_objective"])
            conditions = row["unresolved_conditions"] if when == "2026-01-01" else row["known_unmet_conditions"]
            self.assertTrue(any("commission" in i for i in conditions))
            self.assertIsNone(row["feasibility"])

    def test_dependencies_unknown_cycles_order_and_project_evidence_block(self):
        for variant in ("unknown", "cycle", "date", "project", "evidence"):
            state, params = feasibility_fixture(); scenario = params["scenarios"][0]; first = scenario["initiatives"][0]
            if variant == "unknown": first["depends_on"] = ["missing"]
            elif variant == "cycle": first["depends_on"] = [first["id"]]
            elif variant == "project": first["project_id"] = "missing"
            elif variant == "evidence": first["evidence_ids"] = ["ev-001"]
            else:
                state["projects"].append(dict(state["projects"][0], id="prerequisite-project"))
                second = dict(first, id="prerequisite", project_id="prerequisite-project", commission_date="2029-12-02")
                scenario["initiatives"].append(second); first["depends_on"] = [second["id"]]
            self.assertEqual(run_strategy(state, "evaluate-target-feasibility", params)["result"]["status"], "blocked", variant)

    def test_source_scope_period_factor_and_projection_requirements(self):
        for variant in ("scope", "factor", "period", "tier", "unknown", "units", "basis", "overlap", "service", "fit"):
            state, params = feasibility_fixture(); scenario = params["scenarios"][0]
            if variant == "scope": scenario["scenario_review"]["scope"] = "Another plant"
            if variant == "factor":
                state["results"][0]["status"] = "partial"
                state["results"][0]["review_states"].append("EVIDENCE_INCOMPLETE")
                state["results"][0]["data_gaps"] = copy.deepcopy(state["data_gaps"])
                state["results"][0]["diagnostics"].append({"code": "EMISSION_FACTOR_REQUIRED", "message": "Fictional factor missing"})
            if variant == "period": metric(state, "joint-outcome")["period"] = state["reporting_period"]
            if variant == "tier": next(e for e in state["evidence"] if e["id"] == "joint-outcome-evidence")["source"]["tier"] = 1
            if variant == "unknown": metric(state, "joint-outcome")["value"] = None
            if variant == "units": metric(state, "joint-outcome")["unit"] = "kg CO2e"
            if variant == "basis": scenario["scenario_review"]["accounting_basis"] = "Netted offsets"
            if variant == "overlap": scenario["scenario_review"]["aggregation_basis"] = "sum_isolated_savings"
            if variant == "service": metric(state, "future-service")["value"] = 0
            if variant == "fit": scenario["scenario_review"]["metric_contexts"]["joint-outcome"]["confirmed"] = False
            out = run_strategy(state, "evaluate-target-feasibility", params)
            self.assertEqual(out["result"]["status"], "blocked", variant); self.assertEqual(out["result"]["metrics"], [])
            if variant == "factor": self.assertTrue(any(d["code"] == "EMISSION_FACTOR_REQUIRED" for d in out["result"]["diagnostics"]))

    def test_target_changes_wrong_range_and_constraint_omissions_block(self):
        for variant in ("target", "range", "domains", "status", "evidence", "budgetcurrency"):
            state, params = feasibility_fixture(); scenario = params["scenarios"][0]
            if variant == "target": metric(state, "strategy-target-target")["value"] = 9
            if variant == "range": metric(state, "joint-low")["value"] = 1800
            if variant == "domains": scenario["constraints"].pop()
            if variant == "status": scenario["constraints"][0]["status"] = "approved"
            if variant == "evidence": scenario["constraints"][0]["evidence_ids"] = []
            if variant == "budgetcurrency": metric(state, "available-budget")["unit"] = "USD"
            self.assertEqual(run_strategy(state, "evaluate-target-feasibility", params)["result"]["status"], "blocked", variant)

    def test_non_cash_budget_ancestry_blocks(self):
        state, params = feasibility_fixture()
        source = copy.deepcopy(state["results"][0]); source["id"] = "shadow-result"
        shadow = copy.deepcopy(metric(state, "available-budget")); shadow["id"] = "shadow-budget"
        source["metrics"] = [shadow]; source["diagnostics"] = [{"code": "NONCASH_SHADOW_PRICE", "message": "Noncash fictional internal value"}]
        state["results"].append(source); metric(state, "available-budget")["calculation"]["inputs"] = [shadow["id"]]
        self.assertEqual(run_strategy(state, "evaluate-target-feasibility", params)["result"]["status"], "blocked")

    def test_source_unit_conversion_and_dated_profile(self):
        state, params = feasibility_fixture()
        metric(state, "joint-outcome").update(value=1.5, unit="MWh")
        params["scenarios"][0]["initiatives"][0]["commission_date"] = "2030-07-01"
        params["scenarios"][0]["scenario_review"]["timing_basis"] = "dated_profile_modelled"
        out = run_strategy(state, "evaluate-target-feasibility", params); row = record(out, "TARGET_FEASIBILITY")["scenarios"][0]
        self.assertEqual(next(m["value"] for m in out["result"]["metrics"] if m["id"] == row["point_metric_id"]), 7.5)
        converted = next(c for c in row["conversions"] if c["metric_id"] == "joint-outcome")
        self.assertEqual(converted["source_unit"], "MWh"); self.assertEqual(converted["unit"], "kWh"); self.assertEqual(converted["factor"], 1000)
        self.assertFalse(any("period starts" in item for item in row["known_unmet_conditions"]))

    def test_native_initial_cost_is_reproduced_and_changed_quote_blocks(self):
        from scripts.finance_tools import run_finance
        from tests.test_finance_composition import composition_fixture
        state, params = feasibility_fixture(); _, requests = composition_fixture()
        cost = copy.deepcopy(requests["calculate-sustainability-project-cost"])
        cost["lines"] = [{"id": "joint-quote", "metric_id": "joint-cost", "kind": "cost", "category": "capital"}]
        for review in (cost["composition_review"], cost["analysis_review"]):
            review["evidence_ids"] = ["joint-cost-evidence"]
        cost["analysis_review"].update(valuation_date="2025-09-01", dollar_basis="nominal")
        cost["analysis_review"]["horizon"]["start"] = "2025-09-01"
        state = run_finance(state, "calculate-sustainability-project-cost", cost)["proposal"]["state"]
        investment = params["scenarios"][0]["investment"]; investment["cost_metric_id"] = "composed-cost-value"
        contexts = investment["review"]["metric_contexts"]; contexts["composed-cost-value"] = contexts.pop("joint-cost")
        out = run_strategy(state, "evaluate-target-feasibility", params)
        self.assertEqual(record(out, "TARGET_FEASIBILITY")["scenarios"][0]["investment"]["budget_minus_cost"], -100)
        metric(state, "joint-cost")["value"] = 399
        self.assertEqual(run_strategy(state, "evaluate-target-feasibility", params)["result"]["status"], "blocked")

    def test_saved_full_output_and_cli_replay_preserve_source_file(self):
        saved = json.loads((ROOT / "evaluations/sus15-feasibility-workflow.json").read_text(encoding="utf-8"))
        request = saved["request"]
        self.assertEqual(run_strategy(request["state"], request["skill"], request["parameters"]), saved["output"])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "request.json"; raw = json.dumps(request)
            path.write_text(raw, encoding="utf-8")
            process = subprocess.run([sys.executable, "-m", "scripts.run_strategy", str(path)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(process.returncode, 0, process.stdout)
            self.assertEqual(json.loads(process.stdout), saved["output"])
            self.assertEqual(path.read_text(encoding="utf-8"), raw)
