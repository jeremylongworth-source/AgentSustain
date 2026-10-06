"""Emit a bounded fuel-energy proposal without modifying request or state files."""
import argparse
import json
from pathlib import Path
import sys
from .contract_validation import validate_shape
from .fuel_energy import run_fuel_energy


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('request',type=Path);args=parser.parse_args()
    try:
        r=json.loads(args.request.read_text(encoding='utf-8'));validate_shape('input.schema.json',r)
        if r['skill']!='build-energy-baseline':raise ValueError('Existing energy baseline skill required.')
        print(json.dumps(run_fuel_energy(r['state'],r['parameters']),indent=2,allow_nan=False));return 0
    except Exception as error:
        print(json.dumps({'error':'INVALID_REQUEST','kind':type(error).__name__}));return 2


if __name__=='__main__':sys.exit(main())
