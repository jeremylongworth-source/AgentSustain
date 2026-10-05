"""Explicit preliminary energy-only project screening, without portfolio totals."""
import json

from .data_tools import number, serialize


def screen_projects(state, parameters, rerun, review_check):
    """Return a sourced candidate register under the supplied supported criterion."""
    review = parameters["decision_review"]
    known = {e["id"] for e in state["evidence"]}
    refs = review_check(review, known, ("question", "rationale", "eligibility_basis"))
    if review.get("criterion") != "descending_lower_bound_kWh":
        raise ValueError("Supply the supported lower-bound energy criterion; no weights or financial scores inferred.")
    projects = parameters["projects"]
    if not isinstance(projects, list) or not projects or any(not isinstance(p, dict) for p in projects):
        raise ValueError("A nonempty project register is required.")
    ids = [p.get("id") for p in projects]
    if any(not isinstance(i, str) or not i.strip() for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("Unique project IDs required.")
    fields = {"id", "equipment", "mechanism", "owner", "constraints", "dependencies", "readiness",
              "evidence_ids", "savings_result_id", "range", "interacts_with"}
    rows = []
    for project in projects:
        if set(project) != fields or any(not isinstance(project[k], str) or not project[k].strip()
                                        for k in ("equipment", "mechanism", "constraints")):
            raise ValueError("Each project needs equipment, mechanism, constraints and the complete screening record.")
        refs.update(review_check({"confirmed": True, "evidence_ids": project["evidence_ids"]}, known, ()))
        if project["readiness"] not in {"ready_for_screening", "deferred"}:
            raise ValueError("Explicit ready_for_screening/deferred status required; neither is implementation approval.")
        owner = project["owner"]
        if owner is not None and (not isinstance(owner, str) or not owner.strip()):
            raise ValueError("Owner must be a named role or null for unassigned.")
        dependencies = project["dependencies"]
        if not isinstance(dependencies, list) or any(not isinstance(d, dict) or set(d) != {"description", "satisfied"}
                or not isinstance(d["description"], str) or not d["description"].strip()
                or not isinstance(d["satisfied"], bool) for d in dependencies):
            raise ValueError("Declare each dependency and its explicitly assessed satisfaction.")
        interactions = project["interacts_with"]
        if (not isinstance(interactions, list) or any(not isinstance(i, str) for i in interactions)
                or len(interactions) != len(set(interactions)) or not set(interactions) <= set(ids)-{project["id"]}):
            raise ValueError("Interactions must reference other distinct selected projects.")
        prior = next((r for r in state["results"] if r["id"] == project["savings_result_id"]), None)
        if prior is None or prior["skill"] != "estimate-energy-savings" or prior["status"] not in {"completed", "partial"}:
            raise ValueError("Each candidate must link a supported savings result.")
        inputs = [json.loads(d["message"]) for d in prior["diagnostics"] if d["code"] == "ENERGY_INPUTS"]
        if len(inputs) != 1 or inputs[0]["comparison_review"]["analysis_type"] != "projection":
            raise ValueError("Candidate benefits must be labeled projections with reproducible input records.")
        inputs[0]["result_id"] = parameters["result_id"] + "-recheck-" + project["id"]
        reproduced = rerun(state, "estimate-energy-savings", inputs[0])["result"]
        def content(metrics):
            return [{k: v for k, v in m.items() if k != "id"} for m in metrics]
        if not reproduced["metrics"] or content(reproduced["metrics"]) != content(prior["metrics"]):
            raise ValueError("Projected benefit fails revalidation against current source quantities/context.")
        estimate = number(prior["metrics"][0]["value"])
        bounds = project["range"]
        if not isinstance(bounds, dict) or set(bounds) != {"low", "high", "unit", "basis", "evidence_ids"}:
            raise ValueError("Supply a sourced scenario range; no confidence interval inferred.")
        refs.update(review_check(dict(bounds, confirmed=True), known, ("basis",)))
        if bounds["unit"] != "kWh":
            raise ValueError("Scenario range must explicitly be in kWh.")
        low, high = number(bounds["low"]), number(bounds["high"])
        if not low <= estimate <= high:
            raise ValueError("Projected estimate must lie within the supplied ordered range.")
        reasons = []
        if project["readiness"] == "deferred": reasons.append("Supplied readiness is deferred.")
        if owner is None: reasons.append("Owner is unassigned.")
        reasons.extend(d["description"] for d in dependencies if not d["satisfied"])
        if low <= 0: reasons.append("Supplied lower bound does not establish positive energy benefit.")
        refs.update(prior["evidence_ids"])
        rows.append(dict(project, estimated_kWh=serialize(estimate), lower_bound_kWh=serialize(low),
                         upper_bound_kWh=serialize(high), eligible=not reasons, deferral_reasons=reasons, rank=None))
    for row in rows:
        for other in rows:
            if (row["id"] != other["id"] and row["savings_result_id"] == other["savings_result_id"]
                    and other["id"] not in row["interacts_with"]):
                raise ValueError("Reused savings results must be declared as interacting alternatives.")
        for other in row["interacts_with"]:
            if row["id"] not in next(r for r in rows if r["id"] == other)["interacts_with"]:
                raise ValueError("Declare interactions symmetrically; do not imply independent savings.")
    eligible = sorted((r for r in rows if r["eligible"]), key=lambda r: (-number(r["lower_bound_kWh"]), r["id"]))
    for row in eligible:
        row["rank"] = 1 + sum(number(other["lower_bound_kWh"]) > number(row["lower_bound_kWh"]) for other in eligible)
    sensitivity = []
    for index, left in enumerate(eligible):
        for right in eligible[index+1:]:
            if max(number(left["lower_bound_kWh"]), number(right["lower_bound_kWh"])) <= min(number(left["upper_bound_kWh"]), number(right["upper_bound_kWh"])):
                sensitivity.append({"projects": [left["id"], right["id"]], "finding": "Supplied ranges overlap; estimated-benefit order can tie or reverse."})
    report = {"decision_review": review, "period": state["reporting_period"],
              "boundary_id": state["organizational_boundary"]["id"], "projects": eligible + [r for r in rows if not r["eligible"]],
              "sensitivity": sensitivity, "portfolio_total": None,
              "limits": "Preliminary energy-only screening; supplied feasibility/ranges are not authenticated. Interacting projects require a joint model. No investment or engineering approval."}
    return report, refs, bool(eligible)
