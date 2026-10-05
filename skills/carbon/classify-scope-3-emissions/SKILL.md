---
name: classify-scope-3-emissions
description: Classify value-chain emission sources into scope 3 categories using evidence and explicit boundary facts.
---

# Classify scope 3 emissions

Apply the [scope 3 and inventory contract](../../../docs/scope-3-inventory-contract.md) for method sources, common envelopes, helper signatures and limits.

Inspect each source relationship and scope 1/2 reconciliation. Use category-specific discriminator facts rather than supplier names or transport direction alone. For purchases resolve capital treatment and coverage already assigned elsewhere; for transport establish payer, product and stage. For leases require an explicit prior scope 1/2 exclusion, retaining unknown control and professional reviews. Invoke classify_scope3 only with inspected records. Return its classified register with unresolved sources preserved; classification creates no emission quantity.

Return a common result and checked proposed state. Retain assumptions, gaps, outstanding review requirements and evidence IDs; every quantity has units, period, boundary, method, uncertainty and calculation lineage. No external publication or state-file mutation follows from invocation.
