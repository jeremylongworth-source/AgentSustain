# Fuel CO2e source/basis evaluation

All entities, calorific values, emission factors, GWP bases and review/combustion facts are fictional. [Complete actual CLI requests and outputs](sus06-fuel-co2e.json) include ten bridge cases and four exact raw CSV-to-partial-Scope-1 handoffs. No real coefficient or default factor is supplied.

| Case | Expected result |
| --- | --- |
| 5,000 kWh LHV fuel energy, supplied 0.5 kg CO2e/kWh on matching declared basis | 2,500 kg CO2e conditional core result |
| 1,000 kWh volume-derived energy and same fictional coefficient | 500 kg CO2e |
| 5,000 kWh with supplied 0.05 kg CO2e/MJ | 900 kg CO2e; unit conversion preserves LHV |
| Missing factor | Blocked with EMISSION_FACTOR_REQUIRED |
| Factor HHV while fuel LHV | Blocked before arithmetic; no basis conversion inferred |
| Unknown combustion support | Blocked before arithmetic; delivery is not assumed combustion |
| Changed original calorific metric | Blocked source reproduction; stored total is not a fallback |
| Unfit core factor-policy confirmation | Core and aggregate blocked; original eligibility controls survive |
| Future factor source | Blocked before arithmetic |
| Ordinary-mode request with synthetic upstream fuel | Blocked; no fixture relabeling |

Nine focused tests additionally cover zero fuel with no factor, false/unknown/nonliteral combustion support, unknown/unfit heating basis, mismatched fuel/material/reference/identity/boundary/date, wrong factor source unit/version/period, edited quantity/converted report, exact standalone core equality, source hashes and original state/factors/uncertainty/open-review custody.

The raw-source composition runs the existing pinned CSV ingester, existing fuel-energy helper, new basis bridge and existing scope account as four actual CLI/helper requests with exact state handoffs. Its fictional CO2-only contribution is 2,500 kg CO2e, while an additional unresolved source with CH4/N2O coverage produces an explicit gap and partial Scope 1 status. All engineering/factor/professional requirements remain. Original CSV byte pins and embedded source instructions remain unchanged data. This is controlled author-led evaluation, not actual gas/source classification, scientific fitness or independent organization acceptance.

[The contract](../docs/fuel-co2e-contract.md) records primary parsed method context without importing defaults or original source bytes. Actual combustion, factor/technology/gas/heating interpretation, emissions completeness, statutory methods, owner/scientific/legal/assurance/reuse and independent/public-v1 requirements remain open. This interface and prior historical-task/fuel-energy changes await scoped approval. The full roadmap remains active.

[Final validation](sus06-fuel-co2e-validation.json) records 775 repository tests in 633.102 seconds, nine focused tests in 3.471 seconds and twenty architecture checks in 0.179 seconds. The [durable suite witness](sus06-fuel-co2e-suite-run.json) confirms successful completion and unchanged runtime/test/Canada/raw-CSV hashes during the run. Fourteen new actual CLI/helper cases preserve request bytes and exact source handoffs; thirteen prior full CLI/helper outputs and all 372 prior runtime/test/schema/standard/router/skill/data files remain unchanged. These author-led checks establish conditional method/source composition and compatibility, not actual scientific source fitness, complete inventory coverage or independent organization acceptance.
