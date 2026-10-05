# Facility source/species ledger candidates

The draft `gas-ledger-0.1.0` helper in `scripts/gas_ledger.py` reproduces selected species conversions and records distinct contributions for one declared in-boundary facility. It exposes missing/unfit slots and a selected-source CO2e subtotal, preserving raw quantities and reviews. It verifies neither statutory facility identity nor a regulated total. Shared schemas, legacy CO2e operations and factor registry remain unchanged; the new interface awaits scoped review.

## Versioned profile and interface

Use `python -m scripts.run_gas_mass request.json` with operation `build-facility-gas-ledger`. Exact parameters are `profile_pin`, `sources`, `components`, `ledger_review`, `fixture_mode`, `result_id`. Result ID is unused and fixture mode explicitly boolean. No individual skill is generated.

A profile pin has `path`, `sha256`, with the same confined `standards/jurisdictions` JSON path and exact-byte requirements as jurisdiction packs. The separately typed profile has `id`, `version`, `execution_contract`, `synthetic`, `gases`, `basis`, `time_horizon_years`, `source`, `scope`, `limitations`. Its species roster is nonempty/distinct; basis and integer time horizon are explicit. Source has locator/version/accessed, requiring HTTPS for real profiles and nonfuture access relative to review. Synthetic profiles and upstream conversions cannot be promoted into real ledgers. The checked-in profile is fictional, not a Canadian gas roster, method, factor or GWP table.

Ledger review has `facility_id`, `boundary_id`, `period`, `as_of_date`, `source_inventory_complete`, `exclusions`, `evidence_ids`, `evidence_fit`, `scope`, `reviewer_role`, `rationale`. Facility must be in the current organization boundary and the period/boundary match current state. Profile source/version has matched supporting evidence with known nonfuture versions/access. `source_inventory_complete` and exclusions are explicit caller judgments; neither authenticates statutory source coverage or facility grouping.

Each source has `id`, `facility_id`, `activity_id`, `activity_kind`, `gases`, `evidence_ids`, `evidence_fit`, `rationale`. Source IDs are distinct within the selected facility; each declares the complete selected-profile gas roster. Source evidence binds the selected activity's evidence IDs and kind to that source, with supporting fitness, known versions, matching boundary and nonfuture access. This is explicit reviewer attribution, not proof that an organizational accounting boundary is a statutory facility. This initial profile requires every selected gas for every declared source; source-specific legal exclusions/methods remain future profile work.

Each component has `source_id`, `gas`, `conversion_result_id` (an explicit ID or null). Slots are unique and belong to declared sources/species. Missing slots and absent/blocked conversions remain visible; they are never imputed as zero. Only the species-conversion operation can occupy a result slot; corporate/scope subtotals cannot substitute.

## Reproduction and non-overlap

Every selected supported conversion replays its original arguments against current state. Complete output metric/period/boundary/method/calculation/uncertainty, conversion report and evidence IDs must match after normalizing only the verification result ID. The conversion itself reproduces the raw gas parent/source evidence. Selected species, source activity/kind/evidence, profile basis/horizon and assessment date must match exactly. Changed sources, contexts, metrics, input arguments or evidence lineage block the ledger.

A result cannot occupy multiple slots. The same activity/species cannot contribute through another source label or alternative conversion. Shared whole-record activity evidence for the same species also blocks, even when cloned activity/result IDs differ. Distinct species from the same measured fuel activity may coexist; common primary factor/GWP evidence is retained without being treated as extra activity. This initial whole-record method performs no allocation or source-fragment splitting; explicit partitions need a separately implemented and reviewed method.

Source/profile fitness controls inclusion. Reproduced quantities with unverified facility/source attribution are retained in row snapshots and withheld from the subtotal. Missing-factor blocked conversions preserve EMISSION_FACTOR_REQUIRED, their blocked snapshots and linked raw results. A linked raw result retained in a blocked row is explicitly not independently reproduced by that row; it preserves available historical quantity/evidence for review without authorizing a contribution.

## Outputs and limitations

`FACILITY_GAS_LEDGER` retains the profile/pin, review/primary sources, declared source inventory, every slot and full selected conversion snapshots. `included_species_mass_kg` shows only included raw masses by species; a species with no included contribution is null. `known_co2e_kg` is null if no contribution is included, rather than an inferred zero. Explicitly calculated zero contributions remain distinguishable from missing slots.

The optional metric is always labelled `Selected facility-source CO2e subtotal`. It sums distinct reproduced JSON contributions using 34-digit Decimal arithmetic and preserves source uncertainty without claiming combined numerical uncertainty. All assumptions enter both the metric and result. Out-of-range numeric representation or invalid input/source reproduction blocks with no metric. Missing slots can leave a partial known subtotal; unsupported entire source/profile contexts produce no subtotal metric.

`declared_coverage_reproduced` requires every declared slot included, a complete-inventory declaration, no declared exclusions and supporting profile fitness. It describes the caller's selected roster only. `regulatory_quantity_verified`, `facility_attribution_authenticated`, `whole_organization_coverage_verified`, `statutory_threshold_authorized` and `scope_account_created` remain false. Even a complete fictional roster is not a defensible statutory threshold or whole-organization inventory.

Every output remains partial with a new open professional ledger review. Original quantities, source evidence, assumptions, factor gaps, legal/professional/engineering reviews and prior results survive. Scope references and factor registry remain unchanged. Copied source instructions cannot certify a subtotal, close reviews or adopt authority.

## Evidence and next work

[The fictional workflow](../evaluations/sus19-gas-ledger.md) composes CH4/N2O factor and explicit GWP calculations before ledger composition. The invented factors/GWPs yield separate 0.01/0.008 kg gas masses and 0.1/0.04 kg CO2e contributions, with 0.14 kg CO2e selected subtotal. Omitting N2O conversion leaves a marked 0.1 kg subtotal; withholding source attribution leaves no metric. These inputs and roster are fictional; no actual factor, GWP or Canadian profile is encoded.

This is initial reproduced-source accounting, not a completed regulated ledger. Statutory subject definitions, required gas/source/fuel coverage and exclusion rules, sampling/property/reference-condition/substitution methods, real primary-source Canadian profiles, independent source/organization evaluation and all scoped/domain/legal/release gates remain open. No roadmap wave or public-v1 readiness is closed.
