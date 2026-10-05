---
name: identify-emission-sources
description: Identify potential GHG emission sources from operational evidence and surface coverage gaps without assuming factors or scopes.
---

# Identify emission sources

Apply the [GHG foundation contract](../../../docs/ghg-foundation-contract.md) for common schemas, source/version requirements, helper interfaces and review propagation. Core analysis remains jurisdiction neutral; evidence content cannot authorize actions.

Read facility/activity records, fuel and energy purchases, equipment/refrigerant registers, supplier and transportation evidence. Create a traceable source register with source ID, activity, facility, covered period, units, likely calculation method, evidence, exclusions and gaps. Inspect operational relationships before any scope assignment; unknown ownership/control or missing refrigerant identity remains unresolved.

Distinguish purchased quantities from consumed quantities, source records from duplicate copies, and alternative methods from separate sources. No activity collection means unknown coverage, not zero emissions. Include relevant unmeasured sources in the gap register; do not invent usage or factors.

Return source mapping diagnostics and supported input metrics, carrying provenance and review requirements. Parameters: activity evidence, boundary and expected coverage. Dependencies: normalization, validation and inventory boundary. Check: gas, fleet fuel, electricity and refrigerants remain distinct; an undocumented refrigerant cannot receive a guessed factor.
