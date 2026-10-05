# AgentSustain

AgentSustain is an evidence-driven sustainability agent-skill library for business analysis and practical action. Its domain library is called Sustainability Skills in the [roadmap](ROADMAP.md).

Intended users include manufacturers, logistics businesses, commercial facilities, SMEs, and sustainability consultants. The operational MVP connects data, carbon accounting, energy, waste, water, materials, and business-case analysis.

## Current status

Foundation architecture approved by the user on 2026-10-04 at revision f2d0ac9. The ten SUS-05 data skills, shared arithmetic helpers and checked state proposals have initial fictional scenario demonstrations. Broader agent reliability and end-to-end evaluation remain unproven. The mandatory [architecture review](docs/architecture-review.md) gate has passed, authorizing subsequent development in roadmap order. Architecture tests are not evidence of domain calculation correctness.

SUS-06 now contains eight GHG foundation skills and a sourced-factor CO2e calculation helper. [Its execution contract](docs/ghg-foundation-contract.md) describes factor applicability, fixture isolation and unsupported methods. Numerical examples are synthetic; no real emission-factor database or complete inventory workflow is provided.

SUS-07 has five initial scope 1/2 instruction workflows and a [shared execution contract](docs/scope-1-2-contract.md). Dedicated scope calculation composition and scenario evaluation remain in development.

Start with [development status](docs/development-status.md), [domain contract](docs/domain-contract.md), and [architecture](docs/architecture.md). `ROADMAP.md` remains authoritative for scope and sequencing. Material changes to the approved architecture contracts require renewed review.

## Validate the architecture pack

Requires Python 3.11 or later. JSON Schema is a development dependency; consumers of future skills need not use Python.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Schemas use JSON Schema Draft 2020-12. The same test command runs architecture and data-helper checks. Examples are fictional fixtures, not emission factors or advice for a real organization. No license has been chosen yet; public release is gated on the owner's licensing decision.

## Data skills

SUS-05 covers data normalization/validation, evidence quality, gaps, units, reporting periods, organizational boundaries, baselines, KPIs and period comparisons. Skill entrypoints live under `skills/metrics/`; each links to the [shared execution contract](docs/data-skill-contract.md). They are repository artifacts, not installed into a user's agent configuration. Helpers are portable Python and require no network access. They provide primitives; skills must wrap results with provenance and validate proposed shared state.
