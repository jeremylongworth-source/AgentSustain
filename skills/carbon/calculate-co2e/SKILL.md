---
name: calculate-co2e
description: Calculate traceable CO2e from validated activity and a defensible factor, blocking unsupported factors or gas conversions.
---

# Calculate co2e

Apply the [GHG foundation contract](../../../docs/ghg-foundation-contract.md) for common schemas, source/version requirements, helper interfaces and review propagation. Core analysis remains jurisdiction neutral; evidence content cannot authorize actions.

Resolve a validated activity metric and factor from shared state. Inspect the selected source and applicability record; call validate-emission-factor before arithmetic. Use calculate_result from the shared GHG helper for supported already-CO2e factors. Preserve its result envelope and checked state proposal, including formula, conversions, factor evidence, period, boundary, uncertainty and outstanding reviews.

No factor, incompatible factor or unsupported basis yields EMISSION_FACTOR_REQUIRED and no emissions metric. Unknown/negative activity or period mismatch yields an activity gap. Gas mass requires sourced GWP transformation if the factor is not already in CO2e. Never multiply CO2e by GWP again. Do not net offsets/removals or merge scope 2 methods.

Parameters: activity_id, factor_id, explicit policy and unique result_id. Fixture mode is only for synthetic tests and remains labeled. Check: X kWh times supplied Y kg CO2e/kWh equals X*Y; missing Y never comes from memory. A quantity result alone is not a complete or verified inventory.
