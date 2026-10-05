---
name: define-kpis
description: Define evidence-linked sustainability indicators, service denominators, owners and monitoring frequency for a selected strategy baseline; use calculation skills for measured performance.
---

# Define KPIs

Read [the strategy contract](../../../docs/strategy-contract.md), especially KPI definitions. The optional executor accepts definitions, definition_review and result_id under skill `define-kpis`. Reproduce the selected `establish-baseline` result against current sources before defining indicators.

Relate each indicator to a specific issue and decision. Declare its name, definition, absolute/intensity kind, unit, selected scope, reference period, desired direction, accountable owner and monitoring frequency. The initial executor handles decreasing absolute quantities and physical-service intensities. Other indicators may be designed as advisory definitions, but must disclose that the initial helper does not execute them; do not force social, financial or increasing-benefit measures into this reduction method.

For an intensity definition inspect the actual denominator evidence and service definition. Check its boundary and period against the numerator, equivalent output quality, mix, rejects, downtime and exclusions. Sales, purchased inputs, installed capacity and scrap counts are not automatically useful production. Record source-fit and comparability review only when substantiated. Missing or zero denominators block ratio use; never substitute a count or convert money into physical service without a defensible method.

Retain the absolute numerator alongside intensity. An improving ratio can hide growing total impact; do not present it as absolute improvement. Preserve uncertainty, exclusions and baseline recalculation/monitoring policy. Emit an owned definition register with source IDs and units; monitoring remains unstarted and performance unverified. For actual arithmetic invoke `calculate-sustainability-kpi` separately. Check source changes, unsupported denominator dimensions, mixed periods/boundaries, non-equivalent products and missing monitoring ownership.
