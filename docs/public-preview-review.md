# Public-preview preparation review

Scope: a local, filtered **0.1.0-draft helper preview** and six GitHub Wiki-compatible Markdown drafts. This pass retains all SUS-00–25 requirements and distinguishes preview publication from full public-v1 readiness. It changes no existing calculation, schema, review decision, source module or factor.

Current prepared artifact: [the licensed cbafe96 receipt](../evaluations/sus25-licensed-preview-preparation.md), with exact source revision, SHA-256 and validation. It supersedes the earlier unlicensed 8cf5e45 proposal while preserving its historical evidence.

## Prepared surface

`scripts/prepare_public_preview.py` computes the selected helpers' relative-import closure without running those imports, then packages their original source and shared schemas. It adds the preview README, distribution-status notice, dependency requirement, fictional conversion example, six wiki pages and the owner-selected MIT license/contributor/security/third-party notices. The manifest records file sizes/hashes, source revision, entry points, exclusions, the verified license choice and false publication/v1/verified-security-enablement flags. Build output is restricted to a fresh directory under ignored `private-data/public-preview/`; existing files are preserved. The archive contains no Python environment or third-party binaries.

The nineteen included source files support data, energy, water, material/waste and finance helpers. They do not install agent skills or include framework/jurisdiction catalogs, emissions/GWP tables, research text, source archives, historical captures, funding/account metadata or Git history. Exclusions reduce distribution exposure without claiming those materials' rights have been approved. Preview dependency declarations do not relicense installed third-party packages.

## Validation and content review

Three package tests verify the import closure, output boundary, preservation of existing files, archive paths/duplicates, exact manifest hashes, absence of excluded trees, Markdown links, packaged imports, actual fictional conversion and invalid-conversion refusal. The initial preparation passed 66 selected tests. The later raw-input runner's full suite passed 842 tests before license-export updates; the final combined package/core/runner subset passed 70 tests afterward. Final artifact validation records the exact committed source revision and archive SHA-256 separately; historical witnesses are not relabeled as a final full run.

The proposed public content explicitly states draft status, MIT coverage for original project material, pending publication/source rights, no full v1 claim, partial scope, fictional inputs, review duties and unverified native Linux/agent discovery. GitHub private reporting is the selected route; AgentSustain setting/form/delivery remains unverified. The wiki is prepared locally; no remote wiki was opened or published. A limited credential-shape scan of the archive and a local content review are evidence with stated limits, not confidentiality, ownership or legal approval. The archive manifest and original source files make the surface reviewable.

## Decision and holds

Recommendation: **ready for owner review as a limited preview proposal; publication remains on hold**.

| Owner decision | Concrete proposed material / remaining issue |
|---|---|
| Project license and contributor terms | Resolved: exact collection-matching MIT, Copyright (c) 2026 Jeremy Longworth; compatible no-CLA/no-ownership-transfer contributor posture. Selected-content provenance and third-party rights remain separate. |
| Security contact | Resolved route: GitHub private vulnerability reporting. AgentSustain API read returned 404; setting/form/delivery verification remains open, with no enablement change or report sent. |
| Selected-content rights and confidentiality | Review the exact manifest/export, source citations and proposed original materials. Excluded frameworks/Canadian research remain unresolved in the full repository. |
| Publication surface | A filtered archive is proposed. Making the full Git repository public would expose excluded content and history; it needs a separate complete rights/content review or an approved clean publication surface. |
| Public copy and wiki | Approve the README and six local wiki pages with their limited capability claims. |
| Consequential actions | Give separate explicit authorization for push, visibility change, wiki publication and any release. This pass authorizes none of them. |

No additional agents were dispatched. Independent/domain acceptance remains limited to existing authorizations and evidence. Full framework/currentness/Canada/source/scientific/financial/legal/engineering/state reviews, broader acceptance and full public-v1 gates stay open. No PMGate site, production system, repository trust/ownership setting or third-party communication changed. If a later release is authorized, retain the exact approved export hash; withdrawal/replacement of that artifact is the bounded rollback path, with no production migration implied.
