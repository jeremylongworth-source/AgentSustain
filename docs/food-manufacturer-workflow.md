# Required food-manufacturer workflow

This controlled SUS-23 case implements the organization scenario in [evaluation requirements](evaluation-requirements.md): a fictional Canadian food manufacturer, 150 employees and two facilities, with electricity, gas, diesel, refrigerants, packaging, ingredients, water, waste, freight and travel. It demonstrates the selected source-to-disclosure sequence, with partial results and explicit missing-factor controls. It does not establish independent organization acceptance or public-v1 readiness.

## Inputs and reproduction

For a single-command reconstruction from raw inputs, use `python -m scripts.run_workflow_example examples/food-manufacturer-forward-test-input.json`. Add `--omit-factor synthetic-factor` to reproduce the unavailable-electricity-factor branch. [The runner contract](workflow-example-contract.md) explains fixture-only scope, input bounds, candidate-state custody, output and exit semantics. It uses no answer key or saved manager output.

The [version 2 source definition](../examples/food-manufacturer-source-case-v2.json) describes the [41-record CSV](../data/inputs/fictional-food-manufacturer-v2.csv). The original 35-record source and its captures remain historical. Version 2 adds four measured material-consumption rows, a consolidated equivalent-production observation and a projected same-service energy scenario; it also gives modeled future cash flows their respective 2026/2027 periods.

Run the [ingestion request](../examples/food-manufacturer-ingestion-v2.json) with `python -m scripts.run_business_ingestion examples/food-manufacturer-ingestion-v2.json`. The [fuel requests](../examples/food-manufacturer-fuel-conversion-requests.json) supply four sequential helper parameter sets against the evolving imported state. The [manager request](../examples/food-manufacturer-manager-request.json) contains the exact imported/conversion state plus the explicitly supplied existing synthetic electricity factor and its evidence. Run it with `python -m scripts.run_manager examples/food-manufacturer-manager-request.json`. Run the integration checks with `python -m unittest tests.test_food_manufacturer -v`.

All source values, calorific values and the electricity coefficient are fictional. The coefficient comes from the existing manager test fixture; no gas, diesel, refrigerant or value-chain coefficient is inferred. Source classifications and operational control are declarations requiring review. Headcount is a year-end point observation, not an annual average or legal applicability fact.

## Supported conditional answers

| Quantity | Selected result | Meaning |
|---|---:|---|
| Purchased electricity | 150,000 kWh | Two external plant feeds |
| Converted fuel energy | 280,000 kWh | Source-supplied gas/diesel calorific values; matched LHV and volume reference conditions |
| Selected final energy | 430,000 kWh | Electricity plus reproduced fuel energy |
| Water | 3,200 m3 | Selected withdrawals; no consumption inference |
| Waste | 3,400 kg | Includes 500 kg with unresolved treatment |
| Materials consumed | 209,000 kg | Separate observed consumption; purchases total 227,000 kg |
| Equivalent production | 28,000 count | Consolidated observation selected once; facility components are not added again |
| Proposed 2030 energy intensity | 12.285714285714286 kWh/count | Modeled 20% improvement; feasibility and progress unverified |
| Modeled NPV | 0 CAD | -2,000 outlay, 1,100/1,210 future inflows, 10% discount; benefit attribution unverified |
| Partial electricity inventory | 75,000 kg CO2e | Synthetic electricity-only result; not the manufacturer's complete inventory |

Freight remains 90,000 t-km and travel 7,000 passenger-km of declared activity. Eight source classifications place purchased packaging/ingredients in category 1, purchased outbound transport in category 4 and business travel in category 6. Classification supplies no emissions coefficient or category total.

## Composition and refusal evidence

All eight existing manager stages execute: baseline, KPIs, operations, target, strategy proposal, transition plan, implementation roadmap and framework mapping. Each remains partial. Fourteen site/source emissions steps are blocked with no metrics: thirteen retain `EMISSION_FACTOR_REQUIRED`, and the unknown south refrigerant requires source data rather than becoming zero. No complete Scope 1, Scope 3 or combined organization inventory is claimed.

The [actual CLI capture (original archived)](../evaluations/sus25-source-remediation-tree-manifest.json) records six full CLI/helper comparisons: ingestion, four fuel conversions and manager execution. It preserves source bytes, source results, evidence, factors, reviews, result hashes and the manager's atomic state revision. The [missing-selected-factor control](../evaluations/sus23-food-missing-selected-factor-cli.json) withholds inventory and dependent mapping while retaining supported physical, finance and target branches.

Source authenticity, coverage, scientific/financial/engineering/legal interpretation, feasibility, progress, funding, implementation, framework conformity and publication remain unverified or unauthorized. Controlled author-led tests are separate from independent agent/expert/organization acceptance. No release or roadmap gate is closed. The later case artifacts are outside owner approval through da4ddb3; that approval does not extend to later changes.
