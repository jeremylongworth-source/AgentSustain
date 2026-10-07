# AgentSustain approval checklist — October 7, 2026

**Review proposal only. No item below is approved by preparing this checklist.**

Review snapshot: `90f0273c4195fe3ff0898eb76cfc038fae0ee1e4`. Preview source: `cbafe96c9ca91c1dafccfda499dc6e463b29d14d`. Private remote/main remains `56de36e`; newer changes are local.

## Exact review surfaces

| ID | Scope | SHA-256 |
|---|---|---|
| P | 40-file `0.1.0-draft` [archive](../private-data/public-preview/cbafe96/AgentSustain-preview-0.1.0-draft.zip), including 19 helpers, six schemas, six wiki pages and MIT/policy notices | `398dee8f84733254f55a29f4e83ddb3082808d020da72a69a99757c7d0b62f7a` |
| W | Six wiki pages at cbafe96: Home, Getting-started, Preview-scope, Evidence-and-review, Validation, Release-decisions | `442ba11d37cf2f2552bf61130b4710095fefbfd4f9eb5750f28db1749831af65` |
| R | `workflow-example-0.1.0`: two runner files, contract, tests, input bundle and two execution/suite witnesses at cbafe96 | `694e5654f4afc6d7e4ef8715cb327d5c55874391e27278223ee0410503ff2657` |

W/R are set hashes of sorted UTF-8 JSON path-to-file-SHA maps. [The current verification record](../evaluations/sus25-approval-checklist-verification-2026-10-07.json) contains every individual file hash, Git history and the hash method. Any content change requires a revised review surface.

## Already satisfied or safely checked

- **Owner choices:** exact collection MIT license, Copyright (c) 2026 Jeremy Longworth, verified against seven pinned repositories; GitHub private reporting is the selected route. [Decision/evidence](collection-license-security-decision.md).
- **Current artifact integrity:** 40 archive entries/39 payload pins, six unchanged wiki pages, 25 code/schema history records matching cbafe96, and 430 unchanged files in the final tested source scope. Actual October 7 conversion returned 2,000 kWh with input bytes preserved.
- **Existing validation:** 842 full tests before final license-exporter updates; 70 final subset tests afterward; four prior actual archive smoke/refusal executions and nine local-link checks. No new full suite or independent evaluation ran today.
- **Distribution exclusions:** no standards/jurisdiction catalogs, research/raw archives, emissions/GWP/reference tables, historical captures, private data, skill/router assets, account/funding metadata or Git history in P. The sole example is the explicit fictional 2 MWh conversion.
- **Reporting check:** authenticated AgentSustain API read again returned **404**; repository remains private. This proves neither enabled nor disabled status. Signed-in form, delivery and notification remain unverified. No setting or report changed.

## Decisions for Jeremy

| ID / exact question | Evidence and recommendation | What approval would mean |
|---|---|---|
| A1 — **Approve continued local development of runner R under its stated fixture-only contract?** | [Contract](workflow-example-contract.md), [runner evidence](../evaluations/sus24-workflow-example.md). Recommend approval for bounded reproduction with qualified/blocked outputs and reviews preserved. | Scoped development-interface approval at cbafe96 only; no professional, source, acceptance or release sign-off. |
| A2 — **After reviewing provenance and confidentiality, confirm you have permission to distribute the selected contents of P, or identify exclusions still needed?** | Current verification supplies Git lineage, byte agreement and citations; it does not prove ownership/originality or legal clearance. Recommend the filtered surface, subject to owner provenance review and any qualified advice needed. | Owner confirmation for selected material only. Omitted standards/research and the full repository/history remain unresolved. |
| A3 — **Approve P's README/limitations and the six wiki pages W as the proposed public-preview copy?** | [Preview copy](public-preview.md), [wiki](../wiki/Home.md), [review proposal](public-preview-review.md). Recommend the limited helper-preview wording, not a full skills-library or v1 claim. | Content approval for these hashes; does not publish them or establish v1 readiness. |
| A4 — **Use a clean filtered publication surface while keeping the full development repository/history private? If yes, specify the destination; otherwise hold publication.** | P excludes material still present in the full repository/history. Recommend clean filtered export rather than changing current repository visibility. | Publication-plan approval only. Push, new remote creation, visibility, wiki publication and release require explicit action authorization. |
| A5 — **After choosing the public destination, authorize a separately scoped GitHub private-reporting enablement/verification step, or keep it pending?** | [Security policy](../SECURITY.md), current API 404 evidence. Recommend verified operational reporting before public sharing; no test report unless separately authorized. | Permission for a later named setting step, not immediate execution under this checklist; form/delivery evidence cannot be inferred from setting enablement. |

Suggested response: **A1 approve/hold; A2 confirm/list exclusions; A3 approve/list edits; A4 clean export + destination/hold; A5 authorize later scoped step/hold.**

**Not cleared by these answers:** qualified scientific/engineering/financial/legal/source/state reviews, excluded third-party rights, broader independent/domain acceptance and full SUS-00–25/public-v1 gates. No further agent, push, publication, site, account/trust change or external contact is authorized by this document. Recommendation: ready for owner decisions; publication remains on hold.
