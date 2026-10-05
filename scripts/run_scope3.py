"""Emit scope 3, selected inventory and inventory analysis proposals; no writes."""
import argparse
import json
from pathlib import Path
import sys

from .contract_validation import validate_shape
from .scope3_accounting import classify_scope3, calculate_category
from .ghg_inventory import build_inventory
from .inventory_analysis import compare_inventories, identify_hotspots


OPERATIONS = {
    "classify-scope-3-emissions": (classify_scope3, {"sources", "result_id"}),
    "calculate-scope-3-category": (calculate_category, {"category", "sources", "components", "coverage_review", "result_id"}),
    "build-ghg-inventory": (build_inventory, {"scope1_result_id", "scope2_result_id", "scope3_result_ids", "category_screening", "coverage_review", "result_id"}),
    "compare-ghg-inventories": (compare_inventories, {"prior_state", "prior_inventory_id", "current_inventory_id", "comparability_review", "result_id"}),
    "identify-emission-hotspots": (identify_hotspots, {"inventory_id", "level", "coverage_review", "result_id"}),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    args = parser.parse_args()
    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
        validate_shape("input.schema.json", request)
        operation, required = OPERATIONS[request["skill"]]
        params = request["parameters"]
        if not required <= set(params) or set(params) - required - {"fixture_mode"}:
            raise ValueError("Invalid scope 3 operation parameters")
        output = operation(request["state"], **params)
        print(json.dumps(output, indent=2, allow_nan=False))
        return 0
    except Exception as error:
        print(json.dumps({"error":"INVALID_REQUEST","kind":type(error).__name__}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
