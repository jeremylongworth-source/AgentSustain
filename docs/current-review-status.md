# Current development review status

This is a discovery index, not a new approval. [The owner decision ledger](architecture-review.md) is authoritative. Latest explicit owner development approval covers content snapshot `da4ddb3827931589b1fbf1f95cfef13fcac4075e`, recorded on 2026-10-06. Original architecture approval covers `f2d0ac9b5b34a4eef3f2678173d387d16fe0784c`.

## How to interpret frozen instructions

Some byte-pinned skill/manifests still say their subsequent interface awaits scoped review. Those statements record the original draft state. The later owner decisions supersede pending development-review descriptions only for their named interfaces through their exact reviewed snapshots. Read the decision ledger and inspect current content before treating a historical sentence as a new permission request. No permission should be invented or extended to material later changes.

Pinned skill assets and the specialist router remain unchanged. The seven-specialist router uses capability snapshot `7bad9dd3a07069b7a99979f80fd509ad0eb40486` and validates actual historical/current assets; broader owner approval does not silently change that pin or its available callbacks.

| Development interface | Current recorded owner-development status | Authority / limits |
|---|---|---|
| SUS-01 through SUS-04 architecture | Approved at f2d0ac9 | Original decision ledger; individual skills may be developed under this foundation |
| Core/helper and initial seven specialist compositions through ba42b4e | Covered by the ledger's successive scoped decisions | Latest approval supersedes pending wording for committed named interfaces; current byte drift must still be checked |
| Historical task/operator reconciliation, fuel energy/CO2e bridge, specialist routing, literal workbook import and selected water reconciliation through ba42b4e | Approved for continued local roadmap development | Latest ba42b4e decision explicitly names these interfaces |
| Conditional thermal-performance interface added in b8ec407 | Approved for continued local roadmap development through da4ddb3 | [Contract](thermal-performance-contract.md); source/scientific/engineering review remains separate |
| Optional CSV 0.2 classification and organization acceptance added in 6670800 | Approved for continued local roadmap development through da4ddb3 | [Source contract](business-ingestion-contract.md), [acceptance map](organization-acceptance.md) |
| Acceptance input-control correction in f5a82ac | Approved for continued local roadmap development through da4ddb3 | [Regression evidence](../evaluations/sus23-acceptance-input-controls.md); valid/refusal captures remain exact |
| Local platform workflow and Python 3.11/3.12/3.14 evidence | Validation evidence only | [Platform evidence](platform-validation.md); no GitHub dispatch, publication or release approval |
| Required food-manufacturer case added in 000e7cc | Later controlled evaluation artifacts; excluded from approval through da4ddb3 | [Workflow](food-manufacturer-workflow.md); existing runtime/assets unchanged, no independent acceptance or release approval |

Development approval does not authenticate sources, settle scientific/financial/legal/engineering judgments, approve statutory applicability or filing, resolve result/state review ledgers, authorize implementation/funding/public claims, close roadmap waves or establish public-v1 readiness. Source/currentness/reuse rights, independent expert/agent/organization acceptance and owner license/security/contribution/release decisions remain open. No license has been chosen. No push, merge, publish, deploy, release or third-party contact is authorized.
