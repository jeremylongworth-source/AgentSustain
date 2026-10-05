"""Comparable project registers and explicit lexicographic screening ranks."""
import copy
import json

from .data_tools import number
from .finance_abatement import AbatementFactorRequired


def _review(record, known, fields):
    if (not isinstance(record, dict) or record.get("confirmed") is not True
            or any(not isinstance(record.get(f), str) or not record[f].strip() for f in fields)):
        raise ValueError("Explicit sourced decision/comparability review required.")
    evidence = record.get("evidence_ids")
    if (not isinstance(evidence, list) or not evidence or any(not isinstance(e, str) for e in evidence)
            or not set(evidence) <= known):
        raise ValueError("Known review evidence required.")
    return set(evidence)


def _basis(result):
    items = [d for d in result["diagnostics"] if d["code"] == "FINANCIAL_ANALYSIS_BASIS"]
    if len(items) != 1: raise ValueError("One reproducible financial input record required.")
    record = json.loads(items[0]["message"])
    if not isinstance(record, dict) or not isinstance(record.get("analysis_review"), dict):
        raise ValueError("Structured financial input basis required.")
    return copy.deepcopy(record)


def compare_projects(state, parameters, resolve, refs, rerun, operations):
    review, analysis = parameters["comparison_review"], parameters["analysis_review"]
    known = {e["id"] for e in state["evidence"]}
    refs.update(_review(review, known, ("baseline_id", "service_basis", "comparability_basis", "rationale")))
    if not isinstance(review.get("coverage_complete"), bool): raise ValueError("Explicit coverage completeness required.")
    criteria, projects = parameters["criteria"], parameters["projects"]
    if not isinstance(criteria, list) or not criteria or any(not isinstance(c, dict) for c in criteria):
        raise ValueError("Nonempty criterion register required.")
    criterion_ids = [c.get("id") for c in criteria]
    if any(not isinstance(i, str) or not i.strip() for i in criterion_ids) or len(set(criterion_ids)) != len(criterion_ids):
        raise ValueError("Unique criterion IDs required.")
    for criterion in criteria:
        if (set(criterion) != {"id", "unit", "direction", "period_basis", "definition"}
                or criterion["direction"] not in {"maximize", "minimize"}
                or criterion["period_basis"] not in {"horizon", "reporting_period"}
                or any(not isinstance(criterion[f], str) or not criterion[f].strip() for f in ("unit", "definition"))):
            raise ValueError("Declare each criterion's unit, direction, definition and comparable period basis.")
    if not isinstance(projects, list) or len(projects) < 2 or any(not isinstance(p, dict) for p in projects):
        raise ValueError("At least two project alternatives required.")
    ids = [p.get("id") for p in projects]
    if any(not isinstance(i, str) or not i.strip() for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("Unique project IDs required.")
    owners = {m["id"]: r for r in state["results"] for m in r["metrics"]}
    metrics = {m["id"]: m for r in state["results"] for m in r["metrics"]}
    contexts = review.get("source_contexts")
    if not isinstance(contexts, dict): raise ValueError("Current metric source confirmations required.")
    economic = {f: analysis[f] for f in ("currency", "valuation_date", "horizon", "dollar_basis", "tax_basis")}
    signatures, checked, selected, rows, entries = {}, set(), set(), [], []
    for project_index, project in enumerate(projects, 1):
        if (set(project) != {"id", "owner", "readiness", "constraints", "dependencies", "interacts_with", "evidence_ids", "economic_basis", "baseline_id", "service_basis", "metrics"}
                or project["economic_basis"] != economic or project["baseline_id"] != review["baseline_id"]
                or project["service_basis"] != review["service_basis"]
                or project["readiness"] not in {"ready_for_screening", "deferred"}
                or not isinstance(project["constraints"], str) or not project["constraints"].strip()
                or not isinstance(project["metrics"], dict) or set(project["metrics"]) != set(criterion_ids)):
            raise ValueError("Complete project record with comparable baseline, service and economic basis required.")
        refs.update(_review(dict(project, confirmed=True), known, ()))
        if project["owner"] is not None and (not isinstance(project["owner"], str) or not project["owner"].strip()):
            raise ValueError("Project owner must be a named role or explicitly unassigned.")
        deps = project["dependencies"]
        if (not isinstance(deps, list) or any(not isinstance(d, dict) or set(d) != {"description", "satisfied"}
                or not isinstance(d["description"], str) or not d["description"].strip() or not isinstance(d["satisfied"], bool) for d in deps)):
            raise ValueError("Explicit dependencies and assessed satisfaction required.")
        interacts = project["interacts_with"]
        if (not isinstance(interacts, list) or any(not isinstance(i, str) for i in interacts)
                or len(interacts) != len(set(interacts)) or not set(interacts) <= set(ids)-{project["id"]}):
            raise ValueError("Interactions must identify other selected alternatives once.")
        row = copy.deepcopy(project); row["values"] = {}; row["rank"] = None
        reasons = [d["description"] for d in deps if not d["satisfied"]]
        if project["owner"] is None: reasons.append("Owner is unassigned.")
        if project["readiness"] == "deferred": reasons.append("Supplied readiness is deferred.")
        row["eligible"] = not reasons; row["deferral_reasons"] = reasons
        for criterion_index, criterion in enumerate(criteria, 1):
            item = project["metrics"][criterion["id"]]
            if not isinstance(item, dict) or set(item) != {"metric_id", "range"}:
                raise ValueError("Each project criterion requires a source metric and sourced range.")
            metric = resolve(item["metric_id"], criterion["unit"], criterion["period_basis"] == "horizon")
            selected.add(metric["id"])
            period = analysis["horizon"] if criterion["period_basis"] == "horizon" else state["reporting_period"]
            source = contexts.get(metric["id"])
            if (metric["period"] != period or not metric["evidence_ids"] or not isinstance(source, dict)
                    or any(source.get(f) != metric[f] for f in ("value", "unit", "period", "boundary_id", "method", "evidence_ids"))
                    or source.get("definition") != criterion["definition"]):
                raise ValueError("Criterion quantity/context/definition must match current source confirmation and selected period.")
            owner = owners[metric["id"]]
            physical = None
            if "CO2e" in criterion["unit"]:
                if any(not isinstance(source.get(f), str) or not source[f].strip() for f in ("gwp_basis", "scope_boundary")):
                    raise ValueError("CO2e criteria require explicit comparable GWP and physical scope context.")
                physical = (source["gwp_basis"], source["scope_boundary"])
            signature = (owner["skill"], json.dumps(metric["method"], sort_keys=True), physical)
            if criterion["id"] in signatures and signatures[criterion["id"]] != signature:
                raise ValueError("Unlike source methods cannot be collapsed into the same criterion.")
            signatures[criterion["id"]] = signature
            pending, seen = [metric["id"]], set()
            while pending:
                key = pending.pop()
                if key in seen or key not in metrics: continue
                seen.add(key)
                if any(d["code"] == "EMISSION_FACTOR_REQUIRED" for d in owners[key]["diagnostics"]):
                    raise AbatementFactorRequired("Selected project criterion retains missing emission-factor lineage.")
                pending.extend(metrics[key]["calculation"]["inputs"])
            if owner["skill"] in operations:
                if owner["skill"] in {"compare-sustainability-projects", "rank-sustainability-investments"}:
                    raise ValueError("Use original project measures rather than recycling comparison/rank outputs as project outcomes.")
                basis = _basis(owner)
                if owner["skill"] == "calculate-marginal-abatement-cost" and physical is not None:
                    abatement = basis.get("abatement_review")
                    if not isinstance(abatement, dict) or not isinstance(abatement.get("source_contexts"), dict):
                        raise ValueError("Saved abatement physical source context required.")
                    baseline_context = abatement["source_contexts"].get(basis.get("baseline_emissions_id"))
                    if (not isinstance(baseline_context, dict)
                            or physical != (baseline_context.get("gwp_basis"), abatement.get("scope_boundary"))):
                        raise ValueError("Declared comparison GWP/scope differs from saved abatement source basis.")
                if any(basis["analysis_review"].get(f) != value for f, value in economic.items()):
                    raise ValueError("Source financial calculation economic basis differs from project comparison.")
                if owner["skill"] == "calculate-npv":
                    if basis.get("discount_rate_id") != review.get("discount_rate_id"):
                        raise ValueError("NPV comparisons require the same declared sourced discount-rate metric.")
                if owner["id"] not in checked:
                    basis["result_id"] = parameters["result_id"]+"-check-"+owner["id"]
                    while basis["result_id"] in {r["id"] for r in state["results"]}: basis["result_id"] += "-next"
                    reproduced = rerun(state, owner["skill"], basis)["result"]
                    content = lambda items: [{k:v for k,v in m.items() if k != "id"} for m in items]
                    if not reproduced["metrics"] or content(reproduced["metrics"]) != content(owner["metrics"]):
                        raise ValueError("Project financial outcomes do not reproduce from current source inputs.")
                    checked.add(owner["id"])
            bounds = item["range"]
            if not isinstance(bounds, dict) or set(bounds) != {"low", "high", "unit", "basis", "evidence_ids"} or bounds["unit"] != criterion["unit"]:
                raise ValueError("Explicit sourced scenario bounds in the criterion unit required.")
            refs.update(_review(dict(bounds, confirmed=True), known, ("basis",)))
            if not number(bounds["low"]) <= number(metric["value"]) <= number(bounds["high"]):
                raise ValueError("Estimate must lie within its ordered supplied bounds.")
            row["values"][criterion["id"]] = metric["value"]
            entries.append((parameters["result_id"]+f"-project-{project_index}-criterion-{criterion_index}", number(metric["value"]), metric["unit"], [metric["id"]],
                "Selected comparable project measure; no portfolio summation or cross-unit scoring", period))
        rows.append(row)
    if set(contexts) != selected: raise ValueError("Source confirmations must cover selected metrics only.")
    for left in rows:
        for right in rows:
            if left["id"] == right["id"]: continue
            if ((right["id"] in left["interacts_with"]) != (left["id"] in right["interacts_with"])):
                raise ValueError("Declare project interactions symmetrically.")
            shared = {x["metric_id"] for x in left["metrics"].values()} & {x["metric_id"] for x in right["metrics"].values()}
            if shared and right["id"] not in left["interacts_with"]:
                raise ValueError("Reused outcome quantities require declared interacting alternatives.")
    return entries, {"criteria": criteria, "projects": rows, "comparison_review": review,
        "portfolio_total": None, "limits": "Conditional comparable alternatives; supplied ranges and feasibility are not authenticated. No joint portfolio model or investment approval."}, review["coverage_complete"]


def rank_projects(state, parameters, resolve, refs, rerun):
    source = next((r for r in state["results"] if r["id"] == parameters["comparison_result_id"]), None)
    if source is None or source["skill"] != "compare-sustainability-projects":
        raise ValueError("A supported project comparison result required.")
    basis = _basis(source)
    if any(basis["analysis_review"].get(f) != parameters["analysis_review"][f] for f in ("currency", "valuation_date", "horizon", "dollar_basis", "tax_basis")):
        raise ValueError("Ranking and comparison economic bases must match.")
    basis["result_id"] = parameters["result_id"]+"-comparison-check"
    while basis["result_id"] in {r["id"] for r in state["results"]}: basis["result_id"] += "-next"
    checked = rerun(state, "compare-sustainability-projects", basis)["result"]
    content = lambda items: [{k:v for k,v in m.items() if k != "id"} for m in items]
    if not checked["metrics"] or content(checked["metrics"]) != content(source["metrics"]):
        raise ValueError("Project comparison fails current-source reproduction.")
    reports = [d for d in checked["diagnostics"] if d["code"] == "PROJECT_COMPARISON"]
    if len(reports) != 1: raise ValueError("Reproduced comparison report required.")
    report = json.loads(reports[0]["message"])
    review = parameters["decision_review"]
    refs.update(source["evidence_ids"])
    refs.update(_review(review, {e["id"] for e in state["evidence"]}, ("question", "rationale", "eligibility_basis")))
    criteria = {c["id"]: c for c in report["criteria"]}
    order = review.get("criteria_order")
    if (review.get("method") != "lexicographic_estimate" or not isinstance(order, list)
            or any(not isinstance(i, str) for i in order) or len(order) != len(set(order)) or set(order) != set(criteria)):
        raise ValueError("Explicit lexicographic priority order covering every criterion once required; no weights inferred.")
    thresholds = review.get("thresholds")
    if (not isinstance(thresholds, dict) or not set(thresholds) <= set(criteria)
            or any(not isinstance(t, dict) or not t or not set(t) <= {"minimum", "maximum"} for t in thresholds.values())):
        raise ValueError("Explicit criterion minimum/maximum thresholds (or empty register) required.")
    for bounds in thresholds.values():
        for value in bounds.values(): number(value)
        if "minimum" in bounds and "maximum" in bounds and number(bounds["minimum"]) > number(bounds["maximum"]):
            raise ValueError("Threshold bounds are reversed.")
    for row in report["projects"]:
        for criterion, bounds in thresholds.items():
            value = number(row["values"][criterion])
            if ("minimum" in bounds and value < number(bounds["minimum"])) or ("maximum" in bounds and value > number(bounds["maximum"])):
                row["deferral_reasons"].append("Supplied threshold not met: "+criterion)
        row["eligible"] = not row["deferral_reasons"]
    def key(row):
        return tuple(number(row["values"][c])*(-1 if criteria[c]["direction"] == "maximize" else 1) for c in order)
    eligible = sorted((r for r in report["projects"] if r["eligible"]), key=lambda r:(key(r), r["id"]))
    for row in eligible: row["rank"] = 1+sum(key(other) < key(row) for other in eligible)
    sensitivity = []
    primary = order[0]
    for index, left in enumerate(eligible):
        for right in eligible[index+1:]:
            a, b = left["metrics"][primary]["range"], right["metrics"][primary]["range"]
            if max(number(a["low"]),number(b["low"])) <= min(number(a["high"]),number(b["high"])):
                sensitivity.append({"projects":[left["id"],right["id"]],"criterion":primary,
                    "finding":"Supplied primary ranges overlap; estimate ordering is not established as robust across these scenarios."})
    report.update(projects=eligible+[r for r in report["projects"] if not r["eligible"]],decision_review=review,sensitivity=sensitivity)
    inputs = [m["id"] for m in source["metrics"]]
    entries = [(parameters["result_id"]+"-"+r["id"], number(r["rank"]), "rank", inputs,
        "Competition rank under supplied lexicographic criterion estimates among eligible alternatives; exact tuples tie", parameters["analysis_review"]["horizon"]) for r in eligible]
    return entries, report, basis["comparison_review"]["coverage_complete"]
