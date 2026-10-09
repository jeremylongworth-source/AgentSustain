import argparse
import json
from pathlib import Path
import sys
from .contract_validation import validate_shape
from .canada_ghgrp import screen_canada_ghgrp
from .jurisdiction_tools import SourcePackRequired


def main():
    parser=argparse.ArgumentParser(description='Emit a draft Canada GHGRP subject screen.');parser.add_argument('request',type=Path);args=parser.parse_args()
    try:
        request=json.loads(args.request.read_text(encoding='utf-8'));validate_shape('input.schema.json',request)
        if request['skill']!='screen-subject-jurisdiction-applicability':raise ValueError('Existing subject-screen skill required.')
        print(json.dumps(screen_canada_ghgrp(request['state'],request['parameters']),indent=2,allow_nan=False));return 0
    except SourcePackRequired:
        print(json.dumps({'error':'SOURCE_PACK_REQUIRED','message':'Requested Canadian source pack is omitted pending source rights and review.'}));return 2
    except Exception as error:
        print(json.dumps({'error':'INVALID_REQUEST','kind':type(error).__name__}));return 2


if __name__=='__main__':sys.exit(main())
