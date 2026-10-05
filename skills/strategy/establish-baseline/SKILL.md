---
name: establish-baseline
description: Select and document a representative sustainability reference period and scoped baseline for strategy or targets, composing reconciled metrics rather than restating history.
---

# Establish baseline

Read [the strategy contract](../../../docs/strategy-contract.md), especially baseline selection and source-fit review. Use the common state/result proposal contract. The optional executor is `scripts/strategy_tools.py` through `python -m scripts.run_strategy request.json`; skill `establish-baseline` takes metric_ids, unit, baseline_review and result_id.

Inspect the actual sources and operating context before selecting a base period. Explain why the period is representative, what operations, flows and accounts it covers, and what remains excluded. Reconcile corrected invoices, subtotals and component records. Compose `build-sustainability-baseline` for supported disjoint quantities; do not treat overlapping metrics as distinct merely because their IDs differ. Inspect emission factor, GWP, scope/accounting and gross/net context where relevant; unresolved defensible factors remain EMISSION_FACTOR_REQUIRED. Neither unit conversion nor a checked state establishes method validity.

Provide metric-specific evidence-fit review only when the sources substantiate the selected quantities and scope. Unverified or irrelevant records cannot be confirmed to make the helper run. Coverage_complete refers to the declared selection, not the entire organization. Preserve exclusions, source uncertainty and all existing gaps/reviews. A partial subtotal can be a conditional reference with a coverage gap; never label it a complete footprint. Missing quantities stay unknown.

Record the selection rationale, nonoverlap basis, source fragments where documents are reused, units, period, boundary and recalculation policy. Recalculation triggers such as acquisitions, corrected sources or method changes require later documented review; do not overwrite past baselines or claim a restatement occurred. Emit the source-linked baseline and proposed state, preserving history. Check disjoint aggregation/conversion, invoice duplication, nonrepresentative operating periods, incompatible units, and incomplete coverage.
