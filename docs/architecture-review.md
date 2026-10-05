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

## SUS-18 execution extension awaiting scoped review

The original f2d0ac9 architecture approval remains recorded above. The initial executable jurisdiction semantics extend the reviewed interface and reopen scoped review under the material-contract-change rule. This extension has no owner approval yet. Review [jurisdiction-model.md](jurisdiction-model.md), `scripts/jurisdiction_tools.py`, `scripts/run_jurisdiction.py`, the fictional module under `standards/jurisdictions/fixtures/`, tests and [saved scenario evidence](../evaluations/sus18-jurisdiction-foundation.md) together. The final validation record identifies exact file hashes; successful tests do not approve this extension.

Review scope includes exact byte/version selection, typed whole-period entity facts, separate source/currency fitness, three-valued threshold/exception predicates, inclusive effective-date segmentation, historical repeal/proposed-status handling, jurisdiction overlap without hierarchy/precedence inference, source snapshots and append-only legal-review propagation. Shared state schemas, neutral core calculations, original architecture approval and all existing professional/source/owner/release gates remain unchanged. Actual Canadian rules, independent source interpretation and organization coverage remain open.
