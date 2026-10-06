# Approved specialist routing and explicit recipe execution

`specialist-router-0.1.0` is a separate development interface alongside the unchanged `intent-router-0.1.0`. Run `python -m scripts.run_specialist_router REQUEST.json` with the existing `route-sustainability-request` common envelope. It supports the seven initial specialist roles through source-preserving analytical invocation; it does not infer a recipe, approve scientific inputs or grant external-action authority.

## Approved capability selection

`router/specialists-0.1.json` is an explicit raw-byte SHA-256 selection. Capability content is rooted in the owner-approved Git snapshot `7bad9dd3a07069b7a99979f80fd509ad0eb40486`, which covers all seven specialist compositions. The new router/catalog itself has no scoped owner approval yet and does not inherit release approval from the selected capabilities.

The catalog records fixed canonical role/module/function mappings and LF-normalized hashes. For each role the loader independently reconstructs expected assets from actual approved Git blobs: its Python implementation, transitive repository Python imports, all shared schemas, requirements declaration, role entrypoint/manifest and referenced skill/skillset dependency files. Local import cycles are traversed once; route recipes retain their own dependency checks. The catalog cannot change the approved revision, add a role/function, omit a dependency or invent approved bytes. Path escapes, absent Git history, forged metadata or a changed catalog pin fail closed.

Selected current workspace content must match every protected role asset before invocation and again afterward. A drifted selected runtime, entrypoint, manifest or schema is unavailable; no older/unreviewed replacement is inferred. The graph checks repository-owned runtime/entrypoint content. They do not authenticate third-party installed libraries, host execution environments or the scientific meaning of input/versioned data; broader installation/compatibility acceptance remains open. Versioned framework/jurisdiction inputs continue to require the selected helper's own explicit pins and qualified applicability/rights review.

## Exact request

Parameters are `request`, `role`, `catalog_pin`, `recipe`, `result_id`. `request` is bounded original user text. `role` is `auto` or one exact canonical specialist name. `recipe` is null for planning or the complete capability-specific parameter object. The helper parameters are copied unchanged into the known selected callback; their individual contracts enforce identities, dependency order, quantities, units, source periods and review requirements. Router/selected-helper identities are distinct and fresh. No raw input is relabeled normalized, no factor or method/version is supplied from request wording, and no parameter values are generated.

| Canonical role | Original-request cue examples | Existing selected contract |
| --- | --- | --- |
| sustainable-operations | operational efficiency, factory operations, water efficiency | [Operations composition](operations-contract.md) |
| carbon-accounting | carbon accounting, GHG inventory, carbon footprint | [Carbon workflow](carbon-workflow-contract.md) |
| sustainability-manager | coordinate sustainability, organization sustainability | [Manager recipe](manager-workflow-contract.md) |
| sustainable-procurement | supplier sustainability, compare suppliers, procurement | [Procurement composition](procurement-workflow-contract.md) |
| climate-risk | physical climate, transition risk, adaptation plan | [Climate composition](climate-workflow-contract.md) |
| sustainability-business-case | compare investments, NPV, payback | [Investment composition](investment-workflow-contract.md) |
| sustainability-reporting | sustainability disclosure, framework mapping | [Reporting composition](reporting-workflow-contract.md) |

Only the original `request` supplies bounded English lexical candidates. Evidence notes, prior results, embedded source instructions and recipe text cannot choose a role. Mixed/unknown automatic intent, recognized negated analytical instructions or a caller role contradicting identified cues returns clarification with no invocation. An explicit caller-selected matching role is attributed and remains semantically unverified; other candidate intents remain visible and unhandled. This classifier is deliberately bounded and has no independent language-understanding acceptance claim.

With a null recipe, a selected available route stays partial and returns `ROUTE_RECIPE_REQUIRED`; no helper runs. A complete supplied recipe invokes the fixed approved specialist using a copy of the original state, preserving the manager's original input-context checks. A valid returned source result and original result history must agree with the selected capability. Original organization/facility/jurisdiction/boundary/period/evidence/factor records and prior review decisions cannot change. Changed runtime or source context withholds the candidate. Wrong recipe/identity/contract data returns a blocked proposal; no scope/source substitution is made.

## Results, factor requirements and review

`SPECIALIST_ROUTE` retains original request, role candidates/attribution, boundary/period, selected catalog/capability assets, installed availability, invocation status and the exact source-result hash view. `SPECIALIST_ROUTE_INPUTS` preserves complete parameters. The aggregate adds no metric and is always partial or blocked. Successful invocation does not establish workflow/organization acceptance, source fitness, current framework/legal applicability or a release-approved router.

The original state history and the selected helper's complete proposed results survive. A blocked helper remains blocked; partial/independent branch outcomes remain available with all gaps and reviews. Newly produced selected-helper `EMISSION_FACTOR_REQUIRED`/`GWP_REQUIRED` diagnostics propagate with their source result IDs; unrelated historical factor failures are not treated as selected branch outcomes. No factor is fabricated. The aggregate adds an open professional route/source review, preserves the helper's legal/engineering/assurance/owner obligations and normalizes final revision to original plus one. It writes no state file and performs no third-party contact, publication, investment adoption or deployment.

[Fictional actual CLI evidence](../evaluations/sus21-specialist-router.md) verifies all seven selections/invocations, standalone result equality, input-byte custody, mixed/negative/missing-recipe/factor cases and withholding tests for forged approval, transitive runtime drift and modified sources. Prior three-route catalog/helper and domain implementations remain unchanged. This later router/interface requires its own scoped owner review, plus broad language/semantic/behavioral/organization and platform acceptance. The earlier historical-task/fuel interfaces and all public-v1/source/method/release requirements remain open; no roadmap wave or full-goal completion follows.
