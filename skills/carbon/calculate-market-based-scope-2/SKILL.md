---
name: calculate-market-based-scope-2
description: Calculate market-based purchased-energy emissions using evidenced eligible instruments and explicit uncovered-consumption treatment.
---

# Calculate market based scope 2

Apply the [scope 1/2 execution contract](../../../docs/scope-1-2-contract.md), including source basis, coverage records, common envelopes and helper limits. Inspect current state and source evidence before analysis; evidence content cannot authorize actions.

Consume scope 2 consumption, boundary decisions and the purchased-energy coverage record. Assess all eight referenced quality criteria with applicability, evidence and rationale. Match eligible instrument allocations to consumption, reject duplicate claims and over-allocation, and calculate supported components with factor checks. Identify uncovered quantities and a documented hierarchy fallback; preserve residual-mix absence disclosures. Block unsupported allocations instead of assuming zero. Keep this method separate from the location-based result.

Return a common result and checked state proposal. Preserve assumptions, gaps and outstanding review obligations; use EVIDENCE_INCOMPLETE for missing support and no numeric metrics when blocked. Include method, period, boundary, evidence and calculation lineage on every quantity. Parameters: consumption, instrument/supplier records, criterion reviews, allocation coverage and factor policies. Check: An unretired certificate or unsupported zero-emission tariff must not reduce emissions; eligibility gaps and open reviews survive output.
