# SUS-02 through SUS-04: Architecture and scaffolding

Status: proposed. Authority: ROADMAP.md sections 3, 22, 23, 26.

## Layers and workflow

Evidence enters normalized shared state. Atomic skills read validated state and emit a common result envelope plus explicit proposed state changes. Skillsets compose these results, retaining lineage and review obligations. The router selects approved capabilities; framework adapters map core results to disclosure requirements; jurisdiction modules add geographically and temporally scoped applicability screening.

Core calculations must not import jurisdiction-specific legal logic or replicate a calculation per framework. Inputs and outputs remain portable JSON-compatible objects; no hosted service, model provider, or agent runtime is required by the contract.

## Scaffolding specification

| Path | Responsibility | First wave |
|---|---|---|
| docs/ | Contracts, taxonomy, sources, review and progress evidence | SUS-00-04 |
| schemas/ | Versioned evidence, result and shared-state schemas | SUS-03-04 |
| skills/{family}/{skill-name}/SKILL.md | Atomic capability, references, optional deterministic helpers | SUS-05 onward |
| skillsets/{skillset-name}/ | Composed workflow and dependency manifest | SUS-13, SUS-22 |
| standards/{framework}/ | Versioned mapping and methodology adapter | SUS-17 |
| standards/jurisdictions/{country}/ | Jurisdiction modules, subdivisions and effective versions | SUS-18-19 |
| templates/ | Evidence-preserving reports and action plans | With consuming skill |
| examples/ | Fictional reproducible workflows | Each implemented wave; SUS-24 |
| scenarios/ | Routing and behavioral fixtures | Each implemented wave; SUS-23 |
| evaluations/ | Scored results with versions, failures and limitations | Each implemented wave |
| tests/ | Schema and deterministic known-answer/error tests | SUS-04 onward |

Use `standards/jurisdictions/` as the single jurisdiction location (roadmap section 3); section 15's standalone tree describes its internal organization. Avoid two competing stores. Family directories and future-wave files are created when used, not as empty placeholders. `engagement` is a cross-family tag under strategy, procurement, supply-chain and implementation; it does not create a seventeenth taxonomy family.

## Dependency and version rules

Each future skill declares its name, contract version, family, dependencies, input requirements, allowed outputs, methods, safety states and scenarios. Dependencies must resolve and be acyclic. Contract versions use semantic versioning; changing meaning, required fields, unit policy or review-state handling requires a major version and explicit migration. This pack uses draft `0.1.0`; it is not a stable release promise.

State changes carry base revision, added/updated IDs, provenance and reasons. Reject stale revisions, dangling references, and deletions that destroy lineage. Validate the complete candidate state before accepting a revision. Mutations are proposed, not silently applied by a router or adapter. Multi-user storage and runtime persistence are intentionally undecided until a consumer requires them.

## Implementation sequence

Research consolidation precedes domain, taxonomy, evidence and common schema review. After explicit architecture approval, SUS-05 establishes data foundations; SUS-06-08 establish GHG foundations and scopes; SUS-09-13 build the operational MVP; SUS-14-22 add advanced capabilities; SUS-23-25 consolidate evaluation, documentation and readiness. Testing is incremental, not postponed to SUS-23.

## Open owner decisions

Approve or revise the architecture pack before skill development. Select a license before public distribution. Public publishing is a separate authorization. No customer interviews or proprietary datasets have been supplied; target-user needs currently come from the roadmap.
