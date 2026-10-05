# AgentSustain

AgentSustain is an evidence-driven sustainability agent-skill library for business analysis and practical action. Its domain library is called Sustainability Skills in the [roadmap](ROADMAP.md).

Intended users include manufacturers, logistics businesses, commercial facilities, SMEs, and sustainability consultants. The operational MVP connects data, carbon accounting, energy, waste, water, materials, and business-case analysis.

## Current status

Foundation architecture approved by the user on 2026-10-04 at revision f2d0ac9. The ten SUS-05 data skills, shared arithmetic helpers and checked state proposals have initial fictional scenario demonstrations. Broader agent reliability and end-to-end evaluation remain unproven. The mandatory [architecture review](docs/architecture-review.md) gate has passed, authorizing subsequent development in roadmap order. Architecture tests are not evidence of domain calculation correctness.

SUS-06 now contains eight GHG foundation skills and a sourced-factor CO2e calculation helper. [Its execution contract](docs/ghg-foundation-contract.md) describes factor applicability, fixture isolation and unsupported methods. Numerical examples are synthetic; no real emission-factor database or complete inventory workflow is provided.

SUS-07 has five scope 1/2 workflows and a [shared execution contract](docs/scope-1-2-contract.md). Classification checks supplied control/equity facts and retains uncertain sources; composition checks existing CO2e components, allocation, coverage and supplied market-quality records. A [mixed-source helper workflow](evaluations/sus07-composed-workflow.md) reruns all five skills. Independent behavioral evaluation remains in development.

SUS-08 adds [scope 3 and inventory workflows](docs/scope-3-inventory-contract.md), factual category classification, sourced physical-activity category composition and selected inventory accounts. A [composed fixture](evaluations/sus08-composed-workflow.md) retains unknown leased emissions and review requirements while producing a partial inventory subtotal. [Comparison and hotspot cases](evaluations/sus08-analysis-workflow.md) revalidate inventories and preserve coverage/denominator limits. Specialized category derivations and independent behavioral evaluation remain in development.

SUS-09 adds seven [energy workflows](docs/energy-contract.md) and helpers for baselines, intensity, use contributions, explicitly labeled savings arithmetic and bounded project screening. An [initial fictional workflow](evaluations/sus09-energy-workflow.md) records supported calculations and missing-context handling; a [project case](evaluations/sus09-project-screening.md) retains interacting alternatives, deferred candidates and sensitivity. An [author-led equipment investigation](evaluations/sus09-equipment-workflow.md) preserves service and calibration gaps. Engineering methods and independent evaluation remain in development.

SUS-10 adds ten [waste/resource workflows](docs/waste-resource-contract.md) and seven helpers. A [composed fixture](evaluations/sus10-mass-workflow.md) calculates waste generation, explicitly defined known diversion, mass contributions, material consumption and intensity while retaining unknown treatment. [Balance and invoice cases](evaluations/sus10-loss-cost-workflows.md) separate measured loss from unexplained residuals and recorded charges from credits. An [author-led opportunity scenario](evaluations/sus10-opportunity-workflow.md) retains unknown residue and unquantified candidates. Independent evaluation remains in development.

SUS-11 adds five [water workflows](docs/water-contract.md) and three helpers for same-basis volumes, intensity and contributions. A [selected withdrawal fixture](evaluations/sus11-water-workflow.md) retains missing catchment context; an [author-led dependency example](evaluations/sus11-dependency-workflow.md) preserves unquantified investigations and engineering review. Consumption/storage methods and independent evaluation remain in development.

SUS-12 adds thirteen [economics workflows](docs/finance-contract.md) with initial deterministic methods for initial cost, projected annual net savings, simple payback, horizon ROI, annual NPV, bounded annual IRR, annual cash-flow composition, explicit energy/resource/carbon price paths, project cost per abatement, comparison, screening ranks and evidence-linked business cases. A [fictional financial case](evaluations/sus12-finance-workflow.md) preserves explicit economic assumptions and signed results; [cost/savings composition](evaluations/sus12-composed-cost-savings.md) includes maintenance and unchanged fixed charges before payback. [IRR cases](evaluations/sus12-irr-cases.md) retain ambiguous roots and verify numerical residuals. [Annual cash-flow composition](evaluations/sus12-cashflow-composition.md) feeds sourced cost/savings into NPV/IRR. [Explicit price paths](evaluations/sus12-price-paths.md) preserve annual units and distinguish carbon shadow values from payments. [Cost-per-abatement cases](evaluations/sus12-abatement-cost.md) match costs and physical reduction over a common horizon. [Project comparison/ranking](evaluations/sus12-project-comparison.md) preserves explicit priorities, ties, ranges and interacting alternatives. [Business-case composition](evaluations/sus12-business-case.md) connects rechecked physical/financial alternatives, sensitivity and ownership to pending human decisions. Broader tariffs/timing/ranking methods and independent business-case/organization evaluation remain in development.

SUS-13 now adds the [sustainable-operations skillset](skillsets/sustainable-operations/SKILL.md), [bounded composition contract](docs/operations-contract.md) and a [fictional cross-domain replay](evaluations/sus13-operations-composition.md). Source assessments feed candidate opportunities and proposed owned actions, preserving missing data, engineering gates and pending business-case decisions. The initial composition and dependency manifest have [human approval for continued development](docs/operations-review.md). One independent raw-source scenario prompted a corrected data-only review gate. [Proposed action dependencies](evaluations/sus13-action-sequence.md) now validate cross-domain precedence and dates; broader planning and evaluation remain.

Start with [development status](docs/development-status.md), [domain contract](docs/domain-contract.md), and [architecture](docs/architecture.md). `ROADMAP.md` remains authoritative for scope and sequencing. Material changes to the approved architecture contracts require renewed review.

## Validate the architecture pack

Requires Python 3.11 or later. JSON Schema is a development dependency; consumers of future skills need not use Python.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Schemas use JSON Schema Draft 2020-12. The same test command runs architecture, data, GHG, scope-composition and saved-artifact checks. Examples are fictional fixtures, not emission factors or advice for a real organization. No license has been chosen yet; public release is gated on the owner's licensing decision.

## Data skills

SUS-05 covers data normalization/validation, evidence quality, gaps, units, reporting periods, organizational boundaries, baselines, KPIs and period comparisons. Skill entrypoints live under `skills/metrics/`; each links to the [shared execution contract](docs/data-skill-contract.md). They are repository artifacts, not installed into a user's agent configuration. Helpers are portable Python and require no network access. They provide primitives; skills must wrap results with provenance and validate proposed shared state.
