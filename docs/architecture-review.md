# SUS-01 through SUS-04 architecture review

Status: APPROVED by the user on 2026-10-04 (America/Toronto). Individual skill implementation may proceed in roadmap order, beginning with SUS-05.

The gate is defined in ROADMAP.md sections 23 and 26: "Once this architecture pack passes review, development can proceed into SUS-05 Sustainability Data Skills". The active goal additionally preserves human review. Review this pack as a coherent set; test success alone does not pass the gate.

## Review artifact map

| Roadmap artifact | Draft artifact | Acceptance evidence |
|---|---|---|
| Domain contract | domain-contract.md, safety-boundaries.md | Permitted/restricted capabilities and review obligations specified |
| Complete hierarchical taxonomy | taxonomy.md | All 16 families and all named roadmap skills; coverage test |
| Evidence/provenance schema | evidence-policy.md, ../schemas/evidence.schema.json, ../schemas/emission-factor.schema.json | Provenance, factor metadata and proxy fixtures |
| Common I/O contract | io-state-contract.md, ../schemas/input.schema.json, ../schemas/result.schema.json | Input envelope, blocked/partial states and result tests |
| Shared-state schema | ../schemas/state.schema.json | Fictional state and reference/temporal tests |
| Skill naming | naming-conventions.md | Global uniqueness and taxonomy coverage |
| Router contract | router-contract.md | Observable future routing scenarios specified |
| Framework-adapter contract | framework-adapter-contract.md, framework-registry.md | Version/source/mapping requirements specified |
| Jurisdiction-module contract | jurisdiction-model.md | Canadian structure and applicability boundaries specified |
| Evaluation requirements | evaluation-requirements.md | Known-answer, adversarial and end-to-end requirements specified |
| Review/escalation states | domain-contract.md, ../schemas/common.schema.json | Concurrent obligations and explicit resolution fixtures |
| Scaffolding specification | architecture.md | Layers, locations and dependency rules specified |

## Decisions requested

Approve or request changes to the proposed contracts, JSON-compatible schemas, naming and family placement, `standards/jurisdictions/` as the canonical location, and the required-state propagation model. Approving this pack authorizes SUS-05 and subsequent development in roadmap order; it does not certify domain methods or authorize publishing.

License choice is needed before public distribution, but does not prevent private architecture review or subsequent authorized development. Full domain-source research remains assigned to the consuming waves.

## Decision record

- Reviewer: project owner, via this development chat
- Reviewed revision/content snapshot: `f2d0ac9b5b34a4eef3f2678173d387d16fe0784c` (SUS-01 through SUS-04 architecture pack)
- Decision and date: approved on 2026-10-04 (America/Toronto); user instruction: "approve the review"
- Conditions or requested changes: none stated; existing roadmap, validation, professional-review and publication boundaries remain applicable
- Implementation authorization: granted for SUS-05 and subsequent development in roadmap order; no publication authorization granted

Record explicit user approval with the reviewed revision and conditions. Material contract changes reopen review. Preserve this record; never substitute an agent's self-review for the required human decision.

## SUS-18 execution extension scoped approval

The original f2d0ac9 architecture approval remains recorded above. The initial executable jurisdiction semantics extend the reviewed interface and reopen scoped review under the material-contract-change rule. This extension received scoped owner approval on 2026-10-05 at revision `898d790af43a0cc867ab1f81a3519a6da5bbe49d`; the decision record below identifies the scope. Review [jurisdiction-model.md](jurisdiction-model.md), `scripts/jurisdiction_tools.py`, `scripts/run_jurisdiction.py`, the fictional module under `standards/jurisdictions/fixtures/`, tests and [saved scenario evidence](../evaluations/sus18-jurisdiction-foundation.md) together. The final validation record identifies exact file hashes; successful tests do not approve this extension.

Review scope includes exact byte/version selection, typed whole-period entity facts, separate source/currency fitness, three-valued threshold/exception predicates, inclusive effective-date segmentation, historical repeal/proposed-status handling, jurisdiction overlap without hierarchy/precedence inference, source snapshots and append-only legal-review propagation. Shared state schemas, neutral core calculations, original architecture approval and all existing professional/source/owner/release gates remain unchanged. Actual Canadian rules, independent source interpretation and organization coverage remain open.

The pending jurisdiction review now also includes the draft subject/year extension in `scripts/jurisdiction_subjects.py`, its explicit subject-pack fixture and [complete scenario evidence](../evaluations/sus18-jurisdiction-subjects.md). Review subject membership/boundary, source binding, observed-through versus actual cessation, responsibility-event identity/period support, reporting-year selection without inferred legal commencement, retained source/effective metadata, non-additive shared evidence and unverified regulatory quantities. Legacy company captures replay unchanged. No earlier approval is extended to this draft; actual Canada content, qualified legal decisions and broader evaluation remain open.

## SUS-18 scoped decision record

- Reviewer: project owner via this development chat.
- User instruction: "approve the review".
- Reviewed revision/content snapshot: `898d790af43a0cc867ab1f81a3519a6da5bbe49d`.
- Decision/date: approved for continued roadmap development on 2026-10-05 (America/Toronto); no additional conditions stated.
- Scope: the company screening foundation and subject/year/event extension described above, including pinned pack separation, explicit subject/source membership, annual/operating/event periods, conditional operator identity, reporting-year selection, unknown-status withholding and append-only review propagation.
- Evidence: [final validation record](../evaluations/sus18-jurisdiction-subjects-validation.json), 537 repository tests, 32 focused tests and six full helper/CLI replays.

This supersedes the pending scoped-owner-review status recorded before this decision, while preserving the original f2d0ac9 architecture approval. Actual statutory grouping, source/legal interpretation, regulated-emission methods, independent organization evaluation and all professional/source/owner/release requirements remain open. Approval does not resolve state reviews, establish actual Canadian applicability or v1 readiness, close SUS-18/SUS-19, or authorize external actions. Material subsequent contract changes reopen review.

## Subsequent conditional task-register extension awaiting scoped review

The separate task catalog/history/composition contract follows approved revision 898d790 under continued roadmap authorization. It does not inherit scoped approval. Review [the contract](jurisdiction-model.md) and [complete fictional evidence](../evaluations/sus18-jurisdiction-tasks.md), including complete screened-result/source/lineage reproduction, all-branch and year coverage, history/operator attribution, unknown versus false submissions, source currency, separate notification/reporting/certification/retention candidates and explicit retention calendar/anchor limits. This is neutral draft infrastructure, not an actual Canada module. Qualified legal/source review, regulated quantities, real retention anchors, complete Canadian coverage, independent evaluation and release gates remain open; no state review, filing, certification or authority is resolved.

## Subsequent species-mass foundation extension awaiting scoped review

The separate `gas-mass-0.1.0` factor/review/arithmetic interface follows approved 898d790 under continued roadmap authorization and does not inherit scoped approval. Review [the species-mass contract](gas-mass-method.md) and [complete fictional evidence](../evaluations/sus19-gas-mass.md), including dimensional gas/energy units, exact activity/factor/source/current-review binding, synthetic isolation, missing-factor blocking, partial results and propagated professional/legal reviews. The shared schemas and existing CO2e registry/calculations are unchanged. Actual species conversion, regulated source/fuel/facility method coverage, sampling/reference conditions, independent evaluation and all professional/release gates remain open; no actual Canadian applicability, factor, GWP, filing, authority or review resolution is adopted.

## Subsequent explicit GWP-conversion extension awaiting scoped review

The separate `gas-co2e-0.1.0` parent-reproduction/source/basis/horizon/conversion contract follows approved 898d790 under continued roadmap authorization and does not inherit scoped approval. Review [the conversion contract](gas-conversion-method.md) and [complete fictional evidence](../evaluations/sus19-gas-conversion.md), including full gas-report/metric/source/uncertainty/lineage replay, exact species/ratio/basis/horizon and input-result source confirmation, current applicability, synthetic isolation, explicit alternative selection and Decimal/JSON representability. The gas-mass primitive now traps extreme Decimal underflow rather than emitting zero; its existing valid captures remain unchanged. No actual GWP, regulated method/ledger, scope account, Canadian rule, filing, authority or state-review resolution is adopted. Qualified source/domain/organization and broader architecture/development/release requirements remain open.

## Subsequent facility/source ledger extension awaiting scoped review

The separate `gas-ledger-0.1.0` pinned-profile/source/species/coverage interface follows approved 898d790 under continued roadmap authorization and does not inherit scoped approval. Review [the ledger contract](gas-ledger-method.md) and [complete fictional evidence](../evaluations/sus19-gas-ledger.md), including exact profile bytes, source/facility attribution, parent/metric/source/uncertainty/lineage reproduction, activity/evidence-species non-overlap, missing/unfit contributions, preserved raw history and selected-subtotal versus statutory-total boundaries. Original schemas/calculations are unchanged. Statutory definitions, real required gas/source/fuel profiles, sampling/reference/substitution methods, source-fragment allocation, independent organization evaluation and all qualified/release requirements remain open. No actual Canadian quantity, threshold, scope account, filing, authority or state-review resolution is adopted.

## Subsequent explicit retention-anchor extension awaiting scoped review

The separate v2 task catalog adds explicit required-versus-actual submission anchors and report-task source references under continued roadmap authorization. It does not inherit scoped approval. Review [the anchor contract](retention-anchor-method.md), [complete fictional evidence](../evaluations/sus19-retention-anchors.md) and the separate non-executable Canadian source calendar, including source/version/date fitness, trigger differences, unknown-date withholding, unchanged v1 captures and calendar-versus-legal-endpoint boundaries. Actual operator applicability, extensions/exceptions, storage/address conditions, statutory quantities, independent organization evaluation and all qualified/release gates remain open. No actual Canada task, filing, record destruction or state-review resolution is adopted.

## Subsequent claim-evidence interface awaiting scoped review

The initial `claim-evidence-0.1.0` dossier/classification/criterion/source-replay interface follows approved 898d790 under continued roadmap authorization and does not inherit scoped approval. Review [the contract](claim-evidence-method.md) and [complete fictional evidence](../evaluations/sus20-claim-evidence.md), including original material/representation dates, supplied judgment provenance, mandatory criterion completeness, exact scoped numeric assertions, visible original qualifications, source/metric/report/uncertainty/lineage replay and incomplete-subtotal/product/facility boundaries. Core review determines no jurisdiction applicability or publication approval. Independent material/general-impression reading, full inventory/neutrality/test/comparison/future-plan methods, actual legal/source profiles and all qualified/owner/release gates remain open. No original statement, source quantity or review is rewritten/resolved, and no individual skill or public claim is adopted.

## Scoped owner approval through d99a70b

- Reviewer: project owner via this development chat.
- User instruction: "approve the review".
- Reviewed revision/content snapshot: `d99a70b72448c8e847ceef8d3bae03445daa841d`.
- Decision/date: approved for continued roadmap development on 2026-10-05 (America/Toronto); no additional conditions stated.
- Scope: the committed snapshot through the initial claims-evidence reviewer, including the conditional task register, species-mass calculations, explicit GWP conversion, facility/source/species ledger, v2 retention anchors and associated Canadian source research and recorded validation.
- Evidence: [claims validation record](../evaluations/sus20-claim-evidence-validation.json), recording 610 repository tests, 13 focused claims tests, five composed CLI captures and fifteen historical gas replays at the reviewed snapshot. These are existing results, not newly rerun tests.

This decision supersedes the pending scoped-owner-review descriptions for these committed increments through d99a70b, while preserving earlier decision records and historical validation artifacts. The uncommitted plain-text material-binding helper, CLI changes and material fixtures are outside this reviewed snapshot and remain unapproved. Subsequent material changes reopen scoped review.

Approval authorizes continued development under ROADMAP.md. It does not resolve professional, legal, source-specific, organization or state reviews, certify actual Canadian applicability or claims, close roadmap waves, establish v1 readiness, or authorize pushing, publishing, merging, releasing, deploying or contacting third parties.

## Subsequent plain-text claim-material binding awaiting scoped review

The `claim-evidence-0.2.0` material-pin/character-span interface follows approved snapshot d99a70b under continued roadmap authorization and does not inherit scoped approval. Review [the contract](claim-material-binding.md) and [complete fictional evidence](../evaluations/sus20-bound-claim.md), including exact bytes and evidence locator/version, original statement/qualification/numeric selectors, no rewriting or inferred unit conversion, separate actual conflicting material, source-preserving state composition and unchanged legacy captures. Byte identity and text presence do not establish publication provenance, authenticity, semantic classification, general impression or visual prominence. Qualified/source/legal/organization and owner/release gates remain open; no original record, state review, legal/public claim or v1 readiness is approved.

## Subsequent inventory-claim source bridge awaiting scoped review

The separate `claim-inventory-0.1.0` bridge and `claim-evidence-0.3.0` report follow approved snapshot d99a70b without inheriting scoped approval. Review [the contract](inventory-claim-method.md) and [complete fictional evidence](../evaluations/sus20-inventory-claim.md), including current full inventory/account/accepted-leaf metric/report/uncertainty/lineage reproduction, explicit factors, source/facility/category/method/period/date fitness, preserved unsupported components, declared-versus-external completeness and selected-subtotal versus whole-subject boundaries. Whole quantity claims require inventory criteria; reduction, credit and residual methods remain distinct unknowns. Existing operations/captures and core calculations are preserved. Source authenticity, archived provenance, qualified scientific/legal/owner review, independent organization evaluation and all release gates remain open. No original record, state review, neutrality, public/legal claim, wave closure or v1 readiness is approved.

## Subsequent comparison-claim source bridge awaiting scoped review

The `claim-comparison-0.1.0` bridge and `claim-evidence-0.4.0` report follow approved d99a70b without inheriting scoped approval. Review [the contract](comparison-claim-method.md) and [complete fictional evidence](../evaluations/sus20-comparison-claim.md), including explicit retained prior state, both full inventory/account/leaf replays, exact comparison metadata/uncertainty/lineage, compatible periods/boundaries/coverage, signed versus decrease-magnitude interpretation, zero-baseline percentage withholding, source/gap/review retention and observed-versus-causal limits. Existing operations/captures and core calculations are preserved. Semantic interpretation, actual source completeness/authenticity, qualified scientific/legal/owner review, independent organization evaluation and release gates remain open. No project attribution, actual legal/public claim, state-review resolution, wave closure or v1 readiness is approved.

## Scoped owner approval through 7fff776

- Reviewer: project owner via this development chat.
- User instruction: "approve the review".
- Reviewed revision/content snapshot: `7fff776d2f2406adefe4eb45a75ae6ffeb05c838`.
- Decision/date: approved for continued roadmap development on 2026-10-05 (America/Toronto); no additional conditions stated.
- Scope: the committed snapshot through the comparison-claims bridge, including exact material binding, reproduced inventory/account/leaf source context, declared versus external completeness, signed/decrease-magnitude interpretation, explicit paired periods and retained prior state, selected-comparison criterion binding, single-proof hash references, zero-baseline percentage withholding and observed-versus-causal boundaries.
- Evidence: [final comparison validation record](../evaluations/sus20-comparison-claim-validation.json), recording 632 repository tests, 35 focused claims tests, six sequential CLI cases, one independent zero-baseline CLI probe and twenty-nine historical full-output replays. These are existing reviewed-snapshot results, not tests rerun for this approval.

This decision supersedes pending scoped-owner-review descriptions for the material, inventory and comparison interfaces committed through 7fff776. Earlier approvals and historical validation artifacts remain unchanged. The unfinished future-goal helper and its uncommitted claims/CLI integration are outside the reviewed snapshot and remain unapproved and unvalidated. Subsequent material changes reopen scoped review.

Approval authorizes continued development under ROADMAP.md. It does not authenticate sources, professional judgments, semantics, organization completeness or actual publication; resolve state/source/legal/owner reviews; establish project causation, neutrality, conformity or v1 readiness; close roadmap waves; or authorize pushing, publishing, merging, releasing, deploying or contacting third parties.

## Subsequent future-goal proposal bridge awaiting scoped review

The draft `claim-future-goal-0.1.0` source bridge and `claim-evidence-0.5.0` report follow approved 7fff776 without inheriting scoped approval. Review [the contract](future-goal-claim-method.md) and [complete fictional evidence](../evaluations/sus20-future-goal-claim.md), including exact target/transition/roadmap replay, pathway/final-checkpoint identity, planned-versus-evidence periods, annual goal-year/source-text binding, intensity-versus-absolute units, unmet conditions, source/date/fixture fitness and single-proof references. Proposal evidence cannot supply observed progress, adopted commitments or future guarantees. Existing operations/captures, core strategy/calculation code and shared schemas are preserved. Actual progress/adoption/feasibility, independent source/semantic/scientific/legal/organization and owner/release requirements remain open; no state review, actual legal/public claim, wave closure or v1 readiness is approved.

## Subsequent development router awaiting scoped review

The draft `intent-router-0.1.0` planner and pinned capability catalog follow approved 7fff776 without inheriting approval. Review [the routing contract](router-contract.md) and [fictional evidence](../evaluations/sus21-router.md): actual approved Git content/name checks, original-request-only classification, mixed/unsupported intent clarification, acyclic prerequisites, explicit versions, declared-versus-verified input fitness, selected source blocking, independent energy/carbon branches, missing factors and retained legal/professional/assurance review/history. No workflow is executed or approved; current claims content drift remains unavailable. Router/catalog and prior future-goal scope, independent behavioral/organization outcomes, specialist composition and release requirements remain open. No wave closure or v1 readiness follows.

## Subsequent carbon-accounting specialist awaiting scoped review

The draft `carbon-accounting-workflow-0.1.0` and development skillset/manifest follow approved 7fff776 without inheriting scoped approval. Review [the contract](carbon-workflow-contract.md) and [fictional evidence](../evaluations/sus22-carbon-accounting.md): unchanged core dispatch/formulas, exact helper parameters and per-step synthetic isolation, fresh result/metric IDs, source-producing ancestor checks, blocked/partial handling, independent branches, separate location/market accounts and selected inventories/changes/hotspots, atomic original-revision state composition, full source/result/uncertainty lineage and open professional/assurance/history gates. No combined inventory total, coverage authentication, statutory account, causal reduction, assurance or publication authority is supplied. This specialist and the prior router/future-goal interfaces await scoped owner review; broader organization/behavioral evaluation, remaining specialists and all release requirements remain open. No SUS-22 closure or v1 readiness follows.

## Subsequent sustainability-manager organization recipe awaiting scoped review

The draft `organization-manager-0.1.0` and manager skillset/manifest follow approved 7fff776 without inheriting scoped approval. Review [the contract](manager-workflow-contract.md) and [coherent fictional evidence](../evaluations/sus22-organization-manager.md): one pre-normalized source state, matched raw energy selections, fresh recipe bindings, unchanged core helper execution, selected-source blocking and independent branches, exact single-result hash views, separate physical/monetary/future definitions and atomic original-revision state with all evidence/factors/uncertainty/gaps/reviews preserved. Existing derived context is not relabeled normalized input. Incomplete scopes, source fitness, future delivery/resources and historical mapping/rights requirements survive. Manager and prior future-goal/router/carbon interfaces await scoped owner review; raw ingestion, independent organization reliability, remaining specialists, active methods and release gates remain open. No roadmap wave or v1 readiness is approved.

## Subsequent pinned CSV source ingestion awaiting scoped review

The draft `business-csv-ingestion-0.1.0` follows approved 7fff776 without inheriting approval. Review [the contract](business-ingestion-contract.md) and [actual raw-source/manager composition](../evaluations/sus23-business-source-workflow.md): exact workspace path/byte/version selection, bounded UTF-8 record schema, typed literal numbers and unknowns, declared unit/period/geography/model/uncertainty preservation, fresh identities, document/row ancestry, multiline source-instruction isolation, synthetic-example controls, whole-file rollback and unchanged input/history/factor/review custody. Successful normalization remains partial with source review open; CSV data creates no factor/GWP or authentication. The existing manager receives the exact ingested candidate with its own ingestion flag unchanged. This ingestion and prior future/router/specialist interfaces await scoped owner review; other input formats, independent evaluation, active methods and public-v1/release requirements remain open. No phase closure or readiness follows.

## Subsequent sustainable-procurement specialist awaiting scoped review

The draft `procurement-workflow-0.1.0` and specialist/manifest follow approved 7fff776 without inheriting scoped approval. Review [the contract](procurement-workflow-contract.md) and [fictional evidence](../evaluations/sus22-procurement-workflow.md): unchanged supplier/carbon methods, explicit acyclic typed source dependencies, per-step fixture flags, fresh output identities, source blocking and independent branches, exact standalone/source-hash results, separate rating/risk/purchase/emissions/cost semantics and atomic original-revision state with all source/supplier/factor/uncertainty/gap/review history retained. No supplier selection, procurement, contact, implemented benefit, portfolio total or publication is granted. This specialist and prior pending interfaces require scoped owner review; broader independent source/organization reliability, other named specialists and release gates remain open. No wave closure or v1 readiness follows.

## Subsequent climate-risk specialist awaiting scoped review

The draft `climate-workflow-0.1.0` and specialist/manifest follow approved 7fff776 without inheriting scoped approval. Review [the contract](climate-workflow-contract.md) and [coherent fictional evidence](../evaluations/sus22-climate-workflow.md): unchanged climate helpers, exact source/result identities, acyclic typed producer dependencies, full standalone/hash equality, conditional scenario/horizon/source/stock/service definitions, ordinal uncertainty and proposed adaptation/plan conditions, blocked/independent branch handling and atomic original-revision history/review custody. No source/model authentication, probability/loss/safety/legal finding, portfolio total, actual effectiveness, implementation or publication is granted. This and prior pending interfaces require scoped owner review; broader methods, two remaining specialists, independent organization acceptance and v1/release requirements remain open. No wave closure follows.

## Scoped owner approval through cd0c991

- Reviewer: project owner via this development chat.
- User instruction: "approve the review".
- Reviewed revision/content snapshot: `cd0c991a18909459f27eb6abd10843963345b748`; the validated climate-risk review package was saved locally before recording this decision.
- Decision/date: approved for continued roadmap development on 2026-10-05 (America/Toronto); no additional conditions stated.
- Scope: the pending development interfaces through this snapshot: future-goal claims, intent router/catalog, carbon-accounting specialist, organization-manager recipe, pinned business CSV ingestion, sustainable-procurement specialist, climate-risk specialist and public-v1 evidence audit. This includes typed dependencies, blocked and independent branches, exact source-result views, separate conditional outputs, atomic state composition and preserved evidence, units, periods, uncertainty, assumptions and outstanding reviews.
- Evidence: [climate validation](../evaluations/sus22-climate-workflow-validation.json) and [durable suite witness](../evaluations/sus22-climate-suite-run.json) record 691 passing repository tests, seven focused tests, twenty architecture checks and four actual CLI/helper cases. These checks were completed before this approval; they were not rerun for the decision. Earlier increment validation remains unchanged.

This decision supersedes pending scoped-owner-development-review descriptions for the interfaces committed through this revision. Historical records and draft labels describe their original state; approval does not rewrite them or extend to later material changes.

Approval permits continued local roadmap development. It does not authenticate sources, validate climate probabilities or losses, establish legal applicability, organization safety, adaptation effectiveness, implementation or independent organization acceptance; resolve result/state/source/professional/legal reviews; close roadmap waves; establish v1 readiness; or authorize pushing, merging, publishing, releasing, deploying, filing or third-party contact. Two named specialists and the remaining source, method, independent acceptance and public-v1 requirements remain open.

## Subsequent investment specialist awaiting scoped review

The draft `investment-workflow-0.1.0` and sustainability-business-case skillset follow approved cd0c991 without inheriting scoped approval. Review [the contract](investment-workflow-contract.md) and [the fictional evidence](../evaluations/sus22-investment-workflow.md): unchanged finance dispatch/calculations, distinct cash-flow and full-case request forms, fresh identities, typed producing ancestors, blocked/independent branches, standalone/hash equality, conditional monetary/physical definitions, sensitivity, pending funding decisions and atomic review/history custody. No combined portfolio, source authentication, realized saving, verified physical reduction, investment selection, funding, implementation or publication authority is granted. Reporting composition, broader methods, independent organization acceptance and full public-v1/release requirements remain open; no wave closure follows.

## Subsequent reporting specialist awaiting scoped review

The draft `reporting-workflow-0.1.0` and sustainability-reporting skillset follow approved cd0c991 without inheriting scoped approval. Review [the contract](reporting-workflow-contract.md) and [fictional composition evidence](../evaluations/sus22-reporting-workflow.md): unchanged carbon/framework methods, per-step synthetic flags, explicit producer graph, blocked/independent branches, separate inventory accounts, exact catalog/source-result hashes, omitted-field and narrative limits, original source/history/uncertainty custody and atomic state. Historical editions and TNFD referral context do not supply active authoritative mapping or fulfilled external requirements. No combined inventory, complete coverage, conformity, legal applicability, assurance, reuse rights, public claim or publication is granted. This reporting and later investment interface await scoped owner review; broader methods, framework/Canada source coverage, independent organization/agent acceptance and public-v1/release requirements remain open. All seven named roles now have initial compositions, without roadmap closure or v1 readiness.

## Subsequent Canada GHGRP draft predicate module awaiting scoped review

The `canada-ghgrp-screen-0.1.0` front end and two real-source edition modules follow approved cd0c991 without inheriting scoped approval. Review [the contract](canada-ghgrp-draft-screen.md) and [fictional evidence](../evaluations/sus19-canada-draft-screen.md): explicit original/amended selection, all three branches, separate declared subject kinds, typed source classifications, negative-quantity/provincial-string rejection, unchanged core report, preserved source/event/range/review context and atomic proposal. Parsed primary reading is recorded; direct raw-source retrieval timed out, so no raw-source hash/archive is claimed. Quantity/method/source/subject interpretation and legal/reuse review remain open. No activated Canadian regulatory pack, statutory total, adopted obligation, task/filing, conformity or v1 readiness is granted. Investment/reporting interfaces and this subsequent module await scoped owner review; all remaining roadmap and release requirements remain open.

## Subsequent source/species matrix awaiting scoped review

The neutral `source-species-ledger-0.2.0` helper follows approved cd0c991 without inheriting scoped approval. Review [the contract](source-species-ledger-contract.md) and [fictional evidence](../evaluations/sus19-source-species-ledger.md): unchanged parent mass/conversion replays, strict explicit measured-zero/GWP/date/source binding, unknown versus zero, separate included/excluded quantities, retained blocked/raw results, non-overlap, exact source views and atomic uncertainty/review custody. The only new profile is fictional; no real statutory roster or policy is imported. Source/attribution/method/quantity, legal exclusions, actual Canada threshold binding/activation, broader methods, independent organization acceptance and public-v1/release requirements remain open. This and prior later interfaces await scoped owner review; no legal or roadmap readiness follows.

## Subsequent direct species-mass extension awaiting scoped review

The neutral `source-species-ledger-0.3.0` measured-mass path follows approved cd0c991 without inheriting scoped approval. Review [the contract](source-species-ledger-contract.md) and [fictional evidence](../evaluations/sus19-direct-species-mass.md): explicit profile/status selection, nonnegative species measurements, unit/boundary/full-period/source/date/GWP confirmation, included/excluded direct quantities, raw uncertainty/result views and source/review custody. Old 0.2 profiles reject the new mode and saved complete outputs remain exact. No emission factor is inferred for a supplied direct mass; GWP provenance remains mandatory. The new profile is fictional. Source/method/attribution, actual statutory profile and Canada quantity binding/activation, independent acceptance and public-v1/release requirements remain open; no roadmap closure follows.

## Subsequent Canada quantity bridge awaiting scoped review

The `canada-quantity-screen-0.1.0` bridge and primary-linked 24-species/GWP/treatment data follow approved cd0c991 without inheriting scoped approval. Review [the contract](canada-quantity-bridge.md) and [fictional evaluation](../evaluations/sus19-canada-quantity-bridge.md): strict full-roster coefficient/source/period checks, explicit subject-facility coverage, cross-ledger non-overlap, retained biomass quantities, caller-supplied evidence-bound uncertainty ranges, no subtotal or original-total fallback, independent activity branches, exact source views and atomic review custody. Numeric/species transcription omits CAS and emission-factor tables; source-byte custody and semantic/scientific/legal/currentness/reuse decisions remain open. No actual regulatory quantity, legal finding, grouping authentication, sector-method validation, activated pack or filing authority is granted. This and prior later interfaces await scoped owner review; independent organization and full public-v1/release requirements remain open.

## Subsequent conditional Canada task workflow awaiting scoped review

The `canada-task-workflow-0.1.0` composition and source-linked original/amended task catalogs follow approved cd0c991 without inheriting scoped approval. Review [the contract](canada-task-workflow.md) and [fictional evidence](../evaluations/sus19-canada-tasks.md): fresh quantity/screen/task reproduction, exact edition/branch/date/ID selection, separate report/notification/certification/required-submission retention, preserved supported historical retention, conditional storage/parent-address contexts, no source/history/quantity fallback, exact source views and atomic review custody. Actual duties, receipts, operator changes, authorized signatory, storage/completion, source/method/currentness/legal/reuse and independent acceptance remain open; no external action or pack activation is granted. This and other later interfaces await scoped owner review; no public-v1 or roadmap closure follows.

## Scoped owner approval through 7bad9dd

- Reviewer: project owner via this development chat.
- User instruction: "approve the review".
- Reviewed revision/content snapshot: `7bad9dd3a07069b7a99979f80fd509ad0eb40486`.
- Decision/date: approved for continued roadmap development on 2026-10-06 (America/Toronto); no additional conditions stated.
- Scope: the pending development interfaces committed since approved cd0c991: investment and reporting specialists, Canada GHGRP predicate screening, neutral source/species matrix and direct species-mass extension, Canada quantity bridge, and conditional Canada task workflow with original/amended catalogs. This includes explicit versions, evidence-bound quantities and uncertainty, separate conditional outputs, exact source-result views, blocked and independent branches, and preserved state/history/review custody.
- Evidence: [Canada task validation](../evaluations/sus19-canada-tasks-validation.json) and [durable suite witness](../evaluations/sus19-canada-tasks-suite-run.json) record 747 passing repository tests, eight focused tests, twenty architecture checks and six actual CLI/helper cases. These are existing reviewed-snapshot results, not tests rerun for this approval. Earlier increment validation remains unchanged.

This decision supersedes pending scoped-owner-development-review descriptions for these interfaces through the reviewed revision. Historical records and draft labels retain their original meaning. Subsequent material changes require separate scoped review; no uncommitted or proposed extension is included.

Approval permits continued local roadmap development. Actual source authenticity/custody, scientific and sector-method fitness, Canadian legal applicability, duties, operator/signatory/receipt/storage verification, currentness and reuse rights, result/state reviews, independent organization acceptance and public-v1 requirements remain open. This approval does not activate a regulatory pack, approve an actual filing or public claim, close roadmap waves, establish v1 readiness, or authorize pushing, merging, publishing, releasing, deploying or third-party contact.

## Subsequent historical subject/operator task extension awaiting scoped review

The explicit `jurisdiction-tasks-0.3.0` and separate Canada history catalogs follow approved 7bad9dd without inheriting scoped approval. Review [the neutral contract](jurisdiction-model.md), [Canada composition](canada-task-workflow.md) and [fictional evidence](../evaluations/sus19-canada-task-history.md): evidence-bound matched same-subject reviews, preserved historical/current operator identities, explicit negative/unknown handling, older source-year date withholding, unchanged preceding-year notification selection, full source/review snapshots and original-catalog outputs. Parsed original-notice facility-history and operator-responsibility wording supports a conditional implementation interpretation only; actual continuity/authority/successor duties/source/legal/currentness/reuse and independent/public-v1 review remain open. No regulatory pack activation, actual duty, filing, storage verification or roadmap closure follows.
