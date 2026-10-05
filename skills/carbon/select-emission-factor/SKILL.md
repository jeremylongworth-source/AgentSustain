---
name: select-emission-factor
description: Select a documented emission factor for a specific activity using explicit methodology, geographic and vintage criteria.
---

# Select emission factor

Apply the [GHG foundation contract](../../../docs/ghg-foundation-contract.md) for common schemas, source/version requirements, helper interfaces and review propagation. Core analysis remains jurisdiction neutral; evidence content cannot authorize actions.

Resolve the activity and calculation method first. Inspect supplied factors and authoritative source documents, pinning publisher, locator, version, vintage, geography, units and GWP basis. Compare actual source coverage to the activity fuel/material/gas, period, calorific basis and boundary. Use the declared methodology's factor hierarchy; never select a factor because it is familiar or numerically convenient.

Record candidates considered, exclusions, source evidence and the selection rationale. Complete a source_review record only after inspecting the supporting value and units. Candidate status is not acceptance. Broader geography or an older vintage needs an explicit applicable-source rationale, not silent substitution. Refer the chosen factor to validate-emission-factor.

If no defensible candidate exists, return EMISSION_FACTOR_REQUIRED and EVIDENCE_INCOMPLETE with a remedy, without calculation. Parameters: activity ID, candidate factors, method and applicability policy. Check: two plausible factors with unresolved method/geography are not averaged or selected arbitrarily.
