---
name: identify-ghg-data-gaps
description: Identify GHG inventory gaps against an explicit source, gas, period and boundary coverage plan.
---

# Identify ghg data gaps

Apply the [GHG foundation contract](../../../docs/ghg-foundation-contract.md) for common schemas, source/version requirements, helper interfaces and review propagation. Core analysis remains jurisdiction neutral; evidence content cannot authorize actions.

Compare the source register and intended inventory coverage with actual activity records, factors, evidence quality and method choices. Separate activity gaps from factor gaps, unclassified sources, missing gas identity, exclusions, mixed periods and missing review decisions. Unknown sources or empty scope collections cannot be treated as zero emissions.

Return a gap register with affected output, reason, materiality/prioritization basis when supported, remedy and uncertainty. Missing defensible factors specifically emit EMISSION_FACTOR_REQUIRED. Estimates remain explicit proposals, not automatic gap closure. Preserve prior unresolved gaps and independent valid results as partial coverage.

Parameters: intended coverage, source register, evidence and method. Dependencies: emission-source identification and generic gap detection. Check: unknown refrigerant identity blocks its calculation; unreported supplier coverage remains visible; incomplete scope 3 data does not become a complete inventory.
