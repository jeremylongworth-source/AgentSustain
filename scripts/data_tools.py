"""Portable deterministic data primitives for SUS-05, not emission calculators."""

import argparse
import calendar
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
import json
import math
from pathlib import Path
import re
import sys


UNIT_SOURCE = "https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b8"
UNITS = {
    "g": ("mass", "0.001"), "kg": ("mass", "1"), "t": ("mass", "1000"),
    "L": ("volume", "0.001"), "m3": ("volume", "1"),
    "J": ("energy", "1"), "MJ": ("energy", "1000000"), "GJ": ("energy", "1000000000"),
    "Wh": ("energy", "3600"), "kWh": ("energy", "3600000"), "MWh": ("energy", "3600000000"),
    "count": ("count", "1"), "kg CO2e": ("co2e", "1"), "t CO2e": ("co2e", "1000"),
}


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise ValueError("A finite quantity is required; unknown is not zero.")
    try:
        result = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError("Invalid numeric quantity.") from error
    if not result.is_finite():
        raise ValueError("Nonfinite quantity.")
    return result


def convert(value, source_unit, target_unit):
    if source_unit not in UNITS or target_unit not in UNITS:
        raise ValueError("Unsupported or ambiguous unit.")
    kind, source_factor = UNITS[source_unit]
    target_kind, target_factor = UNITS[target_unit]
    if kind != target_kind:
        raise ValueError("Incompatible dimensions; density, heating value and exchange rates are not assumed.")
    with localcontext() as context:
        context.prec = 34
        factor = Decimal(source_factor) / Decimal(target_factor)
        return {"value": number(value) * factor, "unit": target_unit, "factor": factor, "source": UNIT_SOURCE}


def period(value):
    if isinstance(value, str) and re.fullmatch(r"\d{4}", value):
        year = int(value)
        return {"start": date(year, 1, 1).isoformat(), "end": date(year, 12, 31).isoformat()}
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}", value):
        year, month = map(int, value.split("-"))
        return {"start": date(year, month, 1).isoformat(), "end": date(year, month, calendar.monthrange(year, month)[1]).isoformat()}
    if isinstance(value, dict) and set(value) == {"start", "end"}:
        if not all(isinstance(item, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", item) for item in value.values()):
            raise ValueError("Use YYYY-MM-DD dates.")
        start, end = date.fromisoformat(value["start"]), date.fromisoformat(value["end"])
        if start > end:
            raise ValueError("Reporting period is reversed.")
        return {"start": start.isoformat(), "end": end.isoformat()}
    raise ValueError("Use a calendar year, YYYY-MM month or explicit ISO start/end dates; fiscal labels need dates.")


def comparable(items, same_period=True):
    if not items:
        raise ValueError("No metrics supplied.")
    for item in items:
        number(item["value"])
        period(item["period"])
        if item["boundary_id"] != items[0]["boundary_id"]:
            raise ValueError("Input boundaries differ.")
        if same_period and item["period"] != items[0]["period"]:
            raise ValueError("Input reporting periods differ.")


def baseline(metrics, target_unit, nonoverlap_confirmed=False):
    comparable(metrics)
    if nonoverlap_confirmed is not True:
        raise ValueError("Confirm mutually exclusive quantity coverage before aggregation.")
    refs = [ident for item in metrics for ident in item["evidence_ids"]]
    if any(not item["evidence_ids"] for item in metrics) or len(refs) != len(set(refs)):
        raise ValueError("Shared or missing evidence requires reconciliation before summing.")
    converted = [convert(item["value"], item["unit"], target_unit) for item in metrics]
    with localcontext() as context:
        context.prec = 34
        return {"value": sum((item["value"] for item in converted), Decimal(0)), "unit": target_unit,
                "formula": "sum(converted inputs)", "conversions": converted}


def kpi(numerator, denominator, operation):
    comparable([numerator, denominator])
    bottom = number(denominator["value"])
    if bottom <= 0:
        raise ValueError("KPI denominator must be positive.")
    with localcontext() as context:
        context.prec = 34
        if operation == "percent":
            conversion = convert(numerator["value"], numerator["unit"], denominator["unit"])
            return {"value": conversion["value"] / bottom * 100, "unit": "%", "formula": "converted numerator / denominator * 100", "conversion": conversion}
        if operation == "ratio":
            return {"value": number(numerator["value"]) / bottom, "unit": f"{numerator['unit']}/{denominator['unit']}", "formula": "numerator / denominator"}
    raise ValueError("Declare ratio or percent operation.")


def compare(prior, current, comparability_confirmed=False):
    comparable([prior, current], same_period=False)
    if prior["name"] != current["name"]:
        raise ValueError("Metric definitions differ.")
    before_period, after_period = prior["period"], current["period"]
    def days(value):
        return (date.fromisoformat(value["end"]) - date.fromisoformat(value["start"])).days + 1
    if before_period["end"] >= after_period["start"] or days(before_period) != days(after_period):
        raise ValueError("Periods must be sequential, nonoverlapping and equal-duration; no silent annualization.")
    if comparability_confirmed is not True:
        raise ValueError("Confirm comparable definitions, boundary and operating context.")
    before = number(prior["value"])
    converted = convert(current["value"], current["unit"], prior["unit"])
    with localcontext() as context:
        context.prec = 34
        delta = converted["value"] - before
        return {"absolute_change": delta, "unit": prior["unit"],
                "percentage_change": delta / before * 100 if before > 0 else None,
                "percentage_gap": None if before > 0 else "Prior value is zero or negative; percentage change not interpreted.",
                "formula": "current - prior; (current - prior) / prior * 100", "conversion": converted}


def serialize(value):
    if isinstance(value, Decimal):
        result = float(value)
        if not math.isfinite(result) or (value != 0 and result == 0):
            raise ValueError("Quantity outside supported JSON number range.")
        return result
    raise TypeError("Unsupported output type")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    args = parser.parse_args()
    try:
        with args.request.open(encoding="utf-8") as source:
            request = json.load(source)
        operation = request["operation"]
        if operation == "convert":
            output = convert(request["value"], request["source_unit"], request["target_unit"])
        elif operation == "period":
            output = period(request["period"])
        elif operation == "baseline":
            output = baseline(request["metrics"], request["target_unit"], request.get("nonoverlap_confirmed", False))
        elif operation == "kpi":
            output = kpi(request["numerator"], request["denominator"], request["kpi_operation"])
        elif operation == "compare":
            output = compare(request["prior"], request["current"], request.get("comparability_confirmed", False))
        else:
            raise ValueError("Unsupported operation.")
        print(json.dumps(output, indent=2, default=serialize, allow_nan=False))
        return 0
    except (ValueError, TypeError, KeyError, OSError, OverflowError) as error:
        # Never print input records, source content or private file locators.
        print(json.dumps({"error": "INVALID_INPUT", "reason": type(error).__name__}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
