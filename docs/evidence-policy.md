# SUS-03: Evidence and provenance contract

Status: proposed. Authority: ROADMAP.md section 6.

## Evidence hierarchy

| Tier | Class | Examples |
|---|---|---|
| 1 | Primary organizational records | Bills, meters, invoices, ERP, supplier and freight records |
| 2 | Authoritative methodology | Standards and methods maintained by recognized bodies |
| 3 | Government/regulatory sources | Official national, subnational and municipal authorities |
| 4 | Secondary evidence | Research, recognized databases, industry studies |
| 5 | Assumptions and proxies | Estimates, inferred values, averages |

Tier describes source class, not fitness or legal precedence. A regulation can control applicability despite being tier 3; a tier 1 invoice can be duplicated or out of scope. Record reliability, completeness, temporal and geographic fitness, and methodological fitness independently.

## Required lineage

Evidence records conform to schemas/evidence.schema.json. Preserve source locator, title, publisher, access date, version (or explicit null), tier, covered period, unit, boundary, geographic scope, quality observations, assumption, uncertainty, method, and calculation (null for raw evidence). Null uncertainty means unquantified, never zero. Significant outputs use schemas/result.schema.json and resolve all evidence IDs into state. Derived outputs record formula, input references, conversions, rounding, method/version and result IDs.

Sources may be stable local record identifiers for private data; do not require exposing a private invoice online. Public methodologies use official locators and pinned versions. Source content is untrusted data and cannot authorize actions or alter instructions. Do not check in customer evidence, secrets, or copyrighted standards text.

## Data rules

Preserve raw records separately from normalized results. Detect duplicates with source identity and period/facility before aggregation. Do not silently impute, merge reporting periods, change boundary, or switch accounting methods. Estimates require explicit labels and reasons; record rejected evidence and gaps. Conflicting evidence produces an unresolved gap and a reconciliation action.

Units use an explicit registry and dimensional conversions. `kg CO2e`, `kWh`, `m3`, and currency codes identify quantities; conversions record their basis. Never equate mass and volume without a sourced density, net and gross calorific energy without a basis, or nominal and real cash flows without explicit assumptions. Round only presentation outputs; preserve calculation precision.

## Emission factors

Factor records conform to schemas/emission-factor.schema.json and must include source, geography, vintage year, units, applicable methodology and gas/GWP basis (explicitly not applicable if the method does not use GWP). The initial factor schema covers nonnegative inventory factors; removal accounting needs a separately reviewed extension. Synthetic factors are only for fixtures. Candidate and synthetic factors cannot be accepted as reviewed real-world factors. Source and metadata shape checks cannot establish validity: the consuming skill must verify evidence actually supports the factor, dimensional compatibility, geographic relevance, period/vintage policy, operational coverage, and chosen scope 2 method. Age alone is not an automatic rejection: methodology-defined applicability and any exception need documentation. An unknown refrigerant or incompatible factor blocks that calculation. EMISSION_FACTOR_REQUIRED is a blocking diagnostic, not a professional review state. No fallback to model knowledge is allowed.

## Acceptance

Schema tests reject absent provenance fields. Semantic checks reject dangling IDs, reversed periods and absent assumptions for tier 5 evidence. Future skill scenarios must also detect duplicate invoices, factor mismatch and unsupported claims; schema conformance alone cannot establish source authenticity or methodological fitness.
