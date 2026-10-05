"""Emit a climate-screening result and checked append-only state proposal."""
import argparse
import json
from pathlib import Path
import sys

from .contract_validation import validate_shape
from .climate_tools import run_climate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    args = parser.parse_args()
    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
        validate_shape("input.schema.json", request)
        output = run_climate(request["state"], request["skill"], request["parameters"])
        print(json.dumps(output, indent=2, allow_nan=False))
        return 0
    except Exception as error:
        print(json.dumps({"error": "INVALID_REQUEST", "kind": type(error).__name__}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
