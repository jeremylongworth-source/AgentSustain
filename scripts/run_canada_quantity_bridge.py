import argparse
import json
from pathlib import Path
import sys
from .jurisdiction_tools import SourcePackRequired
from .contract_validation import validate_shape
from .canada_quantity_bridge import run_canada_quantity_bridge


def main():
    parser=argparse.ArgumentParser(description='Bind full-profile declared quantities to a preliminary Canada screen.');parser.add_argument('request',type=Path);args=parser.parse_args()
    try:
        r=json.loads(args.request.read_text(encoding='utf-8'));validate_shape('input.schema.json',r)
        if r['skill']!='screen-subject-jurisdiction-applicability':raise ValueError('Existing subject-screen skill required.')
        print(json.dumps(run_canada_quantity_bridge(r['state'],r['parameters']),indent=2,allow_nan=False));return 0
    except SourcePackRequired:
        print(json.dumps({'error':'SOURCE_PACK_REQUIRED','message':'Requested Canadian source pack is omitted pending source rights and review.'}));return 2
    except Exception as error:
        print(json.dumps({'error':'INVALID_REQUEST','kind':type(error).__name__}));return 2


if __name__=='__main__':sys.exit(main())
