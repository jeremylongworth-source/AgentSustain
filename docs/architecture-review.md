# SUS-01 through SUS-04 architecture review

Status: PENDING HUMAN REVIEW. No individual skill implementation is authorized yet.

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

- Reviewer: pending
- Reviewed revision/content snapshot: pending
- Decision and date: pending
- Conditions or requested changes: pending
- Implementation authorization: not granted

Record explicit user approval with the reviewed revision and conditions. Material contract changes reopen review. Preserve this record; never substitute an agent's self-review for the required human decision.
