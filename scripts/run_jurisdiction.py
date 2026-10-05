"""Emit evidence-linked preliminary jurisdiction screening without modifying inputs."""
import argparse
import json
from pathlib import Path
import sys

from .contract_validation import validate_shape
from .jurisdiction_tools import screen_jurisdiction
from .jurisdiction_subjects import screen_subject_jurisdiction


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request', type=Path)
    args = parser.parse_args()
    try:
        request = json.loads(args.request.read_text(encoding='utf-8'))
        validate_shape('input.schema.json', request)
        operations = {'screen-jurisdiction-applicability': screen_jurisdiction,
                      'screen-subject-jurisdiction-applicability': screen_subject_jurisdiction}
        if request['skill'] not in operations:
            raise ValueError('Unsupported jurisdiction operation')
        print(json.dumps(operations[request['skill']](request['state'], request['parameters']), indent=2, allow_nan=False))
        return 0
    except Exception as error:
        print(json.dumps({'error': 'INVALID_REQUEST', 'kind': type(error).__name__}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
