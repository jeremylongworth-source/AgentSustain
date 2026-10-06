# Source-supplied fuel calorific energy

`fuel-energy-0.1.0` converts an explicit supplied fuel quantity using an explicit supplied calorific-value metric. It is separate from the existing delivered-energy helper and uses the existing `build-energy-baseline` common envelope through `python -m scripts.run_fuel_energy REQUEST.json`. Existing energy dispatch, unit registry, schemas, emission factors, skill instructions and saved workflows are unchanged.

The method reference is [2006 IPCC Guidelines, Volume 2 Chapter 1, section 1.4.1.2](https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_1_Ch1_Introduction.pdf), parsed on 2026-10-06. It distinguishes net and gross calorific energy and relates physical fuel quantities to energy quantities. This implementation preserves a declared `LHV` or `HHV`; it imports no default calorific/emission/density values and performs no gross/net conversion. The national-inventory reference supplies no legal obligation for this neutral energy workflow. No original-response byte archive or source/rights approval is claimed.

## Exact inputs

Parameters are `quantity_id`, `calorific_value_id`, `quantity_basis`, `calorific_value_basis`, `heating_basis`, `conversion_review`, `fixture_mode`, `result_id`. Use a fresh result identity and an explicit boolean fixture mode. A missing selected calorific record returns a blocked proposal with `CALORIFIC_VALUE_REQUIRED`; unknown quantities or unfit/incompatible data produce no metric. Zero fuel still requires a positive, defensible supplied calorific value.

Both basis records contain exactly `fuel_id`, `fuel_definition`, `material_basis`, `reference_conditions`. Fuel identity/definition, material basis and reference conditions must match exactly. Material basis is `as_received`, `dry` or `declared_composition`; no dry-mass or moisture correction is inferred. Mass inputs require null reference conditions. Volume inputs require explicit matching `temperature_K`, `pressure_kPa`, `compressibility`, `definition`, with positive finite numerical conditions. These are supplied reference-volume declarations; no ideal-gas, compressibility, reference-volume or density correction is performed. Different descriptions or conditions require a separately defensible transformation before invocation.

`conversion_review` is exactly `quantity_id`, `calorific_value_id`, `boundary_id`, `period`, `as_of_date`, `heating_basis`, `evidence_ids`, `evidence_fit`, `representativeness`, `rationale`, `reviewer_role`. Identities, full state period/boundary and declared heating basis match the selected input; supporting source evidence and `reviewed_supporting` fitness are mandatory. The assessment date must be on or after the reporting-period end. Representativeness is an explicit source/qualified-review declaration, not independently demonstrated by arithmetic.

Selected inputs belong to completed/partial current results and are direct source-leaf metrics: calculation inputs reference only their declared evidence, not a hidden derived metric chain. Their full period/boundary match the state. Source evidence has the same declared input unit, covers the full applicability period, has a known version and nonfuture access, and retains uncertainty. Projected metrics/evidence assumptions and tier-5 models are unsupported in this observed-source path. Fictional selected sources require explicit fixture mode; known synthetic/fixture CSV ingestion ancestry cannot be relabeled ordinary use merely because its source locator starts with workspace:. No source authenticity or actual scientific fitness is certified.

| Supplied calorific unit | Compatible physical quantity | Product unit |
| --- | --- | --- |
| MJ/kg | supported mass converted to kg | MJ |
| GJ/t | supported mass converted to t | GJ |
| MJ/m3 | supported volume converted to m3, matching conditions | MJ |
| MJ/L | supported volume converted to L, matching conditions | MJ |

The shared unit registry supplies dimension-preserving conversions; 34-digit Decimal arithmetic multiplies the compatible quantity and supplied calorific value, then converts the product to kWh. The helper infers no heating value from fuel name, geography, model memory, an energy bill, or an emission factor. Unsupported units and mass/volume pairs block rather than borrowing density. Overflow/nonfinite/negative quantities and nonpositive calorific values cannot produce an output.

## Outputs and composition

The result is partial on success and blocked when inputs are unsupported. `FUEL_ENERGY_INPUTS` retains the exact request; `FUEL_ENERGY_CONVERSION` retains basis/review context, full source metric/evidence snapshots, exact original result hashes and the energy quantity. Raw sources, history, emission factors, assumptions, gaps, uncertainty and outstanding reviews remain in the checked proposed state. A qualified energy-professional review is added; no review is resolved. The helper writes no state file and performs no external action.

The single kWh metric is **input fuel calorific energy on the selected basis**, not useful heat, efficiency, avoided energy, emissions or a verified baseline. All source authentication, engineering approval, emissions/useful-heat findings and external-action flags remain false. Output uncertainty remains unquantified even if input records have quantified ranges; no covariance or confidence interval is invented. Quantity uncertainty records remain visible in source snapshots.

The existing energy baseline can consume the new kWh metric with an explicit carrier/nonoverlap/representativeness review, preserving the fuel-conversion review. Retain its LHV/HHV/material/reference definition and assess compatibility before combining fuel streams. Do not combine input fuel energy with output useful heat as independent consumption, or relabel this result as an efficiency/savings/emissions calculation. The existing helper does not automatically determine heating-basis compatibility or authenticate coverage. Downstream carbon calculations still require separate defensible emission factors and preserve `EMISSION_FACTOR_REQUIRED` when absent.

[Complete fictional requests, actual CLI outputs and baseline handoff](../evaluations/sus09-fuel-energy.json) and [evaluation narrative](../evaluations/sus09-fuel-energy.md) test known answers and adversarial conditions. This later interface follows approved 7bad9dd and awaits its own scoped owner/source/method review. Thermal loss/efficiency/heat-transfer, blended or sampled calorific aggregation, source/reference corrections, complete sector methods, independent organization acceptance and public-v1 requirements remain further work. No roadmap wave or full-goal completion follows.
