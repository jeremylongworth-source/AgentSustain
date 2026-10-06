# Organization workflow acceptance

This artifact supports maintainers and owner reviewers assessing ROADMAP section 24's complete organization sequence. `organization-acceptance-0.1.0` exercises the existing source and manager helpers against a second fictional dataset and a separately declared answer key. It is an author-led mechanical acceptance scenario. It does not approve scientific, legal, financial, source, independent agent/organization or release decisions.

Run from a complete checkout with validation dependencies installed:

```text
python -m scripts.run_organization_acceptance examples/organization-acceptance.json examples/organization-acceptance-oracle.json
```

The command reads inputs and prints a report; it writes no shared state or source files. Exit 0 means every controlled-scenario check passed, exit 1 means its declared expected behavior was not matched, and exit 2 means invalid inputs. Real-source mode is refused by this evaluation utility. A negative source/factor case appropriately fails the supported-dataset answer key; its refusal/branch-preservation behavior is checked separately in tests and saved CLI captures.

## Inputs and known answers

[The case](../examples/organization-acceptance.json) provides an empty normalized history, an explicitly fictional supplied factor registry, a pinned [second organization CSV](../data/inputs/fictional-acceptance-organization.csv), declared per-record source classifications and the existing manager recipe. The parser produces eighteen records, retaining raw rows and model assumptions. Observed meter/log records declare tier 1; hypothetical model inputs declare tier 5. The document keeps its own declared tier and publisher identity. These classifications are supplied judgments with professional review open, never source authentication.

[The separate answer key](../examples/organization-acceptance-oracle.json) declares values before comparing the workflow output: 2,400 kWh plus 0.6 MWh gives 3,000 kWh; 20,000 L plus 10 m3 gives 30 m3; 1.2 t plus 600 kg plus 200 kg gives 2,000 kg waste; material consumption is 4,000 kg. The explicitly fictional supplied 0.5 kg CO2e/kWh factor yields a partial 1,500 kg CO2e inventory. No real factor is imported. Five hundred equivalent service units give 6 kWh/count and a proposed 20% endpoint of 4.8 kWh/count in 2030. The separately modeled cash flows give `-2000 + 1100/1.1 + 1210/1.1^2 = 0 CAD`. Zero NPV is a test result, not an investment recommendation or proof of physical benefit attribution.

## Required checks

Given the declared fictional case, when the source-to-manager pipeline runs, the following results must be observable. Evidence is the complete output plus its labeled check results in [the actual CLI captures](../evaluations/sus23-organization-acceptance.json).

| ID | Required behavior / pass evidence |
|---|---|
| ORG-01 | Eighteen pinned business records import with source authentication false |
| ORG-02 | Sustainability baseline matches the declared 3,000 kWh answer |
| ORG-03 | Inventory matches 1,500 kg CO2e and remains partial; omitted scopes are not zero |
| ORG-04 | Energy, water, materials and waste match separate unit-bearing answers |
| ORG-05 | Selected inventory hotspot keeps partial-coverage qualification |
| ORG-06 | Four sourced opportunity candidates remain proposed; implementation is unauthorized |
| ORG-07 | Explicit modeled cash flows match 0 CAD NPV without financial approval |
| ORG-08 | Target matches 4.8 kWh/count in its distinct 2030 period |
| ORG-09 | Roadmap keeps unresolved resource/delivery conditions and no funding/implementation authority |
| ORG-10 | KPI definitions resolve the declared baseline and equivalent-service denominator |
| ORG-11 | Historical disclosure candidates stay partial without conformity verification |
| ORG-12 | Every produced source result has an exact current hash view and all eight manager stages remain traced |
| CUST-01 | Initial state and pinned source bytes remain unchanged |
| CUST-02 | The exact normalized candidate and its complete original result history survive |
| CUST-03 | Imported/prior evidence and its uncertainty remain unchanged |
| CUST-04 | Supplied factors remain unchanged; none are created |
| CUST-05 | Jurisdictions, facilities, boundary and reporting period remain unchanged |
| CUST-06 | Assumptions and original gaps remain with conditional outputs |
| CUST-07 | Existing review decisions survive without resolution |
| CUST-08 | Ingestion and manager each make one atomic proposal: original revision +2 |
| CUST-09 | Physical, monetary and future quantities have no combined cross-domain total |
| CUST-10 | Source, coverage, finance attribution, feasibility, progress, funding, conformity, publication and readiness flags stay false with reviews open |

## Refusal and safety checks

Given an absent selected factor, emissions must remain withheld with `EMISSION_FACTOR_REQUIRED`, while independent physical and financial branches can survive. Given [the blank-water source](../data/inputs/fictional-acceptance-missing-water.csv), water is withheld rather than turned into zero, while supported energy/inventory remain. A wrong source checksum stops before manager invocation. Source instructions to discard reviews or publish a certified claim remain inert data. Real-source mode is outside this fixture utility's scope. Tests also require complete classification coverage, typed tier declarations, whole-import rollback, and bounded known-fictional/renamed-copy protection.

## Evidence limits and optional quality signals

The answer key is declared separately from computed output, but its author is the same development agent. Agreement cannot establish independent expert/agent acceptance, actual source fitness, organization completeness, standardized reporting conformity or reliable behavior on another platform. Successful selected arithmetic does not settle the roadmap's twenty public-v1 checks. Other optional evidence includes alternate platform/interpreter runs, independent reviewer notes and richer source-format scenarios; their absence is not hidden by this controlled report.

The current manager/specialist contracts and capability pin remain unchanged. The optional `business-csv-ingestion-0.2.0` classification extension and this later evaluation interface require scoped owner review. Whole-release data/rights checks, active framework/jurisdiction methods, scientific/legal/engineering reviews, independent organization acceptance, license/security/contribution decisions and public-v1 requirements remain open. No push, publication, dispatch, filing, release or third-party communication is authorized.
