# SUS-08 scope 3 and inventory execution

Use the approved common envelopes and [GHG foundation](ghg-foundation-contract.md) and [scope 1/2](scope-1-2-contract.md) contracts. Core calculations do not determine jurisdictional obligations or authorize reporting claims.

## Methodology sources

Reviewed 2026-10-04: [Corporate Value Chain Standard, 2011 electronic edition](https://ghgprotocol.org/sites/default/files/standards/Corporate-Value-Chain-Accounting-Reporing-Standard_041613_2.pdf), chapters 5–9 and appendices A/B; [2013 corrections](https://ghgprotocol.org/sites/default/files/2022-12/List%20of%20Corrections%20for%20Scope%203%20Standard.pdf); [Calculation Guidance, 2013](https://ghgprotocol.org/sites/default/files/2023-03/Scope3_Calculation_Guidance_0%5B1%5D.pdf), category chapters and appendix D. Apply the [required-gases amendment](https://ghgprotocol.org/sites/default/files/2022-12/Required%20gases%20and%20GWP%20values_0.pdf) alongside these editions. No numerical factors or GWP values are copied or supplied by these links.

The standard separates fifteen categories, defines their minimum boundaries and requires disclosed exclusions. Transport category selection depends on the activity and purchaser, not just shipment direction. Category assessment must distinguish overlapping lifecycle components. Reporting-year purchased/sold cohorts can include future use or disposal emissions; a reporting-period label alone does not define the time boundary of those factors. Consult the category chapter before selecting a calculation method.

## Category register

| ID | Category |
|---|---|
| 1 | Purchased goods and services |
| 2 | Capital goods |
| 3 | Fuel- and energy-related activities |
| 4 | Upstream transportation and distribution |
| 5 | Waste generated in operations |
| 6 | Business travel |
| 7 | Employee commuting |
| 8 | Upstream leased assets |
| 9 | Downstream transportation and distribution |
| 10 | Processing of sold products |
| 11 | Use of sold products |
| 12 | End-of-life treatment of sold products |
| 13 | Downstream leased assets |
| 14 | Franchises |
| 15 | Investments |

This register is a classification vocabulary, not implementation of every category-specific derivation. Unknown leased control is not evidence that a lease belongs in category 8 or 13. Resolve scope 1/2 treatment first.

## Factual classification

`classify_scope3(state, sources, result_id, fixture_mode=False)` in scripts/scope3_accounting.py returns a common result/proposal and SCOPE3_CLASSIFICATION diagnostic. Source facts require id, relationship, period, boundary_id, evidence_ids, rationale, in_value_chain=true and emissions_in_scope_1_2=false. Those flags represent inspected factual assessments, not authentication performed by the helper. Missing evidence or discriminator facts leave category=null and create gaps; the helper creates no quantities.

Relationships are purchase, energy_lifecycle, transport, operational_waste, business_travel, employee_commuting, lease, processing_sold_products, use_sold_products, end_of_life_sold_products, franchise or investment. Purchase requires boolean capital_good and not_other_categories=true. Transport records transported_product, transport_stage and transport_purchased_by_org: fuel/energy transport is assessed with category 3; tier2_to_tier1 uses the purchased-product lifecycle category with explicit capital_good; tier1_to_org and purchased freight use category 4; org_to_customer not purchased by the organization uses category 9. Source inspection must establish these relationships and third-party emissions coverage; no keywords in evidence text make that decision automatically.

Lease facts additionally require lease_role=lessee/lessor and scope12_result_id pointing to a classify-scope-1/2 result whose SOURCE_CLASSIFICATION register excludes that same source ID. Unknown control cannot be reclassified through a false scope flag. The exclusion is only from scope 1/2; it does not establish the full lease category boundary or clear an open review.

## Category arithmetic

`calculate_category(state, category, sources, components, coverage_review, result_id, fixture_mode=False)` consumes the selected category's classified sources and existing CO2e metrics. Sources add activity_id. Components contain source_id, metric_id, factor_id and policy. Foundation factor policy is extended with scope3_category, lifecycle_boundary and allocation_basis. Allocation must already be reflected in the reviewed physical activity/factor; the helper does not apply a second fraction.

coverage_review records category, confirmed=true, evidence_ids, minimum_boundary_assessment, exclusions_and_optional_coverage and gwp_basis. Explain actual source coverage and exclusions; field presence does not prove minimum-boundary completeness. The helper recalculates each component from its resolved activity/factor, checks units/context/lineage, and accepts one aggregate intensity per independent activity. Multiple lifecycle-stage/gas components require a separately reconciled aggregate intensity; a total plus its components must never be summed. Repeated activity IDs under different source IDs and repeated component metrics are rejected.

Supported arithmetic is physical activity times a sourced, already-CO2e intensity in foundation-supported units. Supplier intensities and average physical intensities can use this primitive when their coverage is documented. Spend/currency, distance compound units, hybrid lifecycle construction, product lifetime modeling, waste treatment derivation and financial investment attribution are not implemented by this primitive. Obtain or derive appropriate factors through a separately sourced method; otherwise emit EMISSION_FACTOR_REQUIRED. Source data gaps remain distinct from missing factors. Estimates need tier 5 evidence, explicit assumptions and honest uncertainty.

## Inventory selection

`build_inventory(state, scope1_result_id, scope2_result_id, scope3_result_ids, category_screening, coverage_review, result_id, fixture_mode=False)` in scripts/ghg_inventory.py consumes explicit domain-linked scope results. Choose one scope 2 account. Screen all 15 categories with category, status (applicable/not_applicable/excluded/unknown), evidence_ids and rationale. Applicable categories need selected supported totals. Excluded/unknown categories retain gaps; omitted categories do not become zero. Missing scope accounts also remain gaps.

Inventory coverage_review requires confirmed=true, evidence_ids, rationale and gwp_basis. The helper rechecks selected totals from their component records, rejects duplicate categories and shared emissions-component IDs, enforces common period/boundary/GWP basis, and sums only supported accounts. Independently labeled records can still overlap in real activity: inspect source coverage before confirming. Scope 3 energy lifecycle may legitimately use the same energy quantity as scope 2 generation, but must have a distinct, nonoverlapping lifecycle component and factor.

Partial scope/category results remain partial at inventory level, with open professional reviews, assumptions and gaps retained. The inventory result has a selected emissions subtotal and INVENTORY_SELECTION diagnostic. It does not append its aggregate to scope domain arrays, which would cause later double counting. Distinct inventory totals using different scope 2 methods require separate explicit calls.

Common requests for these operations and the analysis operations below run with `python -m scripts.run_scope3 request.json`. skill selects the operation; parameters match its signature after state. Exit 0 includes valid blocked outcomes; exit 2 is invalid input and does not echo private records. No state file is written.

## Comparison and hotspots

scripts/inventory_analysis.py implements compare_inventories and identify_hotspots. Both revalidate the selected inventory from its account/component records and retain revalidation gaps, factor failures and partial coverage. A valid numeric change or ranking is not a verified reduction or feasible savings estimate. The [Scope 3 Standard chapter 9](https://ghgprotocol.org/sites/default/files/standards/Corporate-Value-Chain-Accounting-Reporing-Standard_041613_2.pdf) provides the change/recalculation context; the helper does not select a significance threshold or restate data automatically.

`compare_inventories(state, prior_state, prior_inventory_id, current_inventory_id, comparability_review, result_id, fixture_mode=False)` accepts a validated historical snapshot alongside current shared state. Prior inventory/accounts, metric/evidence lineage and used factors must be present unchanged in current history. No missing historical IDs are silently imported or renamed. Organization, boundary ID/approach/facilities/exclusions, GWP basis, selected scope 2 method, screened categories and accepted source/gas/allocation/lifecycle coverage must match. Supply a documented restated prior snapshot when these differ; a confirmed flag cannot override a mismatch. Factor changes require explicit assessment rather than an automatic reduction interpretation.

comparability_review contains confirmed=true, exact prior_inventory_id/current_inventory_id, evidence_ids, reviewer, rationale, boundary_changes_assessment, coverage_changes_assessment, factor_changes_assessment and restatement_assessment. These are supplied source-backed judgments, not authenticated professional approval. Open prior obligations are retained even in a blocked comparison; current recorded resolutions remain authoritative. Snapshot validation and common lineage rules still apply.

Periods must be ordered and nonoverlapping, with equal duration or matching full calendar-year/month cadence. Leap-year and month-length differences do not trigger silent annualization. Absolute change is current minus prior, with both values converted to kg CO2e. Percentage change requires a positive prior value. Zero prior yields only absolute change and a denominator gap. The change metric uses the current reporting period; the comparison diagnostic records both periods and the review.

`identify_hotspots(state, inventory_id, level, coverage_review, result_id, fixture_mode=False)` supports level=scope/category/source. coverage_review contains confirmed=true, exact inventory_id/level, evidence_ids and rationale establishing nonoverlap. Contributions come only from the selected inventory accounts; arbitrary metric lists, the inventory total itself and alternative scope 2 accounts are not contribution inputs. Source contributions apply the scope component's recorded activity/consolidation allocation once, and combine disjoint gas components for the same source. Scope 3 allocation is already reflected in its physical activity/factor.

The denominator is always the selected inventory subtotal. Scope/source contributions must reconcile to it. Category ranking is a scope 3 subset of that denominator, so its shares need not sum to 100%. Positive denominators produce emissions and share metrics with lineage; zero supports zero quantities without percentage metrics. Ranking ties use stable source/category keys. Partial inventories retain their gaps and review states; omitted sources cannot become zero. The diagnostic records contribution level, rank, quantity, denominator and qualifications.

Initial deterministic tests and fictional examples are evidence of bounded behavior. Category-specific derivation, independent extraction/classification, inventory restatement and organization-wide workflow evaluation remain further work. No v1 readiness or assurance is established.
