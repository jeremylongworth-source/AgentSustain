# SUS-10 waste and resource execution

Apply the approved common contracts and data execution contract. Preserve reporting period, measurement boundary, provenance, uncertainty, assumptions and all unresolved reviews/gaps. Helpers return analytical proposals, never approvals or shared-state writes.

## Method basis

Reviewed 2026-10-04: [GRI 306: Waste 2020](https://www.globalreporting.org/pdf.ashx?id=12521) separates generation, diversion and disposal disclosures; its disposal category includes incineration with energy recovery. [EPA's nonhazardous materials hierarchy](https://www.epa.gov/smm/sustainable-materials-management-non-hazardous-materials-and-waste-management-hierarchy) prioritizes prevention and distinguishes recycling, energy recovery and disposal. These are methodological references. The core requires an explicit diversion definition rather than silently applying one framework or jurisdiction. This implementation does not supply GRI conformance, legal waste classification, disposal instructions or a reporting adapter.

## Common helper request

`python -m scripts.run_resources request.json` accepts the common input envelope; `run_resources(state, skill, parameters)` returns result and checked proposal. Exit 0 includes valid blocked results; exit 2 means invalid request. Results with supported metrics append to state.waste or state.materials. All selected quantities must be finite nonnegative, in the current period/boundary, and convertible to kg for mass. Litres, bin counts and mixed volume tickets need separately documented mass conversion, not an assumed density. Review fields express supplied judgments, not source authentication.

## Waste baseline and streams

build-waste-baseline parameters: streams, coverage_review, result_id. Each stream has exactly id, metric_id, material, hazard (hazardous/nonhazardous/unknown), route and route_evidence_ids. Routes: preparing_for_reuse, recycling, composting, other_recovery, landfill, incineration_energy, incineration_no_energy, other_disposal, unknown. Known routes require evidence IDs. Describe actual final treatment rather than labeling collection into a recycling bin as confirmed recycling. A source can support separate fragments; coverage_details must reconcile shared-document quantities.

coverage_review has confirmed=true, basis=generated_waste_same_cohort, measurement_boundary, nonoverlap_assessment, coverage, rationale and evidence_ids; optional coverage_details uses the data-baseline contract. Select nonoverlapping generated masses reconciled to the same treatment cohort. Do not add a generation total to its routed subtotals, count transfers twice, or mix prior-year backlog with current generated waste. The helper rejects selected aggregate/component lineage overlap. Hidden overlaps still need source review. Unknown route/hazard creates a gap while retaining known mass. A partial selection supports only the selected total, never an organization-wide completeness claim. State an explicit gap when coverage is incomplete; review prose is not automatically interpreted by the helper.

classify-waste-streams is an instruction workflow: classify composition from records and assess hazard/treatment evidence, retaining unknowns. Hazard labels are supplied assessments, not jurisdiction-specific legal determinations. Hazardous/unknown handling, permits and treatment decisions need applicable specialist review; avoid universal sorting or disposal advice.

## Diversion and hotspots

calculate-diversion-rate parameters: baseline_result_id, route_policy, result_id. The baseline must reproduce from current quantities, lineage and context. route_policy contains confirmed=true, name, version, source, rationale, evidence_ids and included_routes. Supported eligible routes are reuse preparation, recycling, composting, other recovery and optionally energy-recovery incineration under an explicitly supplied definition. Landfill, other disposal, incineration without energy recovery and unknown cannot enter diversion. Framework-specific adapters must enforce their own definitions; do not present a custom energy-recovery-inclusive ratio as GRI 306 diversion.

Known eligible mass / all selected generated mass is the percentage. Unknown treatment stays in the denominator and makes known diverted mass a lower-bound subtotal with a gap. An empty eligible-route list is a valid explicit policy with zero known diversion. Zero total emits mass only, with a percentage-denominator gap. Classification gaps and baseline partiality remain. Source prevention is not generated mass diverted and cannot inflate this numerator.

identify-waste-hotspots parameters: baseline_result_id, result_id. Revalidate the same baseline and rank its mutually exclusive stream masses. The order describes selected mass contributions; it does not rank toxicity, environmental impact, cost or reduction feasibility.

## Material consumption and intensity

analyze-material-consumption parameters: metric_ids, coverage_review, result_id. Review uses the baseline fields with basis=consumed_material. Establish actual consumption through process/stock records; purchases alone are insufficient. Sum documented mutually exclusive consumed masses in kg. Unlike-material totals need an explained management purpose and cannot imply interchangeable performance.

calculate-material-intensity parameters: material_result_id, denominator_id, denominator_review, result_id. Reproduce an analyze-material-consumption result before division. The denominator review has confirmed=true, exact metric_id, definition, unit, rationale and evidence_ids. Use a compatible positive activity quantity and preserve product/service meaning. Unknown units or zero denominator block the KPI; no production, currency, quality or product-mix adjustments are inferred. A change in intensity alone does not establish causal resource efficiency.

## Instruction workflows and limits

identify-material-loss reconciles opening stock + receipts - closing stock - accounted outputs for one material/process and compatible mass basis. Distinguish measured scrap/loss from an unexplained balance residual, using explicit output/loss categories without double counting. A negative residual is an inconsistency to investigate, not zero loss. Unmeasured moisture, work in progress, returns or period differences require gaps/assumptions rather than assigning the residual to waste. No deterministic balance helper is implemented yet.

analyze-waste-cost separates evidenced service, haul, treatment and rental charges, rebates and avoided purchase costs. Keep currencies/periods, taxes, allocation and contracts explicit. Do not multiply mass by an invented tariff; existing numerical helpers do not implement waste-cost accounting. SUS-12 supplies monetary decision analysis.

identify-waste-reduction-opportunities and identify-resource-efficiency-opportunities return source-backed candidate registers with affected process/material, mechanism, ownership, constraints, interactions, required measurements and review states. Prefer examining prevention and material yield before a diversion claim. Do not infer toxicity reduction, emissions benefit, safe reuse, or a standard savings percentage. These workflows and classify-waste-streams require agent interpretation; helper success is not independent reasoning evidence.
