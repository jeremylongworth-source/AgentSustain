"""Evidence-backed delivered-energy arithmetic; no fuel or emissions factors."""
import copy
from decimal import Decimal, localcontext
import json

from .contract_validation import validate_state
from .data_tools import baseline, convert, kpi, number, serialize
from .state_proposal import propose


SOURCE = "https://www.energy.gov/cmei/femp/articles/mv-guidelines-measurement-and-verification-performance-based-contracts-version-0"
OPERATIONS = {
    "build-energy-baseline": {"metric_ids", "coverage_review", "result_id"},
    "calculate-energy-intensity": {"energy_id", "denominator_id", "denominator_review", "result_id"},
    "estimate-energy-savings": {"baseline_id", "scenario_id", "comparison_review", "result_id"},
    "detect-energy-hotspots": {"baseline_result_id", "coverage_review", "result_id"},
}


def _review(review, known, fields):
    refs = review.get("evidence_ids") if isinstance(review,dict) else None
    if (not isinstance(review,dict) or review.get("confirmed") is not True or not isinstance(refs,list) or not refs
            or any(not isinstance(ref,str) for ref in refs) or not set(refs) <= known
            or any(not isinstance(review.get(field),str) or not review[field].strip() for field in fields)):
        raise ValueError("An explicit source-backed review with the required coverage/context fields is needed.")
    return set(refs)


def _resolve(state, ident, energy=False):
    metric = next((m for r in state["results"] for m in r["metrics"] if m["id"]==ident),None)
    if metric is None or metric["value"] is None or number(metric["value"]) < 0:
        raise ValueError("Resolved nonnegative measured/modelled quantity required; unknown is not zero.")
    if metric["period"] != state["reporting_period"] or metric["boundary_id"] != state["organizational_boundary"]["id"]:
        raise ValueError("Quantity period or boundary differs from the reporting context.")
    if energy:
        convert(metric["value"],metric["unit"],"kWh")
    return metric


def _baseline(state, ids, review, unit):
    if not isinstance(ids,list) or not ids or len(ids)!=len(set(ids)):
        raise ValueError("Select unique energy quantity IDs.")
    known = {e["id"] for e in state["evidence"]}
    refs = _review(review,known,("measurement_boundary","nonoverlap_assessment","representativeness","rationale"))
    if review.get("basis") != "delivered_final_energy" or not isinstance(review.get("carrier_map"),dict) or set(review["carrier_map"]) != set(ids):
        raise ValueError("Declare delivered final energy and each selected quantity's carrier; no source-energy conversion inferred.")
    if any(not isinstance(carrier,str) or not carrier.strip() for carrier in review["carrier_map"].values()):
        raise ValueError("Energy carrier labels required.")
    convert(1,unit,"kWh")
    metrics = [_resolve(state,ident,True) for ident in ids]
    all_metrics = {m["id"]:m for r in state["results"] for m in r["metrics"]}
    def ancestors(ident):
        found, pending = set(),list(all_metrics[ident]["calculation"]["inputs"])
        while pending:
            key = pending.pop()
            if key in found:
                continue
            found.add(key)
            if key in all_metrics:
                pending.extend(all_metrics[key]["calculation"]["inputs"])
        return found
    if any((set(ids)-{ident}) & ancestors(ident) for ident in ids):
        raise ValueError("An aggregate and its component quantity cannot both enter a baseline.")
    primitive = baseline(metrics,unit,True,review.get("coverage_details"))
    refs.update(eid for metric in metrics for eid in metric["evidence_ids"])
    return primitive,refs,metrics


def run_energy(state, skill, parameters):
    validate_state(state)
    if skill not in OPERATIONS or not isinstance(parameters,dict):
        raise ValueError("Supported energy operation and parameters required")
    required = OPERATIONS[skill]
    optional = {"target_unit"} if skill=="build-energy-baseline" else set()
    if not required <= set(parameters) or set(parameters)-required-optional:
        raise ValueError("Invalid energy parameters")
    ident = parameters["result_id"]
    if not isinstance(ident,str) or not ident.strip():
        raise ValueError("Result ID required")
    result = {"id":ident,"skill":skill,"contract_version":"0.1.0","status":"completed","review_states":["ANALYTICAL"],
              "review_requirements":copy.deepcopy(state["review_requirements"]),"metrics":[],"evidence_ids":[],"assumptions":list(state["assumptions"]),
              "data_gaps":copy.deepcopy(state["data_gaps"]),"diagnostics":[],"next_actions":[]}
    refs = set()
    known = {e["id"] for e in state["evidence"]}
    def gap(code,message):
        result["data_gaps"].append({"id":f"{ident}-gap-{len(result['data_gaps'])}","field":"energy_analysis","reason":message,
            "impact":"Energy coverage or interpretation is incomplete.","remedy":"Supply compatible measured/modelled energy quantities, source coverage and context review."})
        result["diagnostics"].append({"code":code,"message":message})
    def emit(suffix,name,value,unit,inputs,formula,assumption=None):
        if assumption and assumption not in result["assumptions"]:
            result["assumptions"].append(assumption)
        result["metrics"].append({"id":ident+"-"+suffix,"name":name,"value":serialize(value),"unit":unit,
            "period":copy.deepcopy(state["reporting_period"]),"boundary_id":state["organizational_boundary"]["id"],"evidence_ids":sorted(refs),
            "method":{"name":"Documented delivered-energy arithmetic","version":"0.1.0","source":SOURCE},"assumption":assumption,
            "uncertainty":{"kind":"unquantified","description":"Input and operating-condition uncertainty remains unquantified; no verification performed.","value":None,"unit":None},
            "calculation":{"formula":formula,"inputs":list(dict.fromkeys(inputs)),"conversions":["Energy converted with the supported unit registry; no inferred fuel heating value or source-energy factor"],"rounding":"34-digit Decimal arithmetic; JSON serialization"}})
    try:
        if skill=="build-energy-baseline":
            unit = parameters.get("target_unit","kWh")
            primitive,refs,metrics = _baseline(state,parameters["metric_ids"],parameters["coverage_review"],unit)
            emit("energy","Delivered final-energy baseline",primitive["value"],unit,parameters["metric_ids"],"Sum of nonoverlapping source quantities converted to target energy unit")
            result["diagnostics"].append({"code":"ENERGY_BASELINE","message":json.dumps({"metric_ids":parameters["metric_ids"],"target_unit":unit,
                "coverage_review":parameters["coverage_review"],"limits":"Source coverage/representativeness is supplied, not authenticated; not weather or production normalized."},sort_keys=True)})
        elif skill=="calculate-energy-intensity":
            energy = _resolve(state,parameters["energy_id"],True)
            denominator = _resolve(state,parameters["denominator_id"])
            review = parameters["denominator_review"]
            refs = _review(review,known,("definition","unit","rationale"))
            if review.get("metric_id")!=denominator["id"] or review["unit"]!=denominator["unit"] or denominator["unit"]=="UNKNOWN_UNIT":
                raise ValueError("Denominator definition and units must match the actual activity metric.")
            numerator = copy.deepcopy(energy)
            numerator.update(value=convert(energy["value"],energy["unit"],"kWh")["value"],unit="kWh")
            primitive = kpi(numerator,denominator,"ratio")
            refs.update(energy["evidence_ids"]+denominator["evidence_ids"])
            emit("intensity","Delivered-energy intensity",primitive["value"],primitive["unit"],[energy["id"],denominator["id"]],"Energy in kWh / evidenced positive activity denominator")
        elif skill=="estimate-energy-savings":
            before = _resolve(state,parameters["baseline_id"],True)
            after = _resolve(state,parameters["scenario_id"],True)
            review = parameters["comparison_review"]
            refs = _review(review,known,("baseline_conditions","scenario_conditions","adjustment_method","rationale"))
            if (review.get("baseline_id")!=before["id"] or review.get("scenario_id")!=after["id"] or review.get("comparison_basis") not in {"same_conditions","adjusted_baseline"}
                    or review.get("analysis_type") not in {"projection","observed_difference"}):
                raise ValueError("Specific input IDs, comparison basis and projection/observed type required.")
            assumption = None
            if review["analysis_type"]=="projection":
                evidence = {e["id"]:e for e in state["evidence"]}
                if not after["assumption"] or not any(evidence[eid]["source"]["tier"]==5 for eid in after["evidence_ids"]):
                    raise ValueError("Projected scenario needs explicit assumptions and tier 5 model evidence.")
                assumption = "Projected energy savings from supplied scenario assumptions; not realized or verified savings."
            refs.update(before["evidence_ids"]+after["evidence_ids"])
            with localcontext() as context:
                context.prec = 34
                initial = convert(before["value"],before["unit"],"kWh")["value"]
                scenario = convert(after["value"],after["unit"],"kWh")["value"]
                savings = initial-scenario
                emit("savings","Projected energy savings" if assumption else "Observed energy difference",savings,"kWh",[before["id"],after["id"]],"Comparable/adjusted baseline energy - scenario/reporting energy in kWh",assumption)
                if initial>0:
                    emit("savings-percent","Energy difference relative to baseline",savings/initial*100,"%",[before["id"],after["id"]],"(baseline - scenario) / baseline * 100",assumption)
                else:
                    gap("PERCENTAGE_DENOMINATOR_REQUIRED","Zero baseline supports absolute difference, not percentage savings.")
            result["diagnostics"].append({"code":"ENERGY_SAVINGS_BASIS","message":json.dumps(review,sort_keys=True)})
        else:
            prior = next((r for r in state["results"] if r["id"]==parameters["baseline_result_id"]),None)
            if prior is None or prior["skill"]!="build-energy-baseline" or prior["status"] not in {"completed","partial"} or len(prior["metrics"])!=1:
                raise ValueError("Supported energy baseline result required.")
            records = [json.loads(d["message"]) for d in prior["diagnostics"] if d["code"]=="ENERGY_BASELINE"]
            if len(records)!=1:
                raise ValueError("One baseline coverage record required.")
            record = records[0]
            primitive,refs,metrics = _baseline(state,record["metric_ids"],record["coverage_review"],"kWh")
            total = convert(prior["metrics"][0]["value"],prior["metrics"][0]["unit"],"kWh")["value"]
            if (serialize(total)!=serialize(primitive["value"])
                    or set(prior["metrics"][0]["calculation"]["inputs"])!=set(record["metric_ids"])
                    or prior["metrics"][0]["period"]!=state["reporting_period"]
                    or prior["metrics"][0]["boundary_id"]!=state["organizational_boundary"]["id"]):
                raise ValueError("Energy baseline does not reproduce from its source quantities.")
            review = parameters["coverage_review"]
            refs.update(_review(review,known,("rationale",)))
            if review.get("baseline_result_id")!=prior["id"]:
                raise ValueError("Hotspot coverage review must identify the selected baseline.")
            ranked = sorted(metrics,key=lambda m:(-convert(m["value"],m["unit"],"kWh")["value"],m["id"]))
            ranking = []
            for rank,metric in enumerate(ranked,1):
                amount = convert(metric["value"],metric["unit"],"kWh")["value"]
                emit(f"rank-{rank}-energy",f"Rank {rank}: {metric['name']}",amount,"kWh",[metric["id"]],"Selected nonoverlapping baseline component converted to kWh")
                share = None
                if total>0:
                    with localcontext() as context:
                        context.prec = 34
                        share = amount/total*100
                    emit(f"rank-{rank}-share",f"Rank {rank}: selected baseline share",share,"%",[metric["id"],prior["metrics"][0]["id"]],"Component energy / selected baseline energy * 100")
                ranking.append({"metric_id":metric["id"],"rank":rank,"kWh":serialize(amount),"share_percent":serialize(share) if share is not None else None})
            if total==0:
                gap("PERCENTAGE_DENOMINATOR_REQUIRED","Zero baseline supports zero energy quantities, not shares.")
            if prior["status"]=="partial":
                gap("PARTIAL_ENERGY_BASELINE","Selected baseline is partial; hotspot shares describe supported selected coverage only.")
            result["diagnostics"].append({"code":"ENERGY_HOTSPOTS","message":json.dumps({"baseline_result_id":prior["id"],"ranking":ranking,
                "denominator_kWh":serialize(total),"limits":"Shares of selected energy coverage; not efficiency or emissions impact."},sort_keys=True)})
        result["diagnostics"].append({"code":"ENERGY_INPUTS","message":json.dumps(parameters,sort_keys=True)})
    except (ValueError,KeyError,TypeError) as error:
        result["metrics"] = []
        gap("ENERGY_DATA_REQUIRED",str(error))
    result["evidence_ids"] = sorted(refs)
    result["status"] = "blocked" if not result["metrics"] else ("partial" if result["data_gaps"] else "completed")
    for review in result["review_requirements"]:
        if review["status"]=="open":
            result["review_states"].append(review["state"])
    if result["data_gaps"]:
        result["review_states"].append("EVIDENCE_INCOMPLETE")
        result["next_actions"] = list(dict.fromkeys(gap["remedy"] for gap in result["data_gaps"]))
    result["review_states"] = list(dict.fromkeys(result["review_states"]))
    proposal = propose(state,result,"Compute evidenced delivered-energy analysis without verification or state writes")
    if result["metrics"]:
        proposal["state"]["energy"].append(ident)
        validate_state(proposal["state"])
    return {"result":result,"proposal":proposal}
