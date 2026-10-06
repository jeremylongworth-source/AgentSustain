import argparse
import json
from pathlib import Path
import sys
from .contract_validation import validate_shape
from .reporting_workflow import run_reporting_workflow


def main():
    parser = argparse.ArgumentParser(description='Emit a conditional reporting specialist candidate.'); parser.add_argument('request', type=Path); args = parser.parse_args()
    try:
        r = json.loads(args.request.read_text(encoding='utf-8')); validate_shape('input.schema.json', r)
        if r['skill'] != 'sustainability-reporting': raise ValueError('Unsupported reporting specialist.')
        print(json.dumps(run_reporting_workflow(r['state'], r['parameters']), indent=2, allow_nan=False)); return 0
    except Exception as error:
        print(json.dumps({'error': 'INVALID_REQUEST', 'kind': type(error).__name__})); return 2


if __name__ == '__main__': sys.exit(main())
