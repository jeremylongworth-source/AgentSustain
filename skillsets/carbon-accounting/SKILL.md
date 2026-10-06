---
name: carbon-accounting
description: Compose evidenced carbon calculations, separate scope accounts, selected inventories, comparisons and hotspots while preserving missing factors, coverage and assurance review.
---

# Carbon accounting

Use the [workflow contract](../../docs/carbon-workflow-contract.md) and [development dependency manifest](manifest.json). This subsequent specialist interface awaits scoped owner review; its dependency inventory does not activate a production workflow or establish independent reliability.

Inspect validated organization/boundary/reporting state, activity records, factor/source review, units, method and GWP basis before selecting analytical steps. Missing defensible factors must remain `EMISSION_FACTOR_REQUIRED`; supply no default factor or gas conversion. Use the exact existing [GHG foundation](../../docs/ghg-foundation-contract.md), [Scope 1/2](../../docs/scope-1-2-contract.md) and [Scope 3/inventory](../../docs/scope-3-inventory-contract.md) methods. Declared source or category coverage remains a supplied judgment. Identify unresolved exclusions, overlaps, uncertainty and source/professional/assurance requirements.

Invoke `run_carbon_workflow(state, parameters)` or `python -m scripts.run_carbon_workflow request.json` with `skill=carbon-accounting`. Select explicit acyclic prerequisites and fresh result IDs; produced sources must name their producing step as an ancestor. The runner invokes existing helpers unchanged. An explicitly blocked prerequisite records a blocked dependent step without running its helper; independent branches may continue. Partial sources remain qualified and are checked by the downstream domain method. Each synthetic step must opt into boolean fixture mode individually.

Select inventory, hotspot and comparison outputs separately. Retain location-based and market-based accounts as alternatives; never add them together or sum an inventory with its own scopes, leaves or hotspot shares. Keep selected subtotals, unknown scopes/categories, biogenic disclosures and credits/removals distinct. An observed comparable change supplies no causal project reduction or claim approval. Return original source results, evidence, methods, units, periods, boundary, uncertainty, gaps and open reviews in the common result and atomic candidate state. The aggregate emits no duplicate numeric total.

The workflow registers open accounting and assurance review requirements. It does not authenticate professional judgments, certify an inventory, establish a statutory total, resolve reviews, grant publication authority, write a state file, push a repository or contact external parties. Report incomplete coverage and unresolved source/method prerequisites plainly. Broader organization evaluation and specialist/router/release gates remain open.
