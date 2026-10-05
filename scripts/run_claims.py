"""Emit a checked evidence review candidate without publishing or changing claims."""
import argparse
import json
from pathlib import Path
import sys
from .contract_validation import validate_shape
from .claims_review import assess_claim


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('request',type=Path);args=parser.parse_args()
    try:
        r=json.loads(args.request.read_text(encoding='utf-8'));validate_shape('input.schema.json',r)
        if r['skill']!='assess-claim-evidence':raise ValueError('Unsupported claims operation.')
        print(json.dumps(assess_claim(r['state'],r['parameters']),indent=2,allow_nan=False));return 0
    except Exception as error:
        print(json.dumps({'error':'INVALID_REQUEST','kind':type(error).__name__}));return 2


if __name__=='__main__':sys.exit(main())
