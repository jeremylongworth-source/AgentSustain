# SUS-06 GHG foundation execution

Use the approved common state/result schemas and [data execution contract](data-skill-contract.md). This wave adds inventory boundary/source assessment, sourced-factor selection/validation, CO2e calculation, GHG gaps, estimates and quality assessment. Scope classification and scope totals are developed in SUS-07/08; no foundation arithmetic result is a complete inventory.

## Methodology sources and versions

Reviewed official sources on 2026-10-04:

- [Corporate Standard revised edition, 2004](https://ghgprotocol.org/sites/default/files/standards/ghg-protocol-revised.pdf), chapters 3, 4, 6 and 7: organizational consolidation, operational boundaries, emissions quantification and inventory quality. The consolidation choice requires organizational facts; an asset name alone is insufficient.
- [Required gases and GWP amendment, February 2013](https://ghgprotocol.org/sites/default/files/2022-12/Required%20gases%20and%20GWP%20values_0.pdf): read with the original edition; its gas coverage amendment prevents treating the older document's gas list as the sole current basis. GWP values must have a selected source/basis and must not come from memory.
- [Scope 2 Guidance, 2015](https://ghgprotocol.org/sites/default/files/2023-03/Scope%202%20Guidance.pdf) and [official guidance page](https://ghgprotocol.org/scope-2-guidance): required support for the forthcoming purchased-energy calculations. A revision consultation is not an issued replacement; pin the edition and relevant corrections at use time.
- [Corporate Value Chain Standard source page](https://ghgprotocol.org/corporate-value-chain-scope-3-standard): orientation for SUS-08; detailed category rules remain to be researched then.

This source review does not establish any numerical emission factor, certify conformity, implement all standard provisions or determine jurisdiction-specific obligations. Those remain distinct from core analysis.

## Factor applicability policy

Every factor conforms to emission-factor.schema.json. `scripts/ghg_foundation.py` exposes `factor_issues` and `calculate_result(state, activity_id, factor_id, policy, result_id, fixture_mode=False)`. Inputs resolve from validated shared state. Output is a common result and checked append-only proposal.

Policy requires explicit geography, acceptable_vintages, method (name/version/source), gwp_basis and source_review. The review records factor_id, activity_id, source_locator, source_version, confirmed_value, confirmed_unit, evidence_ids, reviewer, coverage and rationale. The skill must actually inspect source support and coverage; free-form review fields or a `reviewed` label are not evidence of authenticity or an authenticated professional decision. Preserve the policy with the invocation/evaluation record. No default vintage, geography, method, GWP or source review is filled by the helper.

Acceptable vintages come from the chosen methodology and documented source applicability; they need not equal the activity year. Explain any lag and exceptions in the review rationale. Explicit geography is the approved factor geographic basis for the particular activity, not an automatic country/subdivision conversion. Verify fuel/material/gas/activity coverage, period, calorific basis and calculation boundaries before declaring eligibility.

The arithmetic helper currently accepts a nonnegative, already-CO2e factor expressed as `kg CO2e/<supported activity unit>` or `t CO2e/<supported activity unit>`. It supports defined unit conversions, preserves source evidence and carries open review obligations, gaps and assumptions. Gas-mass-to-CO2e derivation requires a separately sourced GWP transformation; the helper does not infer one. Spend-based currencies, unsupported compound activity units, removals, offsets, netting and specialist calculations require additional reviewed methods rather than pretending this primitive covers them.

Missing or incompatible factors emit EMISSION_FACTOR_REQUIRED, EVIDENCE_INCOMPLETE and a specific gap, with no emissions metric. Missing, negative or context-mismatched activity emits ACTIVITY_DATA_REQUIRED. Zero observed activity remains zero if factor eligibility is established. Outputs are analytical and unassured, with unquantified combined uncertainty unless a supported uncertainty method is supplied.

For a common input request run `python -m scripts.run_ghg_calculation request.json` from the repository root. Set skill to calculate-co2e and parameters to activity_id, factor_id, policy, result_id and optional boolean fixture_mode. The command emits JSON only and does not save state. Exit 0 means a valid result was emitted, including blocked results; inspect result.status. Exit 2 means the request could not be processed. The synthetic request in examples/ghg-foundation/ is reproducible using this command and cannot be used for a real inventory.

## Fixture isolation and limits

Synthetic factors are allowed only with explicit boolean fixture_mode=True, and every such output is labeled SYNTHETIC_FIXTURE with a retained assumption. Fixture locators are blocked in ordinary mode even if a factor is relabeled reviewed. No real factor database is included. Tests supply hypothetical factors solely for known-answer arithmetic and failure handling. An initial eight-skill author-led scenario is recorded in [the execution report](../evaluations/sus06-author-execution.md); its saved outputs exercise incomplete records and boundary review preservation. Broader independent factor-selection, boundary/source coverage and professional workflow evaluations remain necessary; neither helper tests nor this scenario establish SUS-06 or v1 readiness.
