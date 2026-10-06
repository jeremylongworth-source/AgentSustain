import argparse
import json
from pathlib import Path
import sys
from .contract_validation import validate_shape
from .investment_workflow import run_investment_workflow


def main():
    parser = argparse.ArgumentParser(description='Emit a conditional investment specialist candidate.'); parser.add_argument('request', type=Path); args = parser.parse_args()
    try:
        r = json.loads(args.request.read_text(encoding='utf-8')); validate_shape('input.schema.json', r)
        if r['skill'] != 'sustainability-business-case': raise ValueError('Unsupported investment specialist.')
        print(json.dumps(run_investment_workflow(r['state'], r['parameters']), indent=2, allow_nan=False)); return 0
    except Exception as error:
        print(json.dumps({'error': 'INVALID_REQUEST', 'kind': type(error).__name__})); return 2


if __name__ == '__main__': sys.exit(main())
