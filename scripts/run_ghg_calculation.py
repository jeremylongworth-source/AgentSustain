"""Emit a CO2e result/proposal from a common input request; never write state."""

import argparse
import json
from pathlib import Path
import sys

from .contract_validation import validate_shape
from .ghg_foundation import calculate_result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    args = parser.parse_args()
    try:
        with args.request.open(encoding="utf-8") as source:
            request = json.load(source)
        validate_shape("input.schema.json", request)
        if request["skill"] != "calculate-co2e":
            raise ValueError("This entrypoint runs calculate-co2e only")
        parameters = request["parameters"]
        required = {"activity_id", "factor_id", "policy", "result_id"}
        if not required <= set(parameters) or set(parameters) - required - {"fixture_mode"}:
            raise ValueError("Invalid calculation parameters")
        result = calculate_result(request["state"], parameters["activity_id"], parameters["factor_id"],
                                  parameters["policy"], parameters["result_id"], parameters.get("fixture_mode", False))
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except Exception as error:
        # Do not expose raw private inputs, file locators or tracebacks.
        print(json.dumps({"error": "INVALID_REQUEST", "kind": type(error).__name__}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
