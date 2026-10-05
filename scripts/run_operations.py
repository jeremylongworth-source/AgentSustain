"""Return a sustainable-operations analytical batch proposal without state writes."""
import argparse
import json
from pathlib import Path
import sys
from .contract_validation import validate_shape
from .operations_tools import run_operations


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("request",type=Path);args=parser.parse_args()
    try:
        request=json.loads(args.request.read_text(encoding="utf-8"));validate_shape("input.schema.json",request)
        if request["skill"] != "sustainable-operations":raise ValueError("Supported operations skillset required.")
        print(json.dumps(run_operations(request["state"],request["parameters"]),indent=2,allow_nan=False));return 0
    except Exception as error:
        print(json.dumps({"error":"INVALID_REQUEST","kind":type(error).__name__}));return 2


if __name__=="__main__":sys.exit(main())
