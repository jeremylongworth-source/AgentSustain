"""Read a selected workspace CSV and emit a candidate, without source/state writes."""
import argparse
import json
from pathlib import Path
import sys
from .contract_validation import validate_shape
from .business_ingestion import ingest_business_csv


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('request', type=Path); args = parser.parse_args()
    try:
        request = json.loads(args.request.read_text(encoding='utf-8')); validate_shape('input.schema.json', request)
        if request['skill'] != 'ingest-business-records': raise ValueError('Unsupported ingestion operation.')
        print(json.dumps(ingest_business_csv(request['state'], request['parameters']), indent=2, allow_nan=False)); return 0
    except Exception as error:
        print(json.dumps({'error': 'INVALID_REQUEST', 'kind': type(error).__name__})); return 2


if __name__ == '__main__': sys.exit(main())
