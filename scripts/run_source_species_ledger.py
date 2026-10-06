import argparse
import json
from pathlib import Path
import sys
from .contract_validation import validate_shape
from .source_species_ledger import build_source_species_ledger


def main():
    parser=argparse.ArgumentParser(description='Emit a qualified source/species treatment ledger.');parser.add_argument('request',type=Path);args=parser.parse_args()
    try:
        r=json.loads(args.request.read_text(encoding='utf-8'));validate_shape('input.schema.json',r)
        if r['skill']!='build-facility-gas-ledger':raise ValueError('Existing gas-ledger skill required.')
        print(json.dumps(build_source_species_ledger(r['state'],r['parameters']),indent=2,allow_nan=False));return 0
    except Exception as error:
        print(json.dumps({'error':'INVALID_REQUEST','kind':type(error).__name__}));return 2


if __name__=='__main__':sys.exit(main())
