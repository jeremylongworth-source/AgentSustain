"""Emit a checked evidence review candidate without publishing or changing claims."""
import argparse
import json
from pathlib import Path
import sys
from .contract_validation import validate_shape
from .claims_review import assess_claim
from .claim_material import assess_bound_claim
from .claim_inventory import assess_inventory_claim
from .claim_comparison import assess_comparison_claim
from .claim_future_goal import assess_future_goal_claim


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('request',type=Path);args=parser.parse_args()
    try:
        r=json.loads(args.request.read_text(encoding='utf-8'));validate_shape('input.schema.json',r)
        operations={'assess-claim-evidence':assess_claim,'assess-bound-claim-evidence':assess_bound_claim,
                    'assess-inventory-claim-evidence':assess_inventory_claim,'assess-comparison-claim-evidence':assess_comparison_claim,
                    'assess-future-goal-claim-evidence':assess_future_goal_claim}
        if r['skill'] not in operations:raise ValueError('Unsupported claims operation.')
        print(json.dumps(operations[r['skill']](r['state'],r['parameters']),indent=2,allow_nan=False));return 0
    except Exception as error:
        print(json.dumps({'error':'INVALID_REQUEST','kind':type(error).__name__}));return 2


if __name__=='__main__':sys.exit(main())
