"""Sourced-factor eligibility and CO2e arithmetic; no built-in factors or GWPs."""

import copy
from decimal import localcontext

from jsonschema import ValidationError

from .contract_validation import validate_shape, validate_state
from .data_tools import convert, number, serialize
from .state_proposal import propose


def factor_issues(factor, activity, policy, fixture_mode=False):
    """Check supplied metadata and applicability record, not source authenticity."""
    issues = []
    if not isinstance(fixture_mode, bool):
        raise ValueError("Fixture mode must be an explicit boolean")
    if factor is None:
        return ["No sourced emission factor supplied."]
    try:
        validate_shape("emission-factor.schema.json", factor)
    except ValidationError:
        return ["Emission-factor metadata is incomplete or invalid."]
    if factor["status"] != "reviewed" and not (fixture_mode and factor["status"] == "synthetic"):
        issues.append("Factor is not reviewed for real use; synthetic factors require explicit fixture mode.")
    if not fixture_mode and (factor["source"]["locator"].startswith("fixture:") or factor["method"]["source"].startswith("fixture:")):
        issues.append("Fictional source locators cannot support a real inventory.")
    if factor["geography"] != policy.get("geography"):
        issues.append("Factor geography does not match the explicitly approved geographic basis.")
    vintages = policy.get("acceptable_vintages")
    if not isinstance(vintages, list) or not vintages or any(isinstance(year, bool) or not isinstance(year, int) for year in vintages) or factor["vintage_year"] not in vintages:
        issues.append("Factor vintage is not in the declared applicability policy.")
    if factor["method"] != policy.get("method"):
        issues.append("Factor methodology/version/source differs from the selected method.")
    if factor["gwp_basis"] != policy.get("gwp_basis"):
        issues.append("Factor GWP basis differs from the declared inventory basis.")
    review = policy.get("source_review", {})
    if not isinstance(review, dict):
        review = {}
    checks = {
        "factor_id": factor["id"], "activity_id": activity.get("id"),
        "source_locator": factor["source"]["locator"], "source_version": factor["source"]["version"],
        "confirmed_value": factor["value"], "confirmed_unit": factor["unit"],
        "evidence_ids": factor["evidence_ids"],
    }
    if any(review.get(key) != value for key, value in checks.items()):
        issues.append("Source review does not confirm this factor value, units, version, activity and evidence.")
    try:
        number(review.get("confirmed_value"))
    except ValueError:
        issues.append("Source review needs a finite numeric confirmed factor value.")
    if any(not isinstance(review.get(key), str) or not review[key].strip() for key in ("reviewer", "coverage", "rationale")):
        issues.append("Source coverage and applicability rationale require an explicit reviewer record.")
    try:
        if number(factor["value"]) < 0:
            raise ValueError("Negative factor")
        if factor["unit"].count("/") != 1:
            raise ValueError("Unsupported compound factor unit")
        numerator, denominator = [part.strip() for part in factor["unit"].split("/")]
        if numerator not in ("kg CO2e", "t CO2e"):
            raise ValueError("Factor must already express CO2e; no implicit GWP conversion")
        convert(activity["value"], activity["unit"], denominator)
        convert(1, numerator, "kg CO2e")
    except (ValueError, KeyError, TypeError):
        issues.append("Factor/activity units or values are incompatible; no implicit gas, GWP or heating-value conversion.")
    return issues


def calculate_result(state, activity_id, factor_id, policy, result_id, fixture_mode=False):
    """Emit a common result and append-only state proposal from resolved inputs."""
    validate_state(state)
    if not isinstance(result_id, str) or not result_id.strip():
        raise ValueError("Supply a nonempty result ID")
    metrics = {metric["id"]: metric for result in state["results"] for metric in result["metrics"]}
    if activity_id not in metrics:
        raise ValueError("Activity metric does not resolve")
    activity = metrics[activity_id]
    factor = next((item for item in state["emission_factors"] if item["id"] == factor_id), None)
    if not isinstance(policy, dict):
        raise ValueError("Factor applicability policy must be an object")
    result = {
        "id": result_id, "skill": "calculate-co2e", "contract_version": "0.1.0", "status": "completed",
        "review_states": ["ANALYTICAL"], "review_requirements": copy.deepcopy(state["review_requirements"]),
        "metrics": [], "evidence_ids": sorted(set(activity["evidence_ids"] + (factor["evidence_ids"] if factor else []))),
        "assumptions": list(state["assumptions"]), "data_gaps": copy.deepcopy(state["data_gaps"]),
        "diagnostics": [], "next_actions": [],
    }
    for review in result["review_requirements"]:
        if review["status"] == "open":
            result["review_states"].append(review["state"])
    activity_errors = []
    if activity["period"] != state["reporting_period"]:
        activity_errors.append("Activity period differs from the reporting context.")
    if activity["value"] is None or number(activity["value"]) < 0:
        activity_errors.append("Activity is unknown or negative; no netting or imputation is supported.")
    issues = factor_issues(factor, activity, policy, fixture_mode) if not activity_errors else []
    if activity_errors or issues:
        result["status"] = "blocked"
        code = "ACTIVITY_DATA_REQUIRED" if activity_errors else "EMISSION_FACTOR_REQUIRED"
        message = " ".join(activity_errors or issues)
        gap_id = result_id + "-gap"
        if gap_id in {gap["id"] for gap in result["data_gaps"]}:
            raise ValueError("Generated gap ID conflicts with existing state")
        result["data_gaps"].append({"id": gap_id, "field": "activity" if activity_errors else "emission_factor",
                                    "reason": message, "impact": "CO2e calculation is unavailable.",
                                    "remedy": "Supply and validate compatible activity, factor source and applicability evidence."})
        result["diagnostics"].append({"code": code, "message": message})
    else:
        numerator, denominator = [part.strip() for part in factor["unit"].split("/")]
        activity_conversion = convert(activity["value"], activity["unit"], denominator)
        with localcontext() as context:
            context.prec = 34
            emissions = activity_conversion["value"] * number(factor["value"])
            output = convert(emissions, numerator, "kg CO2e")
        assumptions = [activity["assumption"]] if activity["assumption"] else []
        if fixture_mode:
            assumptions.append("Synthetic fixture calculation only; not an emission factor or inventory for real use.")
            result["diagnostics"].append({"code": "SYNTHETIC_FIXTURE", "message": assumptions[-1]})
        result["assumptions"] = list(dict.fromkeys(result["assumptions"] + assumptions))
        result["metrics"] = [{
            "id": result_id + "-metric", "name": "Calculated CO2e", "value": serialize(output["value"]), "unit": "kg CO2e",
            "period": copy.deepcopy(activity["period"]), "boundary_id": activity["boundary_id"],
            "evidence_ids": result["evidence_ids"], "method": copy.deepcopy(factor["method"]),
            "assumption": "; ".join(assumptions) if assumptions else None,
            "uncertainty": {"kind": "unquantified", "description": "Input uncertainty remains in source evidence; combined uncertainty is not quantified.", "value": None, "unit": None},
            "calculation": {"formula": f"activity {activity_id} * conversion {activity_conversion['factor']} * factor {factor['id']} ({factor['value']} {factor['unit']}) * output conversion {output['factor']}",
                            "inputs": list(dict.fromkeys([activity_id] + factor["evidence_ids"])),
                            "conversions": [f"{activity['unit']} -> {denominator}, factor {activity_conversion['factor']}; {activity_conversion['source']}",
                                            f"{numerator} -> kg CO2e, factor {output['factor']}; {output['source']}"],
                            "rounding": "34-digit Decimal arithmetic; JSON number serialization, no display rounding"},
        }]
        # A joined metric assumption must also be traceable in the result ledger.
        if result["metrics"][0]["assumption"] and result["metrics"][0]["assumption"] not in result["assumptions"]:
            result["assumptions"].append(result["metrics"][0]["assumption"])
        result["diagnostics"].append({"code": "FACTOR_BASIS", "message": f"Applied {factor['id']} with declared geography, vintage, methodology, GWP basis and supplied source-review record; no source authentication or assurance performed."})
        if result["data_gaps"]:
            result["status"] = "partial"
    if result["data_gaps"]:
        result["review_states"].append("EVIDENCE_INCOMPLETE")
        result["next_actions"] = list(dict.fromkeys(gap["remedy"] for gap in result["data_gaps"]))
    result["review_states"] = list(dict.fromkeys(result["review_states"]))
    proposal = propose(state, result, "Calculate or block CO2e using resolved factor and activity evidence")
    return {"result": result, "proposal": proposal}
