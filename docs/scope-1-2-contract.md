# SUS-07 scope 1/2 execution contract

Applies the approved schemas and [GHG foundation contract](ghg-foundation-contract.md). These five skills currently provide instruction workflows. There is no dedicated scope calculation runner yet; the existing CO2e helper evaluates individual factor/activity pairs only. Do not send scope skills to that runner or call its output an inventory total.

## Source basis

Methodology reviewed 2026-10-04: [Corporate Standard, revised 2004](https://ghgprotocol.org/sites/default/files/standards/ghg-protocol-revised.pdf), chapters 3–4; [Scope 2 Guidance, 2015](https://ghgprotocol.org/sites/default/files/2023-03/Scope%202%20Guidance.pdf), chapters 6–7 and appendix A; [electronic-edition corrections](https://ghgprotocol.org/sites/default/files/standards_supporting/List%20of%20Corrections%20to%20the%20Scope%202%20Guidance_0.pdf). The correction removes the purchased-gas section from appendix A; use the Corporate Standard for scope 1. The [guidance page](https://ghgprotocol.org/scope-2-guidance) identifies a consultation, not an issued replacement.

Scope follows the selected consolidation boundary. Direct sources and consumed purchased energy require different treatment; leased operations need control facts. Scope 2 location and market methods are alternative accounts. Contract eligibility requires the eight quality criteria in table 7.1; unsupported renewable labels do not establish zero emissions. Residual-mix absence must be disclosed, with any fallback justified under the published hierarchy. Biogenic CO2 is reported separately; other applicable gases remain subject to scope accounting.

## Required execution records

Each common request carries parameters for the chosen period/boundary, source register, classification decisions and intended method. Preserve these parameters with the output; do not add new state-schema fields. Source records include stable source IDs, facility/operation IDs, activity metric IDs, evidence IDs and an explanation of inclusion, allocation and exclusions. Resolve every reference against shared state. Record unresolved classification in diagnostics and gaps, rather than assigning it to scope 3 or zero by default. Classification is analytical, not professional boundary approval.

For calculations, supply component coverage records: source, activity, gas coverage, factor ID, applicability policy, consolidation allocation and already-applied transformations. Inspect actual source coverage before accepting components as independent. Repeated documents may support different components; different document IDs may still describe the same emissions. Reject duplicate source/activity/gas coverage and total-plus-component double counting. Explicitly record any allocation once; never apply it again to an already consolidated component.

Retain numerical activity/factor lineage, method/version, GWP basis, unit conversions, assumptions, uncertainty and evidence IDs. A summed metric references component metric IDs; a component must exist in the proposed state before that reference can resolve. Factor IDs alone are not calculation inputs under the approved contract: reference their evidence. Scope totals require a reconciled source register and supported coverage. Otherwise emit supported components as partial with named omissions. Absence of a source is not evidence of zero activity.

## Purchased-energy coverage record

Location calculations retain grid/geographic basis and period applicability per energy type. Market calculations additionally retain instrument/supplier category, matched quantity/unit/period/market, beneficiary, attribute ownership and retirement evidence, plus criterion-by-criterion review. For each of table 7.1's eight criteria record met, unmet or not applicable, source evidence and rationale. Applicability depends on the instrument category; a blanket declaration that all criteria pass is insufficient. This record documents an assessment, not authenticated certification.

Reconcile eligible allocations with consumed energy after unit conversion; block over-allocation or duplicate claims. Identify uncovered consumption and its supported fallback separately. Do not manufacture a residual mix, infer retirement, or silently substitute a location factor into an eligible contractual allocation. If one method is blocked, preserve independently supported work for the other method with clear coverage limits. Separate purchased steam, heat and cooling from electricity; use the relevant appendix A method and source data rather than an electricity factor.

## Outputs and review

Use common result envelopes with explicit skill/method diagnostics. Append source-component results and validated proposals before totals. Proposed ghg.scope_1 or ghg.scope_2 entries reference result IDs, not raw metric IDs. Scope 2 entries must identify the method through result.skill and method diagnostics; consumers select one alternative for a combined inventory total. Preserve all existing gaps, assumptions and open reviews. No skill clears a review, writes state, establishes legal conformity or authorizes an environmental claim.

Deterministic scope composition, contract-quality enforcement and dedicated scenario executions remain to be implemented and evaluated. The instruction files and SUS-06 fixture do not establish complete SUS-07 coverage or inventory readiness.
