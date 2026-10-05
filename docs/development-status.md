# Development status

ROADMAP.md is authoritative. Snapshot: 2026-10-04, America/Toronto.

## Repository

Authenticated access verified the intended GitHub repository is private and empty. Local Git was initialized on `main` with the supplied URL as `origin`; no content has been pushed. The original roadmap was preserved.

## Waves

| Wave | Deliverable | Current evidence/status |
|---|---|---|
| SUS-00 | Research consolidation | Initial official-source orientation recorded; domain research remains incremental |
| SUS-01 | Domain contract | Architecture approved by user on 2026-10-04 at f2d0ac9 |
| SUS-02 | Master taxonomy | Architecture approved; all roadmap-listed names included |
| SUS-03 | Evidence/provenance | Contract and schema approved for implementation |
| SUS-04 | Common schemas/state | Architecture approved; 20 architecture tests passed at review snapshot |
| SUS-05 | Data skills | Ten skills with five helper operations and checked state proposals; nine initial author-led scenarios and shared-document rerun recorded; broader behavioral reliability remains unproven |
| SUS-06 | GHG foundation | Not implemented |
| SUS-07 | Scope 1/2 | Not implemented |
| SUS-08 | Scope 3 | Not implemented |
| SUS-09 | Energy | Not implemented |
| SUS-10 | Waste/resources | Not implemented |
| SUS-11 | Water | Not implemented |
| SUS-12 | Economics/business case | Not implemented |
| SUS-13 | Operations composition | Not implemented |
| SUS-14 | Procurement/supply chain | Not implemented |
| SUS-15 | Strategy/targets | Not implemented |
| SUS-16 | Climate risk | Not implemented |
| SUS-17 | Reporting adapters | Not implemented; interface draft only |
| SUS-18 | Jurisdiction architecture | Not implemented; interface draft only |
| SUS-19 | Canada pack | Not implemented |
| SUS-20 | Claims controls | Not implemented |
| SUS-21 | Router | Not implemented; interface draft only |
| SUS-22 | Specialist skillsets | Not implemented |
| SUS-23 | Evaluation suite | 51 architecture/helper/proposal/artifact tests pass; author-led scenario outputs recorded; independent and end-to-end suites remain |
| SUS-24 | Documentation/examples | Foundation docs, shared data-skill guide and fictional schema fixtures |
| SUS-25 | Public v1 readiness | Not assessed; no release authorization |

## Current gate

The user approved the architecture pack at revision f2d0ac9 on 2026-10-04. The decision is recorded in architecture-review.md. SUS-05 and subsequent development may proceed in roadmap order. Architecture validation results in architecture-validation.md describe the reviewed snapshot and their limits; they do not establish domain correctness or v1 readiness. Material contract changes reopen architecture review.

## Next implementation work

Begin SUS-06 GHG foundations using authoritative methodology sources, without inventing emission factors. The initial SUS-05 author-led scenarios have checked outputs and state proposals; the discovered shared-document aggregation limit was addressed with explicit source-fragment coverage and a successful rerun. Continue broader behavioral and source-format evaluations as later capabilities consume these foundations; no general reliability or v1 readiness is claimed.

The shared contract validator lives in scripts/contract_validation.py; tests/contract_checks.py remains a compatibility entrypoint. Schema shapes are unchanged. Runtime validation now additionally rejects nonfinite quantities and calculation-lineage cycles. State proposals preserve review obligations, assumptions, gaps and existing source records. Historical architecture hashes continue to identify the reviewed f2d0ac9 snapshot.
