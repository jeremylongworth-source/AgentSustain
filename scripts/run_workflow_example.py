"""Run a supplied fictional workflow bundle without an answer key or state writes."""
import argparse
import json
from pathlib import Path
import sys

from .workflow_example import run_workflow_example


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--omit-factor', action='append', default=[], metavar='FACTOR_ID')
    args = parser.parse_args()
    try:
        # Bound the bytes actually read as well as the file's reported size.
        with args.bundle.open('rb') as source:
            raw = source.read(1048577)
        if len(raw) > 1048576:
            raise ValueError('Bounded workflow example file required')
        bundle = json.loads(raw.decode('utf-8'))
        output = run_workflow_example(bundle, args.omit_factor)
        print(json.dumps(output, indent=2, allow_nan=False))
        return 0
    except Exception as error:
        print(json.dumps({'error': 'INVALID_WORKFLOW_EXAMPLE', 'kind': type(error).__name__}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
