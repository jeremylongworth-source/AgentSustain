import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.contract_validation import ROOT, validate_state
from scripts.strategy_tools import run_strategy


def record(output, code):
    return json.loads(next(d["message"] for d in output["result"]["diagnostics"] if d["code"] == code))


def strategy_fixture():
    state = json.loads((ROOT / "examples/architecture-state.json").read_text(encoding="utf-8"))
    metric = state["results"][0]["metrics"][0]
    metric["value"] = 1000
    evidence = copy.deepcopy(state["evidence"][0]); evidence["id"] = "service-record"; evidence["unit"] = "count"
    evidence["source"].update(locator="fixture:output-log", title="Fictional 100-unit production log")
    evidence["method"].update(name="Fictional accepted-output log", source="fixture:output-log")
    state["evidence"].append(evidence)
    service = copy.deepcopy(metric); service.update(id="service-metric", name="Fictional production output", value=100, unit="count", evidence_ids=[evidence["id"]])
    service["calculation"]["inputs"] = [evidence["id"]]
    service["method"] = copy.deepcopy(evidence["method"])
    state["results"][0]["metrics"].append(service); state["results"][0]["evidence_ids"].append(evidence["id"])
    scope = "Fictional plant purchased electricity only"
    review = {"confirmed": True, "reviewer_role": "fictional strategy analyst", "rationale": "Fictional selected meter and production log inspected; not an assurance opinion.",
        "evidence_ids": ["ev-001"], "boundary_id": state["organizational_boundary"]["id"], "scope": scope}
    fit = lambda m: {"confirmed": True, "evidence_ids": m["evidence_ids"], "scope": scope, "rationale": "Fictional source is reviewed for the selected plant service."}
    base = dict(review, period=metric["period"], selection_rationale="Fictional annual operating year", recalculation_policy="Review acquisitions, meter changes and corrected records before a new append-only baseline.",
        accounting_basis="Gross selected purchased electricity, no credits or renewable claims.", coverage_complete=False, exclusions=["Other plants and fuel use"], nonoverlap_confirmed=True,
        metric_contexts={metric["id"]: fit(metric)})
    params = {"metric_ids": [metric["id"]], "unit": "kWh", "baseline_review": base, "result_id": "strategy-baseline"}
    base["metric_contexts"][metric["id"]]["accounting_basis"] = base["accounting_basis"]
    definition = {"id": "electricity-intensity", "name": "Electricity per produced unit", "kind": "intensity", "baseline_result_id": params["result_id"],
        "denominator_metric_id": service["id"], "denominator_review": dict(review, service_definition="Count of completed equivalent fictional units", comparability_policy="Same product and plant output log; review product-mix changes.", metric_contexts={service["id"]: fit(service)}),
        "owner": "Fictional operations lead", "frequency": "annual", "definition": "Selected electricity kWh divided by completed equivalent units", "desired_direction": "decrease"}
    definitions = {"definitions": [definition], "definition_review": dict(review, monitoring_basis="Annual matched meter/output records; not started."), "result_id": "strategy-kpis"}
    target = {"definition_result_id": "strategy-kpis", "kpi_id": definition["id"], "target": {"id": "electricity-objective", "kind": "intensity", "level_type": "reduction_percent", "value": 20, "unit": "%", "period": {"start": "2030-01-01", "end": "2030-12-31"}, "owner": "Fictional operations lead"},
        "target_review": dict(review, ambition_basis="Fictional proposed 20% level; technical and financial delivery not assessed.", period_comparability="Annual matched service; no future production quantity supplied.", growth_assumptions="Unknown future output; intensity improvement cannot imply absolute improvement.", double_counting_policy="Selected meter only; do not add a projected reduction to the inventory.", recalculation_policy=base["recalculation_policy"], offset_policy="excluded"), "result_id": "strategy-target"}
    return state, params, definitions, target


def chain(kind="intensity"):
    state, base, definitions, target = strategy_fixture()
    if kind == "absolute":
        definitions["definitions"][0].update(kind="absolute", denominator_metric_id=None, denominator_review=None)
        target["target"]["kind"] = "absolute"
    first = run_strategy(state, "establish-baseline", base)
    second = run_strategy(first["proposal"]["state"], "define-kpis", definitions)
    return second["proposal"]["state"], target, [first, second]


class StrategyTests(unittest.TestCase):
    def test_intensity_endpoint_preserves_absolute_unknown_and_open_reviews(self):
        state, params, _ = chain(); old = copy.deepcopy(state)
        out = run_strategy(state, "develop-target", params); report = record(out, "TARGET_PROPOSAL")
        self.assertEqual(out["result"]["metrics"][0]["value"], 8)
        self.assertEqual(out["result"]["metrics"][0]["unit"], "kWh/count")
        self.assertEqual(report["baseline_value"], 10); self.assertEqual(report["proposed_reduction"], 2)
        self.assertEqual(report["baseline_absolute_quantity"]["value"], 1000)
        self.assertIsNone(report["absolute_future_quantity"]); self.assertIsNone(report["trajectory"]); self.assertIsNone(report["feasibility"])
        for flag in ("target_adopted", "science_based_validated", "net_zero_validated", "public_claim_authorized", "implementation_authorized"):
            self.assertFalse(report[flag])
        self.assertEqual(state, old); validate_state(out["proposal"]["state"])
        for review in state["review_requirements"]:
            self.assertIn(review, out["result"]["review_requirements"])
        for gap in state["data_gaps"]:
            self.assertIn(gap, out["result"]["data_gaps"])
        self.assertEqual(out["proposal"]["state"]["ghg"], state["ghg"])

    def test_absolute_and_endpoint_known_answers(self):
        state, params, _ = chain("absolute")
        self.assertEqual(run_strategy(state, "develop-target", params)["result"]["metrics"][0]["value"], 800)
        params["target"].update(level_type="endpoint", value=750, unit="kWh")
        self.assertEqual(run_strategy(state, "develop-target", params)["result"]["metrics"][0]["value"], 750)

    def test_baseline_conversion_and_definition_has_no_monitoring(self):
        state, base, definitions, _ = strategy_fixture(); base["unit"] = "MWh"
        out = run_strategy(state, "establish-baseline", base)
        self.assertEqual(out["result"]["metrics"][0]["value"], 1)
        second = run_strategy(out["proposal"]["state"], "define-kpis", definitions)
        self.assertEqual(second["result"]["metrics"], [])
        self.assertFalse(record(second, "KPI_DEFINITIONS")["monitoring_started"])

    def test_unknown_zero_negative_and_emissions_denominators(self):
        for value, unit in ((0, "count"), (-1, "count"), (100, "kg CO2e"), (100, "CAD"), (None, "count")):
            state, base, definitions, _ = strategy_fixture()
            state["results"][0]["metrics"][1].update(value=value, unit=unit)
            first = run_strategy(state, "establish-baseline", base)
            out = run_strategy(first["proposal"]["state"], "define-kpis", definitions)
            self.assertEqual(out["result"]["status"], "blocked"); self.assertEqual(out["result"]["metrics"], [])

    def test_nonoverlap_unrelated_evidence_unknown_and_mixed_context_block(self):
        for variant in ("overlap", "evidence", "period", "unknown", "repeat", "negative", "basis"):
            state, base, _, _ = strategy_fixture()
            metric = state["results"][0]["metrics"][0]
            if variant == "overlap": base["baseline_review"]["nonoverlap_confirmed"] = False
            if variant == "evidence": base["baseline_review"]["metric_contexts"][metric["id"]]["evidence_ids"] = ["service-record"]
            if variant == "period": base["baseline_review"]["period"] = {"start": "2024-01-01", "end": "2024-12-31"}
            if variant == "unknown": metric["value"] = None
            if variant == "negative": metric["value"] = -1
            if variant == "repeat": base["metric_ids"] *= 2
            if variant == "basis": base["baseline_review"]["metric_contexts"][metric["id"]]["accounting_basis"] = "Different scope/GWP or net credits"
            out = run_strategy(state, "establish-baseline", base)
            self.assertEqual(out["result"]["status"], "blocked"); self.assertEqual(out["result"]["metrics"], [])

    def test_stale_source_metric_and_baseline_report_rejected(self):
        for variant in ("metric", "baseline", "definition"):
            state, params, _ = chain()
            if variant == "metric": state["results"][0]["metrics"][0]["value"] = 1100
            else:
                owner = next(r for r in state["results"] if r["skill"] == ("establish-baseline" if variant == "baseline" else "define-kpis"))
                code = "STRATEGY_BASELINE" if variant == "baseline" else "KPI_DEFINITIONS"
                d = next(d for d in owner["diagnostics"] if d["code"] == code)
                r = json.loads(d["message"]); r["tampered"] = True; d["message"] = json.dumps(r)
            self.assertEqual(run_strategy(state, "develop-target", params)["result"]["status"], "blocked")

    def test_factor_requirement_is_preserved_through_reproduction(self):
        state, params, _ = chain()
        state["results"][0]["diagnostics"].append({"code": "EMISSION_FACTOR_REQUIRED", "message": "Fictional missing defensible factor"})
        state["results"][0]["status"] = "partial"
        state["results"][0]["review_states"].append("EVIDENCE_INCOMPLETE")
        state["results"][0]["data_gaps"] = copy.deepcopy(state["data_gaps"])
        out = run_strategy(state, "develop-target", params)
        self.assertEqual(out["result"]["status"], "blocked")
        self.assertTrue(any(d["code"] == "EMISSION_FACTOR_REQUIRED" for d in out["result"]["diagnostics"]))

    def test_unsupported_offsets_levels_periods_policies_and_scope_block(self):
        for variant in ("offsets", "negative", "over100", "unit", "zero", "past", "multiyear", "scope", "policy", "unreviewed"):
            state, params, _ = chain()
            if variant == "offsets": params["target_review"]["offset_policy"] = "net_with_credits"
            if variant == "negative": params["target"]["value"] = -1
            if variant == "over100": params["target"]["value"] = 101
            if variant == "unit": params["target"]["unit"] = "kWh"
            if variant == "zero":
                # A valid zero gross baseline still cannot support a relative percentage target.
                fresh, base, defs, target = strategy_fixture(); fresh["results"][0]["metrics"][0]["value"] = 0
                first = run_strategy(fresh, "establish-baseline", base); second = run_strategy(first["proposal"]["state"], "define-kpis", defs)
                state, params = second["proposal"]["state"], target
            if variant == "past": params["target"]["period"] = state["reporting_period"]
            if variant == "multiyear": params["target"]["period"]["start"] = "2026-01-01"
            if variant == "scope": params["target_review"]["scope"] = "Whole organization"
            if variant == "policy": params["target_review"]["recalculation_policy"] = "No restatement ever"
            if variant == "unreviewed": params["target_review"]["confirmed"] = False
            out = run_strategy(state, "develop-target", params)
            self.assertEqual(out["result"]["status"], "blocked", variant); self.assertEqual(out["result"]["metrics"], [])

    def test_leap_year_calendar_and_zero_endpoint(self):
        state, params, _ = chain()
        params["target"].update(period={"start": "2028-01-01", "end": "2028-12-31"}, value=100)
        self.assertEqual(run_strategy(state, "develop-target", params)["result"]["metrics"][0]["value"], 0)

    def test_cli_reproduces_complete_proposal_without_writing_request(self):
        state, params, _ = chain(); expected = run_strategy(state, "develop-target", params)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "request.json"
            raw = json.dumps({"contract_version": "0.1.0", "skill": "develop-target", "state": state, "parameters": params})
            path.write_text(raw, encoding="utf-8")
            proc = subprocess.run([sys.executable, "-m", "scripts.run_strategy", str(path)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stdout); self.assertEqual(json.loads(proc.stdout), expected)
            self.assertEqual(path.read_text(encoding="utf-8"), raw)

    def test_saved_workflow_replays_every_complete_output(self):
        saved = json.loads((ROOT / "evaluations/sus15-target-workflow.json").read_text(encoding="utf-8"))
        for request, expected in zip(saved["requests"], saved["outputs"], strict=True):
            self.assertEqual(run_strategy(request["state"], request["skill"], request["parameters"]), expected)
