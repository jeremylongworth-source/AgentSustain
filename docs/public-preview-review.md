# Public-preview preparation review

Scope: a local, filtered **0.1.0-draft helper preview** and six GitHub Wiki-compatible Markdown drafts. This pass retains all SUS-00–25 requirements and distinguishes preview publication from full public-v1 readiness. It changes no existing calculation, schema, review decision, source module or factor.

## Prepared surface

`scripts/prepare_public_preview.py` computes the selected helpers' relative-import closure without running those imports, then packages their original source and shared schemas. It adds the preview README, distribution-status notice, dependency requirement, fictional conversion example and six wiki pages. The manifest records file sizes/hashes, source revision, entry points, exclusions and false publication/license/v1 flags. Build output is restricted to a fresh directory under ignored `private-data/public-preview/`; existing files are preserved. The archive contains no Python environment or third-party binaries.

The nineteen included source files support data, energy, water, material/waste and finance helpers. They do not install agent skills or include framework/jurisdiction catalogs, emissions/GWP tables, research text, source archives, historical captures, funding/account metadata or Git history. Exclusions reduce distribution exposure without claiming those materials' rights have been approved. Preview dependency declarations do not relicense installed third-party packages.

## Validation and content review

Three package tests verify the import closure, output boundary, preservation of existing files, archive paths/duplicates, exact manifest hashes, absence of excluded trees, Markdown links, packaged imports, actual fictional conversion and invalid-conversion refusal. The combined preview/data/state/energy/water/resource/finance run passed 66 tests. Final artifact validation records the exact committed source revision and archive SHA-256 separately; the earlier 835-test full-suite witness is not relabeled as a current full run.

The proposed public content explicitly states draft status, pending license/publication, no full v1 claim, partial scope, fictional inputs, review duties and unverified native Linux/agent discovery. The wiki is prepared locally; no remote wiki was opened or published. A limited credential-shape scan of the archive and a local content review are evidence with stated limits, not confidentiality, ownership or legal approval. The archive manifest and original source files make the surface reviewable.

## Decision and holds

Recommendation: **ready for owner review as a limited preview proposal; publication remains on hold**.

| Owner decision | Concrete proposed material / remaining issue |
|---|---|
| Project license and contributor terms | No LICENSE is added or selected. Review original helper/schema/docs authorship and choose the distribution terms. |
| Security contact | Select a private reporting address/channel and maintainer process before public sharing; no account or email is invented. |
| Selected-content rights and confidentiality | Review the exact manifest/export, source citations and proposed original materials. Excluded frameworks/Canadian research remain unresolved in the full repository. |
| Publication surface | A filtered archive is proposed. Making the full Git repository public would expose excluded content and history; it needs a separate complete rights/content review or an approved clean publication surface. |
| Public copy and wiki | Approve the README and six local wiki pages with their limited capability claims. |
| Consequential actions | Give separate explicit authorization for push, visibility change, wiki publication and any release. This pass authorizes none of them. |

No additional agents were dispatched. Independent/domain acceptance remains limited to existing authorizations and evidence. Full framework/currentness/Canada/source/scientific/financial/legal/engineering/state reviews, broader acceptance and full public-v1 gates stay open. No PMGate site, production system, repository trust/ownership setting or third-party communication changed. If a later release is authorized, retain the exact approved export hash; withdrawal/replacement of that artifact is the bounded rollback path, with no production migration implied.
