# SUS-02: Master hierarchical taxonomy

Status: proposed. All roadmap-listed atomic skills are enumerated below; none is implemented. Taxonomy family IDs and wave IDs are separate namespaces. See naming-conventions.md for overlapping names.

Hierarchy: family -> capability group -> skill. Skill families without named atomic skills retain their roadmap-defined capability groups; new names require review.

## SUS-01: Sustainability Strategy (`strategy`)

### Analysis and calculations

- `assess-sustainability-maturity`
- `evaluate-target-feasibility`

### Data, evidence and classification

- `identify-material-sustainability-issues`
- `map-stakeholders`
- `identify-sustainability-risks`
- `identify-sustainability-opportunities`

### Planning and composition

- `establish-baseline`
- `define-kpis`
- `develop-target`
- `build-sustainability-strategy`
- `build-transition-plan`

## SUS-02: GHG / Carbon (`carbon`)

### Planning and composition

- `define-ghg-inventory-boundary`
- `build-ghg-inventory`

### Data, evidence and classification

- `identify-emission-sources`
- `classify-scope-1-emissions`
- `classify-scope-2-emissions`
- `classify-scope-3-emissions`
- `select-emission-factor`
- `validate-emission-factor`
- `identify-ghg-data-gaps`
- `identify-emission-hotspots`

### Analysis and calculations

- `calculate-co2e`
- `calculate-scope-1`
- `calculate-location-based-scope-2`
- `calculate-market-based-scope-2`
- `calculate-scope-3-category`
- `estimate-missing-activity-data`
- `assess-ghg-data-quality`
- `compare-ghg-inventories`

## SUS-03: Energy (`energy`)

### Planning and composition

- `build-energy-baseline`

### Analysis and calculations

- `calculate-energy-intensity`
- `analyze-energy-usage`
- `estimate-energy-savings`
- `prioritize-energy-projects`

### Data, evidence and classification

- `detect-energy-hotspots`
- `identify-efficiency-opportunities`

## SUS-04: Resource Efficiency (`resources`)

### Analysis and calculations

- `analyze-material-consumption`
- `calculate-material-intensity`

### Data, evidence and classification

- `identify-material-loss`
- `identify-resource-efficiency-opportunities`

## SUS-05: Waste (`waste`)

### Planning and composition

- `build-waste-baseline`

### Data, evidence and classification

- `classify-waste-streams`
- `identify-waste-hotspots`
- `identify-waste-reduction-opportunities`

### Analysis and calculations

- `calculate-diversion-rate`
- `analyze-waste-cost`

## SUS-06: Circularity (`circularity`)

Circular practice assessment, reuse and recovery, circular business models. Atomic names are not specified in the roadmap and will be designed in the corresponding wave.

## SUS-07: Water (`water`)

### Planning and composition

- `build-water-baseline`

### Analysis and calculations

- `calculate-water-intensity`
- `assess-water-dependency`

### Data, evidence and classification

- `identify-water-hotspots`
- `identify-water-efficiency-opportunities`

## SUS-08: Sustainable Procurement (`procurement`)

### Planning and composition

- `screen-supplier-sustainability-risk`
- `build-supplier-questionnaire`
- `develop-supplier-improvement-plan`

### Analysis and calculations

- `evaluate-supplier-response`
- `score-supplier-sustainability`
- `compare-suppliers`
- `evaluate-low-carbon-procurement-option`

### Data, evidence and classification

- `identify-supplier-data-gaps`

## SUS-09: Supply Chain (`supply-chain`)

### Data, evidence and classification

- `map-supply-chain-emissions`
- `identify-scope-3-hotspots`

### Analysis and calculations

- `prioritize-supplier-engagement`

## SUS-10: Climate Risk (`climate-risk`)

### Data, evidence and classification

- `identify-climate-hazards`
- `map-assets-to-hazards`
- `identify-adaptation-options`
- `identify-policy-risk`
- `identify-market-risk`
- `identify-technology-risk`
- `identify-reputation-risk`

### Analysis and calculations

- `assess-exposure`
- `assess-vulnerability`
- `score-physical-risk`
- `assess-transition-exposure`
- `prioritize-climate-risks`

### Planning and composition

- `build-climate-risk-register`
- `develop-climate-resilience-plan`

## SUS-11: Reporting & Disclosure (`reporting`)

Disclosure mapping, gap analysis, evidence mapping, draft disclosures. Initial SUS-17 atomic names are `map-framework-disclosures` and `compare-framework-mappings`; full framework/domain coverage remains open.

## SUS-12: Compliance Intelligence (`compliance`)

Jurisdiction facts, applicability screening, rule/version monitoring. Atomic names are not specified in the roadmap and will be designed in the corresponding wave.

## SUS-13: Environmental Claims (`claims`)

Claim classification, evidence adequacy, boundary/method/period checks, substantiation states. Atomic names are not specified in the roadmap and will be designed in the corresponding wave.

## SUS-14: Sustainable Finance (`finance`)

### Analysis and calculations

- `calculate-sustainability-project-cost`
- `calculate-operating-savings`
- `calculate-simple-payback`
- `calculate-roi`
- `calculate-npv`
- `calculate-irr`
- `model-energy-price-scenario`
- `model-carbon-price-scenario`
- `model-resource-cost-scenario`
- `calculate-marginal-abatement-cost`
- `compare-sustainability-projects`
- `rank-sustainability-investments`

### Planning and composition

- `build-sustainability-business-case`

## SUS-15: Metrics & Data (`metrics`)

### Data, evidence and classification

- `normalize-sustainability-data`
- `validate-sustainability-data`
- `classify-evidence-quality`
- `detect-data-gaps`
- `normalize-units`
- `normalize-reporting-period`
- `map-organizational-boundary`

### Planning and composition

- `build-sustainability-baseline`

### Analysis and calculations

- `calculate-sustainability-kpi`
- `compare-period-performance`

## SUS-16: Implementation (`implementation`)

### Planning and composition

- `build-implementation-roadmap`
- `assign-accountability`

## Cross-family composition

Engagement is a tag for stakeholder and supplier work, not an extra family. Reporting standards live in `standards/`; compliance jurisdiction modules live in `standards/jurisdictions/`. Router behavior is specified separately. Professional skillsets are sustainability-manager, carbon-accounting, sustainable-operations, sustainable-procurement, climate-risk, sustainability-reporting, and sustainability-business-case. Dependencies require approved manifests when implemented.

## Coverage

All names from ROADMAP.md sections 7-13 are assigned once. Other sections define modules, workflows or domains rather than additional named atomic skills. Public v1 is evaluated by demonstrated capabilities, not this inventory count.
