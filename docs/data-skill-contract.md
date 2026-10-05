# SUS-05 shared execution contract

Applies to the ten skills in skills/metrics/. Architecture approved at f2d0ac9; this guide applies it without changing the schemas.

## Inputs and outputs

Use the input envelope in schemas/input.schema.json: contract_version 0.1.0, skill, state and parameters. Validate shape and references with scripts/contract_validation.py (`validate_shape` and `validate_state`). Then check skill-specific semantic prerequisites; a schema pass does not establish authenticity, coverage or source fitness. Invalid shape prevents calculations. Identify the invalid field without echoing private records.

Return the result envelope in schemas/result.schema.json and explicit proposed state changes. Record IDs, execution status, review_states, review_requirements, metrics, evidence_ids, assumptions, data_gaps, diagnostics and next_actions. Significant quantities use the metric contract, with period, boundary, unit, method, uncertainty, assumption and calculation lineage. No-field outputs (such as quality classifications) use diagnostic records whose messages carry a readable assessment or serialized mapping. Do not silently add unsupported fields to the envelope.

The current evidence schema requires a unit string even for incomplete raw evidence. If a source has no unit, keep the raw value outside calculated metrics and use an explicit unresolved marker (`UNKNOWN_UNIT`) on its evidence record with a data gap. This marker is not a computable unit, conversion target or emission-factor unit. Obtain the real unit before analysis; never infer it from adjacent records.

Copy all outstanding review requirements and their states into composed output. Carry existing assumptions and unresolved gaps; new estimates and gaps must also enter proposed state. Do not clear reviews, relabel historical evidence, or imply a quality assessment is verification. Use ANALYTICAL for calculations and ADVISORY for explanations. Material gaps add EVIDENCE_INCOMPLETE; valid independent calculations may be partial. Blocked/invalid_input results contain no calculated metrics and include remedies. Revalidate the candidate state before proposing it, with base revision and reason. No file or external-system mutation is implied by skill invocation.

## Helper boundaries

scripts/data_tools.py provides optional deterministic primitives for units, periods, aggregation, KPIs and comparison. It returns primitive arithmetic results, not a validated sustainability result envelope. The consuming skill must resolve metrics from shared state, enforce evidence/method/coverage prerequisites, and wrap output with full provenance. The helper does not authenticate sources, classify evidence, choose a boundary, determine completeness or approve review. Python is optional for instruction-only use; executing helpers requires Python 3.11+ and the validator additionally uses jsonschema.

The baseline helper requires nonoverlap_confirmed. Reused document evidence additionally needs coverage_details mapping each selected metric ID to source fragments (`evidence_id`, `source_fragment`). Exact repeated fragments are rejected. Distinct labels are insufficient to establish that a subtotal, corrected invoice and its component records are independent: the skill must reconcile actual source activity coverage and preserve that basis in diagnostics and assumptions. This allows legitimate line items to share their real document source.

scripts/state_proposal.py supplies `propose(state, result, reason, evidence=())` for checked append-only proposals. It requires outstanding reviews, gaps and assumptions to survive, rejects replacement IDs and validates the candidate revision. It does not write state, clear a review, reconcile a gap or perform baseline restatement. Those operations need separately documented decisions. The shared validator now rejects nonfinite quantities and calculation-lineage cycles as well as missing references.

Read scripts/data_tools.py's supported UNITS when conversion is needed. It covers explicit mass, volume, energy, count and CO2e mass units. It does not convert currencies, ambiguous tons/gallons, fuel volume to energy, mass to volume, or incompatible dimensions. CO2e mass conversion cannot determine a GWP basis or emission factor. Decimal calculations use 34-digit precision; JSON output serializes numbers without display rounding. Preserve the recorded conversion and declared display rounding separately.

## Source basis

Unit definitions use [NIST SP 811 conversion factors](https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b8) and [BIPM SI prefixes](https://www.bipm.org/en/measurement-units/si-prefixes), accessed 2026-10-04. This is a conversion registry, not an emission-factor source. No copyrighted standards text or numerical emission factors are copied.

## Validation limits

Known-answer helper tests and contract tests accompany this wave. Frontmatter validation verifies skill packaging only. Nine author-led scenario executions and a corrected shared-document rerun are recorded in evaluations/sus05-author-run-01/ and sus05-author-run-02/. They demonstrate bounded extraction, reconciliation, quality reasoning and state proposals for the named fictional cases. Saved-artifact regression tests do not rerun agent inference. These are initial demonstrations, not independent blind evaluation or proof of general reliability; further regression coverage remains necessary. Neither these cases nor ten SKILL.md files establish v1 readiness.
