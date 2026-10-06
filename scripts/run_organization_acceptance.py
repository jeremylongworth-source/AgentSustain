"""Run a read-only author-led fictional organization acceptance scenario."""
import argparse
import json
from pathlib import Path
import sys
from .organization_acceptance import evaluate_organization_acceptance


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case',type=Path);parser.add_argument('oracle',type=Path);args=parser.parse_args()
    try:
        if any(p.stat().st_size>1048576 for p in (args.case,args.oracle)):raise ValueError('Bounded case and oracle files required.')
        output=evaluate_organization_acceptance(json.loads(args.case.read_text(encoding='utf-8')),json.loads(args.oracle.read_text(encoding='utf-8')))
        print(json.dumps(output,indent=2,allow_nan=False));return 0 if output['scenario_status']=='passed' else 1
    except Exception as error:
        print(json.dumps({'error':'INVALID_ACCEPTANCE_INPUT','kind':type(error).__name__}));return 2


if __name__=='__main__':sys.exit(main())
