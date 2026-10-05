"""Emit evidenced source classification from a common request; no state writes."""
import argparse
import json
from pathlib import Path
import sys

from .contract_validation import validate_shape
from .scope_classification import classify_sources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    args = parser.parse_args()
    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
        validate_shape("input.schema.json", request)
        params = request["parameters"]
        required = {"sources", "result_id"}
        if not required <= set(params) or set(params) - required - {"fixture_mode"}:
            raise ValueError("Invalid classification parameters")
        output = classify_sources(request["state"], request["skill"], **params)
        print(json.dumps(output, indent=2, allow_nan=False))
        return 0
    except Exception as error:
        print(json.dumps({"error": "INVALID_REQUEST", "kind": type(error).__name__}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
