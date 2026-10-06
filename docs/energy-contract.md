# SUS-09 energy execution

Apply the approved common state/result contracts and [data execution contract](data-skill-contract.md). Energy analysis remains separate from GHG calculations, financial decisions and engineering certification.

## Method/source basis

Reviewed 2026-10-04: [DOE/FEMP Measurement and Verification Guidelines, version 5.0, October 2024](https://www.energy.gov/cmei/femp/articles/mv-guidelines-measurement-and-verification-performance-based-contracts-version-0), [baseline and M&V activities](https://www.energy.gov/cmei/femp/measurement-and-verification-activities-required-energy-savings-performance-contract) and [M&V options](https://www.energy.gov/cmei/femp/measurement-and-verification-options-federal-energy-and-water-saving-projects). These sources support documenting baseline conditions, operating changes and a selected verification method. They are methodological references, not jurisdiction-neutral legal obligations or a certification supplied by this project. Unit conversion uses the existing sourced registry.

Energy arithmetic cannot identify verified savings merely by subtracting bills. Weather, occupancy, service/production levels, operating hours, equipment changes and interactions can affect comparisons. Preserve the baseline's raw period and measurement boundary; separate an explicitly adjusted model from measured consumption. Do not multiply one month by twelve or assume a standard savings percentage.

## Helper interface

scripts/energy_tools.py exposes `run_energy(state, skill, parameters)` for four arithmetic operations and project screening below. Common requests run with `python -m scripts.run_energy request.json`. It returns a common result and checked proposal, with supported energy result IDs appended to state.energy. Exit 0 includes valid blocked results; exit 2 is invalid input. No state file is written. Historical domain references, assumptions, gaps and review obligations survive.

All helper energy inputs resolve from state, have finite nonnegative quantities, and match the current period/boundary. They must convert through supported energy units. Raw fuel volume/mass needs a separately sourced calorific transformation before becoming an energy metric; no heating value, source-energy multiplier, tariff, emissions factor or density is supplied from memory. Negative savings can describe increased use; physical consumption itself cannot be negative.

### Baseline

build-energy-baseline parameters: metric_ids, coverage_review, result_id and optional target_unit (default kWh). coverage_review contains confirmed=true, evidence_ids, basis=delivered_final_energy, carrier_map keyed by each selected metric ID, measurement_boundary, nonoverlap_assessment, representativeness and rationale. Actual source review must support those judgments; field presence is not authentication.

The helper sums converted, mutually exclusive quantities. Reused documents require coverage_details mapping each metric to evidence_id/source_fragment records as in the common baseline primitive. It rejects an aggregate and its calculation-lineage components selected together. Different documents can still describe overlapping loads; inspect bills, meter feeds, corrected records and submeter boundaries before confirmation. Carrier totals in a common energy unit are final-energy quantities, not inferred primary-energy or emissions impacts. ENERGY_BASELINE records the selected inputs and supplied coverage.

### Intensity

calculate-energy-intensity parameters: energy_id, denominator_id, denominator_review, result_id. denominator_review contains confirmed=true, metric_id, definition, unit, evidence_ids and rationale. The denominator is a supported positive activity quantity in the same period/boundary; preserve its meaning, such as produced units or occupied floor area. Its declared unit must match the metric and cannot be UNKNOWN_UNIT. The output normalizes energy to kWh and divides by the stated denominator. Currency/service denominators require their own supported accounting definitions; the helper performs no currency conversion or production inference.

Intensity change alone is not proof of energy efficiency: mix, service level, occupancy and operating conditions may differ. Record the interpretation and required context in analyze-energy-usage.

### Savings

estimate-energy-savings parameters: baseline_id, scenario_id, comparison_review, result_id. Inputs must represent the same reporting conditions/period or an already documented adjusted baseline. comparison_review contains confirmed=true, exact input IDs, analysis_type (projection/observed_difference), comparison_basis (same_conditions/adjusted_baseline), baseline_conditions, scenario_conditions, adjustment_method, evidence_ids and rationale.

Projection requires an explicit scenario metric assumption and linked tier 5 model evidence. The helper emits a labeled projected quantity, with assumptions and unquantified uncertainty. Observed differences are labeled observed energy difference, not verified savings. It subtracts scenario/reporting energy from comparable baseline energy in kWh, retaining negative values. Percentage difference requires positive baseline consumption; zero gives only an absolute difference and a denominator gap. Model calibration, weather regressions, equipment simulation, rebound and interactive effects are not derived here; supply defensible models and reference quantities rather than default percentages.

### Hotspots

detect-energy-hotspots parameters: baseline_result_id, coverage_review, result_id. Review contains confirmed=true, exact baseline_result_id, evidence_ids and rationale. It rechecks the baseline's source quantities, lineage and context, then ranks only its nonoverlapping input quantities. Shares use the selected baseline denominator; zero yields zero quantities without percentages. Partial baselines retain gaps and qualifications. A carrier/meter hotspot is a use contribution, not automatically inefficiency or emissions impact.

## Interpretation, opportunities and prioritization

analyze-energy-usage and identify-efficiency-opportunities provide instruction workflows. They return evidence-backed assessments and explicit checked proposals under the common contract. Inspect source patterns and context rather than generating opportunity lists from generic industry stereotypes. Record affected equipment/process, supporting evidence, uncertainty, interactions, feasibility and information still needed.

Project prioritization needs an explicit decision basis. Keep quantified preliminary energy benefits separate from evidence quality, readiness, operational constraints, owner and implementation dependencies. Do not sum overlapping project savings or manufacture financial scores. Monetary business cases are developed in SUS-12; preliminary screening is not an investment recommendation, engineering sign-off or procurement authorization. Preserve applicable professional/engineering review states when those uses are requested.

### Bounded project screening

prioritize-energy-projects accepts projects, decision_review and result_id. decision_review requires confirmed=true, question, rationale, eligibility_basis, evidence_ids and criterion=descending_lower_bound_kWh. This single supported criterion ranks by the supplied lower scenario bound; no weights or additional preferences are inferred.

Each project contains exactly id, equipment, mechanism, owner (role or null), constraints, dependencies (description and boolean satisfied), readiness (ready_for_screening/deferred), evidence_ids, savings_result_id, range and interacts_with. range contains low, high, unit=kWh, basis and evidence_ids. These are supplied scenario bounds, not derived confidence intervals. Inspect their source and relevance before invoking. The referenced projected savings result must reproduce from its ENERGY_INPUTS against current source quantities, period and boundary, and its point estimate must lie within the supplied range.

An unassigned owner, unsatisfied prerequisite, deferred readiness or nonpositive lower bound defers the candidate. Eligible candidates receive descending lower-bound ranks; equal bounds retain tied ranks. Overlapping eligible ranges flag possible order reversal/ties. Interactions must reference selected projects symmetrically; a reused savings result requires an explicit interaction declaration. Hidden interactions still require source review. The ENERGY_PROJECT_SCREENING diagnostic retains all candidates, deferral reasons, context, criterion and sensitivity findings. No portfolio total is computed even for declared independent candidates. All-deferred registers are blocked; mixed registers are partial. Quantities remain in the referenced savings results, avoiding duplicate standalone benefit metrics.

The [fictional fan source pack](../examples/energy-project-source.md) and saved project-screening fixture demonstrate this narrow decision rule. They do not establish general equipment reasoning or source authenticity.

Initial helper tests use fictional meters, production and tier 5 scenario quantities. They establish bounded arithmetic and blocking behavior, not certified M&V, independent agent reasoning or complete energy workflow reliability. Broader operational scenarios and engineering methods remain evaluation/development work.

## Later source-supplied fuel conversion

The separate [fuel-energy contract](fuel-energy-contract.md) converts explicit mass/reference-volume observations with a supplied calorific metric and exact LHV/HHV/material/reference review. `python -m scripts.run_fuel_energy REQUEST.json` uses the existing baseline skill envelope; no original energy operation, schema, unit registry or factor table changes. Its kWh leaf can feed an explicitly reviewed nonoverlapping baseline, preserving input definitions and all professional/source reviews. It does not supply useful heat, efficiency, emissions, inferred coefficients or scientific authentication. This later interface awaits separate scoped review.


## Subsequent conditional equipment thermal performance

[The separate thermal-performance contract](thermal-performance-contract.md) adds observed integrated heat/input ratios with explicit auxiliary/operating/coverage definitions and complete fuel-conversion replay where selected. It preserves LHV/HHV rather than inferring a conversion, distinguishes electrical heating COP from fuel/auxiliary thermal ratios, and retains unknown/zero/above-unity and engineering qualifications. It supplies no certified efficiency, conservation closure, verified saving, factor or emissions inference. This later interface requires scoped review and does not change existing energy helpers or automatically expand specialist/router dispatch.
