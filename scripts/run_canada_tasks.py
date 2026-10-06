import argparse
import json
from pathlib import Path
import sys
from .contract_validation import validate_shape
from .canada_task_workflow import run_canada_tasks


def main():
    parser=argparse.ArgumentParser(description='Emit conditional source-bound Canada task candidates.');parser.add_argument('request',type=Path);args=parser.parse_args()
    try:
        r=json.loads(args.request.read_text(encoding='utf-8'));validate_shape('input.schema.json',r)
        if r['skill']!='prepare-jurisdiction-task-register':raise ValueError('Existing task-register skill required.')
        print(json.dumps(run_canada_tasks(r['state'],r['parameters']),indent=2,allow_nan=False));return 0
    except Exception as error:
        print(json.dumps({'error':'INVALID_REQUEST','kind':type(error).__name__}));return 2


if __name__=='__main__':sys.exit(main())
