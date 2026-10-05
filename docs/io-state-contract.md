# SUS-04: Common input/output and shared state

Status: proposed. Schemas: schemas/common.schema.json, evidence.schema.json, emission-factor.schema.json, input.schema.json, result.schema.json, state.schema.json.

## Inputs

Each skill takes `contract_version`, `skill`, a validated `state`, and explicit `parameters` defined by that skill. The input schema validates the envelope; the consuming skill must additionally validate its parameter schema and semantic state constraints. Require an organization, reporting period, boundary, requested method, and necessary evidence before calculation. Missing task parameters return invalid_input or blocked, with specific gaps. Raw evidence collection may start from an incomplete state; incompleteness must be carried explicitly.

## Outputs

The result envelope contains result ID, skill name, contract version, execution status, review states, review requirements, metrics, evidence IDs, assumptions, data gaps, diagnostics and next actions. Metrics each include value, unit, period, boundary, evidence IDs, method, uncertainty, assumption and calculation. A blocked or invalid_input result has no calculated metrics. A partial result may expose only valid calculations and must describe omitted coverage. EMISSION_FACTOR_REQUIRED requires blocked/partial status, EVIDENCE_INCOMPLETE, and a specific factor gap.

Value null is unknown; 0 is an observed or calculated zero. Result arrays empty mean no results supplied, not zero environmental impact. Scope 2 location-based and market-based results have distinct IDs and methods and must never be summed as one scope 2 total. Scope 3 results identify category and coverage. Aggregation must state completeness; exclusions remain visible.

## State

State includes organization, facilities, jurisdictions, reporting period, organizational boundary, energy, water, materials, waste, GHG (scope 1/2/3), suppliers, targets, risks, opportunities, projects, frameworks, evidence, emission factors, assumptions, data gaps and review requirements. Environmental collections hold result IDs; other domain objects hold IDs, evidence references and structured attributes. Shared state is a lineage container, not a warehouse of unreferenced numeric values.

All evidence/result/facility/entity IDs are unique in their collection. References must resolve, and facility membership must match the boundary. Period start must precede or equal end. Review requirements identify required state, reason, scope, reviewer role, open/resolved status and explicit resolution record. Compositions retain open obligations. The schema expresses shape; tests/contract_checks.py performs documented cross-reference and temporal checks. Skill-specific arithmetic, dimensional fitness, methodology applicability and review propagation will require domain tests.

## Evolution

State revision is a nonnegative integer and contract version is exact. Future updates use optimistic revision checks. A change in reporting period or organizational boundary creates a new baseline/context or explicitly documented restatement; historical results are not relabeled. Schema upgrades need a migration fixture with preserved lineage and outstanding review states.
