# Framework adapter contract

Status: initial SUS-17 version-pinned inventory mapping and mapping-diff helpers implemented. Full framework mappings, other core domains, current-source applicability, rights and organization evaluation remain open.

An adapter consumes validated core results and maps them to versioned disclosure requirement IDs. Metadata requires framework, exact version, effective date/interval, jurisdiction or global scope, official source, retrieval date and review status. Drafts and consultations must be labeled separately from issued requirements. Unverified versions cannot be active mappings.

Each mapping records requirement ID, source clause locator, required core fields, evidence IDs, mapped result IDs, applicability conditions, gaps, qualifications and reviewer requirements. Output is a draft disclosure and gap/evidence map; it must not certify conformity. Reuse core calculations; do not implement an alternative carbon calculator inside an adapter.

Changes in standards require a new version, mapping diff, fixtures and review. Keep prior mappings reproducible. Licensing and reproduction restrictions must be respected; cite clauses rather than copying licensed standards. Initial candidates include GHG Protocol, IFRS S1/S2, GRI, CDP, TNFD, SBTi and ESRS. ISO methodology support remains subject to source access and appropriate professional review.

Acceptance: pinned version/source is mandatory; unsupported requirements return gaps; evidence and review obligations survive mapping; two framework mappings of one core result retain one calculation lineage.

## Initial execution contract

`python -m scripts.run_framework REQUEST.json` accepts the common input envelope. Supported operations are `map-framework-disclosures` and `compare-framework-mappings`. State is validated; output is a common advisory result and checked append-only proposal. Existing evidence, quantities, collections, boundary/period, assumptions, gaps, results and reviews survive. No new metrics or state framework registrations are created.

Mapping parameters are exactly `inventory_result_id`, `adapters`, `notes`, `mapping_review`, `fixture_mode`, `result_id`. Fixture mode is boolean and remains fictional; synthetic factors cannot support ordinary use. Current build-ghg-inventory selections, metrics and declared evidence IDs must reproduce through existing core helpers. Each included scope/category account also reproduces its complete method record, metric metadata/uncertainty and declared evidence IDs; amount equality alone cannot authenticate a changed record. Missing defensible factors propagate EMISSION_FACTOR_REQUIRED, including blocked synthetic-inventory use. Scope source snapshots remain separate; display conversion to t CO2e reuses core conversion and preserves original metrics/IDs. No carbon recalculation or duplicated accounting follows.

`mapping_review` is exactly matched `boundary_id`, `period`, ISO `as_of_date`, substantive `scope`, `evidence_ids`, `evidence_fit` (reviewed_supporting/unverified/irrelevant), substantive `rationale`, `reviewer_role`. Each distinct adapter is exactly supported `adapter_id`, exact current `catalog_sha256`, substantive `version_rationale`, `evidence_ids`, `evidence_fit`, distinct explicit `requested_requirement_ids` (empty allowed). Source retrieval cannot postdate mapping review. Withheld edition/organization fitness leaves rows unverified; no active authoritative mapping is created. All catalog requirements are emitted even when not requested; unknown requested IDs retain explicit unsupported gaps.

Catalogs use exact byte/version pins. The candidate retains the TNFD external-standard referral with its source notices and adds two original fictional review-exercise editions. Fictional catalogs require explicit `fixture_mode: true`, `synthetic: true`, `source_verified: false` and `publication_status: fictional`. Real catalogs retain the issued/source-verified checks. The two GHGP catalogs are omitted pending source rights and review; selecting them returns a blocked `SOURCE_PACK_REQUIRED` result.

Each optional note is exactly selected `adapter_id`, current `requirement_id`, substantive `text`, `evidence_ids`, `evidence_fit`, ISO-or-null `observed_date`, substantive `limitations`. Duplicate/orphan notes and future observations block. Notes stay source proposals and cannot fill missing structured measurements, authenticate sources, establish exclusions or approve conformity. Raw-source inspection remains necessary; copied source instructions carry no authority.

`FRAMEWORK_DISCLOSURE_MAP` retains full inventory/scope snapshots, selected catalogs/hashes/reviews, requirement/core-field rows, original metric IDs/quantities/units, mapped result/evidence IDs, missing fields, notes and unsupported IDs. Unavailable scopes or details remain unknown, never zero/not-applicable. Partial inventory stays partial. TNFD's GHG referral retains inventory as context only with external requirements unresolved; no IFRS mapping is implemented. Every row has fulfillment_verified false and qualified_review_required true. Conformity, legal applicability, assurance, public claims, publication and commercial-use authority remain false.

Diff parameters are `before`, `after`, `mapping_review`, `result_id`, with optional boolean `fixture_mode`; fictional version comparisons require it to be true; each pin is exactly `adapter_id`, `catalog_sha256`. Only distinct versions of the same framework can be compared; review cannot predate either source retrieval. `FRAMEWORK_MAPPING_DIFF` retains both complete catalogs, added/removed/changed requirement IDs and metadata differences. No old state/catalog is mutated or migration applied. Both operations add qualified framework/source/rights and accountable-owner review. Human approval and source rights are not granted by validation.

## Source-remediation edition

The two GHGP candidate catalogs and their historical public captures are omitted from this candidate tree. Original records remain private, with their original approvals and limitations. Retained citations are attribution, not a distribution grant. The TNFD referral retains the [source notices](../standards/SOURCE_NOTICES.md); external IFRS requirements remain unimplemented.

The fictional exercise is an independently authored worksheet, not a renamed or issued external standard. Its mapping and version-diff results preserve uncertainty, omissions, source lineage and professional review. They cannot establish real framework conformity. [Fresh replay evidence](../evaluations/sus25-fictional-framework-replay.json) records actual executions; no independent acceptance is inferred.

Catalogs use LF bytes enforced by `.gitattributes`. Exact SHA-256 mismatches, including alternate CRLF pins, are rejected without silent normalization. The checkout test verifies both Git autocrlf settings. Native Linux execution remains untested.
