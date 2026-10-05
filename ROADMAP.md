# Sustainability Skills Development Roadmap

## 1. Project Mission

**Sustainability Skills** is a standalone, evidence-driven business sustainability agent-skill library designed to provide reusable AI-agent capabilities for organizations that need to:

- Understand sustainability obligations and opportunities.
- Measure environmental performance.
- Build credible sustainability strategies.
- Calculate and manage greenhouse gas (GHG) inventories.
- Identify operational efficiency opportunities.
- Evaluate sustainability investments.
- Manage suppliers and Scope 3 data.
- Prepare sustainability disclosures.
- Assess climate risks.
- Establish targets and transition plans.
- Substantiate environmental claims.
- Convert sustainability objectives into executable business actions.

The project follows the AgentSkills philosophy:

> **evidence -> structured analysis -> decision support -> action plan -> verification**

The project must not position an AI agent as an auditor, certifier, lawyer, professional engineer, financial adviser, or authoritative interpreter of regulation.

---

## 2. Design Principles

Sustainability Skills should be built around the following principles:

1. **Evidence first** - analytical conclusions should be traceable to evidence, methodologies, assumptions, and calculations.
2. **Atomic and composable** - small reusable skills should be composed into professional workflows and specialist skillsets.
3. **Vendor neutral** - core skills should not depend on a specific software vendor or AI platform.
4. **Framework adaptable** - reporting and methodology frameworks should be adapters around shared core capabilities rather than duplicated implementations.
5. **Jurisdiction aware** - regulatory requirements should be isolated in versioned jurisdiction modules.
6. **Human review where required** - legal, assurance, engineering, certification, and other professional decisions must be escalated appropriately.
7. **Operationally useful** - sustainability analysis should connect environmental outcomes with cost, risk, implementation feasibility, and business performance.
8. **Testable** - calculations, routing, evidence handling, and safety behavior should have scenario-based evaluations and known-answer fixtures.

---

## 3. Proposed Repository Architecture

```text
SustainabilitySkills/
|
|-- README.md
|-- LICENSE
|-- CONTRIBUTING.md
|-- SECURITY.md
|
|-- docs/
|   |-- domain-contract.md
|   |-- architecture.md
|   |-- evidence-policy.md
|   |-- safety-boundaries.md
|   |-- terminology.md
|   |-- framework-registry.md
|   `-- jurisdiction-model.md
|
|-- skills/
|   |-- strategy/
|   |-- carbon/
|   |-- energy/
|   |-- resources/
|   |-- waste/
|   |-- circularity/
|   |-- water/
|   |-- procurement/
|   |-- supply-chain/
|   |-- climate-risk/
|   |-- reporting/
|   |-- compliance/
|   |-- claims/
|   |-- finance/
|   |-- metrics/
|   |-- engagement/
|   `-- implementation/
|
|-- skillsets/
|   |-- sustainability-manager/
|   |-- carbon-accounting/
|   |-- sustainable-operations/
|   |-- sustainable-procurement/
|   |-- climate-risk/
|   |-- sustainability-reporting/
|   `-- sustainability-business-case/
|
|-- standards/
|   |-- ghg-protocol/
|   |-- issb/
|   |-- gri/
|   |-- sbti/
|   |-- tnfd/
|   |-- esrs/
|   |-- iso/
|   `-- jurisdictions/
|
|-- schemas/
|-- templates/
|-- examples/
|-- scenarios/
|-- evaluations/
`-- tests/
```

The architecture deliberately separates:

- **skills** - atomic reusable capabilities;
- **skillsets** - composed professional workflows;
- **standards/framework adapters** - methodology and disclosure mappings;
- **jurisdiction modules** - geographically specific requirements.

This prevents core analytical skills from becoming permanently coupled to one jurisdiction or disclosure framework.

---

## 4. Domain Taxonomy

The initial master taxonomy contains 16 primary skill families.

| ID | Skill Family | Purpose |
|---|---|---|
| SUS-01 | Sustainability Strategy | Business sustainability planning |
| SUS-02 | GHG / Carbon | Scope 1, 2, and 3 inventories |
| SUS-03 | Energy | Energy analysis and efficiency |
| SUS-04 | Resource Efficiency | Material and resource productivity |
| SUS-05 | Waste | Waste measurement and reduction |
| SUS-06 | Circularity | Circular business practices |
| SUS-07 | Water | Water use, risk, and efficiency |
| SUS-08 | Sustainable Procurement | Purchasing and supplier requirements |
| SUS-09 | Supply Chain | Supplier sustainability and Scope 3 |
| SUS-10 | Climate Risk | Physical and transition risk |
| SUS-11 | Reporting & Disclosure | Sustainability reporting workflows |
| SUS-12 | Compliance Intelligence | Requirements and applicability |
| SUS-13 | Environmental Claims | Claims substantiation and greenwashing controls |
| SUS-14 | Sustainable Finance | ROI, NPV, and sustainability investments |
| SUS-15 | Metrics & Data | KPIs, evidence, and benchmarking |
| SUS-16 | Implementation | Programs, ownership, and change management |

These families form the first level of the master skill taxonomy.

---

## 5. Phase 0 - Domain Contract

Before individual skills are implemented, create:

```text
docs/domain-contract.md
```

The domain contract defines what Sustainability Skills is permitted to do and where professional review is required.

### Permitted Capabilities

The system may:

- Collect sustainability information.
- Classify evidence.
- Calculate metrics.
- Identify data gaps.
- Perform scenario analysis.
- Compare performance.
- Explain frameworks.
- Prepare draft reports.
- Develop action plans.
- Perform preliminary regulatory applicability analysis.
- Assess sustainability opportunities.
- Analyze investments.
- Identify potential risks.
- Check environmental claims against available evidence.

### Restricted Capabilities

Explicit qualification or escalation is required for:

- Legal conclusions.
- Regulatory compliance determinations.
- Certification.
- Assurance opinions.
- Engineering certification.
- Investment recommendations.
- Official GHG verification.
- Authoritative life-cycle assessment assertions.
- Definitive statements of conformity with ISO standards.

### Standard Review States

```text
ADVISORY
ANALYTICAL
EVIDENCE_INCOMPLETE
PROFESSIONAL_REVIEW_REQUIRED
LEGAL_REVIEW_REQUIRED
ASSURANCE_REQUIRED
ENGINEERING_REVIEW_REQUIRED
```

Relevant skill contracts should expose these states consistently.

---

## 6. Phase 1 - Evidence and Provenance Architecture

Sustainability work depends heavily on evidence quality. The repository should implement a common evidence hierarchy.

### Tier 1 - Primary Evidence

Examples:

- Utility bills.
- Invoices.
- Fuel records.
- Meter readings.
- ERP records.
- Supplier records.
- Transportation records.
- Purchase orders.
- Production records.

### Tier 2 - Authoritative Methodology

Examples include current methodologies and standards maintained by recognized organizations such as:

- GHG Protocol.
- International Sustainability Standards Board (ISSB).
- Global Reporting Initiative (GRI).
- Science Based Targets initiative (SBTi).
- Relevant ISO standards.

### Tier 3 - Government and Regulatory Sources

Federal, provincial/state, municipal, European Union, and other applicable governmental or regulatory authorities.

### Tier 4 - Secondary Evidence

Examples:

- Industry studies.
- Recognized databases.
- Peer-reviewed or reputable research.
- Industry association data.

### Tier 5 - Assumptions and Proxies

Examples:

- Industry averages.
- Estimates.
- Proxy data.
- Inferred values.

### Common Provenance Record

Every significant analytical output should be capable of preserving:

```yaml
source:
method:
period:
unit:
quality:
assumption:
uncertainty:
calculation:
```

Provenance is a foundational architectural requirement, not an optional reporting feature.

---

## 7. Phase 2 - Core Atomic Data Skills

Development should begin with small composable skills rather than large "Sustainability Consultant" prompts.

Initial data-foundation skills:

```text
normalize-sustainability-data
validate-sustainability-data
classify-evidence-quality
detect-data-gaps
normalize-units
normalize-reporting-period
map-organizational-boundary
build-sustainability-baseline
calculate-sustainability-kpi
compare-period-performance
```

These capabilities become dependencies for later domain-specific skills.

---

## 8. Phase 3 - Carbon Accounting Skillset

Carbon accounting should become one of the deepest initial technical modules.

### Atomic Skills

```text
define-ghg-inventory-boundary
identify-emission-sources
classify-scope-1-emissions
classify-scope-2-emissions
classify-scope-3-emissions

select-emission-factor
validate-emission-factor
calculate-co2e

calculate-scope-1
calculate-location-based-scope-2
calculate-market-based-scope-2
calculate-scope-3-category

identify-ghg-data-gaps
estimate-missing-activity-data
assess-ghg-data-quality

build-ghg-inventory
compare-ghg-inventories
identify-emission-hotspots
```

### Emission Factor Safety Rule

Emission factors must never silently appear from model knowledge.

A factor should have traceable:

- Source.
- Geography.
- Vintage/year.
- Units.
- Applicable methodology.

When a defensible factor is unavailable, the skill should return:

```text
EMISSION_FACTOR_REQUIRED
```

rather than inventing a value.

---

## 9. Phase 4 - Sustainable Operations

The operations layer should make Sustainability Skills useful to ordinary businesses, not only ESG departments.

### Energy

```text
build-energy-baseline
calculate-energy-intensity
detect-energy-hotspots
analyze-energy-usage
identify-efficiency-opportunities
estimate-energy-savings
prioritize-energy-projects
```

### Waste

```text
build-waste-baseline
classify-waste-streams
calculate-diversion-rate
identify-waste-hotspots
analyze-waste-cost
identify-waste-reduction-opportunities
```

### Water

```text
build-water-baseline
calculate-water-intensity
identify-water-hotspots
assess-water-dependency
identify-water-efficiency-opportunities
```

### Materials

```text
analyze-material-consumption
calculate-material-intensity
identify-material-loss
identify-resource-efficiency-opportunities
```

A key project objective is connecting **sustainability performance to operating cost and operational performance**.

---

## 10. Phase 5 - Sustainable Procurement and Supply Chain

Develop reusable supplier and supply-chain capabilities.

```text
screen-supplier-sustainability-risk
build-supplier-questionnaire
evaluate-supplier-response
score-supplier-sustainability
identify-supplier-data-gaps
compare-suppliers
develop-supplier-improvement-plan

map-supply-chain-emissions
identify-scope-3-hotspots
prioritize-supplier-engagement
evaluate-low-carbon-procurement-option
```

### Example Composed Workflow

```text
Purchase History
      |
Supplier Segmentation
      |
Sustainability Risk
      |
Scope 3 Relevance
      |
Supplier Evidence
      |
Supplier Score
      |
Engagement Priority
      |
Improvement Plan
```

---

## 11. Phase 6 - Sustainability Economics

Sustainability decisions frequently require capital allocation. Financial analysis should therefore be a dedicated skill family.

### Skills

```text
calculate-sustainability-project-cost
calculate-operating-savings
calculate-simple-payback
calculate-roi
calculate-npv
calculate-irr

model-energy-price-scenario
model-carbon-price-scenario
model-resource-cost-scenario

calculate-marginal-abatement-cost
compare-sustainability-projects
rank-sustainability-investments
build-sustainability-business-case
```

The intended transformation is from a general objective such as:

> Reduce emissions.

to an actionable decision such as:

> These projects provide the strongest combination of cost reduction, emissions reduction, implementation feasibility, and risk reduction.

---

## 12. Phase 7 - Strategy and Target Setting

The strategy layer should be built after the analytical foundations exist.

### Skills

```text
assess-sustainability-maturity
identify-material-sustainability-issues
map-stakeholders
identify-sustainability-risks
identify-sustainability-opportunities

establish-baseline
define-kpis
develop-target
evaluate-target-feasibility

build-sustainability-strategy
build-transition-plan
build-implementation-roadmap
assign-accountability
```

### Strategy Workflow

```text
Current State
     |
Material Issues
     |
Baseline
     |
Risks + Opportunities
     |
Targets
     |
Initiatives
     |
Investment
     |
Roadmap
     |
KPIs
     |
Monitoring
```

---

## 13. Phase 8 - Climate Risk

Physical and transition risk should be modeled separately before being combined into an organization-level climate-risk register.

### Physical Risk Skills

```text
identify-climate-hazards
map-assets-to-hazards
assess-exposure
assess-vulnerability
score-physical-risk
identify-adaptation-options
```

### Transition Risk Skills

```text
identify-policy-risk
identify-market-risk
identify-technology-risk
identify-reputation-risk
assess-transition-exposure
```

### Composed Skills

```text
build-climate-risk-register
prioritize-climate-risks
develop-climate-resilience-plan
```

The system must distinguish high-level climate-risk screening from specialist climate modelling.

---

## 14. Phase 9 - Reporting Framework Adapters

Core sustainability logic should not be duplicated for every reporting framework.

### Adapter Architecture

```text
Core Sustainability Data
          |
Framework Adapter
          |
Disclosure Requirements
          |
Gap Analysis
          |
Evidence Mapping
          |
Draft Disclosure
```

Initial adapters may cover:

```text
GHG Protocol
ISSB / IFRS S1
ISSB / IFRS S2
GRI
CDP
TNFD
SBTi
ESRS
```

Framework metadata should be versionable:

```yaml
framework: ESRS
version:
effective_date:
jurisdiction:
source:
```

This allows standards to evolve without requiring core analytical skills to be rewritten.

---

## 15. Phase 10 - Jurisdiction Packs

Regulatory logic should follow the same modular principle.

```text
jurisdictions/
|-- canada/
|   |-- federal/
|   `-- provinces/
|-- united-states/
|   |-- federal/
|   `-- states/
|-- european-union/
|-- united-kingdom/
`-- ...
```

Canada should be the first reference implementation.

### Proposed Canada Structure

```text
canada/
|-- applicability/
|-- carbon/
|-- climate-disclosure/
|-- environmental-claims/
|-- energy/
|-- waste/
|-- procurement/
`-- reporting/
```

The underlying sustainability skills remain jurisdiction-neutral.

---

## 16. Phase 11 - Environmental Claims Guardrail

Environmental claims substantiation should become a signature safety capability.

### Claims Pipeline

```text
Environmental Claim
        |
Classify Claim
        |
Identify Required Evidence
        |
Inspect Evidence
        |
Check Scope / Boundary
        |
Check Qualifications
        |
Check Methodology
        |
Check Time Period
        |
Assess Substantiation
```

### Standard Claim States

```text
SUPPORTED
SUPPORTED_WITH_QUALIFICATION
INSUFFICIENT_EVIDENCE
POTENTIALLY_MISLEADING
PROFESSIONAL_REVIEW_REQUIRED
```

For a claim such as:

> "Our factory is carbon neutral."

the system should examine:

- Organizational and operational boundary.
- Reporting period.
- Emissions inventory.
- Reduction methodology.
- Offsets or credits.
- Residual emissions.
- Supporting evidence.
- Applicable claims requirements.

It should not simply rewrite or strengthen the marketing claim.

---

## 17. Phase 12 - Composed Professional Skillsets

Atomic skills should be composed into professional agent skillsets.

### Sustainability Manager

```text
skillsets/sustainability-manager/
```

Combines strategy, metrics, operations, reporting, and implementation.

### Carbon Accountant

```text
skillsets/carbon-accounting/
```

Combines boundaries, activity data, emission factors, calculations, QA, and reporting.

### Sustainable Operations Analyst

```text
skillsets/sustainable-operations/
```

Combines energy, materials, water, waste, and financial analysis.

### Sustainable Procurement Analyst

```text
skillsets/sustainable-procurement/
```

Combines supplier analysis, Scope 3, risk, and procurement.

### Climate Risk Analyst

```text
skillsets/climate-risk/
```

### Sustainability Reporting Specialist

```text
skillsets/sustainability-reporting/
```

### Sustainability Investment Analyst

```text
skillsets/sustainability-business-case/
```

---

## 18. Phase 13 - Router Architecture

The project should eventually route user requests to appropriate skills and composed workflows.

### Example: Operational Sustainability Request

```text
"How can my factory cut its carbon footprint?"
                 |
          Intent Router
                 |
     Sustainable Operations
                 |
        Establish Baseline
                 |
         Carbon Inventory
                 |
         Hotspot Analysis
                 |
     Efficiency Opportunities
                 |
       Financial Evaluation
                 |
       Prioritized Roadmap
```

### Example: Regulatory Request

```text
"Does CSRD apply to my company?"
             |
     Regulatory Request
             |
        Jurisdiction
             |
    Framework / Version
             |
     Company Attributes
             |
 Applicability Screening
             |
 Evidence + Uncertainty
             |
LEGAL_REVIEW_REQUIRED when appropriate
```

Routing should preserve evidence, uncertainty, and review requirements.

---

## 19. Phase 14 - Shared State Model

Complex sustainability workflows require persistent analytical state.

### Recommended Schema

```yaml
organization:
facilities:
jurisdictions:
reporting_period:
organizational_boundary:

energy:
water:
materials:
waste:

ghg:
  scope_1:
  scope_2:
  scope_3:

suppliers:

targets:

risks:

opportunities:

projects:

frameworks:

evidence:

assumptions:

data_gaps:

review_requirements:
```

Individual skills should operate on this common state instead of repeatedly rebuilding context.

---

## 20. Phase 15 - Evaluation Framework

Every major skill should have scenario fixtures and known-answer tests.

### Example Evaluation Organization

```text
Canadian food manufacturer
150 employees
2 facilities

Electricity
Natural gas
Diesel fleet
Refrigerants
Purchased packaging
Waste
Water
Inbound freight
Outbound freight
Business travel
Purchased ingredients
```

### Known-Answer Calculation Test

```text
electricity = X kWh
factor = Y kg CO2e/kWh

expected:
emissions = X * Y
```

Tests should validate:

- Calculation correctness.
- Unit conversion.
- Source preservation.
- Rounding.
- Emission-factor year.
- Geography.
- Uncertainty.

### Adversarial and Error Fixtures

The evaluation suite should deliberately contain:

```text
missing units
wrong factor geography
duplicate invoices
mixed reporting periods
supplier estimates
unknown refrigerant
outdated emission factor
market-based/location-based confusion
```

The expected behavior is to detect and surface these problems rather than confidently calculate from invalid inputs.

---

## 21. Recommended MVP

The MVP should focus on operational usefulness rather than beginning with ESG disclosure.

### Sustainability Skills MVP 0.1

```text
Sustainability Data
        +
GHG Accounting
        +
Energy
        +
Waste
        +
Water
        +
Resource Efficiency
        +
Business Case Analysis
```

Approximately **50-70 carefully engineered atomic skills** should provide a substantial initial repository.

### Initial Target Users

The MVP should be useful to:

- Manufacturers.
- Warehouses.
- Wholesalers.
- Restaurants.
- Offices.
- Commercial buildings.
- Logistics businesses.
- Small and medium-sized enterprises.
- Sustainability consultants.

This provides commercial value without requiring the user to be subject to sophisticated ESG disclosure regimes.

---

## 22. Development Waves

| Wave | Deliverable |
|---|---|
| **SUS-00** | Research consolidation |
| **SUS-01** | Domain contract |
| **SUS-02** | Master taxonomy |
| **SUS-03** | Evidence/provenance architecture |
| **SUS-04** | Common schemas and state model |
| **SUS-05** | Sustainability data skills |
| **SUS-06** | GHG foundation |
| **SUS-07** | Scope 1/2 accounting |
| **SUS-08** | Scope 3 accounting |
| **SUS-09** | Energy skills |
| **SUS-10** | Waste/resource skills |
| **SUS-11** | Water skills |
| **SUS-12** | Financial/business-case skills |
| **SUS-13** | Sustainable operations composition |
| **SUS-14** | Procurement/supply-chain skills |
| **SUS-15** | Strategy/target skills |
| **SUS-16** | Climate-risk skills |
| **SUS-17** | Reporting adapters |
| **SUS-18** | Jurisdiction architecture |
| **SUS-19** | Canada pack |
| **SUS-20** | Environmental claims controls |
| **SUS-21** | Router |
| **SUS-22** | Specialist skillsets |
| **SUS-23** | Scenario/evaluation suite |
| **SUS-24** | Documentation/examples |
| **SUS-25** | Public v1 readiness |

The sequence is intentionally designed so that **SUS-05 through SUS-13 produce a commercially useful sustainability toolkit before the more complicated regulatory and disclosure layers are completed.**

---

## 23. Mandatory Architecture Gate

Before Codex or another implementation agent begins generating individual skills, the following waves should be treated as mandatory architecture gates:

```text
SUS-01 Domain Contract
        |
SUS-02 Master Taxonomy
        |
SUS-03 Evidence / Provenance Contract
        |
SUS-04 Common Schema / State Contract
        |
IMPLEMENTATION AUTHORIZED
```

These four contracts should stabilize:

- Domain boundaries.
- Skill taxonomy.
- Evidence requirements.
- Provenance requirements.
- Common inputs and outputs.
- Shared state.
- Naming conventions.
- Review states.
- Framework adapter contracts.
- Evaluation expectations.

This avoids producing dozens of superficially useful prompts and calculators that use incompatible units, boundaries, evidence standards, terminology, or assumptions.

---

## 24. Definition of v1.0

Sustainability Skills v1.0 is reached when an agent can reliably take a fictional or real organization through:

```text
BUSINESS DATA
      |
SUSTAINABILITY BASELINE
      |
GHG INVENTORY
      |
ENERGY / WATER / MATERIAL / WASTE ANALYSIS
      |
HOTSPOTS
      |
IMPROVEMENT OPPORTUNITIES
      |
FINANCIAL ANALYSIS
      |
TARGETS
      |
SUSTAINABILITY ROADMAP
      |
KPIs
      |
REPORTING / DISCLOSURE MAPPING
      |
EVIDENCE-BACKED OUTPUT
```

while consistently preserving:

- Provenance.
- Methodology.
- Units.
- Organizational and operational boundaries.
- Reporting periods.
- Assumptions.
- Uncertainty.
- Jurisdiction.
- Data gaps.
- Professional-review boundaries.

Completion should therefore be defined by demonstrated workflow capability and evaluation results rather than merely by the number of prompts or skills in the repository.

---

## 25. Public v1 Readiness Gate

Before the repository is considered ready for public v1 release, verify:

- [ ] Domain contract is stable and documented.
- [ ] Master taxonomy is stable.
- [ ] Evidence and provenance schema is enforced.
- [ ] Common state and I/O contracts are documented.
- [ ] Core data skills pass evaluations.
- [ ] Scope 1 and Scope 2 calculations pass known-answer tests.
- [ ] Scope 3 handling includes evidence and uncertainty controls.
- [ ] Energy, waste, water, and resource-efficiency workflows are functional.
- [ ] Business-case analysis is testable and traceable.
- [ ] Router behavior is scenario tested.
- [ ] Framework adapters are versioned.
- [ ] Jurisdiction modules are isolated from core skills.
- [ ] Canadian reference pack has source and version controls.
- [ ] Environmental claims guardrails are tested.
- [ ] Professional-review states propagate through composed workflows.
- [ ] Example workflows are reproducible.
- [ ] Documentation explains limitations and intended use.
- [ ] Security and contribution guidance is present.
- [ ] Public examples contain no confidential or proprietary data.
- [ ] v1 acceptance scenarios pass.

---

## 26. Immediate Next Development Artifact

The first implementation-ready artifact should be an **SUS-01 through SUS-04 architecture pack** containing:

1. Domain contract.
2. Complete hierarchical taxonomy.
3. Evidence and provenance schema.
4. Common input/output contract.
5. Shared state schema.
6. Skill naming convention.
7. Router contract.
8. Framework-adapter contract.
9. Jurisdiction-module contract.
10. Evaluation requirements.
11. Review and escalation states.
12. Initial repository scaffolding specification.

Once this architecture pack passes review, development can proceed into **SUS-05 Sustainability Data Skills** and the first MVP implementation waves.

---

## 27. Roadmap Summary

The project should progress through four broad stages:

### Foundation
**SUS-00 through SUS-04**

Research, domain boundaries, taxonomy, evidence architecture, and shared schemas.

### Operational MVP
**SUS-05 through SUS-13**

Data handling, GHG accounting, energy, waste, water, resources, financial analysis, and sustainable-operations composition.

### Advanced Sustainability Intelligence
**SUS-14 through SUS-22**

Supply chain, strategy, climate risk, reporting, jurisdictions, claims controls, routing, and professional skillsets.

### Validation and Release
**SUS-23 through SUS-25**

Scenario testing, documentation, examples, and public v1 readiness.

The central design objective is to create a reusable sustainability capability system that converts evidence into defensible analysis and analysis into practical business action while maintaining explicit safety, provenance, uncertainty, and professional-review boundaries.
