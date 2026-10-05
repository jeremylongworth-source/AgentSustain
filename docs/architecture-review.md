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
