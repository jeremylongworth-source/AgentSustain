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
| SUS-06 | GHG foundation | Eight skills, sourced-factor checks and CO2e helper; initial eight-skill author-led incomplete-inventory scenario recorded; broader independent behavioral evaluation remains |
| SUS-07 | Scope 1/2 | Five workflows, classification/composition helpers and CLIs, boundary review propagation, allocation/coverage and market checks; 25 helper tests, two synthetic CLI reproductions and an eight-step mixed-source workflow pass; independent behavioral evaluation and thermal-factor derivation remain |
| SUS-08 | Scope 3 | Five workflows; category, inventory, comparison and hotspot helpers/CLI; synthetic 725 kg partial inventory and -20% comparable partial-account change recorded; specialized methods and independent behavioral evaluation remain |
| SUS-09 | Energy | Seven workflows, four arithmetic helpers and bounded project screening; fictional arithmetic and interacting fan-project cases recorded; positive agent-driven usage/opportunity interpretation, engineering methods and independent evaluation remain |
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
| SUS-23 | Evaluation suite | 137 architecture/data/GHG/scope/inventory/energy/analysis/proposal/artifact tests pass; rerunnable scope 1/2/3, inventory comparison, hotspot, energy and project-screening cases recorded; independent and organization-wide end-to-end suites remain |
| SUS-24 | Documentation/examples | Foundation docs, shared data-skill guide and fictional schema fixtures |
| SUS-25 | Public v1 readiness | Not assessed; no release authorization |

## Current gate

The user approved the architecture pack at revision f2d0ac9 on 2026-10-04. The decision is recorded in architecture-review.md. SUS-05 and subsequent development may proceed in roadmap order. Architecture validation results in architecture-validation.md describe the reviewed snapshot and their limits; they do not establish domain correctness or v1 readiness. Material contract changes reopen architecture review.

## Next implementation work

Extend SUS-09 with positive agent-driven operational usage and opportunity interpretation, then develop SUS-10 waste/resources in roadmap order. Bounded project screening now reproduces supplied projected benefits, retains deferred candidates and checks declared interactions/range sensitivity. These cases do not establish engineering recommendations or verified savings. Extend specialized scope 3 and thermal-factor derivation as organization scenarios require; independent behavioral/source-format and organization-wide evaluations remain further work. No general reliability or v1 readiness is claimed.

The shared contract validator lives in scripts/contract_validation.py; tests/contract_checks.py remains a compatibility entrypoint. Schema shapes are unchanged. Runtime validation now additionally rejects nonfinite quantities and calculation-lineage cycles. State proposals preserve review obligations, assumptions, gaps and existing source records. Historical architecture hashes continue to identify the reviewed f2d0ac9 snapshot.
