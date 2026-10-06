"""Emit a source-reproduced fuel CO2e proposal without modifying inputs."""
import argparse
import json
from pathlib import Path
import sys
from .contract_validation import validate_shape
from .fuel_co2e import run_fuel_co2e


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('request',type=Path);args=parser.parse_args()
    try:
        r=json.loads(args.request.read_text(encoding='utf-8'));validate_shape('input.schema.json',r)
        if r['skill']!='calculate-co2e':raise ValueError('Existing CO2e skill required.')
        print(json.dumps(run_fuel_co2e(r['state'],r['parameters']),indent=2,allow_nan=False));return 0
    except Exception as error:
        print(json.dumps({'error':'INVALID_REQUEST','kind':type(error).__name__}));return 2


if __name__=='__main__':sys.exit(main())
